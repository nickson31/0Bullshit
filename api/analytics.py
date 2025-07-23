import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.auth import get_current_user
from database.database import Database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class AnalyticsResponse(BaseModel):
    user_stats: Dict
    campaign_stats: Dict
    search_stats: Dict
    engagement_stats: Dict
    growth_metrics: Dict
    period: str
    generated_at: str

class CampaignAnalytics(BaseModel):
    campaign_id: str
    total_messages: int
    sent_messages: int
    responses: int
    connections: int
    response_rate: float
    connection_rate: float
    personalization_avg: float
    performance_score: float

class UserEngagementMetrics(BaseModel):
    daily_active_users: int
    weekly_active_users: int
    monthly_active_users: int
    retention_rate: float
    churn_rate: float
    avg_session_duration: float

class AnalyticsManager:
    def __init__(self):
        self.db = Database()
    
    async def get_user_analytics(self, user_id: UUID, period: str = "30d") -> Dict:
        """
        Obtiene analytics completos para un usuario específico
        """
        try:
            # Calcular fechas del período
            start_date, end_date = self._calculate_period_dates(period)
            
            # Obtener métricas paralelas
            user_stats = await self._get_user_stats(user_id, start_date, end_date)
            campaign_stats = await self._get_campaign_stats(user_id, start_date, end_date)
            search_stats = await self._get_search_stats(user_id, start_date, end_date)
            engagement_stats = await self._get_engagement_stats(user_id, start_date, end_date)
            growth_metrics = await self._get_growth_metrics(user_id, start_date, end_date)
            
            return {
                "user_stats": user_stats,
                "campaign_stats": campaign_stats,
                "search_stats": search_stats,
                "engagement_stats": engagement_stats,
                "growth_metrics": growth_metrics,
                "period": period,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting user analytics: {e}")
            raise HTTPException(status_code=500, detail="Error generating analytics")

    async def get_platform_analytics(self, period: str = "30d") -> Dict:
        """
        Obtiene analytics generales de la plataforma
        """
        try:
            start_date, end_date = self._calculate_period_dates(period)
            
            # Métricas de usuario
            user_metrics = await self._get_platform_user_metrics(start_date, end_date)
            
            # Métricas de campañas
            campaign_metrics = await self._get_platform_campaign_metrics(start_date, end_date)
            
            # Métricas de búsquedas
            search_metrics = await self._get_platform_search_metrics(start_date, end_date)
            
            # Métricas de revenue
            revenue_metrics = await self._get_revenue_metrics(start_date, end_date)
            
            # Métricas de engagement
            engagement_metrics = await self._get_platform_engagement_metrics(start_date, end_date)
            
            return {
                "user_metrics": user_metrics,
                "campaign_metrics": campaign_metrics,
                "search_metrics": search_metrics,
                "revenue_metrics": revenue_metrics,
                "engagement_metrics": engagement_metrics,
                "period": period,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting platform analytics: {e}")
            raise HTTPException(status_code=500, detail="Error generating platform analytics")

    async def _get_user_stats(self, user_id: UUID, start_date: datetime, end_date: datetime) -> Dict:
        """
        Obtiene estadísticas básicas del usuario
        """
        try:
            # Información del usuario
            user_query = self.db.supabase.table("users")\
                .select("*")\
                .eq("id", str(user_id))\
                .execute()
            
            if not user_query.data:
                return {}
            
            user = user_query.data[0]
            
            # Proyectos del usuario
            projects_query = self.db.supabase.table("projects")\
                .select("*")\
                .eq("user_id", str(user_id))\
                .execute()
            
            projects = projects_query.data if projects_query.data else []
            
            # Actividad reciente
            conversations_query = self.db.supabase.table("conversations")\
                .select("*")\
                .eq("user_id", str(user_id))\
                .gte("created_at", start_date.isoformat())\
                .lte("created_at", end_date.isoformat())\
                .execute()
            
            conversations = conversations_query.data if conversations_query.data else []
            
            # Créditos usados en el período
            searches_query = self.db.supabase.table("search_results")\
                .select("credits_used")\
                .eq("user_id", str(user_id))\
                .gte("created_at", start_date.isoformat())\
                .lte("created_at", end_date.isoformat())\
                .execute()
            
            total_credits_used = sum(
                search.get("credits_used", 0) 
                for search in (searches_query.data if searches_query.data else [])
            )
            
            return {
                "user_id": str(user_id),
                "plan": user.get("plan", "free"),
                "credits_remaining": user.get("credits", 0),
                "credits_used_period": total_credits_used,
                "projects_count": len(projects),
                "conversations_count": len(conversations),
                "account_age_days": (datetime.now() - datetime.fromisoformat(user["created_at"])).days,
                "last_activity": max(
                    [conv["created_at"] for conv in conversations] + [user["updated_at"]]
                ) if conversations else user["updated_at"]
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}

    async def _get_campaign_stats(self, user_id: UUID, start_date: datetime, end_date: datetime) -> Dict:
        """
        Obtiene estadísticas de campañas del usuario
        """
        try:
            # Campañas del período
            campaigns_query = self.db.supabase.table("outreach_campaigns")\
                .select("*")\
                .eq("user_id", str(user_id))\
                .gte("created_at", start_date.isoformat())\
                .lte("created_at", end_date.isoformat())\
                .execute()
            
            campaigns = campaigns_query.data if campaigns_query.data else []
            
            if not campaigns:
                return {
                    "total_campaigns": 0,
                    "active_campaigns": 0,
                    "total_targets": 0,
                    "messages_sent": 0,
                    "responses_received": 0,
                    "connections_made": 0,
                    "response_rate": 0.0,
                    "connection_rate": 0.0
                }
            
            # Estadísticas agregadas
            total_campaigns = len(campaigns)
            active_campaigns = len([c for c in campaigns if c.get("status") == "active"])
            
            # Obtener targets de todas las campañas
            campaign_ids = [c["id"] for c in campaigns]
            targets_query = self.db.supabase.table("outreach_targets")\
                .select("*")\
                .in_("campaign_id", campaign_ids)\
                .execute()
            
            targets = targets_query.data if targets_query.data else []
            
            total_targets = len(targets)
            messages_sent = len([t for t in targets if t.get("status") in ["sent", "responded", "connected"]])
            responses_received = len([t for t in targets if t.get("status") == "responded"])
            connections_made = len([t for t in targets if t.get("status") == "connected"])
            
            response_rate = (responses_received / messages_sent * 100) if messages_sent > 0 else 0
            connection_rate = (connections_made / messages_sent * 100) if messages_sent > 0 else 0
            
            return {
                "total_campaigns": total_campaigns,
                "active_campaigns": active_campaigns,
                "total_targets": total_targets,
                "messages_sent": messages_sent,
                "responses_received": responses_received,
                "connections_made": connections_made,
                "response_rate": round(response_rate, 2),
                "connection_rate": round(connection_rate, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting campaign stats: {e}")
            return {}

    async def _get_search_stats(self, user_id: UUID, start_date: datetime, end_date: datetime) -> Dict:
        """
        Obtiene estadísticas de búsquedas del usuario
        """
        try:
            searches_query = self.db.supabase.table("search_results")\
                .select("*")\
                .eq("user_id", str(user_id))\
                .gte("created_at", start_date.isoformat())\
                .lte("created_at", end_date.isoformat())\
                .execute()
            
            searches = searches_query.data if searches_query.data else []
            
            if not searches:
                return {
                    "total_searches": 0,
                    "total_results_found": 0,
                    "avg_relevance_score": 0.0,
                    "most_searched_category": None,
                    "search_frequency": "low"
                }
            
            total_searches = len(searches)
            total_results_found = sum(search.get("total_found", 0) for search in searches)
            
            # Calcular promedio de relevancia
            relevance_scores = [
                search.get("average_relevance", 0) 
                for search in searches 
                if search.get("average_relevance")
            ]
            avg_relevance_score = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
            
            # Categoría más buscada (esto requeriría almacenar la categoría en search_results)
            # Por ahora usaremos un placeholder
            most_searched_category = "fintech"  # Placeholder
            
            # Frecuencia de búsqueda
            days_in_period = (end_date - start_date).days
            searches_per_day = total_searches / days_in_period if days_in_period > 0 else 0
            
            if searches_per_day >= 1:
                search_frequency = "high"
            elif searches_per_day >= 0.3:
                search_frequency = "medium"
            else:
                search_frequency = "low"
            
            return {
                "total_searches": total_searches,
                "total_results_found": total_results_found,
                "avg_relevance_score": round(avg_relevance_score, 2),
                "most_searched_category": most_searched_category,
                "search_frequency": search_frequency,
                "searches_per_day": round(searches_per_day, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting search stats: {e}")
            return {}

    async def _get_engagement_stats(self, user_id: UUID, start_date: datetime, end_date: datetime) -> Dict:
        """
        Obtiene estadísticas de engagement del usuario
        """
        try:
            # Conversaciones del período
            conversations_query = self.db.supabase.table("conversations")\
                .select("*")\
                .eq("user_id", str(user_id))\
                .gte("created_at", start_date.isoformat())\
                .lte("created_at", end_date.isoformat())\
                .execute()
            
            conversations = conversations_query.data if conversations_query.data else []
            
            # Mensajes en conversaciones
            total_messages = 0
            total_session_time = 0
            
            for conv in conversations:
                # Obtener mensajes de la conversación
                messages_query = self.db.supabase.table("messages")\
                    .select("*")\
                    .eq("conversation_id", conv["id"])\
                    .execute()
                
                messages = messages_query.data if messages_query.data else []
                total_messages += len(messages)
                
                # Calcular duración de sesión (aproximada)
                if len(messages) > 1:
                    first_message = min(messages, key=lambda x: x["created_at"])
                    last_message = max(messages, key=lambda x: x["created_at"])
                    
                    session_duration = (
                        datetime.fromisoformat(last_message["created_at"]) - 
                        datetime.fromisoformat(first_message["created_at"])
                    ).total_seconds() / 60  # en minutos
                    
                    total_session_time += session_duration
            
            avg_session_duration = total_session_time / len(conversations) if conversations else 0
            
            # Días activos
            active_days = len(set(
                datetime.fromisoformat(conv["created_at"]).date() 
                for conv in conversations
            ))
            
            # Engagement score (0-100)
            days_in_period = (end_date - start_date).days
            activity_ratio = active_days / days_in_period if days_in_period > 0 else 0
            message_factor = min(total_messages / 50, 1)  # Normalizar a 50 mensajes
            session_factor = min(avg_session_duration / 30, 1)  # Normalizar a 30 min
            
            engagement_score = (activity_ratio * 40 + message_factor * 30 + session_factor * 30)
            
            return {
                "total_conversations": len(conversations),
                "total_messages": total_messages,
                "active_days": active_days,
                "avg_session_duration": round(avg_session_duration, 2),
                "engagement_score": round(engagement_score, 2),
                "activity_ratio": round(activity_ratio * 100, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting engagement stats: {e}")
            return {}

    async def _get_growth_metrics(self, user_id: UUID, start_date: datetime, end_date: datetime) -> Dict:
        """
        Obtiene métricas de crecimiento y progreso del usuario
        """
        try:
            # Progreso de onboarding
            onboarding_query = self.db.supabase.table("user_onboarding")\
                .select("*")\
                .eq("user_id", str(user_id))\
                .execute()
            
            onboarding = onboarding_query.data[0] if onboarding_query.data else None
            onboarding_completed = onboarding.get("completed", False) if onboarding else False
            
            # Completeness de proyectos
            projects_query = self.db.supabase.table("projects")\
                .select("*")\
                .eq("user_id", str(user_id))\
                .execute()
            
            projects = projects_query.data if projects_query.data else []
            
            # Calcular completeness promedio (esto requeriría implementar la función)
            avg_project_completeness = 75.0  # Placeholder
            
            # Evolución de uso de créditos
            prev_start = start_date - (end_date - start_date)
            prev_searches = self.db.supabase.table("search_results")\
                .select("credits_used")\
                .eq("user_id", str(user_id))\
                .gte("created_at", prev_start.isoformat())\
                .lt("created_at", start_date.isoformat())\
                .execute()
            
            current_searches = self.db.supabase.table("search_results")\
                .select("credits_used")\
                .eq("user_id", str(user_id))\
                .gte("created_at", start_date.isoformat())\
                .lte("created_at", end_date.isoformat())\
                .execute()
            
            prev_credits = sum(s.get("credits_used", 0) for s in (prev_searches.data or []))
            current_credits = sum(s.get("credits_used", 0) for s in (current_searches.data or []))
            
            credit_growth = ((current_credits - prev_credits) / prev_credits * 100) if prev_credits > 0 else 0
            
            return {
                "onboarding_completed": onboarding_completed,
                "projects_count": len(projects),
                "avg_project_completeness": avg_project_completeness,
                "credit_usage_growth": round(credit_growth, 2),
                "user_maturity_score": round((
                    (1 if onboarding_completed else 0) * 25 +
                    min(len(projects) / 3, 1) * 25 +
                    (avg_project_completeness / 100) * 25 +
                    min(current_credits / 100, 1) * 25
                ), 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting growth metrics: {e}")
            return {}

    def _calculate_period_dates(self, period: str) -> Tuple[datetime, datetime]:
        """
        Calcula fechas de inicio y fin para el período especificado
        """
        end_date = datetime.now()
        
        if period == "7d":
            start_date = end_date - timedelta(days=7)
        elif period == "30d":
            start_date = end_date - timedelta(days=30)
        elif period == "90d":
            start_date = end_date - timedelta(days=90)
        elif period == "1y":
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=30)  # Default
        
        return start_date, end_date

    async def _get_platform_user_metrics(self, start_date: datetime, end_date: datetime) -> Dict:
        """
        Obtiene métricas de usuarios de la plataforma
        """
        try:
            # Usuarios totales
            total_users_query = self.db.supabase.table("users")\
                .select("id", count="exact")\
                .execute()
            
            total_users = total_users_query.count if total_users_query.count else 0
            
            # Nuevos usuarios en el período
            new_users_query = self.db.supabase.table("users")\
                .select("id", count="exact")\
                .gte("created_at", start_date.isoformat())\
                .lte("created_at", end_date.isoformat())\
                .execute()
            
            new_users = new_users_query.count if new_users_query.count else 0
            
            # Usuarios activos (que han hecho búsquedas o chats)
            active_users_query = self.db.supabase.table("conversations")\
                .select("user_id")\
                .gte("created_at", start_date.isoformat())\
                .lte("created_at", end_date.isoformat())\
                .execute()
            
            active_user_ids = set(conv["user_id"] for conv in (active_users_query.data or []))
            active_users = len(active_user_ids)
            
            return {
                "total_users": total_users,
                "new_users": new_users,
                "active_users": active_users,
                "activation_rate": round((active_users / new_users * 100) if new_users > 0 else 0, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting platform user metrics: {e}")
            return {}

    async def _get_revenue_metrics(self, start_date: datetime, end_date: datetime) -> Dict:
        """
        Obtiene métricas de revenue
        """
        try:
            # Suscripciones activas
            subscriptions_query = self.db.supabase.table("subscriptions")\
                .select("*")\
                .eq("status", "active")\
                .execute()
            
            subscriptions = subscriptions_query.data if subscriptions_query.data else []
            
            # Calcular MRR por plan
            plan_counts = {}
            total_mrr = 0
            
            for sub in subscriptions:
                plan = sub.get("plan", "free")
                plan_counts[plan] = plan_counts.get(plan, 0) + 1
                
                # Precios de planes (debería venir de configuración)
                plan_prices = {"pro": 19, "outreach": 49}
                total_mrr += plan_prices.get(plan, 0)
            
            # Compras de créditos en el período
            credit_purchases_query = self.db.supabase.table("credit_purchases")\
                .select("amount_usd")\
                .gte("created_at", start_date.isoformat())\
                .lte("created_at", end_date.isoformat())\
                .execute()
            
            credit_revenue = sum(
                purchase.get("amount_usd", 0) 
                for purchase in (credit_purchases_query.data or [])
            )
            
            return {
                "total_subscriptions": len(subscriptions),
                "plan_distribution": plan_counts,
                "monthly_recurring_revenue": total_mrr,
                "credit_revenue_period": credit_revenue,
                "average_revenue_per_user": round(total_mrr / len(subscriptions), 2) if subscriptions else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting revenue metrics: {e}")
            return {}


# Instancia global
analytics_manager = AnalyticsManager()

# Endpoints
@router.get("/user", response_model=AnalyticsResponse)
async def get_user_analytics(
    period: str = "30d",
    current_user: UUID = Depends(get_current_user)
):
    """
    Obtiene analytics del usuario actual
    """
    return await analytics_manager.get_user_analytics(current_user, period)

@router.get("/campaign/{campaign_id}")
async def get_campaign_analytics(
    campaign_id: str,
    current_user: UUID = Depends(get_current_user)
):
    """
    Obtiene analytics de una campaña específica
    """
    try:
        # Verificar que la campaña pertenece al usuario
        campaign_query = analytics_manager.db.supabase.table("outreach_campaigns")\
            .select("*")\
            .eq("id", campaign_id)\
            .eq("user_id", str(current_user))\
            .execute()
        
        if not campaign_query.data:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        campaign = campaign_query.data[0]
        
        # Obtener targets de la campaña
        targets_query = analytics_manager.db.supabase.table("outreach_targets")\
            .select("*")\
            .eq("campaign_id", campaign_id)\
            .execute()
        
        targets = targets_query.data if targets_query.data else []
        
        # Calcular métricas
        total_messages = len(targets)
        sent_messages = len([t for t in targets if t.get("status") in ["sent", "responded", "connected"]])
        responses = len([t for t in targets if t.get("status") == "responded"])
        connections = len([t for t in targets if t.get("status") == "connected"])
        
        response_rate = (responses / sent_messages * 100) if sent_messages > 0 else 0
        connection_rate = (connections / sent_messages * 100) if sent_messages > 0 else 0
        
        # Score de personalización promedio (placeholder)
        personalization_avg = 85.0
        
        # Score de performance general
        performance_score = (response_rate + connection_rate + personalization_avg) / 3
        
        return CampaignAnalytics(
            campaign_id=campaign_id,
            total_messages=total_messages,
            sent_messages=sent_messages,
            responses=responses,
            connections=connections,
            response_rate=round(response_rate, 2),
            connection_rate=round(connection_rate, 2),
            personalization_avg=round(personalization_avg, 2),
            performance_score=round(performance_score, 2)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign analytics: {e}")
        raise HTTPException(status_code=500, detail="Error generating campaign analytics")

@router.get("/platform")
async def get_platform_analytics(
    period: str = "30d",
    current_user: UUID = Depends(get_current_user)
):
    """
    Obtiene analytics de la plataforma (solo para admins)
    """
    # Verificar que el usuario es admin
    user_query = analytics_manager.db.supabase.table("users")\
        .select("role")\
        .eq("id", str(current_user))\
        .execute()
    
    if not user_query.data or user_query.data[0].get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return await analytics_manager.get_platform_analytics(period)