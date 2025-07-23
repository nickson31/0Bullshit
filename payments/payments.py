import os
import stripe
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Request, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID

from database.database import db
from api.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

# Stripe configuration
stripe.api_key = os.getenv("STRIPE_API_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Plan pricing (in cents)
PLAN_PRICING = {
    "pro": {
        "price": 2450,  # $24.50
        "credits": 10000,
        "daily_credits": 150,
        "price_id": os.getenv("STRIPE_PRO_PRICE_ID", "price_pro_monthly")
    },
    "outreach": {
        "price": 9450,  # $94.50
        "credits": 29900,
        "daily_credits": 200,
        "price_id": os.getenv("STRIPE_OUTREACH_PRICE_ID", "price_outreach_monthly")
    }
}

# Credit packages pricing (in cents)
CREDIT_PACKAGES = {
    "small": {
        "credits": 4900,
        "price": 1900,  # $19
        "price_id": os.getenv("STRIPE_CREDITS_SMALL_ID", "price_credits_small")
    },
    "medium": {
        "credits": 19900,
        "price": 5900,  # $59
        "price_id": os.getenv("STRIPE_CREDITS_MEDIUM_ID", "price_credits_medium")
    },
    "large": {
        "credits": 49900,
        "price": 14900,  # $149
        "price_id": os.getenv("STRIPE_CREDITS_LARGE_ID", "price_credits_large")
    }
}

# ==========================================
# PYDANTIC MODELS
# ==========================================

class CreateSubscriptionRequest(BaseModel):
    plan: str = Field(..., pattern="^(pro|outreach)$")
    payment_method_id: str

class BuyCreditsRequest(BaseModel):
    package: str = Field(..., pattern="^(small|medium|large)$")
    payment_method_id: str

class SubscriptionResponse(BaseModel):
    id: str
    status: str
    plan: str
    current_period_start: datetime
    current_period_end: datetime

class UserPlanResponse(BaseModel):
    plan: str
    credits: int
    daily_credits: int

class PaymentResponse(BaseModel):
    subscription: Optional[SubscriptionResponse] = None
    user: UserPlanResponse

class CreditPurchaseResponse(BaseModel):
    purchase: Dict[str, Any]
    user: UserPlanResponse

class BillingHistoryItem(BaseModel):
    id: str
    type: str
    description: str
    amount: int
    status: str
    created_at: datetime
    invoice_url: Optional[str] = None

class MessageResponse(BaseModel):
    message: str
    cancels_at: Optional[datetime] = None

# ==========================================
# SUBSCRIPTION MANAGEMENT
# ==========================================

@router.post("/create-subscription", response_model=PaymentResponse)
async def create_subscription(
    request: CreateSubscriptionRequest,
    current_user: UUID = Depends(get_current_user)
):
    """Create new subscription"""
    try:
        # Validate plan
        if request.plan not in PLAN_PRICING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid plan"
            )
        
        # Get user info
        user = await db.get_user_by_id(current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if user already has active subscription
        existing_subscription = await db.get_user_subscription(current_user)
        if existing_subscription and existing_subscription.get("status") == "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already has an active subscription"
            )
        
        # Get or create Stripe customer
        stripe_customer_id = await _get_or_create_stripe_customer(user)
        
        # Attach payment method to customer
        try:
            stripe.PaymentMethod.attach(
                request.payment_method_id,
                customer=stripe_customer_id
            )
        except stripe.error.StripeError as e:
            logger.error(f"Failed to attach payment method: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payment method"
            )
        
        # Create subscription
        plan_config = PLAN_PRICING[request.plan]
        
        try:
            subscription = stripe.Subscription.create(
                customer=stripe_customer_id,
                items=[{
                    'price': plan_config["price_id"]
                }],
                default_payment_method=request.payment_method_id,
                expand=['latest_invoice.payment_intent'],
                metadata={
                    'user_id': str(current_user),
                    'plan': request.plan
                }
            )
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create subscription: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment failed: {str(e)}"
            )
        
        # Update user plan and credits
        await _update_user_plan(
            current_user, 
            request.plan, 
            plan_config["credits"],
            plan_config["daily_credits"]
        )
        
        # Store subscription in database
        await _store_subscription(current_user, subscription)
        
        # Log successful subscription
        logger.info(f"Subscription created: {subscription.id} for user {current_user}")
        
        # Return response
        subscription_response = SubscriptionResponse(
            id=subscription.id,
            status=subscription.status,
            plan=request.plan,
            current_period_start=datetime.fromtimestamp(subscription.current_period_start),
            current_period_end=datetime.fromtimestamp(subscription.current_period_end)
        )
        
        user_response = UserPlanResponse(
            plan=request.plan,
            credits=plan_config["credits"],
            daily_credits=plan_config["daily_credits"]
        )
        
        return PaymentResponse(
            subscription=subscription_response,
            user=user_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Subscription creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/cancel-subscription", response_model=MessageResponse)
async def cancel_subscription(current_user: UUID = Depends(get_current_user)):
    """Cancel user subscription"""
    try:
        # Get current subscription
        subscription_data = await db.get_user_subscription(current_user)
        if not subscription_data or subscription_data.get("status") != "active":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found"
            )
        
        stripe_subscription_id = subscription_data.get("stripe_subscription_id")
        if not stripe_subscription_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid subscription data"
            )
        
        # Cancel subscription at period end
        try:
            subscription = stripe.Subscription.modify(
                stripe_subscription_id,
                cancel_at_period_end=True
            )
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to cancel subscription"
            )
        
        # Update subscription in database
        await db.update_subscription_status(current_user, "canceling")
        
        cancels_at = datetime.fromtimestamp(subscription.current_period_end)
        
        logger.info(f"Subscription canceled: {stripe_subscription_id} for user {current_user}")
        
        return MessageResponse(
            message="Subscription will be canceled at the end of the current period",
            cancels_at=cancels_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Subscription cancellation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# ==========================================
# CREDIT PURCHASES
# ==========================================

@router.post("/buy-credits", response_model=CreditPurchaseResponse)
async def buy_credits(
    request: BuyCreditsRequest,
    current_user: UUID = Depends(get_current_user)
):
    """Purchase additional credits"""
    try:
        # Validate package
        if request.package not in CREDIT_PACKAGES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid credit package"
            )
        
        # Get user info
        user = await db.get_user_by_id(current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get or create Stripe customer
        stripe_customer_id = await _get_or_create_stripe_customer(user)
        
        # Get package config
        package_config = CREDIT_PACKAGES[request.package]
        
        # Create payment intent
        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=package_config["price"],
                currency='usd',
                customer=stripe_customer_id,
                payment_method=request.payment_method_id,
                confirm=True,
                return_url='https://app.0bullshit.com/credits/success',
                metadata={
                    'user_id': str(current_user),
                    'package': request.package,
                    'credits': package_config["credits"]
                }
            )
        except stripe.error.StripeError as e:
            logger.error(f"Payment failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment failed: {str(e)}"
            )
        
        # Check payment status
        if payment_intent.status != "succeeded":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment was not successful"
            )
        
        # Add credits to user
        current_credits = user.get("credits", 0)
        new_credits = current_credits + package_config["credits"]
        
        await db.update_user_credits(current_user, new_credits)
        
        # Store purchase record
        await _store_credit_purchase(current_user, payment_intent, package_config)
        
        logger.info(f"Credits purchased: {package_config['credits']} for user {current_user}")
        
        # Return response
        purchase_response = {
            "id": payment_intent.id,
            "credits_purchased": package_config["credits"],
            "amount_paid": package_config["price"],
            "status": payment_intent.status
        }
        
        user_response = UserPlanResponse(
            plan=user.get("plan", "free"),
            credits=new_credits,
            daily_credits=user.get("daily_credits", 50)
        )
        
        return CreditPurchaseResponse(
            purchase=purchase_response,
            user=user_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Credit purchase error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# ==========================================
# BILLING HISTORY
# ==========================================

@router.get("/billing-history", response_model=List[BillingHistoryItem])
async def get_billing_history(current_user: UUID = Depends(get_current_user)):
    """Get user billing history"""
    try:
        # Get user's Stripe customer ID
        user = await db.get_user_by_id(current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        stripe_customer_id = user.get("stripe_customer_id")
        if not stripe_customer_id:
            return []  # No payment history
        
        # Get charges from Stripe
        try:
            charges = stripe.Charge.list(
                customer=stripe_customer_id,
                limit=50
            )
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get billing history: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve billing history"
            )
        
        # Convert to response format
        billing_items = []
        for charge in charges:
            # Determine type and description
            metadata = charge.get("metadata", {})
            if "package" in metadata:
                charge_type = "credits"
                description = f"Credit Package: {metadata['package'].title()}"
            else:
                charge_type = "subscription"
                plan = metadata.get("plan", "unknown")
                description = f"Plan {plan.title()} - Monthly"
            
            # Get invoice URL if available
            invoice_url = None
            if charge.get("invoice"):
                try:
                    invoice = stripe.Invoice.retrieve(charge["invoice"])
                    invoice_url = invoice.get("hosted_invoice_url")
                except:
                    pass
            
            billing_item = BillingHistoryItem(
                id=charge.id,
                type=charge_type,
                description=description,
                amount=charge.amount,
                status="paid" if charge.paid else "failed",
                created_at=datetime.fromtimestamp(charge.created),
                invoice_url=invoice_url
            )
            billing_items.append(billing_item)
        
        return billing_items
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Billing history error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# ==========================================
# STRIPE WEBHOOKS
# ==========================================

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    try:
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')
        
        if not sig_header:
            raise HTTPException(status_code=400, detail="Missing signature")
        
        # Verify webhook signature
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            logger.error("Invalid payload in webhook")
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid signature in webhook")
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Handle the event
        await _handle_stripe_event(event)
        
        return {"status": "success"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )

# ==========================================
# HELPER FUNCTIONS
# ==========================================

async def _get_or_create_stripe_customer(user: Dict[str, Any]) -> str:
    """Get or create Stripe customer for user"""
    try:
        # Check if user already has Stripe customer ID
        stripe_customer_id = user.get("stripe_customer_id")
        
        if stripe_customer_id:
            # Verify customer exists in Stripe
            try:
                stripe.Customer.retrieve(stripe_customer_id)
                return stripe_customer_id
            except stripe.error.StripeError:
                # Customer doesn't exist, create new one
                pass
        
        # Create new Stripe customer
        customer = stripe.Customer.create(
            email=user["email"],
            name=user["name"],
            metadata={
                'user_id': user["id"]
            }
        )
        
        # Store customer ID in database
        await db.update_user_stripe_customer(UUID(user["id"]), customer.id)
        
        return customer.id
        
    except Exception as e:
        logger.error(f"Failed to get/create Stripe customer: {e}")
        raise

async def _update_user_plan(user_id: UUID, plan: str, credits: int, daily_credits: int):
    """Update user plan and credits"""
    try:
        await db.update_user_plan(user_id, plan, credits, daily_credits)
    except Exception as e:
        logger.error(f"Failed to update user plan: {e}")
        raise

async def _store_subscription(user_id: UUID, subscription: stripe.Subscription):
    """Store subscription data in database"""
    try:
        subscription_data = {
            "user_id": str(user_id),
            "stripe_subscription_id": subscription.id,
            "stripe_customer_id": subscription.customer,
            "status": subscription.status,
            "current_period_start": datetime.fromtimestamp(subscription.current_period_start),
            "current_period_end": datetime.fromtimestamp(subscription.current_period_end),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        await db.store_subscription(subscription_data)
        
    except Exception as e:
        logger.error(f"Failed to store subscription: {e}")
        raise

async def _store_credit_purchase(user_id: UUID, payment_intent: stripe.PaymentIntent, package_config: Dict[str, Any]):
    """Store credit purchase record"""
    try:
        purchase_data = {
            "user_id": str(user_id),
            "stripe_payment_intent_id": payment_intent.id,
            "package": payment_intent.metadata.get("package"),
            "credits_purchased": package_config["credits"],
            "amount_paid": package_config["price"],
            "status": payment_intent.status,
            "created_at": datetime.now()
        }
        
        await db.store_credit_purchase(purchase_data)
        
    except Exception as e:
        logger.error(f"Failed to store credit purchase: {e}")
        raise

async def _handle_stripe_event(event: Dict[str, Any]):
    """Handle different Stripe webhook events"""
    try:
        event_type = event["type"]
        data = event["data"]["object"]
        
        if event_type == "customer.subscription.updated":
            await _handle_subscription_updated(data)
        elif event_type == "customer.subscription.deleted":
            await _handle_subscription_deleted(data)
        elif event_type == "invoice.payment_succeeded":
            await _handle_payment_succeeded(data)
        elif event_type == "invoice.payment_failed":
            await _handle_payment_failed(data)
        else:
            logger.info(f"Unhandled webhook event: {event_type}")
        
    except Exception as e:
        logger.error(f"Failed to handle Stripe event: {e}")
        raise

async def _handle_subscription_updated(subscription_data: Dict[str, Any]):
    """Handle subscription update webhook"""
    try:
        subscription_id = subscription_data["id"]
        new_status = subscription_data["status"]
        
        # Update subscription status in database
        await db.update_subscription_by_stripe_id(subscription_id, {
            "status": new_status,
            "updated_at": datetime.now()
        })
        
        logger.info(f"Subscription {subscription_id} updated to status: {new_status}")
        
    except Exception as e:
        logger.error(f"Failed to handle subscription update: {e}")

async def _handle_subscription_deleted(subscription_data: Dict[str, Any]):
    """Handle subscription deletion webhook"""
    try:
        subscription_id = subscription_data["id"]
        user_id = subscription_data["metadata"].get("user_id")
        
        if user_id:
            # Downgrade user to free plan
            await db.update_user_plan(UUID(user_id), "free", 200, 50)
        
        # Update subscription status
        await db.update_subscription_by_stripe_id(subscription_id, {
            "status": "canceled",
            "updated_at": datetime.now()
        })
        
        logger.info(f"Subscription {subscription_id} deleted")
        
    except Exception as e:
        logger.error(f"Failed to handle subscription deletion: {e}")

async def _handle_payment_succeeded(invoice_data: Dict[str, Any]):
    """Handle successful payment webhook"""
    try:
        subscription_id = invoice_data.get("subscription")
        if subscription_id:
            # Subscription payment succeeded - renew plan
            await db.update_subscription_by_stripe_id(subscription_id, {
                "status": "active",
                "updated_at": datetime.now()
            })
            
            logger.info(f"Payment succeeded for subscription: {subscription_id}")
        
    except Exception as e:
        logger.error(f"Failed to handle payment success: {e}")

async def _handle_payment_failed(invoice_data: Dict[str, Any]):
    """Handle failed payment webhook"""
    try:
        subscription_id = invoice_data.get("subscription")
        if subscription_id:
            # Payment failed - update status
            await db.update_subscription_by_stripe_id(subscription_id, {
                "status": "past_due",
                "updated_at": datetime.now()
            })
            
            logger.warning(f"Payment failed for subscription: {subscription_id}")
        
    except Exception as e:
        logger.error(f"Failed to handle payment failure: {e}")

# ==========================================
# UTILITY FUNCTIONS
# ==========================================

def get_plan_limits(plan: str) -> Dict[str, Any]:
    """Get limits and features for a plan"""
    limits = {
        "free": {
            "monthly_credits": 200,
            "daily_credits": 50,
            "searches_per_hour": 0,
            "chat_cost": 10,
            "features": ["mentor"]
        },
        "pro": {
            "monthly_credits": 10000,
            "daily_credits": 150,
            "searches_per_hour": 5,
            "chat_cost": 5,
            "features": ["mentor", "investors"]
        },
        "outreach": {
            "monthly_credits": 29900,
            "daily_credits": 200,
            "searches_per_hour": 20,
            "chat_cost": 0,
            "features": ["mentor", "investors", "outreach"]
        }
    }
    
    return limits.get(plan, limits["free"])

def calculate_action_cost(action: str, plan: str) -> int:
    """Calculate cost in credits for an action"""
    costs = {
        "chat_message": {
            "free": 10,
            "pro": 5,
            "outreach": 0
        },
        "search_investors": {
            "free": 1000,  # Not allowed, but for reference
            "pro": 1000,
            "outreach": 1000
        },
        "search_companies": {
            "free": 250,  # Not allowed, but for reference
            "pro": 250,
            "outreach": 250
        }
    }
    
    return costs.get(action, {}).get(plan, 0)
