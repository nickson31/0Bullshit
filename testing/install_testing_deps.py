#!/usr/bin/env python3
"""
🔧 TESTING DEPENDENCIES INSTALLER
=================================

Script para instalar automáticamente todas las dependencias necesarias
para ejecutar los tests del backend de 0Bullshit.

Uso:
    python testing/install_testing_deps.py
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Ejecutar comando con manejo de errores"""
    print(f"🔍 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - Success")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - Failed")
        print(f"Error: {e.stderr}")
        return False

def check_python_version():
    """Verificar versión de Python"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ is required")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
    return True

def install_dependencies():
    """Instalar dependencias de testing"""
    print("📦 Installing testing dependencies...")
    
    # Dependencias básicas del proyecto
    basic_deps = [
        "fastapi==0.104.1",
        "uvicorn==0.24.0",
        "httpx==0.24.1",
        "websockets==12.0",
        "python-dotenv==1.0.0",
        "pydantic==2.5.2"
    ]
    
    # Dependencias específicas de testing
    testing_deps = [
        "pytest==7.4.3",
        "pytest-asyncio==0.21.1",
        "pytest-xdist==3.3.1",
        "pytest-timeout==2.2.0",
        "pytest-mock==3.12.0"
    ]
    
    all_deps = basic_deps + testing_deps
    
    for dep in all_deps:
        if not run_command(f"pip install {dep}", f"Installing {dep.split('==')[0]}"):
            return False
    
    return True

def create_env_file():
    """Crear archivo .env.testing si no existe"""
    env_file = Path("testing/.env.testing")
    example_file = Path("testing/.env.testing.example")
    
    if not env_file.exists() and example_file.exists():
        print("📝 Creating testing environment file...")
        try:
            with open(example_file, 'r') as src, open(env_file, 'w') as dst:
                dst.write(src.read())
            print("✅ Created testing/.env.testing from example")
            print("⚠️  Please edit testing/.env.testing with your configuration")
            return True
        except Exception as e:
            print(f"❌ Failed to create .env.testing: {e}")
            return False
    elif env_file.exists():
        print("✅ testing/.env.testing already exists")
        return True
    else:
        print("⚠️  No .env.testing.example found, creating basic configuration...")
        try:
            with open(env_file, 'w') as f:
                f.write("""# Basic testing configuration
API_BASE_URL=http://localhost:8000
TEST_USER_EMAIL=test@0bullshit.com
TEST_USER_PASSWORD=TestPassword123!
TESTING_MODE=true
""")
            print("✅ Created basic testing/.env.testing")
            return True
        except Exception as e:
            print(f"❌ Failed to create basic .env.testing: {e}")
            return False

def verify_installation():
    """Verificar que la instalación fue exitosa"""
    print("🔍 Verifying installation...")
    
    try:
        import httpx
        import websockets
        import pytest
        from dotenv import load_dotenv
        print("✅ All testing dependencies are available")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return False

def main():
    """Función principal"""
    print("🧪 TESTING DEPENDENCIES INSTALLER")
    print("=" * 50)
    
    # Verificar Python
    if not check_python_version():
        sys.exit(1)
    
    # Cambiar al directorio raíz del proyecto
    root_dir = Path(__file__).parent.parent
    os.chdir(root_dir)
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Instalar dependencias
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Crear archivo de entorno
    if not create_env_file():
        print("⚠️  Environment file creation had issues, but continuing...")
    
    # Verificar instalación
    if not verify_installation():
        print("❌ Installation verification failed")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("🎉 INSTALLATION COMPLETED SUCCESSFULLY!")
    print("=" * 50)
    print("\n📋 Next steps:")
    print("1. Make sure your backend is running: python main.py")
    print("2. Edit testing/.env.testing with your configuration")
    print("3. Run tests: python testing/cursor_test_runner.py --all")
    print("\n✨ You're ready to test your SaaS!")

if __name__ == "__main__":
    main()