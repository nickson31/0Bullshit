# api/webhooks.py
import json
import logging
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from database.database import db
from campaigns.message_generator import message_personalizer

router = APIRouter()
logger = logging.getLogger(__name__)

# ==========================================
# WEBHOOK HANDLERS
# ==========================================

@router.post("/webhooks/unipile")
async def unipile_webhook(request: Request, background_tasks: BackgroundTasks):
    """Webhook principal para eventos de Unipile"""
    try:
        # Obtener payload
        payload = await request.json()
        logger.info(f"[Unipile Webhook] Received event: {payload.get('type', 'unknown')}")
        
        # Guardar evento para auditoría
        event_id = await db.save_webhook_event({
            "event_type": payload.get("type", "unknown"),
            "unipile_account_id": payload.get("account_id"),
            "payload": payload
        })
        
        # Procesar evento en background
        background_tasks.add_task(process_unipile_event, event_id, payload)
        
        # Responder inmediatamente a Unipile
        return JSONResponse(content={"ok": True, "event_id": str(event_id)})
        
    except Exception as e:
        logger.error(f"Error processing Unipile webhook: {e}")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(e)}
        )

@router.post("/webhooks/linkedin/auth-success")
async def linkedin_auth_success(request: Request):
    """Webhook para autenticación exitosa de LinkedIn"""
    try:
        payload = await request.json()
        logger.info(f"[LinkedIn Auth] Success: {payload}")
        
        account_id = payload.get("account_id")
        user_id = payload.get("name")  # Enviamos user_id como "name"
        
        if account_id and user_id:
            # Crear/actualizar cuenta de LinkedIn
            account_data = {
                "unipile_account_id": account_id,
                "account_type": "classic",
                "status": "connected",
                "account_name": payload.get("account_name"),
                "account_email": payload.get("account_email")
            }
            
            await db.create_linkedin_account(UUID(user_id), account_data)
            logger.info(f"LinkedIn account {account_id} connected for user {user_id}")
        
        return JSONResponse(content={"ok": True})
        
    except Exception as e:
        logger.error(f"Error processing LinkedIn auth success: {e}")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(e)}
        )

@router.post("/webhooks/linkedin/auth-failure")
async def linkedin_auth_failure(request: Request):
    """Webhook para fallo en autenticación de LinkedIn"""
    try:
        payload = await request.json()
        logger.warning(f"[LinkedIn Auth] Failure: {payload}")
        
        account_id = payload.get("account_id")
        error_message = payload.get("error", "Authentication failed")
        
        if account_id:
            await db.update_linkedin_account_status(account_id, "error", error_message)
        
        return JSONResponse(content={"ok": True})
        
    except Exception as e:
        logger.error(f"Error processing LinkedIn auth failure: {e}")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(e)}
        )

# ==========================================
# EVENT PROCESSORS
# ==========================================

async def process_unipile_event(event_id: UUID, payload: Dict[str, Any]):
    """Procesar evento de Unipile en background"""
    try:
        event_type = payload.get("type", "")
        
        if event_type == "messaging.new_message":
            await process_new_message_event(payload)
            
        elif event_type == "users.invitation_accepted":
            await process_invitation_accepted_event(payload)
            
        elif event_type == "users.new_relation":
            await process_new_relation_event(payload)
            
        elif event_type == "users.invitation_sent":
            await process_invitation_sent_event(payload)
            
        elif event_type == "account.disconnected":
            await process_account_disconnected_event(payload)
            
        elif event_type == "account.reconnected":
            await process_account_reconnected_event(payload)
            
        else:
            logger.info(f"Unhandled event type: {event_type}")
        
        # Marcar evento como procesado exitosamente
        await db.mark_webhook_processed(event_id, success=True)
        
    except Exception as e:
        logger.error(f"Error processing Unipile event {event_id}: {e}")
        await db.mark_webhook_processed(event_id, success=False, error_message=str(e))

