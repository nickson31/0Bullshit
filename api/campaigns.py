# api/campaigns.py
import os
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
import logging

from models.schemas import ApiResponse
from database.database import db
from api.auth import get_current_user
from integrations.unipile_client import unipile_client

# Imports dinámicos para evitar errores de importación circular
try:
    from campaigns.campaign_manager import campaign_manager
    from campaigns.message_generator import message_personalizer
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("Campaign modules not available - some functionality disabled")
    campaign_manager = None
    message_personalizer = None

campaigns_router = APIRouter()
logger = logging.getLogger(__name__)

# ==========================================
# MODELOS DE REQUEST/RESPONSE
# ==========================================

class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    project_id: UUID
    message_template: str = Field(..., min_length=10, max_length=2000)
    target_investor_ids: List[UUID] = []
    linkedin_account_id: Optional[str] = None

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    message_template: Optional[str] = None
    status: Optional[str] = None

class CampaignResponse(BaseModel):
    id: UUID
    name: str
    project_id: UUID
    message_template: str
    status: str
    total_targets: int
    sent_count: int
    reply_count: int
    success_rate: float
    created_at: datetime
    launched_at: Optional[datetime]

class TargetResponse(BaseModel):
    id: UUID
    investor_name: str
    linkedin_url: Optional[str]
    personalized_message: str
    status: str
    sent_at: Optional[datetime]
    replied_at: Optional[datetime]

class CampaignStats(BaseModel):
    total_campaigns: int
    active_campaigns: int
    total_sent: int
    total_replies: int
    average_response_rate: float

# ==========================================
# ENDPOINTS DE CAMPAÑAS
# ==========================================

@campaigns_router.post("/campaigns", response_model=CampaignResponse)
async def create_campaign(
    campaign_data: CampaignCreate,
    current_user: UUID = Depends(get_current_user)
):
    """Crear nueva campaña de outreach"""
    try:
        # Verificar que el proyecto pertenece al usuario
        project = await db.get_project(campaign_data.project_id, current_user)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Verificar que tiene cuenta de LinkedIn conectada
        if not campaign_data.linkedin_account_id:
            linkedin_accounts = await db.get_user_linkedin_accounts(current_user)
            if not linkedin_accounts:
                raise HTTPException(
                    status_code=400, 
                    detail="No LinkedIn account connected. Please connect your LinkedIn account first."
                )
            campaign_data.linkedin_account_id = linkedin_accounts[0]["unipile_account_id"]
        
        # Crear campaña usando el campaign manager si está disponible
        if campaign_manager:
            campaign = await campaign_manager.create_campaign(
                user_id=current_user,
                project_id=campaign_data.project_id,
                name=campaign_data.name,
                message_template=campaign_data.message_template,
                linkedin_account_id=campaign_data.linkedin_account_id,
                target_investor_ids=campaign_data.target_investor_ids
            )
        else:
            # Fallback: crear campaña directamente en DB
            campaign = await create_campaign_fallback(campaign_data, current_user)
        
        return campaign
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating campaign: {e}")
        raise HTTPException(status_code=500, detail="Error creating campaign")

@campaigns_router.get("/campaigns", response_model=List[CampaignResponse])
async def get_user_campaigns(current_user: UUID = Depends(get_current_user)):
    """Obtener todas las campañas del usuario"""
    try:
        campaigns = await get_user_campaigns_from_db(current_user)
        return campaigns
    except Exception as e:
        logger.error(f"Error getting campaigns: {e}")
        raise HTTPException(status_code=500, detail="Error getting campaigns")

@campaigns_router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: UUID,
    current_user: UUID = Depends(get_current_user)
):
    """Obtener campaña específica"""
    try:
        campaign = await get_campaign_from_db(campaign_id, current_user)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return campaign
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign: {e}")
        raise HTTPException(status_code=500, detail="Error getting campaign")

@campaigns_router.put("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: UUID,
    updates: CampaignUpdate,
    current_user: UUID = Depends(get_current_user)
):
    """Actualizar campaña"""
    try:
        campaign = await get_campaign_from_db(campaign_id, current_user)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # No permitir cambios si la campaña ya está activa
        if campaign.status == "active" and updates.status not in ["paused", "completed"]:
            raise HTTPException(
                status_code=400, 
                detail="Cannot modify active campaign. Pause it first."
            )
        
        updated_campaign = await update_campaign_in_db(campaign_id, updates.dict(exclude_unset=True))
        return updated_campaign
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating campaign: {e}")
        raise HTTPException(status_code=500, detail="Error updating campaign")

