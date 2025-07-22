# 📚 API DOCUMENTATION - 0BULLSHIT PLATFORM

## 🎯 BASE URL
```
Development: http://localhost:8000
Production: https://api.0bullshit.com
```

## 🔐 AUTHENTICATION

Todas las rutas (excepto health y auth) requieren autenticación JWT:

```http
Authorization: Bearer <jwt-token>
```

---

## 🏥 HEALTH CHECK

### GET /health
Verificar estado del sistema.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "services": {
    "supabase": "healthy",
    "gemini": "healthy", 
    "unipile": "healthy"
  }
}
```

---

## 🔑 AUTHENTICATION ENDPOINTS

### POST /api/v1/auth/register
Registrar nuevo usuario.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "name": "John Doe"
}
```

**Response:**
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "John Doe",
    "plan": "free",
    "credits": 200,
    "created_at": "2024-01-01T12:00:00Z"
  },
  "access_token": "jwt-token",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### POST /api/v1/auth/login
Iniciar sesión.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "John Doe",
    "plan": "pro",
    "credits": 8500,
    "created_at": "2024-01-01T12:00:00Z"
  },
  "access_token": "jwt-token",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### POST /api/v1/auth/refresh
Renovar token de acceso.

**Request:**
```json
{
  "refresh_token": "refresh-jwt-token"
}
```

**Response:**
```json
{
  "access_token": "new-jwt-token",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### GET /api/v1/auth/me
Obtener información del usuario actual.

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "John Doe",
  "plan": "pro",
  "credits": 8500,
  "daily_credits_remaining": 150,
  "created_at": "2024-01-01T12:00:00Z",
  "subscription": {
    "status": "active",
    "current_period_end": "2024-02-01T12:00:00Z"
  }
}
```

### POST /api/v1/auth/logout
Cerrar sesión.

**Response:**
```json
{
  "message": "Successfully logged out"
}
```

---

## 📋 PROJECT ENDPOINTS

### POST /api/v1/projects
Crear nuevo proyecto.

**Request:**
```json
{
  "name": "Mi Startup FinTech",
  "description": "Plataforma de pagos digitales para PYMES"
}
```

**Response:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "name": "Mi Startup FinTech",
  "description": "Plataforma de pagos digitales para PYMES",
  "categories": [],
  "stage": null,
  "project_data": {
    "categories": null,
    "stage": null,
    "metrics": null,
    "team_info": null,
    "problem_solved": null,
    "product_status": null,
    "previous_funding": null,
    "additional_fields": {}
  },
  "context_summary": null,
  "completeness_score": 0.0,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

### GET /api/v1/projects
Obtener todos los proyectos del usuario.

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Mi Startup FinTech",
    "description": "Plataforma de pagos digitales para PYMES",
    "categories": ["fintech", "payments"],
    "stage": "mvp",
    "completeness_score": 75.5,
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z"
  }
]
```

### GET /api/v1/projects/{project_id}
Obtener proyecto específico.

**Response:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "name": "Mi Startup FinTech",
  "description": "Plataforma de pagos digitales para PYMES",
  "categories": ["fintech", "payments"],
  "stage": "mvp",
  "project_data": {
    "categories": ["fintech", "payments", "b2b"],
    "stage": "mvp",
    "metrics": {
      "arr": "50000",
      "mrr": "4200",
      "users": "1500"
    },
    "team_info": {
      "size": 4,
      "roles": ["CEO", "CTO", "Developer", "Designer"],
      "experience": "5+ years"
    },
    "problem_solved": "Pagos complejos para PYMES",
    "product_status": "MVP en production",
    "previous_funding": "Pre-seed $100k"
  },
  "completeness_score": 85.0,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:30:00Z"
}
```

### GET /api/v1/projects/{project_id}/completeness
Obtener análisis de completitud del proyecto.

