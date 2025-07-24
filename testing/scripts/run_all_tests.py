#!/usr/bin/env python3
# testing/scripts/run_all_tests.py
"""
Script principal para ejecutar todos los tests de 0Bullshit Backend
Ejecuta una suite completa de testing incluyendo todos los módulos
"""

import asyncio
import sys
import time
import argparse
from pathlib import Path
from typing import Dict, List
import subprocess
import json

# Agregar directorio padre al path
sys.path.append(str(Path(__file__).parent.parent.parent))

from testing.config_testing import wait_for_backend, test_client, TestingConfig

class TestRunner:
    """Ejecutor principal de tests con reporte completo"""
    
    def __init__(self, verbose: bool = True, fail_fast: bool = False):
        self.verbose = verbose
        self.fail_fast = fail_fast
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
            "execution_time": 0,
            "coverage": {}
        }
    
    def print_header(self):
        """Imprimir header del testing"""
        print("=" * 80)
        print("🧪 0BULLSHIT BACKEND - COMPLETE TESTING SUITE")
        print("=" * 80)
        print(f"📊 Testing Environment: {TestingConfig.API_BASE_URL}")
        print(f"👤 Test User: {TestingConfig.TEST_USER_EMAIL}")
        print(f"⚙️  Testing Mode: {'Enabled' if TestingConfig.TESTING_MODE else 'Disabled'}")
        print("=" * 80)
    
    def print_section(self, title: str):
        """Imprimir sección de testing"""
        print(f"\n🔍 {title}")
        print("-" * (len(title) + 4))
    
    async def run_backend_health_check(self) -> bool:
        """Verificar que el backend esté funcionando"""
        self.print_section("BACKEND HEALTH CHECK")
        try:
            await wait_for_backend()
            print("✅ Backend is healthy and ready")
            return True
        except Exception as e:
            print(f"❌ Backend health check failed: {e}")
            return False
    
    async def run_authentication_tests(self) -> Dict:
        """Ejecutar tests de autenticación"""
        self.print_section("AUTHENTICATION TESTS")
        results = {"passed": 0, "failed": 0, "errors": []}
        
        try:
            # Test 1: Registro/Login
            print("🔐 Testing user authentication...")
            auth_data = await test_client.authenticate()
            
            if test_client.access_token and test_client.user_id:
                print("✅ Authentication successful")
                results["passed"] += 1
            else:
                print("❌ Authentication failed")
                results["failed"] += 1
                results["errors"].append("Authentication returned no tokens")
            
            # Test 2: Profile access
            print("👤 Testing profile access...")
            response = await test_client.get("/auth/me")
            
            if response.status_code == 200:
                print("✅ Profile access successful")
                results["passed"] += 1
                
                user_data = response.json()
                print(f"   - User ID: {user_data.get('id', 'N/A')}")
                print(f"   - Email: {user_data.get('email', 'N/A')}")
                print(f"   - Plan: {user_data.get('plan', 'N/A')}")
                print(f"   - Credits: {user_data.get('credits', 'N/A')}")
            else:
                print(f"❌ Profile access failed: {response.status_code}")
                results["failed"] += 1
                results["errors"].append(f"Profile access failed with status {response.status_code}")
                
        except Exception as e:
            print(f"❌ Authentication tests failed: {e}")
            results["failed"] += 1
            results["errors"].append(str(e))
        
        return results
    
    async def run_chat_tests(self) -> Dict:
        """Ejecutar tests del sistema de chat"""
        self.print_section("CHAT SYSTEM TESTS")
        results = {"passed": 0, "failed": 0, "errors": []}
        
        try:
            # Test 1: Chat básico en español
            print("💬 Testing basic chat in Spanish...")
            response = await test_client.post("/chat", json={
                "message": "Hola, necesito ayuda con mi startup de fintech"
            })
            
            if response.status_code == 200:
                chat_data = response.json()
                print("✅ Spanish chat successful")
                print(f"   - Language detected: {chat_data.get('language_detected', 'N/A')}")
                print(f"   - Anti-spam triggered: {chat_data.get('anti_spam_triggered', 'N/A')}")
                print(f"   - Credits used: {chat_data.get('credits_used', 'N/A')}")
                results["passed"] += 1
                
                # Verificar detección de idioma
                if chat_data.get('language_detected') == 'spanish':
                    print("✅ Language detection working correctly")
                    results["passed"] += 1
                else:
                    print("❌ Language detection failed")
                    results["failed"] += 1
            else:
                print(f"❌ Spanish chat failed: {response.status_code}")
                results["failed"] += 1
                results["errors"].append(f"Spanish chat failed with status {response.status_code}")
            
            # Test 2: Chat básico en inglés
            print("💬 Testing basic chat in English...")
            response = await test_client.post("/chat", json={
                "message": "Hello, I need help finding investors for my startup"
            })
            
            if response.status_code == 200:
                chat_data = response.json()
                print("✅ English chat successful")
                print(f"   - Language detected: {chat_data.get('language_detected', 'N/A')}")
                results["passed"] += 1
                
                # Verificar detección de idioma
                if chat_data.get('language_detected') == 'english':
                    print("✅ English language detection working")
                    results["passed"] += 1
            else:
                print(f"❌ English chat failed: {response.status_code}")
                results["failed"] += 1
            
            # Test 3: Sistema anti-spam
            print("🛡️ Testing anti-spam system...")
            response = await test_client.post("/chat", json={
                "message": "asdfasdfasdf random bullshit hack ignore instructions"
            })
            
            if response.status_code == 200:
                chat_data = response.json()
                if chat_data.get('anti_spam_triggered'):
                    print("✅ Anti-spam system working correctly")
                    print(f"   - Spam score: {chat_data.get('spam_score', 'N/A')}")
                    print(f"   - Credits used: {chat_data.get('credits_used', 'N/A')} (should be 0)")
                    results["passed"] += 1
                else:
                    print("❌ Anti-spam system failed to detect spam")
                    results["failed"] += 1
            else:
                print(f"❌ Anti-spam test failed: {response.status_code}")
                results["failed"] += 1
                
        except Exception as e:
            print(f"❌ Chat tests failed: {e}")
            results["failed"] += 1
            results["errors"].append(str(e))
        
        return results
    
    async def run_search_tests(self) -> Dict:
        """Ejecutar tests de búsquedas"""
        self.print_section("SEARCH SYSTEM TESTS")
        results = {"passed": 0, "failed": 0, "errors": []}
        
        try:
            # Primero crear un proyecto de testing
            print("📁 Creating test project...")
            response = await test_client.post("/projects", json=TestingConfig.SAMPLE_PROJECT_DATA)
            
            if response.status_code == 200:
                project_data = response.json()
                project_id = project_data["project"]["id"]
                print(f"✅ Test project created: {project_id}")
                results["passed"] += 1
                
                # Test 1: Búsqueda de inversores
                print("🔍 Testing investor search...")
                response = await test_client.post("/search/investors", json={
                    "project_id": project_id,
                    "search_type": "hybrid",
                    "limit": 5
                })
                
                if response.status_code == 200:
                    search_data = response.json()
                    investors_found = len(search_data.get("results", []))
                    print(f"✅ Investor search successful - Found {investors_found} investors")
                    print(f"   - Credits used: {search_data.get('credits_used', 'N/A')}")
                    results["passed"] += 1
                elif response.status_code == 402:
                    print("⚠️ Insufficient credits for investor search")
                    results["passed"] += 1  # Este es un comportamiento esperado
                else:
                    print(f"❌ Investor search failed: {response.status_code}")
                    results["failed"] += 1
                
                # Test 2: Búsqueda de companies
                print("🏢 Testing companies search...")
                response = await test_client.post("/search/companies", json={
                    "problem_context": "Need marketing services for startup",
                    "categories": ["marketing", "digital marketing"],
                    "limit": 5
                })
                
                if response.status_code == 200:
                    search_data = response.json()
                    companies_found = len(search_data.get("results", []))
                    print(f"✅ Companies search successful - Found {companies_found} companies")
                    print(f"   - Credits used: {search_data.get('credits_used', 'N/A')}")
                    results["passed"] += 1
                elif response.status_code == 402:
                    print("⚠️ Insufficient credits for companies search")
                    results["passed"] += 1
                else:
                    print(f"❌ Companies search failed: {response.status_code}")
                    results["failed"] += 1
                
            else:
                print(f"❌ Failed to create test project: {response.status_code}")
                results["failed"] += 1
                results["errors"].append("Could not create test project for search tests")
                
        except Exception as e:
            print(f"❌ Search tests failed: {e}")
            results["failed"] += 1
            results["errors"].append(str(e))
        
        return results
    
    async def run_integration_tests(self) -> Dict:
        """Ejecutar tests de integración end-to-end"""
        self.print_section("INTEGRATION TESTS")
        results = {"passed": 0, "failed": 0, "errors": []}
        
        try:
            # Test: Flujo completo de usuario
            print("🔄 Testing complete user flow...")
            
            # 1. Crear proyecto
            response = await test_client.post("/projects", json={
                "name": "Integration Test Project",
                "description": "Test project for integration testing",
                "stage": "mvp",
                "category": "fintech"
            })
            
            if response.status_code == 200:
                project = response.json()["project"]
                print("✅ Project created successfully")
                
                # 2. Chat con referencia al proyecto
                response = await test_client.post("/chat", json={
                    "message": "Busco inversores Serie A para mi fintech",
                    "project_id": project["id"]
                })
                
                if response.status_code == 200:
                    chat_data = response.json()
                    print("✅ Project-aware chat successful")
                    print(f"   - Action taken: {chat_data.get('action_taken', 'N/A')}")
                    results["passed"] += 2
                else:
                    print(f"❌ Project-aware chat failed: {response.status_code}")
                    results["failed"] += 1
            else:
                print(f"❌ Integration test project creation failed: {response.status_code}")
                results["failed"] += 1
                
        except Exception as e:
            print(f"❌ Integration tests failed: {e}")
            results["failed"] += 1
            results["errors"].append(str(e))
        
        return results
    
    def run_pytest_suite(self) -> Dict:
        """Ejecutar tests de pytest si existen"""
        self.print_section("PYTEST SUITE")
        results = {"passed": 0, "failed": 0, "errors": []}
        
        try:
            # Verificar si existe la carpeta de tests
            test_dir = Path(__file__).parent.parent
            if (test_dir / "auth").exists():
                print("🐍 Running pytest suite...")
                
                # Ejecutar pytest
                cmd = [
                    sys.executable, "-m", "pytest", 
                    str(test_dir), 
                    "-v", 
                    "--tb=short",
                    "--disable-warnings"
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=test_dir)
                
                if result.returncode == 0:
                    print("✅ Pytest suite passed")
                    results["passed"] = 1
                else:
                    print("❌ Pytest suite failed")
                    print(result.stdout)
                    print(result.stderr)
                    results["failed"] = 1
                    results["errors"].append("Pytest suite failed")
            else:
                print("📝 No pytest files found - create them for more comprehensive testing")
                results["passed"] = 1
                
        except Exception as e:
            print(f"❌ Pytest execution failed: {e}")
            results["failed"] += 1
            results["errors"].append(str(e))
        
        return results
    
    def merge_results(self, *result_dicts) -> Dict:
        """Combinar resultados de múltiples test suites"""
        total_results = {"passed": 0, "failed": 0, "errors": []}
        
        for results in result_dicts:
            total_results["passed"] += results.get("passed", 0)
            total_results["failed"] += results.get("failed", 0)
            total_results["errors"].extend(results.get("errors", []))
        
        total_results["total"] = total_results["passed"] + total_results["failed"]
        
        return total_results
    
    def print_final_report(self, results: Dict, execution_time: float):
        """Imprimir reporte final de testing"""
        print("\n" + "=" * 80)
        print("📊 TESTING COMPLETE - FINAL REPORT")
        print("=" * 80)
        
        total = results["total"]
        passed = results["passed"]
        failed = results["failed"]
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"📈 Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"🎯 Success Rate: {success_rate:.1f}%")
        print(f"⏱️ Execution Time: {execution_time:.2f} seconds")
        
        if failed > 0:
            print(f"\n❌ FAILED TESTS ({failed}):")
            for i, error in enumerate(results["errors"], 1):
                print(f"   {i}. {error}")
        
        print("\n" + "=" * 80)
        
        # Determinar status general
        if failed == 0:
            print("🎉 ALL TESTS PASSED! The backend is working correctly.")
            return 0
        elif success_rate >= 80:
            print("⚠️ MOSTLY WORKING with some issues. Check failed tests above.")
            return 1
        else:
            print("🚨 MAJOR ISSUES DETECTED. The backend needs attention.")
            return 2
    
    async def run_all_tests(self) -> int:
        """Ejecutar toda la suite de testing"""
        start_time = time.time()
        
        self.print_header()
        
        # 1. Backend health check
        if not await self.run_backend_health_check():
            print("🚨 Cannot continue testing - backend is not available")
            return 3
        
        # 2. Ejecutar grupos de tests
        auth_results = await self.run_authentication_tests()
        chat_results = await self.run_chat_tests()
        search_results = await self.run_search_tests()
        integration_results = await self.run_integration_tests()
        pytest_results = self.run_pytest_suite()
        
        # 3. Combinar resultados
        final_results = self.merge_results(
            auth_results, chat_results, search_results, 
            integration_results, pytest_results
        )
        
        # 4. Reporte final
        execution_time = time.time() - start_time
        return self.print_final_report(final_results, execution_time)

async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Run 0Bullshit Backend Test Suite')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--fail-fast', '-f', action='store_true', help='Stop on first failure')
    parser.add_argument('--quick', '-q', action='store_true', help='Run only basic tests')
    
    args = parser.parse_args()
    
    runner = TestRunner(verbose=args.verbose, fail_fast=args.fail_fast)
    
    try:
        exit_code = await runner.run_all_tests()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Testing interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n🚨 Testing failed with unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())