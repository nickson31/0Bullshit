# 🔗 API Integration Guide

How to integrate 0BullshitIntelligence microservice with the main 0Bullshit repository.

## 📋 Overview

The 0BullshitIntelligence microservice provides AI-powered chat, search, and intelligence capabilities through clean REST APIs and WebSocket connections. This guide shows how to integrate it with your main application.

## 🔧 Authentication

### Service-to-Service Authentication

All API calls require service authentication using API keys:

```http
Authorization: Bearer YOUR_SERVICE_API_KEY
```

### User Context

Include user context in API calls for personalized responses:

```http
X-User-ID: user-uuid-here
X-User-Plan: free|pro|outreach
X-Project-ID: project-uuid-here
```

## 💬 Chat Integration

### Send Chat Message

**Endpoint:** `POST /api/v1/chat/message`

```javascript
const sendChatMessage = async (message, userId, projectId) => {
  const response = await fetch('http://localhost:8000/api/v1/chat/message', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${SERVICE_API_KEY}`,
      'X-User-ID': userId,
      'X-Project-ID': projectId
    },
    body: JSON.stringify({
      message: message,
      conversation_id: conversationId, // Optional
      include_search: true,
      include_upsell: true,
      include_welcome: true
    })
  });
  
  return await response.json();
};
```

**Response Structure:**
```json
{
  "success": true,
  "data": {
    "response": "AI-generated response text",
    "conversation_id": "uuid",
    "message_id": "uuid",
    "ai_decision": "chat|search_investors|search_companies|welcome|upsell",
    "language_info": {
      "detected_language": "spanish",
      "response_language": "spanish"
    },
    "processing_time_ms": 1250,
    "upsell_opportunity": {
      "should_upsell": true,
      "target_plan": "pro",
      "message": "Upgrade message"
    },
    "search_results": {
      "type": "investors",
      "results": [...],
      "total_found": 15,
      "results_saved_count": 15
    }
  }
}
```

### WebSocket Integration

**Connection:** `ws://localhost:8000/ws/chat/{conversation_id}`

```javascript
class ChatWebSocket {
  constructor(conversationId, apiKey) {
    this.ws = new WebSocket(`ws://localhost:8000/ws/chat/${conversationId}`);
    this.apiKey = apiKey;
    this.setupEventHandlers();
  }
  
  setupEventHandlers() {
    this.ws.onopen = () => {
      console.log('Connected to chat WebSocket');
      this.authenticate();
    };
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };
  }
  
  authenticate() {
    this.send({
      type: 'auth',
      data: { api_key: this.apiKey }
    });
  }
  
  sendMessage(message) {
    this.send({
      type: 'message',
      data: { message }
    });
  }
  
  send(data) {
    this.ws.send(JSON.stringify(data));
  }
  
  handleMessage(data) {
    switch(data.type) {
      case 'message_response':
        this.onMessageResponse(data.data);
        break;
      case 'search_progress':
        this.onSearchProgress(data.data);
        break;
      case 'typing_indicator':
        this.onTypingIndicator(data.data);
        break;
    }
  }
}
```

## 🔍 Search Integration

### Investor Search

**Endpoint:** `POST /api/v1/search/investors`

```javascript
const searchInvestors = async (projectData, userId) => {
  const response = await fetch('http://localhost:8000/api/v1/search/investors', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${SERVICE_API_KEY}`,
      'X-User-ID': userId
    },
    body: JSON.stringify({
      project_id: projectData.id,
      filters: {
        categories: projectData.categories,
        stage: projectData.stage,
        min_angel_score: 40.0,
        max_results: 15
      },
      save_results: true // Always save for outreach
    })
  });
  
  return await response.json();
};
```

### Company Search

**Endpoint:** `POST /api/v1/search/companies`

```javascript
const searchCompanies = async (query, categories, userId) => {
  const response = await fetch('http://localhost:8000/api/v1/search/companies', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${SERVICE_API_KEY}`,
      'X-User-ID': userId
    },
    body: JSON.stringify({
      query: query,
      filters: {
        categories: categories,
        max_results: 10
      },
      save_results: true
    })
  });
  
  return await response.json();
};
```

### Get Saved Search Results

**Endpoint:** `GET /api/v1/search/results/{user_id}`

```javascript
const getSavedSearchResults = async (userId, searchType = null) => {
  const params = new URLSearchParams();
  if (searchType) params.append('search_type', searchType);
  
  const response = await fetch(
    `http://localhost:8000/api/v1/search/results/${userId}?${params}`,
    {
      headers: {
        'Authorization': `Bearer ${SERVICE_API_KEY}`
      }
    }
  );
  
  return await response.json();
};
```

## 🔄 Data Synchronization

### User Data Sync

**Endpoint:** `POST /api/v1/webhooks/user-update`

Send user updates to keep the microservice synchronized:

```javascript
const syncUserData = async (userData) => {
  const response = await fetch('http://localhost:8000/api/v1/webhooks/user-update', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${SERVICE_API_KEY}`
    },
    body: JSON.stringify({
      user_id: userData.id,
      profile_data: {
        email: userData.email,
        plan: userData.plan,
        credits_remaining: userData.credits_remaining,
        onboarding_completed: userData.onboarding_completed
      },
      projects: userData.projects
    })
  });
  
  return await response.json();
};
```

### Project Data Sync

**Endpoint:** `POST /api/v1/webhooks/project-update`

```javascript
const syncProjectData = async (projectData) => {
  const response = await fetch('http://localhost:8000/api/v1/webhooks/project-update', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${SERVICE_API_KEY}`
    },
    body: JSON.stringify({
      project_id: projectData.id,
      user_id: projectData.user_id,
      project_data: projectData
    })
  });
  
  return await response.json();
};
```

## 📊 Analytics Integration

### Get Conversation Analytics

**Endpoint:** `GET /api/v1/analytics/conversations/{user_id}`

```javascript
const getConversationAnalytics = async (userId, timeframe = '7d') => {
  const response = await fetch(
    `http://localhost:8000/api/v1/analytics/conversations/${userId}?timeframe=${timeframe}`,
    {
      headers: {
        'Authorization': `Bearer ${SERVICE_API_KEY}`
      }
    }
  );
  
  return await response.json();
};
```

### Get Search Analytics

**Endpoint:** `GET /api/v1/analytics/searches/{user_id}`

```javascript
const getSearchAnalytics = async (userId, timeframe = '7d') => {
  const response = await fetch(
    `http://localhost:8000/api/v1/analytics/searches/${userId}?timeframe=${timeframe}`,
    {
      headers: {
        'Authorization': `Bearer ${SERVICE_API_KEY}`
      }
    }
  );
  
  return await response.json();
};
```

## 🏥 Health Monitoring

### Service Health Check

```javascript
const checkServiceHealth = async () => {
  try {
    const response = await fetch('http://localhost:8000/health');
    const health = await response.json();
    return health.success;
  } catch (error) {
    console.error('Intelligence service health check failed:', error);
    return false;
  }
};

