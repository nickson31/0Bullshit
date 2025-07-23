from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import requests

outreach_router = APIRouter()

UNIPILE_API_URL = os.getenv("UNIPILE_API_URL")
UNIPILE_API_KEY = os.getenv("UNIPILE_API_KEY")

class OutreachStartRequest(BaseModel):
    campaign_id: str
    targets: List[str]  # IDs de business angels o empleados
    account_id: str  # LinkedIn account_id conectado en Unipile
    message: str

@outreach_router.post("/outreach/start")
def start_outreach(req: OutreachStartRequest):
    results = []
    for target_id in req.targets:
        # Dummy: Determinar si hay relación (en real, consultar Unipile o base de datos)
        has_relationship = False  # TODO: implementar consulta real
        try:
            if has_relationship:
                # Enviar mensaje directo
                payload = {
                    "account_id": req.account_id,
                    "attendees_ids": [target_id],
                    "text": req.message
                }
                headers = {
                    "X-API-KEY": UNIPILE_API_KEY,
                    "accept": "application/json"
                }
                r = requests.post(f"{UNIPILE_API_URL}/chats", data=payload, headers=headers)
                r.raise_for_status()
                results.append({"target_id": target_id, "status": "message_sent"})
            else:
                # Enviar invitación
                payload = {
                    "account_id": req.account_id,
                    "provider_id": target_id,
                    "message": req.message
                }
                headers = {
                    "X-API-KEY": UNIPILE_API_KEY,
                    "accept": "application/json",
                    "content-type": "application/json"
                }
                r = requests.post(f"{UNIPILE_API_URL}/users/invite", json=payload, headers=headers)
                r.raise_for_status()
                results.append({"target_id": target_id, "status": "invitation_sent"})
        except Exception as e:
            results.append({"target_id": target_id, "status": "error", "error": str(e)})
    return {"results": results} 
