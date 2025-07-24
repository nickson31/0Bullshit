#!/usr/bin/env python3
"""
DEBUG: Supabase Connection Test
===============================

Script para probar exactamente la misma conexión que usa el backend
"""

import os
import sys
from pathlib import Path

# Agregar directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

def test_backend_supabase_connection():
    """Probar la conexión exacta que usa el backend"""
    print("🔍 TESTING BACKEND SUPABASE CONNECTION")
    print("=" * 60)
    
    # Simular las mismas variables que usa Render
    supabase_url = "https://jbbymdpptkdlqtzbcsbn.supabase.co"
    supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpiYnltZHBwdGtkbHF0emJjc2JuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTIzNDMwMTcsImV4cCI6MjA2NzkxOTAxN30.TnqTlcB-eHLBPQ0-R2ztGgAk763ThVW5Yhiqx8-DMvg"
    
    # Establecer variables de entorno como lo haría Render
    os.environ["SUPABASE_URL"] = supabase_url
    os.environ["SUPABASE_KEY"] = supabase_key
    
    print(f"✅ SUPABASE_URL: {supabase_url}")
    print(f"✅ SUPABASE_KEY: {supabase_key[:50]}...")
    print()
    
    try:
        # Importar exactamente como lo hace el backend
        from supabase import create_client
        
        # Crear cliente exactamente igual que database.py
        supabase_client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        
        print("✅ Supabase client created successfully")
        
        # Test 1: Verificar conexión básica
        print("\n🔍 Test 1: Basic connection test...")
        try:
            # Intentar hacer una query simple a una tabla que debería existir
            result = supabase_client.table("users").select("id").limit(1).execute()
            print(f"✅ Connection successful. Response: {len(result.data)} records")
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
        
        # Test 2: Probar inserción (simulando registro)
        print("\n🔍 Test 2: Testing user insertion (like registration)...")
        try:
            from uuid import uuid4
            from datetime import datetime
            
            test_user_id = str(uuid4())
            test_user = {
                "id": test_user_id,
                "email": f"test_{test_user_id[:8]}@example.com",
                "password": "hashed_password_here",
                "name": "Test User",
                "plan": "free",
                "credits": 200,
                "daily_credits_used": 0,
                "last_credit_reset": datetime.now().isoformat(),
                "onboarding_completed": False,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Intentar insertar (esto es lo que falla en el backend)
            result = supabase_client.table("users").insert(test_user).execute()
            
            if result.data:
                print(f"✅ User insertion successful: {result.data[0]['email']}")
                
                # Limpiar el usuario de prueba
                supabase_client.table("users").delete().eq("id", test_user_id).execute()
                print("✅ Test user cleaned up")
                
                return True
            else:
                print(f"❌ User insertion failed: No data returned")
                return False
                
        except Exception as e:
            print(f"❌ User insertion failed: {e}")
            print(f"   Error type: {type(e).__name__}")
            
            # Intentar obtener más detalles del error
            if hasattr(e, 'details'):
                print(f"   Error details: {e.details}")
            if hasattr(e, 'message'):
                print(f"   Error message: {e.message}")
            if hasattr(e, 'code'):
                print(f"   Error code: {e.code}")
                
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure supabase is installed: pip install supabase")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_environment_variables():
    """Verificar que las variables estén correctas"""
    print("\n🔍 ENVIRONMENT VARIABLES CHECK")
    print("=" * 60)
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    print(f"SUPABASE_URL: {url}")
    print(f"SUPABASE_KEY: {key[:50] if key else 'None'}...")
    
    if not url or not key:
        print("❌ Missing environment variables")
        return False
    
    if not url.startswith("https://"):
        print("❌ SUPABASE_URL should start with https://")
        return False
        
    if not url.endswith(".supabase.co"):
        print("❌ SUPABASE_URL should end with .supabase.co")
        return False
        
    if not key.startswith("eyJ"):
        print("❌ SUPABASE_KEY should start with eyJ (JWT format)")
        return False
    
    print("✅ Environment variables look correct")
    return True

if __name__ == "__main__":
    print("🚀 DEBUGGING SUPABASE CONNECTION")
    print("This script tests the exact same connection the backend uses")
    print("=" * 80)
    
    # Test environment variables
    env_ok = test_environment_variables()
    
    if env_ok:
        # Test actual connection
        connection_ok = test_backend_supabase_connection()
        
        if connection_ok:
            print("\n🎉 SUCCESS!")
            print("✅ Supabase connection is working correctly")
            print("✅ The backend should be able to connect to Supabase")
            print("\n💡 If the backend is still failing:")
            print("   1. Check Render logs for specific error messages")
            print("   2. Verify the environment variables are set in Render")
            print("   3. Make sure the service was redeployed after setting variables")
        else:
            print("\n❌ FAILURE!")
            print("The exact same connection the backend uses is failing")
            print("This explains why registration returns 'Internal server error'")
    else:
        print("\n❌ ENVIRONMENT SETUP FAILED")
        print("Fix environment variables first")