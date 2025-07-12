from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import requests
from typing import Optional

router = APIRouter()

UNIPILE_API_URL = os.getenv("UNIPILE_API_URL")  # Ej: https://apiXXX.unipile.com:XXX/api/v1
UNIPILE_API_KEY = os.getenv("UNIPILE_API_KEY")

class ConnectLinkedInRequest(BaseModel):
    user_id: str
    success_url: str
    failure_url: str
    notify_url: str

@router.post("/linkedin/connect")
def connect_linkedin(req: ConnectLinkedInRequest):
    payload = {
        "type": "create",
        "providers": ["LINKEDIN"],
        "api_url": UNIPILE_API_URL,
        "expiresOn": "2099-12-31T23:59:59.999Z",
        "success_redirect_url": req.success_url,
        "failure_redirect_url": req.failure_url,
        "notify_url": req.notify_url,
        "name": req.user_id
    }
    headers = {
        "X-API-KEY": UNIPILE_API_KEY,
        "accept": "application/json",
        "content-type": "application/json"
    }
    try:
        r = requests.post(f"{UNIPILE_API_URL}/hosted/accounts/link", json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
        return {"url": data["url"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