@campaigns_router.delete("/campaigns/{campaign_id}")
async def delete_campaign(
    campaign_id: UUID,
    current_user: UUID = Depends(get_current_user)
):
    """Eliminar campaña"""
    try:
        campaign = await get_campaign_from_db(campaign_id, current_user)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        if campaign.status == "active":
            raise HTTPException(
                status_code=400, 
                detail="Cannot delete active campaign. Pause it first."
            )
        
        await delete_campaign_from_db(campaign_id)
        return ApiResponse(success=True, message="Campaign deleted successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting campaign: {e}")
        raise HTTPException(status_code=500, detail="Error deleting campaign")

# ==========================================
# GESTIÓN DE TARGETS
# ==========================================

@campaigns_router.post("/campaigns/{campaign_id}/targets")
async def add_targets_to_campaign(
    campaign_id: UUID,
    investor_ids: List[UUID],
    current_user: UUID = Depends(get_current_user)
):
    """Añadir inversores como targets a campaña"""
    try:
        campaign = await get_campaign_from_db(campaign_id, current_user)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        if campaign.status == "active":
            raise HTTPException(
                status_code=400, 
                detail="Cannot modify targets of active campaign"
            )
        
        # Verificar que los inversores existen
        investors = await get_investors_by_ids(investor_ids)
        if len(investors) != len(investor_ids):
            raise HTTPException(status_code=400, detail="Some investors not found")
        
        # Añadir targets usando campaign manager si está disponible
        if campaign_manager:
            added_targets = await campaign_manager.add_targets_to_campaign(
                campaign_id, investor_ids, campaign.message_template
            )
        else:
            # Fallback: añadir targets directamente
            added_targets = await add_targets_fallback(campaign_id, investor_ids, campaign.message_template)
        
        return ApiResponse(
            success=True,
            message=f"Added {len(added_targets)} targets to campaign",
            data={"targets_added": len(added_targets)}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding targets: {e}")
        raise HTTPException(status_code=500, detail="Error adding targets")

@campaigns_router.get("/campaigns/{campaign_id}/targets", response_model=List[TargetResponse])
async def get_campaign_targets(
    campaign_id: UUID,
    current_user: UUID = Depends(get_current_user)
):
    """Obtener targets de una campaña"""
    try:
        campaign = await get_campaign_from_db(campaign_id, current_user)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        targets = await get_campaign_targets_from_db(campaign_id)
        return targets
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting targets: {e}")
        raise HTTPException(status_code=500, detail="Error getting targets")

@campaigns_router.delete("/campaigns/{campaign_id}/targets/{target_id}")
async def remove_target_from_campaign(
    campaign_id: UUID,
    target_id: UUID,
    current_user: UUID = Depends(get_current_user)
):
    """Remover target de campaña"""
    try:
        campaign = await get_campaign_from_db(campaign_id, current_user)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        if campaign.status == "active":
            raise HTTPException(
                status_code=400, 
                detail="Cannot modify targets of active campaign"
            )
        
        await remove_campaign_target_from_db(target_id)
        return ApiResponse(success=True, message="Target removed from campaign")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing target: {e}")
        raise HTTPException(status_code=500, detail="Error removing target")

# ==========================================
# LANZAMIENTO Y CONTROL DE CAMPAÑAS
# ==========================================

@campaigns_router.post("/campaigns/{campaign_id}/launch")
async def launch_campaign(
    campaign_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: UUID = Depends(get_current_user)
):
    """Lanzar campaña de outreach"""
    try:
        campaign = await get_campaign_from_db(campaign_id, current_user)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        if campaign.status != "draft":
            raise HTTPException(status_code=400, detail="Campaign already launched")
        
        # Verificar que tiene targets
        targets = await get_campaign_targets_from_db(campaign_id)
        if not targets:
            raise HTTPException(status_code=400, detail="Campaign has no targets")
        
        # Verificar cuenta de LinkedIn
        linkedin_account = await get_linkedin_account(campaign.linkedin_account_id)
        if not linkedin_account or linkedin_account.get("status") != "connected":
            raise HTTPException(
                status_code=400, 
                detail="LinkedIn account not connected or in error state"
            )
        
        # Lanzar campaña
        if campaign_manager:
            await campaign_manager.launch_campaign(campaign_id)
            # Programar envío en background
            background_tasks.add_task(
                campaign_manager.process_campaign_sends,
                campaign_id
            )
        else:
            # Fallback: marcar como activa
            await update_campaign_status(campaign_id, "active")
        
        return ApiResponse(
            success=True,
            message="Campaign launched successfully",
            data={
                "campaign_id": str(campaign_id),
                "total_targets": len(targets),
                "estimated_completion": "2-3 days"  # Basado en límites de LinkedIn
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error launching campaign: {e}")
        raise HTTPException(status_code=500, detail="Error launching campaign")

@campaigns_router.post("/campaigns/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: UUID,
    current_user: UUID = Depends(get_current_user)
):
    """Pausar campaña activa"""
    try:
        campaign = await get_campaign_from_db(campaign_id, current_user)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        if campaign.status != "active":
            raise HTTPException(status_code=400, detail="Campaign is not active")
        
        await update_campaign_status(campaign_id, "paused")
        
        return ApiResponse(success=True, message="Campaign paused successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing campaign: {e}")
        raise HTTPException(status_code=500, detail="Error pausing campaign")

@campaigns_router.post("/campaigns/{campaign_id}/resume")
async def resume_campaign(
    campaign_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: UUID = Depends(get_current_user)
):
    """Reanudar campaña pausada"""
    try:
        campaign = await get_campaign_from_db(campaign_id, current_user)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        if campaign.status != "paused":
            raise HTTPException(status_code=400, detail="Campaign is not paused")
        
        await update_campaign_status(campaign_id, "active")
        
        # Reanudar envío en background si el manager está disponible
        if campaign_manager:
            background_tasks.add_task(
                campaign_manager.process_campaign_sends,
                campaign_id
            )
        
        return ApiResponse(success=True, message="Campaign resumed successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming campaign: {e}")
        raise HTTPException(status_code=500, detail="Error resuming campaign")

# ==========================================
# ESTADÍSTICAS Y ANALÍTICAS
# ==========================================

@campaigns_router.get("/campaigns/stats", response_model=CampaignStats)
async def get_campaign_stats(current_user: UUID = Depends(get_current_user)):
    """Obtener estadísticas generales de campañas"""
    try:
        stats = await get_user_campaign_stats(current_user)
        return stats
    except Exception as e:
        logger.error(f"Error getting campaign stats: {e}")
        raise HTTPException(status_code=500, detail="Error getting campaign stats")

@campaigns_router.get("/campaigns/{campaign_id}/analytics")
async def get_campaign_analytics(
    campaign_id: UUID,
    current_user: UUID = Depends(get_current_user)
):
    """Obtener analíticas detalladas de campaña"""
    try:
        campaign = await get_campaign_from_db(campaign_id, current_user)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        if campaign_manager:
            analytics = await campaign_manager.get_campaign_analytics(campaign_id)
        else:
            # Fallback: analíticas básicas
            analytics = await get_basic_analytics(campaign_id)
        
        return analytics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign analytics: {e}")
        raise HTTPException(status_code=500, detail="Error getting campaign analytics")

# ==========================================
# TESTING Y PREVIEW
# ==========================================

@campaigns_router.post("/campaigns/preview-message")
async def preview_personalized_message(
    template: str,
    investor_id: UUID,
    project_id: UUID,
    current_user: UUID = Depends(get_current_user)
):
    """Preview mensaje personalizado"""
    try:
        # Obtener datos del inversor y proyecto
        investor = await get_investor_by_id(investor_id)
        project = await db.get_project(project_id, current_user)
        
        if not investor or not project:
            raise HTTPException(status_code=404, detail="Investor or project not found")
        
        # Generar mensaje personalizado
        if message_personalizer:
            personalized_message = await message_personalizer.personalize_message(
                template=template,
                investor_data=investor,
                startup_data=project.dict()
            )
        else:
            # Fallback: personalización simple
            personalized_message = simple_personalize_message(template, investor, project)
        
        return {
            "template": template,
            "personalized_message": personalized_message,
            "investor_name": investor.get("full_name"),
            "character_count": len(personalized_message)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing message: {e}")
        raise HTTPException(status_code=500, detail="Error previewing message")

@campaigns_router.post("/campaigns/{campaign_id}/test-send")
async def test_send_message(
    campaign_id: UUID,
    target_id: UUID,
    current_user: UUID = Depends(get_current_user)
):
    """Enviar mensaje de prueba a un target específico"""
    try:
        campaign = await get_campaign_from_db(campaign_id, current_user)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Solo en modo desarrollo/testing
        if os.getenv("ENVIRONMENT") != "development":
            raise HTTPException(status_code=403, detail="Test sends only available in development")
        
        if campaign_manager:
            result = await campaign_manager.send_test_message(campaign_id, target_id)
        else:
            # Fallback: simulación de envío
            result = {
                "success": True,
                "target_id": str(target_id),
                "message": "Test simulation completed"
            }
        
        return ApiResponse(
            success=True,
            message="Test message sent successfully",
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending test message: {e}")
        raise HTTPException(status_code=500, detail="Error sending test message")

# ==========================================
# IMPLEMENTACIÓN COMPLETA DE HELPER FUNCTIONS
# ==========================================

async def get_user_campaigns_from_db(user_id: UUID) -> List[CampaignResponse]:
    """Obtener campañas del usuario desde la base de datos"""
    try:
        campaigns_data = await db.get_user_campaigns(user_id)
        
        campaigns = []
        for campaign_data in campaigns_data:
            campaigns.append(CampaignResponse(
                id=UUID(campaign_data["id"]),
                name=campaign_data["name"],
                project_id=UUID(campaign_data["project_id"]),
                message_template=campaign_data["message_template"],
                status=campaign_data["status"],
                total_targets=campaign_data.get("total_targets", 0),
                sent_count=campaign_data.get("sent_count", 0),
                reply_count=campaign_data.get("reply_count", 0),
                success_rate=calculate_success_rate(campaign_data),
                created_at=datetime.fromisoformat(campaign_data["created_at"].replace("Z", "+00:00")),
                launched_at=datetime.fromisoformat(campaign_data["launched_at"].replace("Z", "+00:00")) if campaign_data.get("launched_at") else None
            ))
        
        return campaigns
    except Exception as e:
        logger.error(f"Error getting user campaigns: {e}")
        return []

async def get_campaign_from_db(campaign_id: UUID, user_id: UUID) -> Optional[CampaignResponse]:
    """Obtener campaña específica desde la base de datos"""
    try:
        campaign_data = await db.get_campaign(campaign_id, user_id)
        
        if campaign_data:
            return CampaignResponse(
                id=UUID(campaign_data["id"]),
                name=campaign_data["name"],
                project_id=UUID(campaign_data["project_id"]),
                message_template=campaign_data["message_template"],
                status=campaign_data["status"],
                total_targets=campaign_data.get("total_targets", 0),
                sent_count=campaign_data.get("sent_count", 0),
                reply_count=campaign_data.get("reply_count", 0),
                success_rate=calculate_success_rate(campaign_data),
                created_at=datetime.fromisoformat(campaign_data["created_at"].replace("Z", "+00:00")),
                launched_at=datetime.fromisoformat(campaign_data["launched_at"].replace("Z", "+00:00")) if campaign_data.get("launched_at") else None
            )
        return None
    except Exception as e:
        logger.error(f"Error getting campaign: {e}")
        return None

async def update_campaign_in_db(campaign_id: UUID, updates: Dict[str, Any]) -> CampaignResponse:
    """Actualizar campaña en la base de datos"""
    try:
        success = await db.update_campaign(campaign_id, updates)
        if not success:
            raise Exception("Failed to update campaign")
        
        # Obtener la campaña actualizada
        # Necesitamos el user_id, pero no lo tenemos aquí - esto es un problema de diseño
        # Por ahora, vamos a obtener la campaña de otra manera
        result = db.supabase.table("outreach_campaigns").select("*").eq("id", str(campaign_id)).execute()
        if not result.data:
            raise Exception("Campaign not found after update")
        
        campaign_data = result.data[0]
        return CampaignResponse(
            id=UUID(campaign_data["id"]),
            name=campaign_data["name"],
            project_id=UUID(campaign_data["project_id"]),
            message_template=campaign_data["message_template"],
            status=campaign_data["status"],
            total_targets=campaign_data.get("total_targets", 0),
            sent_count=campaign_data.get("sent_count", 0),
            reply_count=campaign_data.get("reply_count", 0),
            success_rate=calculate_success_rate(campaign_data),
            created_at=datetime.fromisoformat(campaign_data["created_at"].replace("Z", "+00:00")),
            launched_at=datetime.fromisoformat(campaign_data["launched_at"].replace("Z", "+00:00")) if campaign_data.get("launched_at") else None
        )
    except Exception as e:
        logger.error(f"Error updating campaign: {e}")
        raise

async def delete_campaign_from_db(campaign_id: UUID):
    """Eliminar campaña de la base de datos"""
    try:
        success = await db.delete_campaign(campaign_id)
        if not success:
            raise Exception("Failed to delete campaign")
    except Exception as e:
        logger.error(f"Error deleting campaign: {e}")
        raise

async def get_campaign_targets_from_db(campaign_id: UUID) -> List[TargetResponse]:
    """Obtener targets de campaña desde la base de datos"""
    try:
        targets_data = await db.get_campaign_targets(campaign_id)
        
        targets = []
        for target_data in targets_data:
            targets.append(TargetResponse(
                id=UUID(target_data["id"]),
                investor_name=target_data.get("linkedin_name", "Unknown"),
                linkedin_url=target_data.get("linkedin_profile_url"),
                personalized_message=target_data["personalized_message"],
                status=target_data["status"],
                sent_at=datetime.fromisoformat(target_data["sent_at"].replace("Z", "+00:00")) if target_data.get("sent_at") else None,
                replied_at=datetime.fromisoformat(target_data["replied_at"].replace("Z", "+00:00")) if target_data.get("replied_at") else None
            ))
        
        return targets
    except Exception as e:
        logger.error(f"Error getting campaign targets: {e}")
        return []

async def get_investors_by_ids(investor_ids: List[UUID]) -> List[Dict[str, Any]]:
    """Obtener inversores por IDs"""
    try:
        investors = await db.get_investors_by_ids(investor_ids)
        return investors
    except Exception as e:
        logger.error(f"Error getting investors by IDs: {e}")
        return []

async def get_investor_by_id(investor_id: UUID) -> Optional[Dict[str, Any]]:
    """Obtener inversor por ID"""
    try:
        investor = await db.get_investor(investor_id)
        return investor
    except Exception as e:
        logger.error(f"Error getting investor: {e}")
        return None

async def get_linkedin_account(account_id: str) -> Optional[Dict[str, Any]]:
    """Obtener cuenta de LinkedIn"""
    try:
        account = await db.get_linkedin_account(account_id)
        return account
    except Exception as e:
        logger.error(f"Error getting LinkedIn account: {e}")
        return None

async def update_campaign_status(campaign_id: UUID, status: str):
    """Actualizar estado de campaña"""
    try:
        updates = {
            "status": status,
            "updated_at": datetime.now().isoformat()
        }
        
        if status == "active":
            updates["launched_at"] = datetime.now().isoformat()
        elif status == "completed":
            updates["completed_at"] = datetime.now().isoformat()
        
        success = await db.update_campaign(campaign_id, updates)
        if not success:
            raise Exception("Failed to update campaign status")
    except Exception as e:
        logger.error(f"Error updating campaign status: {e}")
        raise

async def remove_campaign_target_from_db(target_id: UUID):
    """Remover target de campaña"""
    try:
        success = await db.remove_campaign_target(target_id)
        if not success:
            raise Exception("Failed to remove target")
    except Exception as e:
        logger.error(f"Error removing campaign target: {e}")
        raise

async def get_user_campaign_stats(user_id: UUID) -> CampaignStats:
    """Obtener estadísticas de campañas del usuario"""
    try:
        stats_data = await db.get_user_campaign_stats(user_id)
        
        return CampaignStats(
            total_campaigns=stats_data.get("total_campaigns", 0),
            active_campaigns=stats_data.get("active_campaigns", 0),
            total_sent=stats_data.get("total_sent", 0),
            total_replies=stats_data.get("total_replies", 0),
            average_response_rate=stats_data.get("average_response_rate", 0.0)
        )
    except Exception as e:
        logger.error(f"Error getting campaign stats: {e}")
        return CampaignStats(
            total_campaigns=0,
            active_campaigns=0,
            total_sent=0,
            total_replies=0,
            average_response_rate=0.0
        )

# ==========================================
# FUNCIONES DE FALLBACK
# ==========================================

async def create_campaign_fallback(campaign_data: CampaignCreate, user_id: UUID) -> CampaignResponse:
    """Crear campaña directamente en DB (fallback)"""
    campaign_id = uuid4()
    
    campaign_dict = {
        "id": str(campaign_id),
        "user_id": str(user_id),
        "project_id": str(campaign_data.project_id),
        "name": campaign_data.name,
        "message_template": campaign_data.message_template,
        "linkedin_account_id": campaign_data.linkedin_account_id,
        "status": "draft",
        "total_targets": 0,
        "sent_count": 0,
        "reply_count": 0,
        "accepted_count": 0,
        "error_count": 0,
        "daily_limit": 80,
        "delay_between_sends": 120,
        "created_at": datetime.now().isoformat()
    }
    
    result = db.supabase.table("outreach_campaigns").insert(campaign_dict).execute()
    
    if result.data:
        campaign_data = result.data[0]
        return CampaignResponse(
            id=UUID(campaign_data["id"]),
            name=campaign_data["name"],
            project_id=UUID(campaign_data["project_id"]),
            message_template=campaign_data["message_template"],
            status=campaign_data["status"],
            total_targets=0,
            sent_count=0,
            reply_count=0,
            success_rate=0.0,
            created_at=datetime.fromisoformat(campaign_data["created_at"].replace("Z", "+00:00")),
            launched_at=None
        )
    else:
        raise Exception("Failed to create campaign")

async def add_targets_fallback(campaign_id: UUID, investor_ids: List[UUID], message_template: str) -> List[Dict]:
    """Añadir targets directamente (fallback)"""
    targets = []
    
    for investor_id in investor_ids:
        target_data = {
            "id": str(uuid4()),
            "campaign_id": str(campaign_id),
            "investor_id": str(investor_id),
            "personalized_message": message_template,  # Sin personalización
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "retry_count": 0,
            "max_retries": 3
        }
        targets.append(target_data)
    
    if targets:
        result = db.supabase.table("outreach_targets").insert(targets).execute()
        return result.data
    
    return []

async def get_basic_analytics(campaign_id: UUID) -> Dict[str, Any]:
    """Analíticas básicas (fallback)"""
    # Obtener datos básicos de la campaña
    campaign_result = db.supabase.table("outreach_campaigns").select("*").eq("id", str(campaign_id)).execute()
    
    if not campaign_result.data:
        return {"error": "Campaign not found"}
    
    campaign = campaign_result.data[0]
    
    # Obtener targets
    targets_result = db.supabase.table("outreach_targets").select("status").eq("campaign_id", str(campaign_id)).execute()
    
    status_counts = {}
    for target in targets_result.data:
        status = target["status"]
        status_counts[status] = status_counts.get(status, 0) + 1
    
    return {
        "campaign_id": str(campaign_id),
        "status": campaign["status"],
        "targets_by_status": status_counts,
        "response_rate": calculate_success_rate(campaign),
        "total_targets": campaign.get("total_targets", 0),
        "sent_count": campaign.get("sent_count", 0),
        "reply_count": campaign.get("reply_count", 0),
        "created_at": campaign["created_at"],
        "launched_at": campaign.get("launched_at")
    }

def simple_personalize_message(template: str, investor: Dict, project) -> str:
    """Personalización simple de mensaje (fallback)"""
    message = template
    
    # Reemplazos básicos
    replacements = {
        "{name}": investor.get("full_name", ""),
        "{fund}": investor.get("fund_name", ""),
        "{startup_name}": project.name,
        "{sector}": ", ".join(project.project_data.categories or []) or "tech"
    }
    
    for placeholder, value in replacements.items():
        message = message.replace(placeholder, value)
    
    # Truncar si es muy largo
    if len(message) > 300:
        message = message[:280] + "..."
    
    return message

def calculate_success_rate(campaign_data: Dict[str, Any]) -> float:
    """Calcular tasa de éxito"""
    sent = campaign_data.get("sent_count", 0)
    replies = campaign_data.get("reply_count", 0)
    
    if sent == 0:
        return 0.0
    
    return round((replies / sent) * 100, 2)
