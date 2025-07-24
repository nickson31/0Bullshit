# campaigns/rate_limiter.py
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class LinkedInRateLimiter:
    """
    Rate limiter para LinkedIn automation según las mejores prácticas y límites de Unipile:
    - 80-100 invitaciones/día (200/semana máx)
    - 100 profile visits/día  
    - 1000 search results/día (2500 con Sales Navigator)
    """
    
    def __init__(self):
        # Contadores por cuenta de LinkedIn
        self.invitation_counts: Dict[str, Dict] = {}
        self.profile_visit_counts: Dict[str, Dict] = {}
        self.search_counts: Dict[str, Dict] = {}
        
        # Límites diarios
        self.DAILY_INVITATION_LIMIT = 90  # Conservative limit
        self.DAILY_PROFILE_VISIT_LIMIT = 100
        self.DAILY_SEARCH_LIMIT = 1000
        
        # Límites semanales
        self.WEEKLY_INVITATION_LIMIT = 200
        
        # Lock para thread safety
        self._lock = asyncio.Lock()
    
    async def can_send_invitation(self, linkedin_account_id: str) -> bool:
        """Verificar si se puede enviar una invitación"""
        async with self._lock:
            try:
                today = datetime.now().date()
                week_start = today - timedelta(days=today.weekday())
                
                # Obtener contadores actuales
                daily_count = await self._get_daily_count(linkedin_account_id, 'invitations', today)
                weekly_count = await self._get_weekly_count(linkedin_account_id, 'invitations', week_start)
                
                # Verificar límites
                if daily_count >= self.DAILY_INVITATION_LIMIT:
                    logger.warning(f"Daily invitation limit reached for account {linkedin_account_id}")
                    return False
                
                if weekly_count >= self.WEEKLY_INVITATION_LIMIT:
                    logger.warning(f"Weekly invitation limit reached for account {linkedin_account_id}")
                    return False
                
                return True
                
            except Exception as e:
                logger.error(f"Error checking invitation rate limit: {e}")
                return False
    
    async def can_visit_profile(self, linkedin_account_id: str) -> bool:
        """Verificar si se puede visitar un perfil"""
        async with self._lock:
            try:
                today = datetime.now().date()
                daily_count = await self._get_daily_count(linkedin_account_id, 'profile_visits', today)
                
                if daily_count >= self.DAILY_PROFILE_VISIT_LIMIT:
                    logger.warning(f"Daily profile visit limit reached for account {linkedin_account_id}")
                    return False
                
                return True
                
            except Exception as e:
                logger.error(f"Error checking profile visit rate limit: {e}")
                return False
    
    async def can_perform_search(self, linkedin_account_id: str) -> bool:
        """Verificar si se puede realizar una búsqueda"""
        async with self._lock:
            try:
                today = datetime.now().date()
                daily_count = await self._get_daily_count(linkedin_account_id, 'searches', today)
                
                if daily_count >= self.DAILY_SEARCH_LIMIT:
                    logger.warning(f"Daily search limit reached for account {linkedin_account_id}")
                    return False
                
                return True
                
            except Exception as e:
                logger.error(f"Error checking search rate limit: {e}")
                return False
    
    async def record_invitation_sent(self, linkedin_account_id: str):
        """Registrar que se envió una invitación"""
        async with self._lock:
            try:
                today = datetime.now().date()
                await self._increment_count(linkedin_account_id, 'invitations', today)
                logger.info(f"Invitation sent recorded for account {linkedin_account_id}")
                
            except Exception as e:
                logger.error(f"Error recording invitation sent: {e}")
    
    async def record_profile_visit(self, linkedin_account_id: str):
        """Registrar que se visitó un perfil"""
        async with self._lock:
            try:
                today = datetime.now().date()
                await self._increment_count(linkedin_account_id, 'profile_visits', today)
                logger.info(f"Profile visit recorded for account {linkedin_account_id}")
                
            except Exception as e:
                logger.error(f"Error recording profile visit: {e}")
    
    async def record_search_performed(self, linkedin_account_id: str):
        """Registrar que se realizó una búsqueda"""
        async with self._lock:
            try:
                today = datetime.now().date()
                await self._increment_count(linkedin_account_id, 'searches', today)
                logger.info(f"Search performed recorded for account {linkedin_account_id}")
                
            except Exception as e:
                logger.error(f"Error recording search performed: {e}")
    
    async def get_daily_limits_status(self, linkedin_account_id: str) -> Dict:
        """Obtener el estado actual de los límites diarios"""
        try:
            today = datetime.now().date()
            
            invitation_count = await self._get_daily_count(linkedin_account_id, 'invitations', today)
            profile_visit_count = await self._get_daily_count(linkedin_account_id, 'profile_visits', today)
            search_count = await self._get_daily_count(linkedin_account_id, 'searches', today)
            
            return {
                'invitations': {
                    'used': invitation_count,
                    'limit': self.DAILY_INVITATION_LIMIT,
                    'remaining': max(0, self.DAILY_INVITATION_LIMIT - invitation_count)
                },
                'profile_visits': {
                    'used': profile_visit_count,
                    'limit': self.DAILY_PROFILE_VISIT_LIMIT,
                    'remaining': max(0, self.DAILY_PROFILE_VISIT_LIMIT - profile_visit_count)
                },
                'searches': {
                    'used': search_count,
                    'limit': self.DAILY_SEARCH_LIMIT,
                    'remaining': max(0, self.DAILY_SEARCH_LIMIT - search_count)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting daily limits status: {e}")
            return {}
    
    async def _get_daily_count(self, linkedin_account_id: str, action_type: str, date) -> int:
        """Obtener contador diario para una acción específica"""
        try:
            from database.database import db
            
            # Query the database for daily count
            query = db.supabase.table("linkedin_rate_limits")\
                .select("count")\
                .eq("linkedin_account_id", linkedin_account_id)\
                .eq("action_type", action_type)\
                .eq("date", str(date))\
                .execute()
            
            if query.data:
                return query.data[0]['count']
            else:
                return 0
                
        except Exception as e:
            logger.error(f"Error getting daily count from database: {e}")
            return 0
    
    async def _get_weekly_count(self, linkedin_account_id: str, action_type: str, week_start) -> int:
        """Obtener contador semanal para una acción específica"""
        try:
            from database.database import db
            
            week_end = week_start + timedelta(days=6)
            
            # Query the database for weekly count
            query = db.supabase.table("linkedin_rate_limits")\
                .select("count")\
                .eq("linkedin_account_id", linkedin_account_id)\
                .eq("action_type", action_type)\
                .gte("date", str(week_start))\
                .lte("date", str(week_end))\
                .execute()
            
            if query.data:
                return sum(row['count'] for row in query.data)
            else:
                return 0
                
        except Exception as e:
            logger.error(f"Error getting weekly count from database: {e}")
            return 0
    
    async def _increment_count(self, linkedin_account_id: str, action_type: str, date):
        """Incrementar contador en la base de datos"""
        try:
            from database.database import db
            
            # Check if record exists
            existing = db.supabase.table("linkedin_rate_limits")\
                .select("*")\
                .eq("linkedin_account_id", linkedin_account_id)\
                .eq("action_type", action_type)\
                .eq("date", str(date))\
                .execute()
            
            if existing.data:
                # Update existing record
                new_count = existing.data[0]['count'] + 1
                db.supabase.table("linkedin_rate_limits")\
                    .update({"count": new_count, "updated_at": datetime.now().isoformat()})\
                    .eq("id", existing.data[0]['id'])\
                    .execute()
            else:
                # Create new record
                db.supabase.table("linkedin_rate_limits")\
                    .insert({
                        "linkedin_account_id": linkedin_account_id,
                        "action_type": action_type,
                        "date": str(date),
                        "count": 1,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    })\
                    .execute()
                    
        except Exception as e:
            logger.error(f"Error incrementing count in database: {e}")

# Global instance
linkedin_rate_limiter = LinkedInRateLimiter()