**Response:**
```json
{
  "overall_score": 85.0,
  "breakdown": {
    "categories": {
      "score": 25.0,
      "percentage": 100,
      "status": "complete",
      "missing_fields": []
    },
    "stage": {
      "score": 25.0,
      "percentage": 100,
      "status": "complete",
      "missing_fields": []
    },
    "metrics": {
      "score": 12.0,
      "percentage": 80,
      "status": "partial",
      "missing_fields": ["growth_rate"]
    },
    "team_info": {
      "score": 10.0,
      "percentage": 100,
      "status": "complete",
      "missing_fields": []
    },
    "problem_solved": {
      "score": 8.0,
      "percentage": 80,
      "status": "partial",
      "missing_fields": []
    },
    "product_status": {
      "score": 5.0,
      "percentage": 50,
      "status": "partial",
      "missing_fields": []
    },
    "previous_funding": {
      "score": 0.0,
      "percentage": 0,
      "status": "missing",
      "missing_fields": ["previous_funding"]
    }
  },
  "recommendations": [
    "Añade más detalles sobre el crecimiento mensual",
    "Especifica mejor el estado actual del producto"
  ],
  "can_search_investors": true,
  "next_questions": [
    "¿Cuál es tu tasa de crecimiento mensual?",
    "¿Qué funcionalidades tiene tu MVP actualmente?"
  ]
}
```

---

## 💬 CHAT ENDPOINTS

### POST /api/v1/chat/welcome-message/{project_id}
Generar mensaje de bienvenida personalizado.

**Response:**
```json
{
  "message": "¡Hola! Soy tu mentor especializado en startups con principios de Y-Combinator. Veo que tienes 'Mi Startup FinTech' con 85% de completitud - ¡excelente! Estás listo para buscar inversores. ¿En qué puedo ayudarte hoy?",
  "message_type": "high_completeness",
  "suggested_actions": [
    "Buscar inversores especializados en FinTech",
    "Revisar tu pitch deck",
    "Prepararte para due diligence"
  ]
}
```

### POST /api/v1/chat/message
Enviar mensaje de chat.

**Request:**
```json
{
  "content": "Busco inversores Serie A para mi startup de FinTech",
  "project_id": "uuid"
}
```

**Response:**
```json
{
  "id": "uuid",
  "project_id": "uuid",
  "role": "assistant",
  "content": "Perfecto, he encontrado 12 inversores especializados en FinTech para Serie A que coinciden con tu perfil:\n\n**TOP MATCHES:**\n1. **Sequoia Capital** - Partner: María González\n   - Especialización: FinTech, B2B SaaS\n   - Inversiones recientes: Stripe, PayPal\n   - LinkedIn: linkedin.com/in/maria-sequoia\n\n2. **Andreessen Horowitz** - Principal: Carlos Tech\n   - Especialización: Payments, B2B\n   - Ticket: $2M-$15M\n   - LinkedIn: linkedin.com/in/carlos-a16z\n\n**NEXT STEPS:**\n¿Quieres que prepare una campaña de outreach personalizada para contactar a estos inversores automáticamente por LinkedIn?",
  "ai_extractions": {
    "judge_decision": {
      "decision": "search_investors",
      "confidence_score": 95.5,
      "completeness_score": 85.0
    },
    "search_results": {
      "total_found": 12,
      "displayed": 2,
      "average_relevance": 87.3
    },
    "upsell_opportunity": {
      "should_upsell": true,
      "target_plan": "outreach",
      "confidence": 82.1
    }
  },
  "gemini_prompt_used": "analyze_and_search_investors",
  "created_at": "2024-01-01T12:00:00Z"
}
```

### GET /api/v1/chat/conversations/{project_id}
Obtener historial de conversación.

**Query Parameters:**
- `limit` (optional): Número de mensajes (default: 50)
- `offset` (optional): Offset para paginación (default: 0)

**Response:**
```json
[
  {
    "id": "uuid",
    "project_id": "uuid",
    "role": "user",
    "content": "Busco inversores Serie A para mi startup de FinTech",
    "created_at": "2024-01-01T11:59:00Z"
  },
  {
    "id": "uuid", 
    "project_id": "uuid",
    "role": "assistant",
    "content": "Perfecto, he encontrado 12 inversores...",
    "ai_extractions": {...},
    "created_at": "2024-01-01T12:00:00Z"
  }
]
```

### GET /api/v1/chat/conversations
Obtener lista de conversaciones (estilo ChatGPT).

