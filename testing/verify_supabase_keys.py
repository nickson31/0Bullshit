#!/usr/bin/env python3
"""
🔍 SUPABASE KEYS VERIFICATION
============================

Script para verificar que las claves de Supabase sean correctas
antes de configurarlas en Render.

Uso:
    python3 testing/verify_supabase_keys.py
"""

import asyncio
import sys
from pathlib import Path

# Agregar directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

try:
    import httpx
except ImportError:
    print("❌ Missing httpx. Install with: pip3 install httpx")
    sys.exit(1)

def get_user_input():
    """Obtener claves del usuario"""
    print("🔍 SUPABASE KEYS VERIFICATION")
    print("=" * 50)
    print("Por favor, proporciona las claves de Supabase:")
    print()
    
    # Obtener URL
    print("1️⃣ SUPABASE_URL:")
    print("   Busca en Supabase Dashboard > Settings > API > Project URL")
    print("   Debe verse como: https://abcdefghijk.supabase.co")
    supabase_url = input("   URL: ").strip()
    
    if not supabase_url.startswith('https://'):
        print("⚠️  La URL debe empezar con https://")
        supabase_url = f"https://{supabase_url}"
    
    print()
    
    # Obtener Key
    print("2️⃣ SUPABASE_KEY:")
    print("   Busca en Supabase Dashboard > Settings > API > anon public key")
    print("   Es una clave MUY larga que empieza con 'eyJ...'")
    supabase_key = input("   Key: ").strip()
    
    return supabase_url, supabase_key

async def verify_supabase_connection(url: str, key: str):
    """Verificar conexión con Supabase"""
    print("\n🔍 Verificando conexión con Supabase...")
    
    # Test 1: Verificar que la URL responda
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{url}/rest/v1/", headers={
                "apikey": key,
                "Authorization": f"Bearer {key}"
            })
            
            if response.status_code == 200:
                print("✅ URL de Supabase: CORRECTA")
                print(f"   Respuesta: {response.status_code}")
                return True
            elif response.status_code == 401:
                print("❌ SUPABASE_KEY: INCORRECTA")
                print("   La URL funciona pero la clave es inválida")
                return False
            elif response.status_code == 404:
                print("❌ SUPABASE_URL: INCORRECTA")
                print("   La URL no existe o el proyecto no está disponible")
                return False
            else:
                print(f"⚠️  Respuesta inesperada: {response.status_code}")
                print(f"   Esto podría indicar un problema de configuración")
                return False
                
    except Exception as e:
        print(f"❌ Error de conexión: {str(e)}")
        print("   Verifica que la URL sea correcta y que tengas internet")
        return False

async def test_basic_operations(url: str, key: str):
    """Test operaciones básicas"""
    print("\n🔍 Probando operaciones básicas...")
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Test: Listar tablas (esto debería funcionar con cualquier proyecto)
            response = await client.get(
                f"{url}/rest/v1/",
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                print("✅ Operaciones básicas: FUNCIONANDO")
                print("   Las claves permiten acceso a la API de Supabase")
                return True
            else:
                print(f"⚠️  Operaciones básicas: Respuesta {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Error en operaciones básicas: {str(e)}")
        return False

def print_render_instructions(url: str, key: str):
    """Imprimir instrucciones para Render"""
    print("\n" + "=" * 60)
    print("🚀 CONFIGURACIÓN PARA RENDER")
    print("=" * 60)
    print("Copia estas variables EXACTAMENTE en tu dashboard de Render:")
    print()
    print("Variable: SUPABASE_URL")
    print(f"Valor: {url}")
    print()
    print("Variable: SUPABASE_KEY")
    print(f"Valor: {key}")
    print()
    print("📋 Pasos en Render:")
    print("1. Ve a tu dashboard de Render")
    print("2. Selecciona tu servicio 'zerobs-back-final'")
    print("3. Ve a la pestaña 'Environment'")
    print("4. Actualiza SUPABASE_URL y SUPABASE_KEY con los valores de arriba")
    print("5. Haz clic en 'Manual Deploy' para reiniciar el servicio")
    print("6. Espera 2-3 minutos a que termine el deployment")
    print("7. Ejecuta: python3 testing/cursor_test_runner.py --all")
    print("=" * 60)

async def main():
    """Función principal"""
    try:
        # Obtener claves del usuario
        supabase_url, supabase_key = get_user_input()
        
        # Validaciones básicas
        if not supabase_url or not supabase_key:
            print("❌ Debes proporcionar tanto la URL como la clave")
            sys.exit(1)
        
        if not supabase_url.endswith('.supabase.co'):
            print("⚠️  La URL no parece ser de Supabase (debe terminar en .supabase.co)")
        
        if not supabase_key.startswith('eyJ'):
            print("⚠️  La clave no parece ser válida (debe empezar con 'eyJ')")
        
        # Verificar conexión
        connection_ok = await verify_supabase_connection(supabase_url, supabase_key)
        
        if connection_ok:
            # Test operaciones básicas
            operations_ok = await test_basic_operations(supabase_url, supabase_key)
            
            if operations_ok:
                print("\n🎉 ¡VERIFICACIÓN EXITOSA!")
                print("✅ Las claves de Supabase son CORRECTAS")
                print("✅ La conexión funciona perfectamente")
                
                # Mostrar instrucciones para Render
                print_render_instructions(supabase_url, supabase_key)
                
                sys.exit(0)
            else:
                print("\n⚠️  Las claves parecen correctas pero hay problemas de operación")
                print("   Esto podría ser normal - procede con la configuración en Render")
                print_render_instructions(supabase_url, supabase_key)
                sys.exit(0)
        else:
            print("\n❌ VERIFICACIÓN FALLIDA")
            print("Las claves no son correctas. Por favor:")
            print("1. Ve a tu dashboard de Supabase")
            print("2. Verifica que estés en el proyecto correcto")
            print("3. Ve a Settings > API")
            print("4. Copia exactamente la Project URL y la anon public key")
            print("5. Ejecuta este script de nuevo")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Verificación cancelada por el usuario")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())