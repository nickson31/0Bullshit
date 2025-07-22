# 0Bullshit Backend API Documentation

**Versión:** 2.0.0  
**Base URL:** `https://your-backend-url.com/api/v1`  
**Autenticación:** Bearer Token (JWT)

---

## 📖 Índice

1. [Autenticación](#autenticación)
2. [Gestión de Créditos](#gestión-de-créditos)
3. [Proyectos](#proyectos)
4. [Chat y Conversaciones](#chat-y-conversaciones)
5. [Búsquedas](#búsquedas)
6. [Pagos con Stripe](#pagos-con-stripe)
7. [LinkedIn y Outreach](#linkedin-y-outreach)
8. [Utilidades](#utilidades)

---

## 🔐 Autenticación

### Registrar Usuario
```http
POST /auth/register
```

**Body:**
```json
{
  "email": "usuario@ejemplo.com",
  "password": "contraseña123",
  "first_name": "Juan",
  "last_name": "Pérez"
}
```

**Respuesta (201):**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "uuid",
    "email": "usuario@ejemplo.com",
    "first_name": "Juan",
    "last_name": "Pérez",
    "credits_balance": 200,
    "daily_credits": 50,
    "plan": "free",
    "created_at": "2024-01-01T00:00:00Z",
    "preferred_language": "es"
  }
}
```

### Login
```http
POST /auth/login
```

**Body:**
```json
{
  "email": "usuario@ejemplo.com",
  "password": "contraseña123"
}
```

### Obtener Perfil Actual
```http
GET /auth/me
Authorization: Bearer <token>
```

### Obtener Balance de Créditos
```http
GET /auth/credits
Authorization: Bearer <token>
```

---

## 📋 Proyectos

### Crear Proyecto
```http
POST /projects
Authorization: Bearer <token>
```

**Body:**
```json
{
  "name": "Mi Startup Fintech",
  "description": "Plataforma de pagos para PyMEs"
}
```

### Obtener Todos los Proyectos
```http
GET /projects
Authorization: Bearer <token>
```

### Obtener Proyecto Específico
```http
GET /projects/{project_id}
Authorization: Bearer <token>
```

### Obtener Completitud del Proyecto
```http
GET /projects/{project_id}/completeness
Authorization: Bearer <token>
```

---

## 💬 Chat y Conversaciones

### Generar Mensaje de Bienvenida
```http
POST /chat/welcome-message/{project_id}
Authorization: Bearer <token>
```

### Enviar Mensaje de Chat
```http
POST /chat/message
Authorization: Bearer <token>
```

**Body:**
```json
{
  "content": "Necesito encontrar inversores para mi startup fintech en etapa seed",
  "project_id": "uuid"
}
```

**Respuesta (200):**
```json
{
  "id": "uuid",
  "project_id": "uuid",
  "role": "assistant",
  "content": "Perfecto. Para tu startup fintech en etapa seed, puedo ayudarte a encontrar inversores ángeles y fondos especializados...",
  "ai_extractions": {
    "categories": ["fintech", "payments"],
    "stage": "seed",
    "action_needed": "search_investors",
    "upsell": {
      "message": "Para tu proyecto pre-seed, con el plan PRO puedes buscar inversores ángeles relevantes.",
      "message_type": "upgrade_to_pro",
      "cta_text": "Upgrade a PRO",
      "cta_url": "/upgrade/pro",
      "show_upsell": true
    }
  },
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Obtener Historial de Conversación
```http
GET /chat/conversations/{project_id}?limit=50
Authorization: Bearer <token>
```

### Obtener Lista de Conversaciones (estilo ChatGPT)
```http
GET /chat/conversations
Authorization: Bearer <token>
```

---

## 🔍 Búsquedas

### Buscar Inversores (Ángeles + Fondos)
```http
POST /search/investors
Authorization: Bearer <token>
```

**Body:**
```json
{
  "project_id": "uuid",
  "query": "inversores fintech seed stage España",
  "search_type": "investors"
}
```

**Respuesta (200):**
```json
{
  "results": [
    {
      "type": "angel",
      "data": {
        "linkedin_url": "https://linkedin.com/in/investor",
        "full_name": "María González",
        "headline": "Angel Investor & Fintech Expert",
        "email": "maria@example.com",
        "location": "Madrid, Spain",
        "profile_pic": "https://media.linkedin.com/...",
        "angel_score": 85.0,
        "validation_reasons_es": "Experiencia en fintech y stage seed",
        "categories_match": ["fintech", "payments"],
        "stage_match": true,
        "relevance_score": 0.9
      }
    },
    {
      "type": "fund",
      "data": {
        "fund_data": {
          "name": "Fintech Ventures",
          "linkedin": "https://linkedin.com/company/fintech-ventures",
          "website": "https://fintechventures.com",
          "short_description": "Fondo especializado en fintech seed y Series A"
        },
        "employees": [
          {
            "linkedin_url": "https://linkedin.com/in/partner",
            "full_name": "Carlos Rodríguez",
            "headline": "Partner at Fintech Ventures",
            "job_title": "Investment Partner",
            "combined_score": 8.5
          }
        ]
      }
    }
  ],
  "total_found": 15,
  "search_type": "investors",
  "criteria_used": {
    "categories_keywords": ["fintech", "payments", "seed"],
    "stage_keywords": ["seed"],
    "industry_keywords": ["financial"],
    "general_keywords": ["España", "inversores"]
  },
  "has_more": true
}
```

### Buscar Empresas/Servicios
```http
POST /search/companies
Authorization: Bearer <token>
```

**Body:**
```json
{
  "project_id": "uuid",
  "query": "agencias marketing digital para startups",
  "search_type": "companies"
}
```

---

## 💳 Pagos con Stripe

### Crear Suscripción (Pro/Outreach)
```http
POST /payments/create-subscription
Authorization: Bearer <token>
```

**Body:**
```json
{
  "plan": "pro"
}
```

**Respuesta (200):**
```json
{
  "checkout_url": "https://checkout.stripe.com/pay/cs_test_..."
}
```

### Comprar Créditos
```http
POST /payments/purchase-credits
Authorization: Bearer <token>
```

**Body:**
```json
{
  "package": "medium"
}
```

**Paquetes Disponibles:**
- `small`: 4,900 créditos - $19
- `medium`: 19,900 créditos - $59
- `large`: 49,900 créditos - $149

### Obtener Planes Disponibles
```http
GET /payments/plans
```

---

## 🔗 LinkedIn y Outreach

### Obtener Cuentas de LinkedIn
```http
GET /linkedin/accounts
Authorization: Bearer <token>
```

### Conectar Cuenta de LinkedIn
```http
POST /linkedin/connect
Authorization: Bearer <token>
```

**Body:**
```json
{
  "success_url": "https://yourapp.com/linkedin/success",
  "failure_url": "https://yourapp.com/linkedin/error"
}
```

### Obtener Campañas de Outreach
```http
GET /outreach/campaigns
Authorization: Bearer <token>
```

### Crear Campaña de Outreach
```http
POST /outreach/campaigns
Authorization: Bearer <token>
```

---

## 🛠 Utilidades

### Health Check
```http
GET /health
```

### Feature Flags
```http
GET /features
Authorization: Bearer <token>
```

### WebSocket para Chat en Tiempo Real
```
WSS /ws/chat/{project_id}?token={jwt_token}
```

---

## 💰 Configuración de Costos por Operación

| Operación | Plan Free | Plan Pro | Plan Outreach |
|-----------|-----------|----------|---------------|
| Mensaje de Chat | 10 créditos | 5 créditos | Ilimitado |
| Búsqueda de Inversores | No disponible | 1000 créditos | 1000 créditos |
| Búsqueda de Empresas | No disponible | 250 créditos | 250 créditos |

## 🎯 Sistema de Upsell

El sistema de upsell es automático y contextual. Los mensajes aparecen en la respuesta del chat cuando:

1. **Plan Free → Pro:** Usuario intenta buscar inversores/empresas
2. **Plan Pro → Outreach:** Usuario ha encontrado inversores y necesita contactarlos
3. **Cualquier plan → Créditos:** Usuario se queda sin créditos

Los mensajes son generados por IA y personalizados según el contexto del usuario.

## 📱 Estructura de Base de Datos (Supabase)

### Tabla `users`
- `id` (UUID, PK)
- `email` (text)
- `password_hash` (text)
- `first_name` (text)
- `last_name` (text)
- `credits_balance` (integer)
- `daily_credits` (integer)
- `plan` (text) - "free", "pro", "outreach"
- `plan_expires_at` (timestamp)
- `stripe_subscription_id` (text)
- `preferred_language` (text)
- `created_at` (timestamp)
- `updated_at` (timestamp)
- `is_active` (boolean)

### Tabla `Angel_Investors`
- `linkedinUrl` (text, PK)
- `fullName` (text)
- `headline` (text)
- `email` (text)
- `about` (text)
- `addressWithCountry` (text)
- `profilePic` (text)
- `angel_score` (float)
- `validation_reasons_spanish` (text)
- `validation_reasons_english` (text)
- `categories_general_es` (text[])
- `categories_general_en` (text[])
- `categories_strong_es` (text[])
- `categories_strong_en` (text[])
- `stage_general_es` (text[])
- `stage_general_en` (text[])
- `stage_strong_es` (text[])
- `stage_strong_en` (text[])

### Tabla `Investment_Funds`
- `linkedin/value` (text, PK)
- `name` (text)
- `short_description` (text)
- `contact_email` (text)
- `phone_number` (text)
- `website/value` (text)
- `location_identifiers/0/value` (text)
- `location_identifiers/1/value` (text)
- `location_identifiers/2/value` (text)
- `category_keywords` (text)
- `stage_keywords` (text)

### Tabla `Employee_Funds`
- `linkedinUrl` (text, PK)
- `fullName` (text)
- `headline` (text)
- `about` (text)
- `email` (text)
- `profilePic` (text)
- `addressWithCountry` (text)
- `fund_name` (text)
- `jobTitle` (text)
- `score_combinado` (float)

### Tabla `Companies`
- `linkedin` (text, PK)
- `nombre` (text)
- `descripcion_completa` (text)
- `descripcion_corta` (text)
- `web_empresa` (text)
- `correo` (text)
- `telefono` (text)
- `sector_categorias` (text)
- `ubicacion_general` (text)
- `keywords_generales` (text)
- `keywords_especificas` (text)

---

## 🚀 Variables de Entorno Requeridas

```env
# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key

# AI
GEMINI_API_KEY=your_gemini_api_key

# Authentication
JWT_SECRET_KEY=your_jwt_secret_key_at_least_32_chars

# Payments
STRIPE_API_KEY=sk_test_or_live_your_stripe_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# LinkedIn Integration (Unipile)
UNIPILE_API_KEY=your_unipile_api_key
UNIPILE_DSN=your_unipile_dsn

# Frontend URL
FRONTEND_URL=https://yourapp.com

# Server Config
HOST=0.0.0.0
PORT=8000
DEBUG=False
ENVIRONMENT=production
```

---

## ✅ TODO para el Frontend Developer

### Autenticación
- [ ] Implementar formularios de registro/login
- [ ] Gestionar tokens JWT en localStorage/cookies
- [ ] Manejar renovación automática de tokens
- [ ] Redirigir a login cuando token expire (401)

### Dashboard Principal
- [ ] Mostrar balance de créditos prominente
- [ ] Lista de proyectos con acceso rápido
- [ ] Indicadores de completitud de proyectos
- [ ] Botones de upgrade cuando corresponda

### Chat Interface
- [ ] Interfaz estilo ChatGPT/Claude
- [ ] Mostrar mensaje de bienvenida personalizado
- [ ] WebSocket para actualizaciones en tiempo real
- [ ] Mostrar progreso de búsquedas con mensajes
- [ ] Implementar mensajes de upsell contextuales
- [ ] Soporte para markdown en respuestas

### Búsquedas y Resultados
- [ ] Páginas separadas para resultados de inversores
- [ ] Páginas separadas para resultados de empresas
- [ ] Filtros y paginación de resultados
- [ ] Guardar favoritos de inversores/empresas
- [ ] Exportar resultados a PDF/CSV

### Pagos
- [ ] Página de planes con pricing claro
- [ ] Integración con Stripe Checkout
- [ ] Gestión de suscripciones (cancelar, cambiar plan)
- [ ] Compra de créditos adicionales
- [ ] Historial de pagos

### LinkedIn Integration
- [ ] Flujo de conexión de LinkedIn
- [ ] Dashboard de campañas de outreach
- [ ] Creación y gestión de campañas
- [ ] Métricas de respuesta y engagement

### UX/UI Considerations
- [ ] Loading states para todas las operaciones
- [ ] Error handling robusto con mensajes útiles
- [ ] Responsive design para móviles
- [ ] Notificaciones push para respuestas importantes
- [ ] Tour/onboarding para nuevos usuarios

---

**¡Listo! Con esta documentación completa tienes todo lo necesario para implementar el frontend de 0Bullshit. El backend incluye todas las funcionalidades requeridas: autenticación, búsquedas inteligentes, sistema de upsell con IA, integración con Stripe y LinkedIn, y está optimizado para proporcionar la mejor experiencia de usuario posible.**