// Use in your app's health monitoring
setInterval(async () => {
  const isHealthy = await checkServiceHealth();
  if (!isHealthy) {
    // Handle service degradation
    console.warn('Intelligence service is unhealthy');
  }
}, 30000); // Check every 30 seconds
```

## 🛡️ Error Handling

### API Error Response Format

```json
{
  "success": false,
  "message": "Error description",
  "error_code": "ERROR_TYPE",
  "details": {
    "field": "validation error details"
  }
}
```

### Handling Common Errors

```javascript
const handleApiResponse = async (response) => {
  const data = await response.json();
  
  if (!data.success) {
    switch (data.error_code) {
      case 'RATE_LIMIT_EXCEEDED':
        // Handle rate limiting
        console.warn('Rate limit exceeded, backing off');
        await new Promise(resolve => setTimeout(resolve, 5000));
        break;
        
      case 'INSUFFICIENT_CREDITS':
        // Handle credit limit
        console.warn('User needs more credits');
        break;
        
      case 'SERVICE_UNAVAILABLE':
        // Handle service degradation
        console.error('Intelligence service unavailable');
        break;
        
      default:
        console.error('API error:', data.message);
    }
    throw new Error(data.message);
  }
  
  return data;
};
```

## 🔧 Configuration

### Environment Variables for Main App

```env
# Intelligence microservice
INTELLIGENCE_SERVICE_URL=http://localhost:8000
INTELLIGENCE_SERVICE_API_KEY=your-service-api-key

# Feature flags
ENABLE_AI_CHAT=true
ENABLE_SEARCH_INTEGRATION=true
ENABLE_REALTIME_CHAT=true
```

### Service Discovery

```javascript
class IntelligenceService {
  constructor(baseUrl, apiKey) {
    this.baseUrl = baseUrl;
    this.apiKey = apiKey;
    this.isHealthy = true;
    this.startHealthChecking();
  }
  
  async request(endpoint, options = {}) {
    if (!this.isHealthy) {
      throw new Error('Intelligence service is unhealthy');
    }
    
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
        ...options.headers
      }
    });
    
    return handleApiResponse(response);
  }
  
  startHealthChecking() {
    setInterval(async () => {
      this.isHealthy = await checkServiceHealth();
    }, 30000);
  }
}

