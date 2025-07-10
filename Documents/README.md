# 0Bullshit Chat Backend 🚀

Sistema de chat con IA especializado en startups que conecta founders con inversores, empresas y proporciona mentoría estilo Y-Combinator.

## 🎯 Características Principales

- **Chat Inteligente**: IA que analiza intención del usuario y toma decisiones contextuales
- **Sistema Juez/Policía**: Analiza cada mensaje y decide la mejor acción (búsqueda, mentoría, preguntas)
- **Bot Bibliotecario**: Actualiza información del proyecto en segundo plano
- **Búsqueda de Inversores**: Conecta con angels y fondos especializados
- **Búsqueda de Empresas**: Encuentra servicios especializados para startups
- **Mentoría Y-Combinator**: Consejos basados en principios de Y-Combinator
- **WebSockets**: Chat en tiempo real con notificaciones de progreso
- **Anti-Spam**: Detección inteligente de contenido no constructivo

## 🏗️ Arquitectura del Sistema

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │────│   FastAPI       │────│   Supabase      │
│   (React/Next)  │    │   Backend       │    │   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   Gemini 2.0    │
                    │   Flash API     │
                    └─────────────────┘
```

### 🤖 Sistema de Agentes IA

1. **Juez/Policía**: Analiza intención y decide acción
2. **Mentor Y-Combinator**: Proporciona consejos especializados
3. **Bibliotecario**: Extrae y actualiza información del proyecto
4. **Generador de Bienvenida**: Crea mensajes personalizados

## 🚀 Instalación y Configuración

### Prerrequisitos

- Python 3.8+
- Cuenta en Supabase
- API Key de Google Gemini
- (Opcional) Cuenta en Unipile para outreach
- (Opcional) Cuenta en Stripe para pagos

### 1. Clonar el repositorio

```bash
git clone <repository-url>
cd obullshit-backend
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

Crear archivo `.env` basado en el template:

```bash
cp .env.example .env
```

Configurar las siguientes variables en `.env`:

```env
# Configuración básica
PROJECT_NAME=0Bullshit Backend
API_V1_STR=/api/v1
DEBUG=True
ENVIRONMENT=development
HOST=0.0.0.0
PORT=8000

# Base de datos Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key_here

# APIs externas
GEMINI_API_KEY=your_gemini_api_key_here
UNIPILE_API_KEY=your_unipile_api_key_here
UNIPILE_DSN=your_unipile_dsn_here
STRIPE_API_KEY=your_stripe_secret_key_here
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret_here

# Seguridad
JWT_SECRET_KEY=your_super_secret_jwt_key_here_change_this
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
```

### 4. Configurar base de datos

Asegurate de que tu Supabase tenga las siguientes tablas creadas:

- `users` - Usuarios del sistema
- `projects` - Proyectos de startups
- `conversations` - Historial de chat
- `investors` - Base de datos de inversores
- `COMPANIES` - Base de datos de empresas
- `outreach_campaigns` - Campañas de outreach
- `outreach_targets` - Targets de outreach

(El esquema completo está en el archivo CSV proporcionado)

### 5. Ejecutar la aplicación

```bash
python main.py
```

La API estará disponible en `http://localhost:8000`

## 📚 Documentación API

### Endpoints Principales

#### 🏠 Health Check
```http
GET /health
```

#### 👤 Autenticación
Todos los endpoints (excepto health) requieren autenticación JWT:
```http
Authorization: Bearer <jwt-token>
```

#### 📋 Proyectos
```http
POST /api/v1/projects                    # Crear proyecto
GET /api/v1/projects                     # Listar proyectos
GET /api/v1/projects/{project_id}        # Obtener proyecto
GET /api/v1/projects/{project_id}/completeness  # Score de completitud
```

#### 💬 Chat
```http
POST /api/v1/chat/welcome-message/{project_id}  # Mensaje de bienvenida
POST /api/v1/chat/message                        # Enviar mensaje
GET /api/v1/chat/conversations/{project_id}     # Historial
GET /api/v1/chat/conversations                  # Lista de chats
```

#### 🔌 WebSocket
```
WS /ws/chat/{project_id}?token=<jwt-token>
```

### Estructura de Mensajes

#### Enviar Mensaje
```json
{
  "content": "Busco inversores para mi startup de fintech",
  "project_id": "uuid"
}
```

#### Respuesta del Chat
```json
{
  "id": "uuid",
  "project_id": "uuid", 
  "role": "assistant",
  "content": "Perfecto, encontré 5 inversores especializados...",
  "ai_extractions": {
    "judge_decision": {...},
    "search_results": {...}
  },
  "created_at": "2024-01-01T12:00:00Z"
}
```

## 🧠 Sistema de IA

### Flujo de Procesamiento

