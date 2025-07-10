#!/usr/bin/env python3
"""
Scripts de deployment y testing para 0Bullshit Backend
======================================================

Utilidades para verificar el sistema, hacer testing básico,
y preparar deployment.
"""

import asyncio
import json
import os
import sys
import time
from typing import Dict, Any, Optional
import httpx
import logging
from pathlib import Path

# Agregar el directorio raíz al Python path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from config.settings import get_settings, validate_settings

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# VERIFICACIÓN DEL SISTEMA
# ==========================================

async def check_dependencies():
    """Verificar que todas las dependencias estén instaladas"""
    logger.info("🔍 Verificando dependencias...")
    
    required_packages = [
        'fastapi', 'uvicorn', 'supabase', 'google.generativeai',
        'pydantic', 'jwt', 'websockets', 'httpx'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            logger.info(f"  ✅ {package}")
        except ImportError:
            missing.append(package)
            logger.error(f"  ❌ {package}")
    
    if missing:
        logger.error(f"Faltan dependencias: {missing}")
        logger.error("Ejecuta: pip install -r requirements.txt")
        return False
    
    logger.info("✅ Todas las dependencias están instaladas")
    return True

async def check_environment():
    """Verificar variables de entorno"""
    logger.info("🔍 Verificando variables de entorno...")
    
    if not validate_settings():
        logger.error("❌ Variables de entorno inválidas")
        return False
    
    settings = get_settings()
    
    # Verificaciones específicas
    checks = [
        (settings.SUPABASE_URL.startswith("https://"), "SUPABASE_URL debe ser HTTPS"),
        (len(settings.GEMINI_API_KEY) > 20, "GEMINI_API_KEY debe ser válida"),
        (len(settings.JWT_SECRET_KEY) >= 32, "JWT_SECRET_KEY debe tener al menos 32 caracteres"),
    ]
    
    for check, message in checks:
        if check:
            logger.info(f"  ✅ {message}")
        else:
            logger.error(f"  ❌ {message}")
            return False
    
    logger.info("✅ Variables de entorno configuradas correctamente")
    return True

async def check_database_connection():
    """Verificar conexión con Supabase"""
    logger.info("🔍 Verificando conexión con Supabase...")
    
    try:
        from database.database import db
        
        # Test simple query
        result = db.supabase.table("users").select("id").limit(1).execute()
        logger.info("✅ Conexión con Supabase exitosa")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error conectando con Supabase: {e}")
        return False

async def check_gemini_connection():
    """Verificar conexión con Gemini API"""
    logger.info("🔍 Verificando conexión con Gemini API...")
    
    try:
        from chat.judge import judge
        
        # Test generation
        response = judge.model.generate_content("Test connection")
        if response and response.text:
            logger.info("✅ Conexión con Gemini API exitosa")
            return True
        else:
            logger.error("❌ Gemini API no responde correctamente")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error conectando con Gemini API: {e}")
        return False

# ==========================================
# TESTING BÁSICO
# ==========================================

async def test_api_endpoints():
    """Test básico de endpoints de la API"""
    logger.info("🧪 Testing endpoints de la API...")
    
    # Verificar que el servidor esté corriendo
    settings = get_settings()
    base_url = f"http://{settings.HOST}:{settings.PORT}"
    
    async with httpx.AsyncClient() as client:
        try:
            # Test health endpoint
            response = await client.get(f"{base_url}/health", timeout=10.0)
            if response.status_code == 200:
                logger.info("  ✅ Health endpoint funcionando")
            else:
                logger.error(f"  ❌ Health endpoint falló: {response.status_code}")
                return False
                
        except httpx.RequestError as e:
            logger.error(f"❌ No se puede conectar al servidor: {e}")
            logger.error("Asegúrate de que el servidor esté corriendo con: python main.py")
            return False
    
    logger.info("✅ API endpoints funcionando correctamente")
    return True

async def test_chat_system():
    """Test básico del sistema de chat"""
    logger.info("🧪 Testing sistema de chat...")
    
    try:
        from chat.judge import judge
        from chat.chat import chat_system
        from models.schemas import Project, ProjectData
        from uuid import uuid4
        from datetime import datetime
        
        # Crear proyecto mock
        project = Project(
            id=uuid4(),
            user_id=uuid4(),
            name="Test Startup",
            description="Una startup de prueba",
            categories=["fintech"],
            stage="seed",
            project_data=ProjectData(
                categories=["fintech"],
                stage="seed"
            ),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Test judge analysis
        decision = await judge.analyze_user_intent(
            "Busco inversores para mi startup de fintech",
            project,
            []
        )
        
        if decision and decision.decision:
            logger.info(f"  ✅ Judge analysis: {decision.decision}")
        else:
            logger.error("  ❌ Judge analysis falló")
            return False
        
        # Test completeness calculation
        completeness = await chat_system.get_project_completeness(project.id, project.user_id)
        if completeness:
            logger.info(f"  ✅ Completeness calculation: {completeness.score:.2f}")
        else:
            logger.error("  ❌ Completeness calculation falló")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en testing del chat: {e}")
        return False
    
    logger.info("✅ Sistema de chat funcionando correctamente")
    return True

# ==========================================
# DEPLOYMENT VERIFICATION
# ==========================================

async def deployment_checklist():
    """Checklist completo para deployment"""
    logger.info("📋 Ejecutando checklist de deployment...")
    
    checks = [
        ("Dependencias", check_dependencies),
        ("Variables de entorno", check_environment), 
        ("Conexión Supabase", check_database_connection),
        ("Conexión Gemini", check_gemini_connection),
        ("Sistema de Chat", test_chat_system),
    ]
    
    results = {}
    
    for name, check_func in checks:
        try:
            result = await check_func()
            results[name] = result
            
            if result:
                logger.info(f"✅ {name}: PASSED")
            else:
                logger.error(f"❌ {name}: FAILED")
                
        except Exception as e:
            logger.error(f"❌ {name}: ERROR - {e}")
            results[name] = False
    
    # Resumen
    passed = sum(results.values())
    total = len(results)
    
    logger.info(f"\n📊 RESUMEN: {passed}/{total} checks pasaron")
    
    if passed == total:
        logger.info("🎉 ¡Sistema listo para deployment!")
        return True
    else:
        logger.error("🚨 Sistema NO listo para deployment")
        return False

# ==========================================
# PERFORMANCE TESTING
# ==========================================

async def performance_test():
    """Test básico de performance"""
    logger.info("⚡ Ejecutando test de performance...")
    
    settings = get_settings()
    base_url = f"http://{settings.HOST}:{settings.PORT}"
    
    async with httpx.AsyncClient() as client:
        # Test de latencia
        start_time = time.time()
        try:
            response = await client.get(f"{base_url}/health", timeout=5.0)
            end_time = time.time()
            
            latency = (end_time - start_time) * 1000  # ms
            
            if latency < 100:
                logger.info(f"✅ Latencia: {latency:.2f}ms (Excelente)")
            elif latency < 500:
                logger.info(f"🟡 Latencia: {latency:.2f}ms (Aceptable)")
            else:
                logger.warning(f"🔴 Latencia: {latency:.2f}ms (Lenta)")
                
        except Exception as e:
            logger.error(f"❌ Error en test de latencia: {e}")
            return False
    
    # Test de carga múltiple
    logger.info("Testing múltiples requests simultáneos...")
    
    async def single_request():
        async with httpx.AsyncClient() as client:
            return await client.get(f"{base_url}/health", timeout=5.0)
    
    start_time = time.time()
    tasks = [single_request() for _ in range(10)]
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    end_time = time.time()
    
    successful = len([r for r in responses if not isinstance(r, Exception)])
    total_time = end_time - start_time
    
    logger.info(f"✅ {successful}/10 requests exitosos en {total_time:.2f}s")
    
    return successful >= 8  # Al menos 80% de éxito

# ==========================================
# UTILIDADES DE DATOS
# ==========================================

def generate_test_data():
    """Generar datos de prueba para testing"""
    logger.info("📝 Generando datos de prueba...")
    
    test_projects = [
        {
            "name": "FinTech Revolucionaria",
            "description": "Plataforma de pagos para startups",
            "categories": ["fintech", "saas"],
            "stage": "seed"
        },
        {
            "name": "EdTech Innovadora", 
            "description": "App de aprendizaje personalizado",
            "categories": ["edtech"],
            "stage": "mvp"
        },
        {
            "name": "HealthTech Disruptiva",
            "description": "Telemedicina con IA",
            "categories": ["healthtech", "ai"],
            "stage": "series-a"
        }
    ]
    
    test_messages = [
        "Busco inversores Serie A para mi startup",
        "Necesito ayuda con marketing digital",
        "¿Cómo puedo mejorar mi pitch deck?",
        "Tengo 50k ARR y busco escalar",
        "Mi equipo necesita un CTO técnico"
    ]
    
    # Guardar en archivos
    os.makedirs("test_data", exist_ok=True)
    
    with open("test_data/projects.json", "w") as f:
        json.dump(test_projects, f, indent=2)
    
    with open("test_data/messages.json", "w") as f:
        json.dump(test_messages, f, indent=2)
    
    logger.info("✅ Datos de prueba generados en test_data/")

# ==========================================
# CLI INTERFACE
# ==========================================

async def main():
    """Función principal CLI"""
    if len(sys.argv) < 2:
        print("""
🚀 0Bullshit Backend - Scripts de Deployment

Uso: python scripts/deploy.py <comando>

Comandos disponibles:
  check-deps          Verificar dependencias
  check-env           Verificar variables de entorno  
  check-db            Verificar conexión con Supabase
  check-gemini        Verificar conexión con Gemini
  test-api            Test básico de API endpoints
  test-chat           Test sistema de chat
  test-performance    Test de performance
  deployment-check    Checklist completo de deployment
  generate-test-data  Generar datos de prueba
  
Ejemplos:
  python scripts/deploy.py deployment-check
  python scripts/deploy.py test-performance
        """)
        return
    
    command = sys.argv[1]
    
    commands = {
        "check-deps": check_dependencies,
        "check-env": check_environment,
        "check-db": check_database_connection,
        "check-gemini": check_gemini_connection,
        "test-api": test_api_endpoints,
        "test-chat": test_chat_system,
        "test-performance": performance_test,
        "deployment-check": deployment_checklist,
    }
    
    if command == "generate-test-data":
        generate_test_data()
        return
    
    if command not in commands:
        logger.error(f"Comando desconocido: {command}")
        return
    
    try:
        success = await commands[command]()
        if success:
            logger.info(f"✅ {command} completado exitosamente")
            sys.exit(0)
        else:
            logger.error(f"❌ {command} falló")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 Operación cancelada por el usuario")
        sys.exit(130)
    except Exception as e:
        logger.error(f"💥 Error inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