**Response:**
```json
{
  "conversations": [
    {
      "project_id": "uuid",
      "project_name": "Mi Startup FinTech",
      "title": "Búsqueda inversores Serie A",
      "last_message": "Perfecto, he encontrado 12 inversores...",
      "message_count": 8,
      "created_at": "2024-01-01T10:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 1
}
```

---

## 🔍 SEARCH ENDPOINTS

### POST /api/v1/search/investors
Buscar inversores (requiere plan Pro+).

**Request:**
```json
{
  "project_id": "uuid",
  "search_type": "hybrid", // "angels", "funds", "hybrid" 
  "stage_filter": ["serie_a", "serie_b"],
  "category_filter": ["fintech", "b2b"],
  "limit": 15
}
```

**Response:**
```json
{
  "results": [
    {
      "id": "uuid",
      "type": "angel", // "angel" | "fund_employee"
      "full_name": "María González",
      "headline": "Partner at Sequoia Capital | FinTech Investor",
      "email": "maria@sequoia.com",
      "linkedin_url": "https://linkedin.com/in/maria-sequoia",
      "profile_pic": "https://...",
      "company_name": "Sequoia Capital",
      "relevance_score": 95.2,
      "categories_match": ["fintech", "payments", "b2b"],
      "stage_match": true,
      "angel_score": 89.5,
      "validation_reasons": "Especialista en FinTech con 15+ inversiones en el sector"
    }
  ],
  "total_found": 42,
  "search_metadata": {
    "query_time_ms": 1250,
    "completeness_score": 85.0,
    "search_quality": "high",
    "credits_used": 1000
  }
}
```

### POST /api/v1/search/companies
Buscar empresas especializadas.

**Request:**
```json
{
  "project_id": "uuid",
  "query": "marketing digital para startups",
  "category": "marketing",
  "limit": 10
}
```

**Response:**
```json
{
  "results": [
    {
      "nombre": "Growth Marketing Agency",
      "descripcion_corta": "Especialistas en growth marketing para startups tech",
      "web_empresa": "https://growthmkt.com",
      "correo": "hello@growthmkt.com",
      "telefono": "+34 600 123 456",
      "sector_categorias": "Digital Marketing, Growth Hacking",
      "ubicacion_general": "Madrid, Spain",
      "relevance_score": 87.3
    }
  ],
  "total_found": 156,
  "search_metadata": {
    "query_time_ms": 850,
    "credits_used": 250
  }
}
```

---

## 🚀 LINKEDIN & OUTREACH ENDPOINTS

### POST /api/v1/linkedin/auth-link
Crear link de autenticación para LinkedIn.

**Request:**
```json
{
  "success_url": "https://app.0bullshit.com/linkedin/success",
  "failure_url": "https://app.0bullshit.com/linkedin/error"
}
```

**Response:**
```json
{
  "auth_url": "https://account.unipile.com/auth/linkedin/xyz123",
  "expires_at": "2024-01-01T14:00:00Z"
}
```

### GET /api/v1/linkedin/accounts
Obtener cuentas de LinkedIn conectadas.

**Response:**
```json
[
  {
    "unipile_account_id": "unipile_123",
    "linkedin_profile": {
      "name": "John Doe",
      "headline": "CEO at My Startup",
      "profile_url": "https://linkedin.com/in/johndoe"
    },
    "status": "active", // "active", "disconnected", "error"
    "connected_at": "2024-01-01T10:00:00Z",
    "last_sync": "2024-01-01T11:30:00Z"
  }
]
```

### POST /api/v1/linkedin/reconnect/{account_id}
Reconectar cuenta desconectada.

**Response:**
```json
{
  "auth_url": "https://account.unipile.com/auth/linkedin/reconnect/xyz123",
  "expires_at": "2024-01-01T14:00:00Z"
}
```

---

## 📧 CAMPAIGN ENDPOINTS

### POST /api/v1/campaigns
Crear campaña de outreach.

**Request:**
```json
{
  "name": "Serie A FinTech Campaign",
  "project_id": "uuid",
  "message_template": "Hola {investor_name}, soy {user_name} fundador de {project_name}...",
  "target_investor_ids": ["uuid1", "uuid2", "uuid3"],
  "linkedin_account_id": "unipile_123"
}
```

