# api/campaigns.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
import logging

from models.schemas import ApiResponse
from database.database import db
from api.utils import get_current_user
from integrations.unipile_client import unipile_client
from campaigns.campaign_manager import campaign_manager
from campaigns.message_generator import message_personalizer

router = APIRouter()
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

@router.post("/campaigns", response_model=CampaignResponse)
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
        
        # Crear campaña
        campaign = await campaign_manager.create_campaign(
            user_id=current_user,
            project_id=campaign_data.project_id,
            name=campaign_data.name,
            message_template=campaign_data.message_template,
            linkedin_account_id=campaign_data.linkedin_account_id,
            target_investor_ids=campaign_data.target_investor_ids
        )
        
        return campaign
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating campaign: {e}")
        raise HTTPException(status_code=500, detail="Error creating campaign")

@router.get("/campaigns", response_model=List[CampaignResponse])
async def get_user_campaigns(current_user: UUID = Depends(get_current_user)):
    """Obtener todas las campañas del usuario"""
    try:
        campaigns = await db.get_user_campaigns(current_user)
        return campaigns
    except Exception as e:
        logger.error(f"Error getting campaigns: {e}")
        raise HTTPException(status_code=500, detail="Error getting campaigns")

@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: UUID,
    current_user: UUID = Depends(get_current_user)
):
    """Obtener campaña específica"""
    try:
        campaign = await db.get_campaign(campaign_id, current_user)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return campaign
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign: {e}")
        raise HTTPException(status_code=500, detail="Error getting campaign")

@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: UUID,
    updates: CampaignUpdate,
    current_user: UUID = Depends(get_current_user)
):
    """Actualizar campaña"""
    try:
        campaign = await db.get_campaign(campaign_id, current_user)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # No permitir cambios si la campaña ya está activa
        if campaign.status == "active" and updates.status not in ["paused", "completed"]:
            raise HTTPException(
                status_code=400, 
                detail="Cannot modify active campaign. Pause it first."
            )
        
        updated_campaign = await db.update_campaign(campaign_id, updates.dict(exclude_unset=True))
        return updated_campaign
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating campaign: {e}")
        raise HTTPException(status_code=500, detail="Error updating campaign")

@router.delete("/campaigns/{campaign_id}")
async def delete_campaign(
    campaign_id: UUID,
    current_user: UUID = Depends(get_current_user)
):
    """Eliminar campaña"""
    try:
        campaign = await db.get_campaign(campaign_id, current_user)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        if campaign.status == "active":
            raise HTTPException(
                status_code=400, 
                detail="Cannot delete active campaign. Pause it first."
            )
        
        await db.delete_campaign(campaign_id)
        return ApiResponse(success=True, message="Campaign deleted successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting campaign: {e}")
        raise HTTPException(status_code=500, detail="Error deleting campaign")

# ==========================================
# GESTIÓN DE TARGETS
# ==========================================

@router.post("/campaigns/{campaign_id}/targets")
async def add_targets_to_campaign(
    campaign_id: UUID,
    investor_ids: List[UUID],
    current_user: UUID = Depends(get_current_user)
):
    """Añadir inversores como targets a campaña"""
    try:
        campaign = await db.get_campaign(campaign_id, current_user)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        if campaign.status == "active":
            raise HTTPException(
                status_code=400, 
                detail="Cannot modify targets of active campaign"
            )
        
        # Verificar que los inversores existen
        investors = await db.get_investors_by_ids(investor_ids)
        if len(investors) != len(investor_ids):
            raise HTTPException(status_code=400, detail="Some investors not found")
        
        # Añadir targets
        added_targets = await campaign_manager.add_targets_to_campaign(
            campaign_id, investor_ids, campaign.message_template
        )
        
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

@router.get("/campaigns/{campaign_id}/targets", response_model=List[TargetResponse])
async def get_campaign_targets(
    campaign_id: UUID,
    current_user: UUID = Depends(get_current_user)
):
    """Obtener targets de una campaña"""
    try:
        campaign = await db.get_campaign(campaign_id, current_user)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        targets = await db.get_campaign_targets(campaign_id)
        return targets
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting targets: {e}")
        raise HTTPException(status_code=500, detail="Error getting targets")

@router.delete("/campaigns/{campaign_id}/targets/{target_id}")
async def remove_target_from_campaign(
    campaign_id: UUID,
    target_id: UUID,
    current_user: UUID = Depends(get_current_user)
):
    """Remover target de campaña"""
    try:
        campaign = await db.get_campaign(campaign_id, current_user)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        if campaign.status == "active":
            raise HTTPException(
                status_code=400, 
                detail="Cannot modify targets of active campaign"
            )
        
        await db.remove_campaign_target(target_id)
        return ApiResponse(success=True, message="Target removed from campaign")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing target: {e}")
        raise HTTPException(status_code=500, detail="Error removing target")