1. **Usuario envía mensaje** → Guardar en BD
2. **Juez analiza intención** → Gemini 2.0 Flash
3. **Decisión del juez**:
   - `search_investors` → Buscar inversores
   - `search_companies` → Buscar empresas  
   - `mentoring` → Dar consejos Y-Combinator
   - `ask_questions` → Solicitar más información
   - `anti_spam` → Respuesta anti-bullshit
4. **Ejecutar acción** → WebSocket progreso
5. **Generar respuesta** → Gemini + context
6. **Bot Bibliotecario** → Actualizar proyecto (background)

### Score de Completitud

El sistema calcula un score basado en:

- **Categories** (25%): Sector/industria de la startup
- **Stage** (25%): Etapa del proyecto (idea, MVP, seed, etc.)
- **Metrics** (15%): ARR, MRR, usuarios, etc.
- **Team Info** (10%): Información del equipo
- **Problem Solved** (10%): Problema que resuelve
- **Product Status** (10%): Estado del producto
- **Previous Funding** (5%): Financiación anterior

### Principios Y-Combinator

El mentor IA está entrenado con principios de Y-Combinator:

- Enfocarse en EJECUTAR vs planear
- Talk to users
- Métricas reales (ARR, MRR, growth)
- Problem-solution fit
- Equipo es crítico
- Concisión en comunicación
- Tracción > Ideas
- Product-market fit

## 🔧 Configuración Avanzada

### Variables de Configuración

Ver `config/settings.py` para todas las opciones:

```python
# Gemini settings
GEMINI_TEMPERATURE: float = 0.7
GEMINI_MAX_OUTPUT_TOKENS: int = 3000

# Chat limits  
MAX_MESSAGE_LENGTH: int = 10000
MAX_CONVERSATION_HISTORY: int = 50

# Feature flags
ENABLE_LIBRARIAN_BOT: bool = True
ENABLE_ANTI_SPAM: bool = True
ENABLE_WEBSOCKETS: bool = True
```

### Feature Flags

- `ENABLE_LIBRARIAN_BOT`: Bot que actualiza info en background
- `ENABLE_WELCOME_MESSAGES`: Mensajes de bienvenida automáticos
- `ENABLE_ANTI_SPAM`: Detección de spam/bullshit
- `ENABLE_SEARCH_CACHING`: Cache de resultados de búsqueda
- `ENABLE_WEBSOCKETS`: Soporte WebSocket
- `ENABLE_RATE_LIMITING`: Límites de requests

## 🧪 Testing

### Endpoints de Debug

```http
POST /api/v1/admin/force-librarian-analysis/{project_id}
GET /api/v1/admin/judge-analysis/{project_id}?message=texto
```

### Testing Manual

1. **Crear proyecto**:
```bash
curl -X POST "http://localhost:8000/api/v1/projects" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Mi Startup", "description": "Fintech revolucionaria"}'
```

2. **Enviar mensaje**:
```bash
curl -X POST "http://localhost:8000/api/v1/chat/message" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"content": "Busco inversores Serie A", "project_id": "uuid"}'
```

3. **WebSocket test**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat/project-id?token=jwt-token');
ws.onmessage = (event) => console.log(JSON.parse(event.data));
```

## 📊 Monitoreo y Logs

### Logging

Los logs se configuran en `config/settings.py`:

```python
LOG_LEVEL: str = "INFO"
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### Métricas

El sistema trackea:
- Decisiones del juez/policía
- Tiempo de respuesta de Gemini
- Score de completitud por usuario
- Errores de procesamiento

## 🚀 Deployment

### Render.com

1. Conectar repositorio a Render
2. Configurar variables de entorno
3. Comando de build: `pip install -r requirements.txt`
4. Comando de start: `python main.py`

### Docker (opcional)

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "main.py"]
```

## 🔮 Roadmap Futuro

- [ ] **Outreach Automatizado**: Integración completa con Unipile
- [ ] **Analytics Dashboard**: Métricas de conversaciones y conversiones  
- [ ] **Más Agentes IA**: Legal, Marketing, Technical advisors
- [ ] **Integración con CRM**: Sincronización con HubSpot/Salesforce
- [ ] **Mobile App**: App nativa para iOS/Android
- [ ] **API Pública**: Webhook para integraciones externas

## 🤝 Contribución

1. Fork el repositorio
2. Crear branch: `git checkout -b feature/nueva-feature`
3. Commit: `git commit -m 'Add nueva feature'`
4. Push: `git push origin feature/nueva-feature`
5. Crear Pull Request

## 📝 Licencia

Este proyecto es privado y propietario de 0Bullshit.

## 🆘 Soporte

Para soporte técnico:
- **Email**: dev@0bullshit.com
- **Slack**: #dev-backend
- **Documentation**: Wiki interno

---

**Hecho con ❤️ por el equipo 0Bullshit**
