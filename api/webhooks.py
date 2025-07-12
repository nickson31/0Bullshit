from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()

@router.post("/webhooks/unipile")
async def unipile_webhook(request: Request):
    payload = await request.json()
    print("[Unipile Webhook] Payload recibido:", payload)
    # TODO: procesar y actualizar estado en la base de datos
    return JSONResponse(content={"ok": True}) 
