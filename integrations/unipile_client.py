# integrations/unipile_client.py
import os
import requests
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class UnipileClient:
    def __init__(self):
        self.api_url = os.getenv("UNIPILE_API_URL", "https://api2.unipile.com:13044/api/v1")
        self.api_key = os.getenv("UNIPILE_API_KEY")
        self.dsn = os.getenv("UNIPILE_DSN")
        
        if not self.api_key:
            logger.warning("UNIPILE_API_KEY not configured - Unipile features disabled")
    
    def _get_headers(self) -> Dict[str, str]:
        """Headers estándar para requests a Unipile"""
        return {
            "X-API-KEY": self.api_key,
            "accept": "application/json",
            "content-type": "application/json"
        }
    
    def _check_config(self):
        """Verificar que la configuración esté lista"""
        if not self.api_key:
            raise ValueError("Unipile API key not configured")
    
    # ==========================================
    # GESTIÓN DE CUENTAS
    # ==========================================
    
    async def create_hosted_auth_link(self, user_id: str, success_url: str, failure_url: str, notify_url: str) -> Dict[str, Any]:
        """Crear link de autenticación hosteada para LinkedIn"""
        self._check_config()
        
        payload = {
            "type": "create",
            "providers": ["LINKEDIN"],
            "api_url": self.api_url,
            "expiresOn": (datetime.now() + timedelta(hours=2)).isoformat() + "Z",
            "success_redirect_url": success_url,
            "failure_redirect_url": failure_url,
            "notify_url": notify_url,
            "name": user_id  # Tu user_id interno para matching
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/hosted/accounts/link",
                json=payload,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error creating hosted auth link: {e}")
            raise
    
    async def reconnect_account(self, account_id: str, user_id: str) -> Dict[str, Any]:
        """Reconectar cuenta desconectada"""
        self._check_config()
        
        payload = {
            "type": "reconnect",
            "providers": ["LINKEDIN"],
            "api_url": self.api_url,
            "expiresOn": (datetime.now() + timedelta(hours=2)).isoformat() + "Z",
            "reconnect_account": account_id,
            "name": user_id
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/hosted/accounts/link",
                json=payload,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error reconnecting account: {e}")
            raise
    
    async def get_accounts(self) -> List[Dict[str, Any]]:
        """Obtener todas las cuentas conectadas"""
        self._check_config()
        
        try:
            response = requests.get(
                f"{self.api_url}/accounts",
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("items", [])
        except Exception as e:
            logger.error(f"Error getting accounts: {e}")
            raise
    
    async def get_account_status(self, account_id: str) -> Dict[str, Any]:
        """Verificar estado de cuenta específica"""
        self._check_config()
        
        try:
            response = requests.get(
                f"{self.api_url}/accounts/{account_id}",
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting account status: {e}")
            raise
    
    # ==========================================
    # BÚSQUEDA DE PERFILES
    # ==========================================
    
    async def search_linkedin_people(self, account_id: str, keywords: str, location: List[str] = None, 
                                   industry: List[str] = None, limit: int = 10) -> Dict[str, Any]:
        """Buscar personas en LinkedIn"""
        self._check_config()
        
        search_params = {
            "api": "classic",  # o "sales_navigator" si disponible
            "category": "people",
            "keywords": keywords,
            "limit": limit
        }
        
        if location:
            # Primero necesitas convertir location names a IDs
            location_ids = await self._get_location_ids(account_id, location)
            if location_ids:
                search_params["location"] = location_ids
        
        if industry:
            industry_ids = await self._get_industry_ids(account_id, industry)
            if industry_ids:
                search_params["industry"] = {"include": industry_ids}
        
        try:
            response = requests.post(
                f"{self.api_url}/linkedin/search",
                params={"account_id": account_id},
                json=search_params,
                headers=self._get_headers(),
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error searching LinkedIn people: {e}")
            raise
    
    async def _get_location_ids(self, account_id: str, locations: List[str]) -> List[int]:
        """Convertir nombres de ubicación a IDs de LinkedIn"""
        location_ids = []
        for location in locations:
            try:
                response = requests.get(
                    f"{self.api_url}/linkedin/search/parameters",
                    params={
                        "account_id": account_id,
                        "type": "LOCATION",
                        "keywords": location,
                        "limit": 5
                    },
                    headers=self._get_headers(),
                    timeout=30
                )
                response.raise_for_status()
                results = response.json().get("items", [])
                if results:
                    location_ids.append(int(results[0]["id"]))
            except Exception as e:
                logger.warning(f"Could not get location ID for {location}: {e}")
        
        return location_ids
    
    async def _get_industry_ids(self, account_id: str, industries: List[str]) -> List[str]:
        """Convertir nombres de industria a IDs de LinkedIn"""
        industry_ids = []
        for industry in industries:
            try:
                response = requests.get(
                    f"{self.api_url}/linkedin/search/parameters",
                    params={
                        "account_id": account_id,
                        "type": "INDUSTRY",
                        "keywords": industry,
                        "limit": 5
                    },
                    headers=self._get_headers(),
                    timeout=30
                )
                response.raise_for_status()
                results = response.json().get("items", [])
                if results:
                    industry_ids.append(results[0]["id"])
            except Exception as e:
                logger.warning(f"Could not get industry ID for {industry}: {e}")
        
        return industry_ids
    
    # ==========================================
    # GESTIÓN DE PERFILES
    # ==========================================
    
    async def get_profile(self, account_id: str, profile_identifier: str, sections: str = "*") -> Dict[str, Any]:
        """Obtener perfil completo de LinkedIn"""
        self._check_config()
        
        try:
            response = requests.get(
                f"{self.api_url}/users/{profile_identifier}",
                params={
                    "account_id": account_id,
                    "linkedin_sections": sections
                },
                headers=self._get_headers(),
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting LinkedIn profile: {e}")
            raise
    
    # ==========================================
    # OUTREACH - INVITACIONES
    # ==========================================
    
    async def send_invitation(self, account_id: str, provider_id: str, message: str) -> Dict[str, Any]:
        """Enviar invitación de LinkedIn"""
        self._check_config()
        
        payload = {
            "account_id": account_id,
            "provider_id": provider_id,
            "message": message[:300]  # LinkedIn límite 300 caracteres
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/users/invite",
                json=payload,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error sending LinkedIn invitation: {e}")
            # Manejar errores específicos
            if "cannot_resend_yet" in str(e):
                raise Exception("LinkedIn invitation limit reached")
            elif "insufficient_credit" in str(e):
                raise Exception("Insufficient LinkedIn credits")
            raise
    
    # ==========================================
    # OUTREACH - MENSAJES
    # ==========================================
    
    async def send_message(self, account_id: str, attendee_provider_id: str, text: str) -> Dict[str, Any]:
        """Enviar mensaje directo a conexión existente"""
        self._check_config()
        
        payload = {
            "account_id": account_id,
            "attendees_ids": [attendee_provider_id],
            "text": text
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/chats",
                data=payload,  # multipart/form-data
                headers={
                    "X-API-KEY": self.api_key,
                    "accept": "application/json"
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error sending LinkedIn message: {e}")
            raise
    
    async def send_inmail(self, account_id: str, provider_id: str, text: str, api_type: str = "classic") -> Dict[str, Any]:
        """Enviar InMail (requiere LinkedIn Premium)"""
        self._check_config()
        
        payload = {
            "account_id": account_id,
            "attendees_ids": [provider_id],
            "text": text,
            "linkedin": {
                "api": api_type,  # classic, recruiter, sales_navigator
                "inmail": True
            }
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/chats",
                data=payload,
                headers={
                    "X-API-KEY": self.api_key,
                    "accept": "application/json"
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error sending LinkedIn InMail: {e}")
            raise
    
    # ==========================================
    # GESTIÓN DE CONVERSACIONES
    # ==========================================
    
    async def get_chats(self, account_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtener lista de chats"""
        self._check_config()
        
        try:
            response = requests.get(
                f"{self.api_url}/chats",
                params={
                    "account_id": account_id,
                    "limit": limit
                },
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("items", [])
        except Exception as e:
            logger.error(f"Error getting chats: {e}")
            raise
    
    async def get_messages(self, chat_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtener mensajes de un chat"""
        self._check_config()
        
        try:
            response = requests.get(
                f"{self.api_url}/chats/{chat_id}/messages",
                params={"limit": limit},
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("items", [])
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            raise
    
    # ==========================================
    # RELACIONES Y CONEXIONES
    # ==========================================
    
    async def get_relations(self, account_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Obtener conexiones/relaciones"""
        self._check_config()
        
        try:
            response = requests.get(
                f"{self.api_url}/users/relations",
                params={
                    "account_id": account_id,
                    "limit": limit
                },
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("items", [])
        except Exception as e:
            logger.error(f"Error getting relations: {e}")
            raise
    
    async def get_sent_invitations(self, account_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Obtener invitaciones enviadas"""
        self._check_config()
        
        try:
            response = requests.get(
                f"{self.api_url}/users/invitations/sent",
                params={
                    "account_id": account_id,
                    "limit": limit
                },
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("items", [])
        except Exception as e:
            logger.error(f"Error getting sent invitations: {e}")
            raise
    
    # ==========================================
    # WEBHOOKS
    # ==========================================
    
    async def create_webhook(self, request_url: str, source: str = "messaging") -> Dict[str, Any]:
        """Crear webhook para recibir eventos"""
        self._check_config()
        
        payload = {
            "request_url": request_url,
            "source": source,  # messaging, users, emails
            "headers": [
                {
                    "key": "Content-Type",
                    "value": "application/json"
                }
            ]
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/webhooks",
                json=payload,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error creating webhook: {e}")
            raise
    
    # ==========================================
    # RATE LIMITING Y HELPERS
    # ==========================================
    
    async def check_rate_limits(self, account_id: str) -> Dict[str, Any]:
        """Verificar límites de rate disponibles"""
        # Por ahora retornar valores simulados
        # En una implementación real, esto vendría de tu base de datos
        # donde trackeas el uso diario/semanal
        return {
            "daily_invitations_sent": 0,
            "daily_invitations_limit": 80,
            "weekly_invitations_sent": 0,
            "weekly_invitations_limit": 200,
            "daily_searches": 0,
            "daily_searches_limit": 100,
            "can_send_invitation": True,
            "can_search": True,
            "next_available_slot": datetime.now().isoformat()
        }
    
    async def wait_for_rate_limit(self, action_type: str, account_id: str):
        """Esperar si se han alcanzado límites de rate"""
        # Implementar lógica de espera basada en límites de LinkedIn
        # Por ahora esperar tiempo random entre acciones
        if action_type == "invitation":
            wait_time = 60  # 1 minuto entre invitaciones
        elif action_type == "search":
            wait_time = 30  # 30 segundos entre búsquedas
        else:
            wait_time = 10
        
        logger.info(f"Waiting {wait_time}s for rate limit compliance")
        await asyncio.sleep(wait_time)

# Instancia global
try:
    unipile_client = UnipileClient()
except Exception as e:
    logger.error(f"Error initializing Unipile client: {e}")
    unipile_client = None