**Response:**
```json
{
  "id": "uuid",
  "name": "Serie A FinTech Campaign",
  "project_id": "uuid",
  "status": "draft", // "draft", "active", "paused", "completed"
  "total_targets": 15,
  "sent_count": 0,
  "reply_count": 0,
  "success_rate": 0.0,
  "created_at": "2024-01-01T12:00:00Z",
  "estimated_completion": "2024-01-03T12:00:00Z"
}
```

### GET /api/v1/campaigns
Obtener todas las campañas del usuario.

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Serie A FinTech Campaign",
    "project_id": "uuid",
    "status": "active",
    "total_targets": 15,
    "sent_count": 8,
    "reply_count": 2,
    "success_rate": 25.0,
    "created_at": "2024-01-01T12:00:00Z",
    "launched_at": "2024-01-01T13:00:00Z"
  }
]
```

### GET /api/v1/campaigns/{campaign_id}
Obtener detalles de campaña específica.

**Response:**
```json
{
  "id": "uuid",
  "name": "Serie A FinTech Campaign",
  "project_id": "uuid",
  "message_template": "Hola {investor_name}...",
  "status": "active",
  "targets": [
    {
      "id": "uuid",
      "investor_name": "María González",
      "linkedin_url": "https://linkedin.com/in/maria-sequoia",
      "personalized_message": "Hola María, soy John fundador de Mi Startup FinTech...",
      "status": "sent", // "pending", "sent", "connection_accepted", "replied"
      "sent_at": "2024-01-01T13:30:00Z",
      "replied_at": null
    }
  ],
  "analytics": {
    "total_targets": 15,
    "sent_count": 8,
    "connection_acceptance_rate": 62.5,
    "reply_count": 2,
    "reply_rate": 25.0
  }
}
```

### POST /api/v1/campaigns/{campaign_id}/launch
Lanzar campaña.

**Response:**
```json
{
  "message": "Campaign launched successfully",
  "estimated_completion": "2024-01-03T12:00:00Z",
  "credits_used": 1500
}
```

### POST /api/v1/campaigns/{campaign_id}/pause
Pausar campaña.

**Response:**
```json
{
  "message": "Campaign paused successfully"
}
```

---

## 💳 PAYMENT ENDPOINTS

### POST /api/v1/payments/create-subscription
Crear suscripción.

**Request:**
```json
{
  "plan": "pro", // "pro", "outreach"
  "payment_method_id": "pm_stripe_123"
}
```

**Response:**
```json
{
  "subscription": {
    "id": "sub_stripe_123",
    "status": "active",
    "plan": "pro",
    "current_period_start": "2024-01-01T12:00:00Z",
    "current_period_end": "2024-02-01T12:00:00Z"
  },
  "user": {
    "plan": "pro",
    "credits": 10000,
    "daily_credits": 150
  }
}
```

### POST /api/v1/payments/cancel-subscription
Cancelar suscripción.

**Response:**
```json
{
  "message": "Subscription will be canceled at the end of the current period",
  "cancels_at": "2024-02-01T12:00:00Z"
}
```

### POST /api/v1/payments/buy-credits
Comprar créditos adicionales.

**Request:**
```json
{
  "package": "medium", // "small" (4900), "medium" (19900), "large" (49900)
  "payment_method_id": "pm_stripe_123"
}
```

**Response:**
```json
{
  "purchase": {
    "id": "pi_stripe_123",
    "credits_purchased": 19900,
    "amount_paid": 5900, // cents
    "status": "succeeded"
  },
  "user": {
    "credits": 25400 // updated balance
  }
}
```

### GET /api/v1/payments/billing-history
Obtener historial de facturación.

**Response:**
```json
[
  {
    "id": "pi_stripe_123",
    "type": "subscription", // "subscription", "credits"
    "description": "Plan Pro - January 2024",
    "amount": 2450, // cents
    "status": "paid",
    "created_at": "2024-01-01T12:00:00Z",
    "invoice_url": "https://invoice.stripe.com/..."
  }
]
```

---

## 📊 ANALYTICS ENDPOINTS

### GET /api/v1/analytics/dashboard
Obtener métricas del dashboard.

**Response:**
```json
{
  "user_stats": {
    "total_projects": 3,
    "total_messages": 45,
    "total_searches": 8,
    "total_campaigns": 2
  },
  "credit_usage": {
    "current_balance": 7500,
    "used_this_month": 2500,
    "daily_remaining": 120
  },
  "campaign_performance": {
    "total_sent": 23,
    "total_replies": 6,
    "average_reply_rate": 26.1
  },
  "recent_activity": [
    {
      "type": "search_completed",
      "description": "Found 15 investors for FinTech project",
      "timestamp": "2024-01-01T11:30:00Z"
    }
  ]
}
```

---

## 🔌 WEBSOCKET ENDPOINTS

### WS /ws/chat/{project_id}?token={jwt-token}
WebSocket para actualizaciones en tiempo real del chat.

**Mensajes enviados:**
```json
{
  "type": "search_progress",
  "data": {
    "status": "searching", // "starting", "searching", "processing", "completed", "error"
    "message": "Buscando en base de datos de 50k inversores...",
    "progress_percentage": 45
  }
}
```

**Tipos de mensajes:**
- `search_progress`: Progreso de búsqueda
- `message_typing`: Bot está escribiendo
- `campaign_update`: Actualización de campaña
- `credit_update`: Cambio en créditos

---

## 📧 WEBHOOK ENDPOINTS

### POST /api/v1/webhooks/stripe
Webhook de Stripe para eventos de pago.

### POST /api/v1/webhooks/unipile  
Webhook de Unipile para eventos de LinkedIn.

**Ejemplo de payload:**
```json
{
  "event": "message_received",
  "account_id": "unipile_123",
  "message": {
    "sender_id": "linkedin_investor_123",
    "content": "Interesante propuesta, me gustaría conocer más detalles...",
    "timestamp": "2024-01-01T14:30:00Z"
  }
}
```

---

## ❌ ERROR RESPONSES

### Formato estándar de errores:
```json
{
  "error": {
    "code": "INSUFFICIENT_CREDITS",
    "message": "No tienes suficientes créditos para esta acción",
    "details": {
      "required_credits": 1000,
      "current_credits": 500
    }
  }
}
```

### Códigos de error comunes:
- `400` - Bad Request
- `401` - Unauthorized (token inválido)
- `403` - Forbidden (sin permisos/créditos)
- `404` - Not Found
- `429` - Too Many Requests (rate limit)
- `500` - Internal Server Error

### Códigos de error específicos:
- `INSUFFICIENT_CREDITS` - Sin créditos suficientes
- `PLAN_REQUIRED` - Necesita plan premium
- `COMPLETENESS_TOO_LOW` - Completitud < 50%
- `LINKEDIN_NOT_CONNECTED` - Sin cuenta LinkedIn
- `GEMINI_API_ERROR` - Error en API de Gemini
- `SEARCH_FAILED` - Error en búsqueda

---

## 🚀 RATE LIMITS

```yaml
Free Plan:
  - 10 requests/minute general
  - 5 chat messages/minute
  
Pro Plan:
  - 60 requests/minute general
  - 30 chat messages/minute
  - 5 searches/hour
  
Outreach Plan:
  - 120 requests/minute general
  - Unlimited chat messages
  - 20 searches/hour
  - 50 LinkedIn messages/day
```

---

## 💾 USAGE EXAMPLES

### Flujo completo típico:

```javascript
// 1. Login
const auth = await fetch('/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password123'
  })
});
const { access_token } = await auth.json();

// 2. Create project
const project = await fetch('/api/v1/projects', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'Mi Startup FinTech',
    description: 'Plataforma de pagos para PYMES'
  })
});
const { id: project_id } = await project.json();

// 3. Chat interaction
const message = await fetch('/api/v1/chat/message', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    content: 'Busco inversores Serie A para mi FinTech',
    project_id
  })
});
const chatResponse = await message.json();

// 4. WebSocket connection
const ws = new WebSocket(`ws://localhost:8000/ws/chat/${project_id}?token=${access_token}`);
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Real-time update:', data);
};
```

---

*API Documentation para 0Bullshit Platform - Versión 2.0.0*