#!/usr/bin/env python3
"""
🚀 AUTO START BACKEND AND TEST
==============================

Script que automáticamente:
1. Verifica si el backend está corriendo
2. Si no está corriendo, lo inicia automáticamente
3. Ejecuta los tests completos
4. Opcionalmente detiene el backend al finalizar

Perfecto para ejecución desde Cursor sin intervención manual.

Uso:
    python testing/start_backend_and_test.py
    python testing/start_backend_and_test.py --quick
    python testing/start_backend_and_test.py --feature auth
"""

import asyncio
import subprocess
import sys
import time
import signal
import argparse
import os
from pathlib import Path
from typing import Optional

# Agregar directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

try:
    import httpx
    from testing.cursor_test_runner import CursorTestRunner
    from testing.config_testing import TestingConfig
except ImportError as e:
    print(f"❌ Missing dependencies: {e}")
    print("Please run: python testing/install_testing_deps.py")
    sys.exit(1)

class BackendManager:
    """Gestor automático del backend para testing"""
    
    def __init__(self):
        self.backend_process: Optional[subprocess.Popen] = None
        self.backend_started_by_us = False
        self.backend_url = TestingConfig.API_BASE_URL
    
    async def is_backend_running(self) -> bool:
        """Verificar si el backend está corriendo"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.backend_url}/health")
                return response.status_code == 200
        except:
            return False
    
    def start_backend(self) -> bool:
        """Iniciar el backend automáticamente"""
        print("🚀 Starting backend server...")
        
        try:
            # Cambiar al directorio raíz
            os.chdir(ROOT_DIR)
            
            # Iniciar backend en segundo plano
            self.backend_process = subprocess.Popen(
                [sys.executable, "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.backend_started_by_us = True
            print(f"✅ Backend started with PID: {self.backend_process.pid}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start backend: {e}")
            return False
    
    async def wait_for_backend_ready(self, timeout: int = 60) -> bool:
        """Esperar a que el backend esté listo"""
        print("⏳ Waiting for backend to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if await self.is_backend_running():
                print("✅ Backend is ready!")
                return True
            
            # Verificar si el proceso sigue corriendo
            if self.backend_process and self.backend_process.poll() is not None:
                print("❌ Backend process died")
                stdout, stderr = self.backend_process.communicate()
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")
                return False
            
            await asyncio.sleep(2)
            print("   Still waiting...")
        
        print(f"❌ Backend not ready after {timeout} seconds")
        return False
    
    def stop_backend(self):
        """Detener el backend si lo iniciamos nosotros"""
        if self.backend_process and self.backend_started_by_us:
            print("🛑 Stopping backend server...")
            try:
                # Intentar terminar gracefully
                self.backend_process.terminate()
                
                # Esperar un poco
                try:
                    self.backend_process.wait(timeout=10)
                    print("✅ Backend stopped gracefully")
                except subprocess.TimeoutExpired:
                    # Si no se detiene, forzar
                    print("⚠️  Forcing backend shutdown...")
                    self.backend_process.kill()
                    self.backend_process.wait()
                    print("✅ Backend force stopped")
                    
            except Exception as e:
                print(f"⚠️  Error stopping backend: {e}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_backend()

async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Auto-start backend and run tests')
    parser.add_argument('--quick', action='store_true', help='Run quick tests only')
    parser.add_argument('--feature', type=str, help='Test specific feature')
    parser.add_argument('--keep-backend', action='store_true', help='Keep backend running after tests')
    parser.add_argument('--no-auto-start', action='store_true', help='Don\'t auto-start backend')
    
    args = parser.parse_args()
    
    print("🧪 AUTO BACKEND MANAGER & TEST RUNNER")
    print("=" * 60)
    
    with BackendManager() as backend_mgr:
        try:
            # Verificar si el backend ya está corriendo
            backend_running = await backend_mgr.is_backend_running()
            
            if backend_running:
                print("✅ Backend is already running")
            elif args.no_auto_start:
                print("❌ Backend is not running and auto-start is disabled")
                print("Please start the backend manually: python main.py")
                sys.exit(1)
            else:
                # Iniciar backend automáticamente
                if not backend_mgr.start_backend():
                    print("❌ Failed to start backend")
                    sys.exit(1)
                
                # Esperar a que esté listo
                if not await backend_mgr.wait_for_backend_ready():
                    print("❌ Backend failed to start properly")
                    sys.exit(1)
            
            # Ejecutar tests
            print("\n🧪 STARTING TESTS")
            print("=" * 40)
            
            runner = CursorTestRunner(verbose=True)
            
            success = False
            if args.quick:
                success = await runner.run_quick_test()
            elif args.feature:
                success = await runner.run_feature_test(args.feature)
            else:
                success = await runner.run_all_tests()
            
            # Resultado final
            print("\n" + "=" * 60)
            if success:
                print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
                exit_code = 0
            else:
                print("🚨 SOME TESTS FAILED - CHECK RESULTS ABOVE")
                exit_code = 1
            
            # Decidir si mantener el backend corriendo
            if args.keep_backend and backend_mgr.backend_started_by_us:
                print("🔄 Keeping backend running as requested...")
                print(f"   Backend PID: {backend_mgr.backend_process.pid}")
                print("   To stop manually: kill {backend_mgr.backend_process.pid}")
                backend_mgr.backend_started_by_us = False  # No lo detengas automáticamente
            elif backend_mgr.backend_started_by_us:
                print("🛑 Stopping backend (started by test runner)...")
            else:
                print("ℹ️  Backend was already running, leaving it as is...")
            
            print("=" * 60)
            sys.exit(exit_code)
            
        except KeyboardInterrupt:
            print("\n🛑 Tests interrupted by user")
            sys.exit(130)
        except Exception as e:
            print(f"\n❌ Test runner failed: {e}")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())