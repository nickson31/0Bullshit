#!/usr/bin/env python3
"""
Sistema de Pagos 0Bullshit con Stripe
====================================

Gestión completa de suscripciones, pagos únicos y webhooks de Stripe.
"""

import os
import stripe
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel

from database.database import db

# Configurar Stripe
stripe.api_key = os.getenv("STRIPE_API_KEY")

# Router de pagos
router = APIRouter()

# ==========================================
# CONFIGURACIÓN DE PLANES
# ==========================================

PLAN_CONFIGS = {
    "pro": {
        "credits_monthly": 10000,
        "daily_credits": 150,
        "price": 24.50,
        "features": ["chat", "investor_search", "company_search"]
    },
    "outreach": {
        "credits_monthly": 29900,
        "daily_credits": 200, 
        "price": 94.50,
        "features": ["chat", "investor_search", "company_search", "linkedin_outreach"]
    }
}

# ==========================================
# WEBHOOK DE STRIPE
# ==========================================

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Webhook para manejar eventos de Stripe"""
    try:
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')
        
        # Verificar webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
        )
        
        # Procesar evento
        if event['type'] == 'checkout.session.completed':
            await handle_checkout_completed(event['data']['object'])
        elif event['type'] == 'customer.subscription.deleted':
            await handle_subscription_deleted(event['data']['object'])
        
        return {"status": "success"}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature")

async def handle_checkout_completed(session: Dict[str, Any]):
    """Manejar checkout completado"""
    try:
        user_id = session['metadata']['user_id']
        session_type = session['metadata']['type']
        
        if session_type == 'subscription':
            # Activar suscripción
            plan = session['metadata']['plan']
            subscription_id = session['subscription']
            
            plan_config = PLAN_CONFIGS.get(plan)
            if plan_config:
                expires_at = datetime.utcnow() + timedelta(days=30)
                
                db.supabase.table("users").update({
                    "plan": plan,
                    "credits_balance": plan_config["credits_monthly"],
                    "daily_credits": plan_config["daily_credits"],
                    "plan_expires_at": expires_at.isoformat(),
                    "stripe_subscription_id": subscription_id,
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", user_id).execute()
            
        elif session_type == 'credit_purchase':
            # Añadir créditos
            credits = int(session['metadata']['credits'])
            
            result = db.supabase.table("users").select("credits_balance").eq("id", user_id).execute()
            if result.data:
                current_credits = result.data[0]["credits_balance"]
                new_credits = current_credits + credits
                
                db.supabase.table("users").update({
                    "credits_balance": new_credits,
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", user_id).execute()
            
    except Exception as e:
        print(f"Error handling checkout completed: {e}")

async def handle_subscription_deleted(subscription: Dict[str, Any]):
    """Manejar suscripción cancelada"""
    try:
        subscription_id = subscription['id']
        
        # Revertir usuario a plan free
        db.supabase.table("users").update({
            "plan": "free",
            "credits_balance": 200,
            "daily_credits": 50,
            "plan_expires_at": None,
            "stripe_subscription_id": None,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("stripe_subscription_id", subscription_id).execute()
        
    except Exception as e:
        print(f"Error handling subscription deleted: {e}")

@router.get("/payments/plans")
async def get_available_plans():
    """Obtener planes disponibles"""
    return {
        "plans": [
            {
                "id": "free",
                "name": "Plan Gratuito",
                "price": 0,
                "credits_monthly": 200,
                "features": ["chat"]
            },
            {
                "id": "pro", 
                "name": "Plan Pro",
                "price": 24.50,
                "credits_monthly": 10000,
                "features": ["chat", "investor_search", "company_search"],
                "popular": True
            },
            {
                "id": "outreach",
                "name": "Plan Outreach", 
                "price": 94.50,
                "credits_monthly": 29900,
                "features": ["chat", "investor_search", "company_search", "linkedin_outreach"]
            }
        ]
    }