# ==========================================
# LANZAMIENTO Y CONTROL DE CAMPAÑAS
# ==========================================

@router.post("/campaigns/{campaign_id}/launch")
async def launch_campaign(
    campaign_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: UUID = Depends(get_current_user)
):
    """Lanzar campaña de outreach"""
    try:
        campaign = await db.get_campaign(campaign_id, current_user)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        if campaign.status != "draft":
            raise HTTPException(status_code=400, detail="Campaign already launched")
        
        # Verificar que tiene targets
        targets = await db.get_campaign_targets(campaign_id)
        if not targets:
            raise HTTPException(status_code=400, detail="Campaign has no targets")
        
        # Verificar cuenta de LinkedIn
        linkedin_account = await db.get_linkedin_account(campaign.linkedin_account_id)
        if not linkedin_account or linkedin_account.status != "connected":
            raise HTTPException(
                status_code=400, 
                detail="LinkedIn account not connected or in error state"
            )
        
        # Lanzar campaña
        await campaign_manager.launch_campaign(campaign_id)
        
        # Programar envío en background
        background_tasks.add_task(
            campaign_manager.process_campaign_sends,
            campaign_id
        )
        
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

@router.post("/campaigns/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: UUID,
    current_user: UUID = Depends(get_current_user)
):
    """Pausar campaña activa"""
    try:
        campaign = await db.get_campaign(campaign_id, current_user)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        if campaign.status != "active":
            raise HTTPException(status_code=400, detail="Campaign is not active")
        
        await db.update_campaign(campaign_id, {"status": "paused"})
        
        return ApiResponse(success=True, message="Campaign paused successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing campaign: {e}")
        raise HTTPException(status_code=500, detail="Error pausing campaign")

@router.post("/campaigns/{campaign_id}/resume")
async def resume_campaign(
    campaign_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: UUID = Depends(get_current_user)
):
    """Reanudar campaña pausada"""
    try:
        campaign = await db.get_campaign(campaign_id, current_user)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        if campaign.status != "paused":
            raise HTTPException(status_code=400, detail="Campaign is not paused")
        
        await db.update_campaign(campaign_id, {"status": "active"})
        
        # Reanudar envío en background
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

@router.get("/campaigns/stats", response_model=CampaignStats)
async def get_campaign_stats(current_user: UUID = Depends(get_current_user)):
    """Obtener estadísticas generales de campañas"""
    try:
        stats = await db.get_user_campaign_stats(current_user)
        return stats
    except Exception as e:
        logger.error(f"Error getting campaign stats: {e}")
        raise HTTPException(status_code=500, detail="Error getting campaign stats")

@router.get("/campaigns/{campaign_id}/analytics")
async def get_campaign_analytics(
    campaign_id: UUID,
    current_user: UUID = Depends(get_current_user)
):
    """Obtener analíticas detalladas de campaña"""
    try:
        campaign = await db.get_campaign(campaign_id, current_user)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        analytics = await campaign_manager.get_campaign_analytics(campaign_id)
        return analytics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign analytics: {e}")
        raise HTTPException(status_code=500, detail="Error getting campaign analytics")

# ==========================================
# TESTING Y PREVIEW
# ==========================================

@router.post("/campaigns/preview-message")
async def preview_personalized_message(
    template: str,
    investor_id: UUID,
    project_id: UUID,
    current_user: UUID = Depends(get_current_user)
):
    """Preview mensaje personalizado"""
    try:
        # Obtener datos del inversor y proyecto
        investor = await db.get_investor(investor_id)
        project = await db.get_project(project_id, current_user)
        
        if not investor or not project:
            raise HTTPException(status_code=404, detail="Investor or project not found")
        
        # Generar mensaje personalizado
        personalized_message = await message_personalizer.personalize_message(
            template=template,
            investor_data=investor.dict(),
            startup_data=project.dict()
        )
        
        return {
            "template": template,
            "personalized_message": personalized_message,
            "investor_name": investor.full_name,
            "character_count": len(personalized_message)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing message: {e}")
        raise HTTPException(status_code=500, detail="Error previewing message")

@router.post("/campaigns/{campaign_id}/test-send")
async def test_send_message(
    campaign_id: UUID,
    target_id: UUID,
    current_user: UUID = Depends(get_current_user)
):
    """Enviar mensaje de prueba a un target específico"""
    try:
        campaign = await db.get_campaign(campaign_id, current_user)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Solo en modo desarrollo/testing
        if os.getenv("ENVIRONMENT") != "development":
            raise HTTPException(status_code=403, detail="Test sends only available in development")
        
        result = await campaign_manager.send_test_message(campaign_id, target_id)
        
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
