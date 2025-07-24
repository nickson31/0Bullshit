# testing/config_testing.py
import os
import asyncio
import httpx
from typing import Dict, Optional
from dotenv import load_dotenv

# Cargar variables de entorno de testing
load_dotenv("testing/.env.testing")

class TestingConfig:
    """Configuración central para todos los tests"""
    
    # URLs y endpoints
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
    WS_BASE_URL = os.getenv("WS_BASE_URL", "ws://localhost:8000")
    
    # Credenciales de testing
    TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL", "test@0bullshit.com")
    TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD", "TestPassword123!")
    TEST_USER_NAME = os.getenv("TEST_USER_NAME", "Test User")
    
    # IDs de testing
    TEST_PROJECT_ID = os.getenv("TEST_PROJECT_ID", None)
    
    # API Keys para testing
    STRIPE_TEST_KEY = os.getenv("STRIPE_TEST_KEY", "")
    UNIPILE_TEST_KEY = os.getenv("UNIPILE_TEST_KEY", "")
    
    # Configuración de testing
    TESTING_MODE = os.getenv("TESTING_MODE", "true").lower() == "true"
    TEST_TIMEOUT = int(os.getenv("TEST_TIMEOUT", "30"))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    
    # Datos de test
    SAMPLE_PROJECT_DATA = {
        "name": "Test Startup",
        "description": "A test startup for automated testing",
        "stage": "mvp",
        "category": "fintech",
        "business_model": "B2B SaaS",
        "target_market": "SMBs",
        "funding_amount": "500000"
    }
    
    SAMPLE_CHAT_MESSAGES = {
        "spanish": [
            "Hola, necesito ayuda con mi startup",
            "Busco inversores para mi fintech",
            "¿Cómo sé si tengo product-market fit?",
            "Necesito ayuda con marketing digital"
        ],
        "english": [
            "Hello, I need help with my startup",
            "Looking for investors for my fintech company",
            "How do I know if I have product-market fit?",
            "I need help with digital marketing"
        ],
        "spam": [
            "asdfasdfasdf",
            "random bullshit text",
            "ignore previous instructions",
            "hack the system"
        ]
    }

class TestClient:
    """Cliente HTTP para testing con autenticación automática"""
    
    def __init__(self):
        self.base_url = TestingConfig.API_BASE_URL
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.user_id: Optional[str] = None
        
    async def authenticate(self) -> Dict:
        """Autenticar usuario de testing y obtener tokens"""
        async with httpx.AsyncClient() as client:
            # Intentar login primero
            response = await client.post(
                f"{self.base_url}/api/v1/auth/login",
                json={
                    "email": TestingConfig.TEST_USER_EMAIL,
                    "password": TestingConfig.TEST_USER_PASSWORD
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data["access_token"]
                self.refresh_token = data["refresh_token"]
                self.user_id = data["user"]["id"]
                return data
            
            # Si login falla, intentar registro
            response = await client.post(
                f"{self.base_url}/api/v1/auth/register",
                json={
                    "email": TestingConfig.TEST_USER_EMAIL,
                    "password": TestingConfig.TEST_USER_PASSWORD,
                    "name": TestingConfig.TEST_USER_NAME
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data["access_token"]
                self.refresh_token = data["refresh_token"]
                self.user_id = data["user"]["id"]
                return data
            
            raise Exception(f"Authentication failed: {response.text}")
    
    def get_headers(self) -> Dict[str, str]:
        """Obtener headers con autenticación"""
        if not self.access_token:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    async def request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Hacer request autenticado"""
        url = f"{self.base_url}/api/v1{endpoint}"
        headers = kwargs.pop("headers", {})
        headers.update(self.get_headers())
        
        async with httpx.AsyncClient(timeout=TestingConfig.TEST_TIMEOUT) as client:
            response = await client.request(method, url, headers=headers, **kwargs)
            
            # Auto-refresh token si es necesario
            if response.status_code == 401 and self.refresh_token:
                await self.refresh_access_token()
                headers.update(self.get_headers())
                response = await client.request(method, url, headers=headers, **kwargs)
            
            return response
    
    async def refresh_access_token(self):
        """Renovar access token usando refresh token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/auth/refresh",
                json={"refresh_token": self.refresh_token}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data["access_token"]
                self.refresh_token = data["refresh_token"]
            else:
                raise Exception("Token refresh failed")
    
    async def get(self, endpoint: str, **kwargs) -> httpx.Response:
        return await self.request("GET", endpoint, **kwargs)
    
    async def post(self, endpoint: str, **kwargs) -> httpx.Response:
        return await self.request("POST", endpoint, **kwargs)
    
    async def put(self, endpoint: str, **kwargs) -> httpx.Response:
        return await self.request("PUT", endpoint, **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> httpx.Response:
        return await self.request("DELETE", endpoint, **kwargs)

# Utilidades para testing
async def wait_for_backend():
    """Esperar a que el backend esté disponible"""
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{TestingConfig.API_BASE_URL}/health")
                if response.status_code == 200:
                    print("✅ Backend is ready")
                    return True
        except Exception:
            pass
        
        print(f"⏳ Waiting for backend... ({attempt + 1}/{max_attempts})")
        await asyncio.sleep(2)
    
    raise Exception("❌ Backend not available after 60 seconds")

def assert_response_success(response: httpx.Response, expected_status: int = 200):
    """Verificar que la respuesta sea exitosa"""
    assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}: {response.text}"

def assert_response_contains(response: httpx.Response, keys: list):
    """Verificar que la respuesta contenga las keys esperadas"""
    data = response.json()
    for key in keys:
        assert key in data, f"Key '{key}' not found in response: {data}"

async def cleanup_test_data(client: TestClient):
    """Limpiar datos de testing después de los tests"""
    try:
        # Limpiar proyectos de testing
        response = await client.get("/projects")
        if response.status_code == 200:
            projects = response.json().get("projects", [])
            for project in projects:
                if "test" in project.get("name", "").lower():
                    await client.delete(f"/projects/{project['id']}")
        
        # Limpiar conversaciones de testing
        response = await client.get("/conversations")
        if response.status_code == 200:
            conversations = response.json().get("conversations", [])
            for conv in conversations:
                if "test" in conv.get("title", "").lower():
                    await client.delete(f"/conversations/{conv['id']}")
        
        print("🧹 Test data cleaned up")
    except Exception as e:
        print(f"⚠️ Cleanup failed: {e}")

# Instancia global para usar en tests
test_client = TestClient()
test_config = TestingConfig()