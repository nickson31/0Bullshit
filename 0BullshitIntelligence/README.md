# 🧠 0BullshitIntelligence

**Independent AI Chat Microservice for 0Bullshit Platform**

## 🎯 Mission

0BullshitIntelligence is a standalone microservice that extracts and enhances the AI chat system from the main 0Bullshit repository. This service handles all AI-driven conversations, intelligent user interactions, and search operations while providing clean APIs for consumption by the main platform.

## 🏗️ Architecture Overview

### Core AI Systems
- **🎯 Judge System** - User intent analysis and action routing using Gemini AI
- **🌍 Language Detection** - Automatic Spanish/English detection with multi-language support
- **🚫 Anti-Spam Detection** - Content filtering and abuse prevention
- **💰 Upselling Intelligence** - Contextual upgrade recommendations
- **👋 Welcome & Onboarding** - New user experience flows
- **📚 Librarian Bot** - Background data extraction and enrichment
- **🤖 Y-Combinator Mentor** - Maintains the mentor personality and prompts

### Search Engines
- **👨‍💼 Investor Search** - Full porting with scoring algorithms and relevance matching
- **🏢 Company Search** - B2B service discovery functionality
- **💾 Search Results Storage** - All results saved to database for CTO outreach campaigns

### API Layer
- **🔄 Real-time Chat API** - Primary endpoint for all user interactions
- **🔍 Search APIs** - Investor and company search endpoints
- **👤 User Context APIs** - User synchronization and context management
- **🌐 WebSocket Support** - Real-time communication capabilities
- **📡 Webhook Receivers** - Data updates from main repository

## 🚀 Key Features

### Independence & Scalability
- ✅ Runs completely independently from main repository
- ✅ Communicates via clean APIs and webhooks
- ✅ Separate deployment and scaling capabilities
- ✅ Own Supabase database project with synchronized shared tables

### AI Intelligence Preservation & Enhancement
- ✅ All existing AI systems ported and enhanced
- ✅ Gemini AI integration maintained
- ✅ Y-Combinator mentor personality preserved
- ✅ Multi-language support (Spanish/English with expansion capability)

### Team Collaboration & Testing
- ✅ Web-based testing interface for entire team
- ✅ Chat simulation with different user types and scenarios
- ✅ AI decision transparency and reasoning visibility
- ✅ Performance metrics and conversation analytics
- ✅ Export functionality for analysis and feedback

### Data Management
- ✅ Real-time synchronization of shared tables between Supabase instances
- ✅ Comprehensive search result storage for outreach campaigns
- ✅ User context and project data synchronization

## 🔧 Technology Stack

- **Backend**: FastAPI (Python 3.11+)
- **AI**: Google Gemini 2.0 Flash
- **Database**: Supabase (PostgreSQL)
- **Authentication**: JWT-based service-to-service communication
- **WebSockets**: FastAPI WebSocket support
- **Deployment**: Docker + Docker Compose
- **Testing**: Pytest with async support

## 📁 Project Structure

```
0BullshitIntelligence/
├── app/
│   ├── core/                   # Core configuration and settings
│   ├── ai_systems/            # All AI intelligence components
│   │   ├── judge/             # Intent analysis and routing
│   │   ├── language/          # Language detection
│   │   ├── anti_spam/         # Spam detection
│   │   ├── upselling/         # Upselling intelligence
│   │   ├── welcome/           # Welcome and onboarding
│   │   ├── librarian/         # Data extraction bot
│   │   └── mentor/            # Y-Combinator mentor
│   ├── search/                # Search engines
│   │   ├── investors/         # Investor search system
│   │   └── companies/         # Company search system
│   ├── api/                   # API endpoints and routers
│   ├── database/              # Database operations and sync
│   ├── models/                # Pydantic models and schemas
│   └── services/              # Business logic services
├── tests/                     # Comprehensive test suite
├── testing_interface/         # Web-based testing UI
├── docker/                    # Docker configuration
├── docs/                      # Documentation
└── scripts/                   # Utility scripts
```

## 🏃‍♂️ Quick Start

```bash
# 1. Clone and setup
git clone [repository-url]
cd 0BullshitIntelligence

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your configuration

# 4. Run the service
python main.py

# 5. Access testing interface
open http://localhost:8000/test-interface
```

## 📊 Success Metrics

- **✅ Functional Parity**: All existing chat functionality works identically or better
- **✅ Team Adoption**: Testing interface enables productive collaboration
- **✅ Integration Ready**: Main repository can consume this service seamlessly
- **✅ Data Flow**: Search results properly captured for outreach campaigns
- **✅ Performance**: Response times meet or exceed current system
- **✅ Maintainability**: Well-structured and documented code

## 🔗 Integration with Main Repository

This microservice is designed to be consumed by the main 0Bullshit repository through:

- **Chat API**: `/api/v1/chat` - Primary chat endpoint
- **Search APIs**: `/api/v1/search/investors` and `/api/v1/search/companies`
- **WebSocket**: `/ws/chat` - Real-time communication
- **Webhooks**: `/api/v1/webhooks/*` - Receive updates from main repository

## 📚 Documentation

- [API Documentation](docs/api.md)
- [AI Systems Guide](docs/ai-systems.md)
- [Database Schema](docs/database.md)
- [Testing Guide](docs/testing.md)
- [Deployment Guide](docs/deployment.md)

---

**Built with ❤️ by the 0Bullshit Team**