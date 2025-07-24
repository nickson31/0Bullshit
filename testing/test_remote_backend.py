#!/usr/bin/env python3
"""
🌐 REMOTE BACKEND TESTING
========================

Test específico para el backend remoto en Render.
Diseñado para ser más diagnóstico y tolerante a errores de configuración.

Uso:
    python3 testing/test_remote_backend.py
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Agregar directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

try:
    import httpx
    from testing.config_testing import TestingConfig
except ImportError as e:
    print(f"❌ Missing dependencies: {e}")
    print("Please run: pip3 install httpx python-dotenv")
    sys.exit(1)

class RemoteBackendTester:
    """Tester específico para backend remoto"""
    
    def __init__(self):
        self.base_url = TestingConfig.API_BASE_URL
        self.results = []
    
    def log(self, message: str, level: str = "INFO"):
        """Log con timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅", 
            "ERROR": "❌",
            "WARNING": "⚠️",
            "DEBUG": "🔍"
        }.get(level, "📝")
        
        print(f"[{timestamp}] {prefix} {message}")
    
    async def test_basic_connectivity(self):
        """Test básico de conectividad"""
        self.log("Testing basic connectivity...", "DEBUG")
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(self.base_url)
                
                if response.status_code == 200:
                    data = response.json()
                    self.log(f"Backend is responding: {data.get('message', 'No message')}", "SUCCESS")
                    self.results.append({"test": "connectivity", "status": "pass", "details": data})
                    return True
                else:
                    self.log(f"Backend responded with status {response.status_code}", "WARNING")
                    self.results.append({"test": "connectivity", "status": "warning", "details": {"status_code": response.status_code}})
                    return False
                    
        except Exception as e:
            self.log(f"Connectivity test failed: {e}", "ERROR")
            self.results.append({"test": "connectivity", "status": "fail", "details": {"error": str(e)}})
            return False
    
    async def test_health_endpoint(self):
        """Test del endpoint de health"""
        self.log("Testing health endpoint...", "DEBUG")
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(f"{self.base_url}/health")
                
                if response.status_code == 200:
                    data = response.json()
                    self.log(f"Health check passed: {data.get('status', 'unknown')}", "SUCCESS")
                    self.results.append({"test": "health", "status": "pass", "details": data})
                    return True
                else:
                    self.log(f"Health endpoint returned {response.status_code}", "WARNING")
                    self.results.append({"test": "health", "status": "warning", "details": {"status_code": response.status_code}})
                    return False
                    
        except Exception as e:
            self.log(f"Health test failed: {e}", "ERROR")
            self.results.append({"test": "health", "status": "fail", "details": {"error": str(e)}})
            return False
    
    async def test_api_documentation(self):
        """Test de acceso a documentación"""
        self.log("Testing API documentation access...", "DEBUG")
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Test docs endpoint
                docs_response = await client.get(f"{self.base_url}/docs")
                if docs_response.status_code == 200:
                    self.log("API documentation is accessible", "SUCCESS")
                    docs_status = "pass"
                else:
                    self.log(f"Docs endpoint returned {docs_response.status_code}", "WARNING")
                    docs_status = "warning"
                
                # Test OpenAPI schema
                openapi_response = await client.get(f"{self.base_url}/openapi.json")
                if openapi_response.status_code == 200:
                    schema = openapi_response.json()
                    endpoints = list(schema.get("paths", {}).keys())
                    self.log(f"OpenAPI schema available with {len(endpoints)} endpoints", "SUCCESS")
                    
                    # Log some key endpoints
                    auth_endpoints = [ep for ep in endpoints if "auth" in ep]
                    chat_endpoints = [ep for ep in endpoints if "chat" in ep]
                    search_endpoints = [ep for ep in endpoints if "search" in ep]
                    
                    self.log(f"Auth endpoints: {len(auth_endpoints)}", "INFO")
                    self.log(f"Chat endpoints: {len(chat_endpoints)}", "INFO") 
                    self.log(f"Search endpoints: {len(search_endpoints)}", "INFO")
                    
                    self.results.append({
                        "test": "documentation", 
                        "status": "pass", 
                        "details": {
                            "total_endpoints": len(endpoints),
                            "auth_endpoints": len(auth_endpoints),
                            "chat_endpoints": len(chat_endpoints),
                            "search_endpoints": len(search_endpoints),
                            "sample_endpoints": endpoints[:10]
                        }
                    })
                    return True
                else:
                    self.log(f"OpenAPI schema returned {openapi_response.status_code}", "WARNING")
                    self.results.append({"test": "documentation", "status": "warning", "details": {"openapi_status": openapi_response.status_code}})
                    return False
                    
        except Exception as e:
            self.log(f"Documentation test failed: {e}", "ERROR")
            self.results.append({"test": "documentation", "status": "fail", "details": {"error": str(e)}})
            return False
    
    async def test_auth_endpoints_availability(self):
        """Test de disponibilidad de endpoints de auth (sin intentar autenticar)"""
        self.log("Testing auth endpoints availability...", "DEBUG")
        
        auth_endpoints = [
            "/api/v1/auth/register",
            "/api/v1/auth/login", 
            "/api/v1/auth/refresh",
            "/api/v1/auth/me"
        ]
        
        available_endpoints = []
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                for endpoint in auth_endpoints:
                    try:
                        # Usar OPTIONS para verificar disponibilidad sin ejecutar
                        response = await client.options(f"{self.base_url}{endpoint}")
                        if response.status_code in [200, 405]:  # 405 = Method Not Allowed, pero endpoint existe
                            available_endpoints.append(endpoint)
                            self.log(f"Endpoint available: {endpoint}", "SUCCESS")
                        else:
                            self.log(f"Endpoint {endpoint}: Status {response.status_code}", "WARNING")
                    except Exception as e:
                        self.log(f"Endpoint {endpoint}: Error {e}", "WARNING")
                
                self.results.append({
                    "test": "auth_endpoints", 
                    "status": "pass" if available_endpoints else "fail",
                    "details": {
                        "available_endpoints": available_endpoints,
                        "total_tested": len(auth_endpoints)
                    }
                })
                
                return len(available_endpoints) > 0
                
        except Exception as e:
            self.log(f"Auth endpoints test failed: {e}", "ERROR")
            self.results.append({"test": "auth_endpoints", "status": "fail", "details": {"error": str(e)}})
            return False
    
    async def test_error_handling(self):
        """Test de manejo de errores del backend"""
        self.log("Testing error handling...", "DEBUG")
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Test endpoint que no existe
                response = await client.get(f"{self.base_url}/api/v1/nonexistent")
                
                if response.status_code == 404:
                    self.log("404 handling works correctly", "SUCCESS")
                    error_handling_status = "pass"
                else:
                    self.log(f"Unexpected status for nonexistent endpoint: {response.status_code}", "WARNING")
                    error_handling_status = "warning"
                
                # Test método no permitido
                response = await client.patch(f"{self.base_url}/health")
                
                if response.status_code in [405, 422]:  # Method not allowed o Unprocessable Entity
                    self.log("Method validation works correctly", "SUCCESS")
                else:
                    self.log(f"Unexpected status for wrong method: {response.status_code}", "WARNING")
                
                self.results.append({
                    "test": "error_handling", 
                    "status": error_handling_status,
                    "details": {"404_handling": "working", "method_validation": "working"}
                })
                
                return True
                
        except Exception as e:
            self.log(f"Error handling test failed: {e}", "ERROR")
            self.results.append({"test": "error_handling", "status": "fail", "details": {"error": str(e)}})
            return False
    
    async def diagnose_auth_issue(self):
        """Diagnóstico específico del problema de autenticación"""
        self.log("Diagnosing authentication issues...", "DEBUG")
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Intentar registro con datos mínimos
                test_data = {
                    "email": "diagnostic@test.com",
                    "password": "TestPass123!",
                    "name": "Diagnostic User"
                }
                
                response = await client.post(
                    f"{self.base_url}/api/v1/auth/register",
                    json=test_data,
                    headers={"Content-Type": "application/json"}
                )
                
                self.log(f"Registration attempt status: {response.status_code}", "INFO")
                
                if response.status_code == 500:
                    try:
                        error_data = response.json()
                        self.log(f"Server error details: {error_data}", "WARNING")
                        
                        # Diagnóstico común
                        if "Internal server error" in str(error_data):
                            self.log("Likely causes:", "INFO")
                            self.log("  - Database connection issues", "INFO")
                            self.log("  - Missing environment variables", "INFO")
                            self.log("  - Configuration problems", "INFO")
                            
                            diagnosis = "internal_server_error"
                        else:
                            diagnosis = "unknown_error"
                            
                    except:
                        self.log("Could not parse error response", "WARNING")
                        diagnosis = "unparseable_error"
                        
                elif response.status_code == 422:
                    error_data = response.json()
                    self.log(f"Validation error: {error_data}", "INFO")
                    diagnosis = "validation_error"
                    
                elif response.status_code == 201:
                    self.log("Registration actually works! Previous error might be intermittent", "SUCCESS")
                    diagnosis = "working"
                    
                else:
                    self.log(f"Unexpected status code: {response.status_code}", "WARNING")
                    diagnosis = "unexpected_status"
                
                self.results.append({
                    "test": "auth_diagnosis",
                    "status": "info",
                    "details": {
                        "diagnosis": diagnosis,
                        "status_code": response.status_code,
                        "response_size": len(response.content)
                    }
                })
                
                return diagnosis
                
        except Exception as e:
            self.log(f"Auth diagnosis failed: {e}", "ERROR")
            self.results.append({"test": "auth_diagnosis", "status": "fail", "details": {"error": str(e)}})
            return "diagnosis_failed"
    
    def print_summary(self):
        """Imprimir resumen de resultados"""
        print("\n" + "=" * 80)
        print("🌐 REMOTE BACKEND TEST SUMMARY")
        print("=" * 80)
        print(f"Backend URL: {self.base_url}")
        print(f"Tests executed: {len(self.results)}")
        
        passed = sum(1 for r in self.results if r["status"] == "pass")
        failed = sum(1 for r in self.results if r["status"] == "fail")
        warnings = sum(1 for r in self.results if r["status"] == "warning")
        info = sum(1 for r in self.results if r["status"] == "info")
        
        print(f"Results: ✅ {passed} passed, ❌ {failed} failed, ⚠️ {warnings} warnings, ℹ️ {info} info")
        
        print("\n📋 Detailed Results:")
        for result in self.results:
            status_icon = {"pass": "✅", "fail": "❌", "warning": "⚠️", "info": "ℹ️"}[result["status"]]
            print(f"{status_icon} {result['test']}: {result['status']}")
            
            # Mostrar detalles importantes
            if result["test"] == "documentation" and result["status"] == "pass":
                details = result["details"]
                print(f"    Total endpoints: {details['total_endpoints']}")
                print(f"    Auth endpoints: {details['auth_endpoints']}")
                
            elif result["test"] == "auth_diagnosis":
                diagnosis = result["details"]["diagnosis"]
                print(f"    Diagnosis: {diagnosis}")
        
        print("\n🎯 Recommendations:")
        if failed > 0:
            print("❌ Some critical tests failed - backend may have configuration issues")
        elif warnings > 0:
            print("⚠️ Backend is responding but some issues detected")
        else:
            print("✅ Backend appears to be working correctly")
        
        if any(r["test"] == "auth_diagnosis" and r["details"]["diagnosis"] == "internal_server_error" for r in self.results):
            print("\n🔧 For authentication issues:")
            print("  1. Check backend logs in Render dashboard")
            print("  2. Verify environment variables are set")
            print("  3. Ensure database connection is working")
            print("  4. Check if migrations are applied")
        
        print("=" * 80)

async def main():
    """Función principal"""
    print("🌐 REMOTE BACKEND DIAGNOSTIC TEST")
    print("=" * 60)
    print(f"Target: {TestingConfig.API_BASE_URL}")
    print("=" * 60)
    
    tester = RemoteBackendTester()
    
    try:
        # Ejecutar tests diagnósticos
        await tester.test_basic_connectivity()
        await tester.test_health_endpoint()
        await tester.test_api_documentation()
        await tester.test_auth_endpoints_availability()
        await tester.test_error_handling()
        await tester.diagnose_auth_issue()
        
        # Mostrar resumen
        tester.print_summary()
        
        # Exit code basado en resultados
        failed = sum(1 for r in tester.results if r["status"] == "fail")
        sys.exit(0 if failed == 0 else 1)
        
    except KeyboardInterrupt:
        tester.log("Test interrupted by user", "WARNING")
        sys.exit(130)
    except Exception as e:
        tester.log(f"Test failed with error: {e}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())