// Initialize service
const intelligenceService = new IntelligenceService(
  process.env.INTELLIGENCE_SERVICE_URL,
  process.env.INTELLIGENCE_SERVICE_API_KEY
);
```

## 📱 Frontend Integration

### React Hook Example

```jsx
import { useState, useEffect } from 'react';

const useIntelligenceChat = (conversationId) => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [ws, setWs] = useState(null);
  
  useEffect(() => {
    if (conversationId) {
      const websocket = new ChatWebSocket(conversationId, API_KEY);
      websocket.onMessageResponse = (data) => {
        setMessages(prev => [...prev, data]);
        setIsLoading(false);
      };
      setWs(websocket);
      
      return () => websocket.close();
    }
  }, [conversationId]);
  
  const sendMessage = async (message) => {
    setIsLoading(true);
    
    if (ws) {
      ws.sendMessage(message);
    } else {
      // Fallback to REST API
      const response = await intelligenceService.request('/api/v1/chat/message', {
        method: 'POST',
        body: JSON.stringify({ message, conversation_id: conversationId })
      });
      
      setMessages(prev => [...prev, response.data]);
      setIsLoading(false);
    }
  };
  
  return { messages, sendMessage, isLoading };
};
```

## 🚀 Deployment Considerations

### Load Balancing

```nginx
upstream intelligence_service {
    server intelligence:8000;
    # Add more instances for scaling
    # server intelligence-2:8000;
    # server intelligence-3:8000;
}

location /api/v1/intelligence/ {
    proxy_pass http://intelligence_service/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}

location /ws/chat/ {
    proxy_pass http://intelligence_service;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

### Circuit Breaker Pattern

```javascript
class CircuitBreaker {
  constructor(service, threshold = 5, resetTime = 60000) {
    this.service = service;
    this.threshold = threshold;
    this.resetTime = resetTime;
    this.failures = 0;
    this.state = 'CLOSED'; // CLOSED, OPEN, HALF_OPEN
    this.nextAttempt = 0;
  }
  
  async call(method, ...args) {
    if (this.state === 'OPEN') {
      if (Date.now() < this.nextAttempt) {
        throw new Error('Circuit breaker is OPEN');
      }
      this.state = 'HALF_OPEN';
    }
    
    try {
      const result = await this.service[method](...args);
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }
  
  onSuccess() {
    this.failures = 0;
    this.state = 'CLOSED';
  }
  
  onFailure() {
    this.failures++;
    if (this.failures >= this.threshold) {
      this.state = 'OPEN';
      this.nextAttempt = Date.now() + this.resetTime;
    }
  }
}

const intelligenceCircuitBreaker = new CircuitBreaker(intelligenceService);
```

## 📚 Complete Integration Example

```javascript
// main-app/services/IntelligenceService.js
class MainAppIntelligenceIntegration {
  constructor() {
    this.service = new IntelligenceService(
      process.env.INTELLIGENCE_SERVICE_URL,
      process.env.INTELLIGENCE_SERVICE_API_KEY
    );
    this.circuitBreaker = new CircuitBreaker(this.service);
  }
  
  async handleUserMessage(userId, projectId, message) {
    try {
      // Send to intelligence service
      const response = await this.circuitBreaker.call(
        'sendChatMessage', 
        message, 
        userId, 
        projectId
      );
      
      // Process response
      if (response.data.search_results) {
        await this.handleSearchResults(
          userId, 
          response.data.search_results
        );
      }
      
      if (response.data.upsell_opportunity?.should_upsell) {
        await this.handleUpsellOpportunity(
          userId, 
          response.data.upsell_opportunity
        );
      }
      
      return response.data;
      
    } catch (error) {
      console.error('Intelligence service error:', error);
      
      // Fallback to basic response
      return {
        response: "I'm having trouble processing your request right now. Please try again later.",
        ai_decision: "error",
        processing_time_ms: 0
      };
    }
  }
  
  async handleSearchResults(userId, searchResults) {
    // Store search results in main database for outreach campaigns
    await this.saveSearchResultsForOutreach(userId, searchResults);
    
    // Trigger any necessary notifications
    if (searchResults.results_saved_count > 0) {
      await this.notifyUserOfNewResults(userId, searchResults);
    }
  }
  
  async syncUserData(userId) {
    // Get user data from main database
    const userData = await this.getUserData(userId);
    
    // Sync with intelligence service
    await this.service.syncUserData(userData);
  }
}
```

---

**🎯 This integration guide provides everything needed to connect the 0BullshitIntelligence microservice with your main application while maintaining clean separation and robust error handling.**