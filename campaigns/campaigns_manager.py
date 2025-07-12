# campaigns/campaign_manager.py
import asyncio
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime, timedelta
import random

from database.database import db
from integrations.unipile_client import unipile_client
from campaigns.message_generator import message_personalizer
from campaigns.rate_limiter import linkedin_rate_limiter

logger = logging.getLogger(__name__)

class CampaignManager:
    def __init__(self):
        self.active_campaigns = set()  # Track campaigns being processed
        self.processing_lock = asyncio.Lock()
        
    async def create_campaign(
        self, 
        user_id: UUID, 
        project_id: UUID, 
        name: str, 
        message_template: str,
        linkedin_account_id: str,
        target_investor_ids: List[UUID] = None
    ) -> Dict[str, Any]:
        """Crear nueva campaña de outreach"""
        try:
            campaign_id = uuid4()
            
            # Crear campaña en base de datos
            campaign_data = {
                "id": str(campaign_id),
                "user_id": str(user_id),
                "project_id": str(project_id),
                "name": name,
                "message_template": message_template,
                "linkedin_account_id": linkedin_account_id,
                "status": "draft",
                "total_targets": 0,
                "sent_count": 0,
                "reply_count": 0,
                "accepted_count": 0,
                "error_count": 0,
                "daily_limit": 80,
                "delay_between_sends": 120,
                "open_rate": 0.0,
                "response_rate": 0.0,
                "conversion_rate": 0.0,
                "created_at": datetime.now().isoformat(),
                "last_processed": None
            }
            
            result = db.supabase.table("outreach_campaigns").insert(campaign_data).execute()
            
            if not result.data:
                raise Exception("Failed to create campaign")
            
            # Si hay targets, añadirlos
            if target_investor_ids:
                await self.add_targets_to_campaign(campaign_id, target_investor_ids, message_template)
            
            return self._format_campaign_response(result.data[0])
            
        except Exception as e:
            logger.error(f"Error creating campaign: {e}")
            raise
    
    async def add_targets_to_campaign(
        self, 
        campaign_id: UUID, 
        investor_ids: List[UUID], 
        message_template: str
    ) -> List[Dict[str, Any]]:
        """Añadir targets a campaña"""
        try:
            # Obtener datos de inversores
            investors = await db.get_investors_by_ids(investor_ids)
            project = await self._get_campaign_project(campaign_id)
            
            targets = []
            for investor in investors:
                try:
                    # Personalizar mensaje para cada inversor
                    personalized_message = await message_personalizer.personalize_message(
                        template=message_template,
                        investor_data=investor,
                        startup_data=project
                    )
                    
                    target_data = {
                        "id": str(uuid4()),
                        "campaign_id": str(campaign_id),
                        "investor_id": str(investor["id"]),
                        "linkedin_provider_id": investor.get("linkedin_provider_id"),
                        "linkedin_profile_url": investor.get("linkedin_url"),
                        "linkedin_name": investor.get("full_name"),
                        "personalized_message": personalized_message,
                        "message_character_count": len(personalized_message),
                        "status": "pending",
                        "created_at": datetime.now().isoformat(),
                        "retry_count": 0,
                        "max_retries": 3,
                        "profile_data": {
                            "headline": investor.get("headline"),
                            "company": investor.get("company_name"),
                            "fund": investor.get("fund_name")
                        },
                        "relevance_score": investor.get("relevance_score", 0.5),
                        "invitation_sent": False,
                        "invitation_accepted": False,
                        "message_sent": False,
                        "profile_viewed": False
                    }
                    targets.append(target_data)
                    
                except Exception as e:
                    logger.error(f"Error preparing target for investor {investor.get('id')}: {e}")
                    continue
            
            # Insertar en batch
            if targets:
                result = db.supabase.table("outreach_targets").insert(targets).execute()
                
                # Actualizar contador de targets en campaña
                await db.supabase.table("outreach_campaigns").update({
                    "total_targets": len(targets)
                }).eq("id", str(campaign_id)).execute()
                
                logger.info(f"Added {len(targets)} targets to campaign {campaign_id}")
                return result.data
            
            return []
            
        except Exception as e:
            logger.error(f"Error adding targets to campaign: {e}")
            raise
    
    async def launch_campaign(self, campaign_id: UUID):
        """Lanzar campaña - cambiar estado y programar envíos"""
        try:
            # Verificar que la campaña tenga targets
            targets = await self._get_pending_targets(campaign_id)
            if not targets:
                raise Exception("Campaign has no targets to process")
            
            # Cambiar estado a activo
            update_data = {
                "status": "active",
                "launched_at": datetime.now().isoformat()
            }
            
            result = db.supabase.table("outreach_campaigns").update(update_data).eq("id", str(campaign_id)).execute()
            
            if not result.data:
                raise Exception("Failed to launch campaign")
            
            logger.info(f"Campaign {campaign_id} launched successfully with {len(targets)} targets")
            
        except Exception as e:
            logger.error(f"Error launching campaign: {e}")
            raise
    
    async def process_campaign_sends(self, campaign_id: UUID):
        """Procesar envíos de campaña en background"""
        async with self.processing_lock:
            if campaign_id in self.active_campaigns:
                logger.info(f"Campaign {campaign_id} already being processed")
                return
            
            self.active_campaigns.add(campaign_id)
        
        try:
            logger.info(f"Starting campaign processing for {campaign_id}")
            
            # Obtener campaña y verificar estado
            campaign = await self._get_campaign(campaign_id)
            if not campaign or campaign["status"] != "active":
                logger.info(f"Campaign {campaign_id} not active, stopping processing")
                return
            
            # Obtener account de LinkedIn
            linkedin_account_id = campaign["linkedin_account_id"]
            if not linkedin_account_id:
                logger.error(f"Campaign {campaign_id} has no LinkedIn account configured")
                return
            
            # Verificar que Unipile esté configurado
            if not unipile_client:
                logger.error("Unipile client not configured - cannot process outreach")
                return
            
            # Obtener targets pendientes (procesar en lotes)
            batch_size = campaign.get("daily_limit", 80)
            pending_targets = await self._get_pending_targets(campaign_id, limit=batch_size)
            
            if not pending_targets:
                # Marcar campaña como completada
                await self._complete_campaign(campaign_id)
                return
            
            logger.info(f"Processing {len(pending_targets)} pending targets for campaign {campaign_id}")
            
            # Procesar targets respetando rate limits
            processed = 0
            for target in pending_targets:
                try:
                    # Verificar si campaña sigue activa
                    campaign_check = await self._get_campaign(campaign_id)
                    if campaign_check["status"] != "active":
                        logger.info(f"Campaign {campaign_id} paused/stopped, halting processing")
                        break
                    
                    # Verificar rate limits de LinkedIn
                    if not await linkedin_rate_limiter.can_send_invitation(linkedin_account_id):
                        logger.info(f"Rate limit reached for account {linkedin_account_id}, scheduling retry")
                        await self._schedule_retry_later(campaign_id)
                        break
                    
                    # Enviar mensaje/invitación
                    success = await self._send_outreach_message(
                        linkedin_account_id=linkedin_account_id,
                        target=target
                    )
                    
                    if success:
                        await self._mark_target_sent(target["id"])
                        await self._increment_sent_count(campaign_id)
                        processed += 1
                        logger.info(f"Successfully sent message to target {target['id']}")
                    else:
                        await self._mark_target_failed(target["id"], "Send failed")
                        logger.warning(f"Failed to send message to target {target['id']}")
                    
                    # Registrar envío para rate limiting
                    await linkedin_rate_limiter.record_invitation_sent(linkedin_account_id)
                    
                    # Espera random entre envíos (humanizar comportamiento)
                    delay = campaign.get("delay_between_sends", 120)
                    wait_time = random.randint(int(delay * 0.8), int(delay * 1.2))
                    
                    logger.debug(f"Waiting {wait_time}s before next message")
                    await asyncio.sleep(wait_time)
                    
                except Exception as e:
                    logger.error(f"Error processing target {target['id']}: {e}")
                    await self._mark_target_failed(target["id"], str(e))
                    continue
            
            # Actualizar última vez procesada
            await db.supabase.table("outreach_campaigns").update({
                "last_processed": datetime.now().isoformat()
            }).eq("id", str(campaign_id)).execute()
            
            # Verificar si quedan targets pendientes
            remaining_targets = await self._get_pending_targets(campaign_id)
            
            if remaining_targets:
                # Programar siguiente batch
                logger.info(f"Campaign {campaign_id} has {len(remaining_targets)} remaining targets")
            else:
                # Campaña completada
                await self._complete_campaign(campaign_id)
                logger.info(f"Campaign {campaign_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Error processing campaign {campaign_id}: {e}")
            # Marcar campaña como error
            await db.supabase.table("outreach_campaigns").update({
                "status": "error",
                "last_processed": datetime.now().isoformat()
            }).eq("id", str(campaign_id)).execute()
        finally:
            async with self.processing_lock:
                self.active_campaigns.discard(campaign_id)
    
    async def _send_outreach_message(self, linkedin_account_id: str, target: Dict[str, Any]) -> bool:
        """Enviar mensaje de outreach individual"""
        try:
            linkedin_provider_id = target.get("linkedin_provider_id")
            if not linkedin_provider_id:
                logger.error(f"No LinkedIn provider ID for target {target['id']}")
                return False
            
            message = target["personalized_message"]
            
            # Verificar si ya son conexiones
            try:
                relations = await unipile_client.get_relations(linkedin_account_id, limit=1000)
                is_connection = any(rel.get("provider_id") == linkedin_provider_id for rel in relations)
            except Exception as e:
                logger.warning(f"Could not check relations: {e}")
                is_connection = False
            
            if is_connection:
                # Enviar mensaje directo
                logger.info(f"Sending direct message to existing connection")
                result = await unipile_client.send_message(
                    account_id=linkedin_account_id,
                    attendee_provider_id=linkedin_provider_id,
                    text=message
                )
                
                # Marcar como mensaje enviado
                await db.supabase.table("outreach_targets").update({
                    "message_sent": True
                }).eq("id", target["id"]).execute()
                
            else:
                # Enviar invitación
                logger.info(f"Sending invitation to new contact")
                result = await unipile_client.send_invitation(
                    account_id=linkedin_account_id,
                    provider_id=linkedin_provider_id,
                    message=message
                )
                
                # Marcar como invitación enviada
                await db.supabase.table("outreach_targets").update({
                    "invitation_sent": True
                }).eq("id", target["id"]).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending outreach message: {e}")
            return False
    
    async def send_test_message(self, campaign_id: UUID, target_id: UUID) -> Dict[str, Any]:
        """Enviar mensaje de prueba (solo en desarrollo)"""
        try:
            campaign = await self._get_campaign(campaign_id)
            if not campaign:
                raise Exception("Campaign not found")
            
            # Obtener target
            target_result = db.supabase.table("outreach_targets").select("*").eq("id", str(target_id)).execute()
            if not target_result.data:
                raise Exception("Target not found")
            
            target = target_result.data[0]
            
            # Enviar mensaje de prueba
            success = await self._send_outreach_message(
                linkedin_account_id=campaign["linkedin_account_id"],
                target=target
            )
            
            return {
                "success": success,
                "target_id": str(target_id),
                "message": "Test message sent" if success else "Test message failed",
                "personalized_message": target["personalized_message"]
            }
            
        except Exception as e:
            logger.error(f"Error sending test message: {e}")
            raise
    
    # ==========================================
    # HELPER METHODS
    # ==========================================
    
    async def _get_campaign(self, campaign_id: UUID) -> Optional[Dict[str, Any]]:
        """Obtener datos de campaña"""
        result = db.supabase.table("outreach_campaigns").select("*").eq("id", str(campaign_id)).execute()
        return result.data[0] if result.data else None
    
    async def _get_campaign_project(self, campaign_id: UUID) -> Dict[str, Any]:
        """Obtener proyecto asociado a campaña"""
        campaign = await self._get_campaign(campaign_id)
        if not campaign:
            raise Exception("Campaign not found")
        
        project = await db.get_project(UUID(campaign["project_id"]), UUID(campaign["user_id"]))
        return project.dict() if project else {}
    
    async def _get_pending_targets(self, campaign_id: UUID, limit: int = None) -> List[Dict[str, Any]]:
        """Obtener targets pendientes de envío"""
        query = db.supabase.table("outreach_targets").select("*").eq("campaign_id", str(campaign_id)).eq("status", "pending")
        
        if limit:
            query = query.limit(limit)
        
        result = query.execute()
        return result.data
    
    async def _mark_target_sent(self, target_id: str):
        """Marcar target como enviado"""
        update_data = {
            "status": "sent",
            "sent_at": datetime.now().isoformat()
        }
        db.supabase.table("outreach_targets").update(update_data).eq("id", target_id).execute()
    
    async def _mark_target_failed(self, target_id: str, reason: str):
        """Marcar target como fallido"""
        # Obtener retry count actual
        target_result = db.supabase.table("outreach_targets").select("retry_count, max_retries").eq("id", target_id).execute()
        
        if target_result.data:
            target = target_result.data[0]
            retry_count = target.get("retry_count", 0)
            max_retries = target.get("max_retries", 3)
            
            if retry_count < max_retries:
                # Programar reintento
                update_data = {
                    "retry_count": retry_count + 1,
                    "last_retry_at": datetime.now().isoformat(),
                    "failure_reason": reason
                }
            else:
                # Marcar como fallido permanentemente
                update_data = {
                    "status": "failed",
                    "failure_reason": reason,
                    "failed_at": datetime.now().isoformat()
                }
            
            db.supabase.table("outreach_targets").update(update_data).eq("id", target_id).execute()
    
    async def _increment_sent_count(self, campaign_id: UUID):
        """Incrementar contador de enviados"""
        # Obtener count actual
        campaign = await self._get_campaign(campaign_id)
        if campaign:
            new_count = campaign.get("sent_count", 0) + 1
            db.supabase.table("outreach_campaigns").update({
                "sent_count": new_count
            }).eq("id", str(campaign_id)).execute()
    
    async def _complete_campaign(self, campaign_id: UUID):
        """Marcar campaña como completada"""
        update_data = {
            "status": "completed",
            "completed_at": datetime.now().isoformat()
        }
        db.supabase.table("outreach_campaigns").update(update_data).eq("id", str(campaign_id)).execute()
        logger.info(f"Campaign {campaign_id} marked as completed")
    
    async def _schedule_retry_later(self, campaign_id: UUID):
        """Programar campaña para procesar más tarde"""
        # En una implementación completa, usarías Celery o similar
        # Por ahora, solo logueamos
        logger.info(f"Campaign {campaign_id} scheduled for retry later due to rate limits")
    
    def _format_campaign_response(self, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """Formatear respuesta de campaña"""
        return {
            "id": UUID(campaign_data["id"]),
            "name": campaign_data["name"],
            "project_id": UUID(campaign_data["project_id"]),
            "message_template": campaign_data["message_template"],
            "status": campaign_data["status"],
            "total_targets": campaign_data.get("total_targets", 0),
            "sent_count": campaign_data.get("sent_count", 0),
            "reply_count": campaign_data.get("reply_count", 0),
            "success_rate": self._calculate_success_rate(campaign_data),
            "created_at": datetime.fromisoformat(campaign_data["created_at"].replace("Z", "+00:00")),
            "launched_at": datetime.fromisoformat(campaign_data["launched_at"].replace("Z", "+00:00")) if campaign_data.get("launched_at") else None
        }
    
    def _calculate_success_rate(self, campaign_data: Dict[str, Any]) -> float:
        """Calcular tasa de éxito"""
        sent = campaign_data.get("sent_count", 0)
        replies = campaign_data.get("reply_count", 0)
        
        if sent == 0:
            return 0.0
        
        return round((replies / sent) * 100, 2)
    
    async def get_campaign_analytics(self, campaign_id: UUID) -> Dict[str, Any]:
        """Obtener analíticas detalladas de campaña"""
        try:
            campaign = await self._get_campaign(campaign_id)
            if not campaign:
                raise Exception("Campaign not found")
            
            # Obtener estadísticas de targets
            targets_stats = db.supabase.table("outreach_targets").select("status").eq("campaign_id", str(campaign_id)).execute()
            
            status_counts = {}
            for target in targets_stats.data:
                status = target["status"]
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Obtener respuestas
            responses = db.supabase.table("linkedin_responses").select("*").eq("campaign_id", str(campaign_id)).execute()
            
            # Analizar sentimientos de respuestas
            sentiment_analysis = {"positive": 0, "negative": 0, "neutral": 0}
            for response in responses.data:
                sentiment = response.get("response_sentiment", "neutral")
                sentiment_analysis[sentiment] = sentiment_analysis.get(sentiment, 0) + 1
            
            return {
                "campaign_id": str(campaign_id),
                "status": campaign["status"],
                "targets_by_status": status_counts,
                "response_rate": self._calculate_success_rate(campaign),
                "sentiment_analysis": sentiment_analysis,
                "total_responses": len(responses.data),
                "created_at": campaign["created_at"],
                "launched_at": campaign.get("launched_at"),
                "estimated_completion": self._estimate_completion_date(campaign_id)
            }
            
        except Exception as e:
            logger.error(f"Error getting campaign analytics: {e}")
            raise
    
    def _estimate_completion_date(self, campaign_id: UUID) -> Optional[str]:
        """Estimar fecha de completación basada en rate limits"""
        # Implementar lógica basada en targets restantes y límites de LinkedIn
        # Por ahora retornar estimación simple
        return (datetime.now() + timedelta(days=3)).isoformat()

# Instancia global
campaign_manager = CampaignManager()
