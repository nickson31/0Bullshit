#!/usr/bin/env python3
"""
0Bullshit Chat Backend
======================

Sistema de chat con IA especializado en startups que conecta founders
con inversores, empresas y proporciona mentoría estilo Y-Combinator.

Autor: 0Bullshit Team
Version: 1.0.0
"""

import os
import sys
import logging
from pathlib import Path

# Agregar el directorio raíz al Python path
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log') if os.getenv('DEBUG') == 'True' else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)

def check_environment():
    """Verificar variables de entorno necesarias"""
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_KEY', 
        'GEMINI_API_KEY',
        'JWT_SECRET_KEY'
    ]
    
    # Variables opcionales pero recomendadas
    optional_vars = [
        'UNIPILE_API_KEY',
        'UNIPILE_DSN',
        'STRIPE_SECRET_KEY',
        'STRIPE_WEBHOOK_SECRET'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please check your .env file or environment configuration")
        return False
    
    # Check optional vars and warn if missing
    missing_optional = []
    for var in optional_vars:
        if not os.getenv(var):
            missing_optional.append(var)
    
    if missing_optional:
        logger.warning(f"Optional environment variables not set: {', '.join(missing_optional)}")
        logger.warning("Some features may be disabled:")
        if 'UNIPILE_API_KEY' in missing_optional:
            logger.warning("  - LinkedIn automation and outreach campaigns")
        if 'STRIPE_SECRET_KEY' in missing_optional:
            logger.warning("  - Stripe payments and subscriptions")
    
    return True

def check_dependencies():
    """Verificar dependencias críticas"""
    try:
        import fastapi
        import supabase
        import google.generativeai
        import jwt
        import pydantic
        logger.info("✅ All critical dependencies are available")
        return True
    except ImportError as e:
        logger.error(f"❌ Missing critical dependency: {e}")
        logger.error("Please run: pip install -r requirements.txt")
        return False

def main():
    """Función principal"""
    logger.info("🚀 Starting 0Bullshit Chat Backend...")
    
    # Verificar entorno
    if not check_environment():
        sys.exit(1)
    
    # Verificar dependencias
    if not check_dependencies():
        sys.exit(1)
    
    # Importar la aplicación
    try:
        from api.api import app
        logger.info("✅ Application imported successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import application: {e}")
        sys.exit(1)
    
    # Configuración del servidor
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "False").lower() == "true"
    
    logger.info(f"🌐 Server configuration:")
    logger.info(f"   Host: {host}")
    logger.info(f"   Port: {port}")
    logger.info(f"   Debug: {debug}")
    logger.info(f"   Environment: {os.getenv('ENVIRONMENT', 'development')}")
    
    # Iniciar servidor
    try:
        import uvicorn
        
        logger.info("🎯 Starting server...")
        uvicorn.run(
            "api.api:app",
            host=host,
            port=port,
            reload=debug,
            log_level="info" if debug else "warning",
            access_log=debug,
            loop="asyncio"
        )
        
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