async def process_new_message_event(payload: Dict[str, Any]):
    """Procesar nuevo mensaje recibido"""
    try:
        account_id = payload.get("account_id")
        message_data = payload.get("object", {})
        
        sender_id = message_data.get("sender_id")
        chat_id = message_data.get("chat_id")
        message_text = message_data.get("text", "")
        
        if not all([account_id, sender_id, message_text]):
            logger.warning("Incomplete message data received")
            return
        
        # Buscar si este sender es target de alguna campaña activa
        target = await find_target_by_linkedin_id(sender_id)
        
        if target:
            # Guardar respuesta
            response_data = {
                "outreach_target_id": target["id"],
                "campaign_id": target["campaign_id"],
                "response_text": message_text,
                "response_type": "message",
                "unipile_event_data": payload,
                "unipile_message_id": message_data.get("id"),
                "unipile_chat_id": chat_id,
                "received_at": message_data.get("created_at", datetime.now().isoformat())
            }
            
            await db.save_linkedin_response(response_data)
            
            # Actualizar target como que ha respondido
            await update_target_replied(target["id"])
            
            # Analizar sentimiento de la respuesta
            analysis = await message_personalizer.analyze_response_sentiment(message_text)
            
            # Actualizar análisis en la respuesta
            await db.update_response_analysis(UUID(response_data["outreach_target_id"]), analysis)
            
            logger.info(f"New response processed for target {target['id']}: {analysis['sentiment']}")
            
            # Si es positivo, podríamos programar follow-up automático
            if analysis.get("sentiment") == "positive" and analysis.get("interest_level") == "high":
                logger.info(f"High interest response detected for target {target['id']}")
                # Aquí podrías programar follow-up automático
        
    except Exception as e:
        logger.error(f"Error processing new message event: {e}")

async def process_invitation_accepted_event(payload: Dict[str, Any]):
    """Procesar invitación aceptada"""
    try:
        account_id = payload.get("account_id")
        invitation_data = payload.get("object", {})
        
        invitee_id = invitation_data.get("invitee_id")
        
        if not all([account_id, invitee_id]):
            logger.warning("Incomplete invitation data received")
            return
        
        # Buscar target por LinkedIn ID
        target = await find_target_by_linkedin_id(invitee_id)
        
        if target:
            # Actualizar target como invitación aceptada
            await update_target_accepted(target["id"])
            
            # Incrementar contador de aceptaciones en campaña
            await increment_campaign_accepted_count(target["campaign_id"])
            
            logger.info(f"Invitation accepted for target {target['id']}")
        
    except Exception as e:
        logger.error(f"Error processing invitation accepted event: {e}")

async def process_new_relation_event(payload: Dict[str, Any]):
    """Procesar nueva conexión establecida (incluye conexiones aceptadas)"""
    try:
        account_id = payload.get("account_id")
        user_data = payload.get("object", {})
        
        # Datos del nuevo contacto según documentación Unipile
        user_provider_id = user_data.get("user_provider_id")
        user_public_identifier = user_data.get("user_public_identifier") 
        user_full_name = user_data.get("user_full_name")
        user_profile_url = user_data.get("user_profile_url")
        
        if not all([account_id, user_provider_id]):
            logger.warning("Incomplete new relation data received")
            return
        
        # Buscar target por LinkedIn ID o public identifier
        target = await find_target_by_linkedin_id(user_provider_id)
        if not target:
            target = await find_target_by_public_identifier(user_public_identifier)
        
        if target:
            # Actualizar target como conexión establecida
            await update_target_connection_established(
                target["id"], 
                user_full_name, 
                user_profile_url
            )
            
            # Incrementar contador de conexiones en campaña
            await increment_campaign_connections_count(target["campaign_id"])
            
            logger.info(f"New relation established for target {target['id']}: {user_full_name}")
            
            # Opcional: Programar mensaje de seguimiento automático
            # await schedule_follow_up_message(target["id"], delay_hours=24)
        else:
            # Log para nuevas conexiones no relacionadas con campañas
            logger.info(f"New relation established outside campaigns: {user_full_name}")
        
    except Exception as e:
        logger.error(f"Error processing new relation event: {e}")

