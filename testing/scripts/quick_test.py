#!/usr/bin/env python3
# testing/scripts/quick_test.py
"""
Script para testing rápido de funcionalidades específicas
Útil para verificar que una feature específica funciona después de cambios
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Agregar directorio padre al path
sys.path.append(str(Path(__file__).parent.parent.parent))

from testing.config_testing import test_client, TestingConfig, wait_for_backend

async def test_health():
    """Test básico de salud del backend"""
    print("🔍 Testing backend health...")
    try:
        await wait_for_backend()
        print("✅ Backend is healthy")
        return True
    except Exception as e:
        print(f"❌ Backend health check failed: {e}")
        return False

async def test_auth():
    """Test rápido de autenticación"""
    print("🔐 Testing authentication...")
    try:
        await test_client.authenticate()
        if test_client.access_token:
            print("✅ Authentication successful")
            
            # Test profile access
            response = await test_client.get("/auth/me")
            if response.status_code == 200:
                user_data = response.json()
                print(f"✅ Profile access successful - User: {user_data.get('email')}")
                return True
            else:
                print(f"❌ Profile access failed: {response.status_code}")
                return False
        else:
            print("❌ Authentication failed - no token received")
            return False
    except Exception as e:
        print(f"❌ Authentication test failed: {e}")
        return False

async def test_chat():
    """Test rápido del sistema de chat"""
    print("💬 Testing chat system...")
    try:
        # Asegurar autenticación
        if not test_client.access_token:
            await test_client.authenticate()
        
        # Test chat en español
        response = await test_client.post("/chat", json={
            "message": "Hola, necesito ayuda con mi startup"
        })
        
        if response.status_code == 200:
            chat_data = response.json()
            print("✅ Chat successful")
            print(f"   - Language detected: {chat_data.get('language_detected', 'N/A')}")
            print(f"   - Anti-spam triggered: {chat_data.get('anti_spam_triggered', False)}")
            print(f"   - Credits used: {chat_data.get('credits_used', 'N/A')}")
            
            # Test anti-spam
            spam_response = await test_client.post("/chat", json={
                "message": "asdfasdfasdf random bullshit"
            })
            
            if spam_response.status_code == 200:
                spam_data = spam_response.json()
                if spam_data.get('anti_spam_triggered'):
                    print("✅ Anti-spam system working")
                else:
                    print("⚠️ Anti-spam system not triggered (might be expected)")
            
            return True
        else:
            print(f"❌ Chat test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Chat test failed: {e}")
        return False

async def test_search():
    """Test rápido del sistema de búsquedas"""
    print("🔍 Testing search system...")
    try:
        # Asegurar autenticación
        if not test_client.access_token:
            await test_client.authenticate()
        
        # Crear proyecto de test
        response = await test_client.post("/projects", json={
            "name": "Quick Test Project",
            "description": "Project for quick testing",
            "stage": "mvp",
            "category": "fintech"
        })
        
        if response.status_code == 200:
            project = response.json()["project"]
            print(f"✅ Test project created: {project['id']}")
            
            # Test búsqueda de companies (más barata)
            companies_response = await test_client.post("/search/companies", json={
                "problem_context": "Need marketing help",
                "limit": 3
            })
            
            if companies_response.status_code == 200:
                companies_data = companies_response.json()
                companies_found = len(companies_data.get("results", []))
                print(f"✅ Companies search successful - Found {companies_found} companies")
                return True
            elif companies_response.status_code == 402:
                print("⚠️ Insufficient credits for search (expected for some users)")
                return True
            else:
                print(f"❌ Companies search failed: {companies_response.status_code}")
                return False
        else:
            print(f"❌ Failed to create test project: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Search test failed: {e}")
        return False

async def test_projects():
    """Test rápido del sistema de proyectos"""
    print("📁 Testing projects system...")
    try:
        # Asegurar autenticación
        if not test_client.access_token:
            await test_client.authenticate()
        
        # Crear proyecto
        response = await test_client.post("/projects", json={
            "name": "Test Project Quick",
            "description": "Quick test project",
            "stage": "idea",
            "category": "saas"
        })
        
        if response.status_code == 200:
            project = response.json()["project"]
            project_id = project["id"]
            print(f"✅ Project created: {project_id}")
            
            # Obtener proyectos
            response = await test_client.get("/projects")
            if response.status_code == 200:
                projects = response.json()["projects"]
                print(f"✅ Projects retrieved - Total: {len(projects)}")
                
                # Limpiar - eliminar proyecto de test
                delete_response = await test_client.delete(f"/projects/{project_id}")
                if delete_response.status_code == 200:
                    print("✅ Test project cleaned up")
                
                return True
            else:
                print(f"❌ Failed to retrieve projects: {response.status_code}")
                return False
        else:
            print(f"❌ Failed to create project: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Projects test failed: {e}")
        return False

async def run_feature_test(feature: str) -> bool:
    """Ejecutar test de una feature específica"""
    feature_tests = {
        "health": test_health,
        "auth": test_auth,
        "chat": test_chat,
        "search": test_search,
        "projects": test_projects
    }
    
    if feature not in feature_tests:
        print(f"❌ Unknown feature: {feature}")
        print(f"Available features: {', '.join(feature_tests.keys())}")
        return False
    
    print(f"🧪 QUICK TEST - {feature.upper()}")
    print("=" * 40)
    
    result = await feature_tests[feature]()
    
    print("=" * 40)
    if result:
        print(f"🎉 {feature.upper()} test PASSED")
    else:
        print(f"🚨 {feature.upper()} test FAILED")
    
    return result

async def run_all_quick_tests() -> int:
    """Ejecutar todos los tests rápidos"""
    print("🧪 QUICK TESTS - ALL FEATURES")
    print("=" * 50)
    
    features = ["health", "auth", "chat", "projects", "search"]
    results = {}
    
    for feature in features:
        print(f"\n🔍 Testing {feature}...")
        results[feature] = await run_feature_test(feature)
    
    # Reporte final
    print("\n" + "=" * 50)
    print("📊 QUICK TESTS SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for feature, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{feature.upper():12} - {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All quick tests PASSED!")
        return 0
    else:
        print("🚨 Some tests FAILED - check logs above")
        return 1

async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Quick test for 0Bullshit Backend features')
    parser.add_argument('feature', nargs='?', help='Feature to test (health, auth, chat, search, projects, all)')
    parser.add_argument('--all', action='store_true', help='Run all quick tests')
    
    args = parser.parse_args()
    
    try:
        if args.all or args.feature == 'all':
            exit_code = await run_all_quick_tests()
        elif args.feature:
            result = await run_feature_test(args.feature)
            exit_code = 0 if result else 1
        else:
            print("❓ No feature specified. Use --help for usage info")
            print("Available features: health, auth, chat, search, projects, all")
            exit_code = 1
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n🛑 Quick test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n🚨 Quick test failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())