async def process_invitation_sent_event(payload: Dict[str, Any]):
    """Procesar confirmación de invitación enviada"""
    try:
        # Esto es principalmente para logging/confirmación
        account_id = payload.get("account_id")
        invitation_data = payload.get("object", {})
        
        logger.info(f"Invitation sent confirmed for account {account_id}")
        
    except Exception as e:
        logger.error(f"Error processing invitation sent event: {e}")

async def process_account_disconnected_event(payload: Dict[str, Any]):
    """Procesar cuenta desconectada"""
    try:
        account_id = payload.get("account_id")
        error_data = payload.get("object", {})
        
        error_message = error_data.get("error", "Account disconnected")
        
        # Actualizar estado de cuenta
        await db.update_linkedin_account_status(account_id, "disconnected", error_message)
        
        # Pausar campañas activas que usen esta cuenta
        await pause_campaigns_for_account(account_id)
        
        logger.warning(f"LinkedIn account {account_id} disconnected: {error_message}")
        
    except Exception as e:
        logger.error(f"Error processing account disconnected event: {e}")

async def process_account_reconnected_event(payload: Dict[str, Any]):
    """Procesar cuenta reconectada"""
    try:
        account_id = payload.get("account_id")
        
        # Actualizar estado de cuenta
        await db.update_linkedin_account_status(account_id, "connected")
        
        logger.info(f"LinkedIn account {account_id} reconnected")
        
    except Exception as e:
        logger.error(f"Error processing account reconnected event: {e}")

# ==========================================
# HELPER FUNCTIONS
# ==========================================

async def find_target_by_linkedin_id(linkedin_provider_id: str) -> Optional[Dict[str, Any]]:
    """Encontrar target por LinkedIn provider ID"""
    try:
        result = db.supabase.table("outreach_targets").select("*").eq(
            "linkedin_provider_id", linkedin_provider_id
        ).eq("status", "sent").execute()
        
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Error finding target by LinkedIn ID: {e}")
        return None

async def find_target_by_public_identifier(public_identifier: str) -> Optional[Dict[str, Any]]:
    """Encontrar target por public identifier de LinkedIn"""
    try:
        if not public_identifier:
            return None
            
        result = db.supabase.table("outreach_targets").select("*").eq(
            "linkedin_public_identifier", public_identifier
        ).eq("status", "sent").execute()
        
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Error finding target by public identifier: {e}")
        return None

async def update_target_replied(target_id: str):
    """Actualizar target como que ha respondido"""
    try:
        update_data = {
            "replied_at": datetime.now().isoformat()
        }
        db.supabase.table("outreach_targets").update(update_data).eq("id", target_id).execute()
        
        # También incrementar contador de respuestas en campaña
        target_result = db.supabase.table("outreach_targets").select("campaign_id").eq("id", target_id).execute()
        if target_result.data:
            campaign_id = target_result.data[0]["campaign_id"]
            await increment_campaign_reply_count(campaign_id)
            
    except Exception as e:
        logger.error(f"Error updating target replied: {e}")

async def update_target_accepted(target_id: str):
    """Actualizar target como invitación aceptada"""
    try:
        update_data = {
            "invitation_accepted": True,
            "accepted_at": datetime.now().isoformat()
        }
        db.supabase.table("outreach_targets").update(update_data).eq("id", target_id).execute()
        
    except Exception as e:
        logger.error(f"Error updating target accepted: {e}")

async def update_target_connection_established(target_id: str, full_name: str = None, profile_url: str = None):
    """Actualizar target como conexión establecida"""
    try:
        update_data = {
            "connection_established": True,
            "connection_established_at": datetime.now().isoformat()
        }
        
        # Añadir información adicional si está disponible
        if full_name:
            update_data["connected_name"] = full_name
        if profile_url:
            update_data["connected_profile_url"] = profile_url
        
        db.supabase.table("outreach_targets").update(update_data).eq("id", target_id).execute()
        
    except Exception as e:
        logger.error(f"Error updating target connection established: {e}")

async def increment_campaign_reply_count(campaign_id: str):
    """Incrementar contador de respuestas en campaña"""
    try:
        # Obtener count actual
        campaign_result = db.supabase.table("outreach_campaigns").select("reply_count").eq("id", campaign_id).execute()
        if campaign_result.data:
            current_count = campaign_result.data[0].get("reply_count", 0)
            new_count = current_count + 1
            
            db.supabase.table("outreach_campaigns").update({
                "reply_count": new_count
            }).eq("id", campaign_id).execute()
            
    except Exception as e:
        logger.error(f"Error incrementing campaign reply count: {e}")

async def increment_campaign_accepted_count(campaign_id: str):
    """Incrementar contador de aceptaciones en campaña"""
    try:
        # Obtener count actual
        campaign_result = db.supabase.table("outreach_campaigns").select("accepted_count").eq("id", campaign_id).execute()
        if campaign_result.data:
            current_count = campaign_result.data[0].get("accepted_count", 0)
            new_count = current_count + 1
            
            db.supabase.table("outreach_campaigns").update({
                "accepted_count": new_count
            }).eq("id", campaign_id).execute()
            
    except Exception as e:
        logger.error(f"Error incrementing campaign accepted count: {e}")

async def increment_campaign_connections_count(campaign_id: str):
    """Incrementar contador de conexiones establecidas en campaña"""
    try:
        # Obtener count actual
        campaign_result = db.supabase.table("outreach_campaigns").select("connections_count").eq("id", campaign_id).execute()
        if campaign_result.data:
            current_count = campaign_result.data[0].get("connections_count", 0)
            new_count = current_count + 1
            
            db.supabase.table("outreach_campaigns").update({
                "connections_count": new_count
            }).eq("id", campaign_id).execute()
            
    except Exception as e:
        logger.error(f"Error incrementing campaign connections count: {e}")

async def pause_campaigns_for_account(account_id: str):
    """Pausar campañas activas para una cuenta"""
    try:
        # Buscar campañas activas que usen esta cuenta
        campaigns_result = db.supabase.table("outreach_campaigns").select("id").eq(
            "linkedin_account_id", account_id
        ).eq("status", "active").execute()
        
        for campaign in campaigns_result.data:
            db.supabase.table("outreach_campaigns").update({
                "status": "paused"
            }).eq("id", campaign["id"]).execute()
            
            logger.info(f"Paused campaign {campaign['id']} due to account disconnection")
            
    except Exception as e:
        logger.error(f"Error pausing campaigns for account: {e}")

# ==========================================
# DEBUGGING ENDPOINTS
# ==========================================

@router.post("/webhooks/test")
async def test_webhook(request: Request):
    """Endpoint de prueba para webhooks"""
    try:
        payload = await request.json()
        logger.info(f"[Test Webhook] Received: {payload}")
        
        return JSONResponse(content={
            "ok": True,
            "received": payload,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in test webhook: {e}")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(e)}
        )

@router.get("/webhooks/status")
async def webhook_status():
    """Estado de los webhooks"""
    try:
        # Obtener estadísticas de eventos procesados
        recent_events = db.supabase.table("unipile_webhook_events").select("*").order("received_at", desc=True).limit(10).execute()
        
        return JSONResponse(content={
            "status": "healthy",
            "recent_events": len(recent_events.data),
            "last_event": recent_events.data[0]["received_at"] if recent_events.data else None
        })
        
    except Exception as e:
        logger.error(f"Error getting webhook status: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": str(e)}
        )
