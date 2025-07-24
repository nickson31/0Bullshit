# 🚀 **FRONTEND INTEGRATION GUIDE**
### *Complete API integration guide for 0Bullshit frontend development*

---

## 📋 **OVERVIEW**

This document contains all the information you need to integrate the frontend with the 0Bullshit backend API. The backend is built with FastAPI and provides a comprehensive REST API with real-time WebSocket features.

**Backend URL**: `https://zerobs-back-final.onrender.com` 
**API Version**: `v1`
**All endpoints are prefixed with**: `/api`

---

## 🔐 **AUTHENTICATION**

### **Authentication Flow**
The API uses JWT (JSON Web Tokens) for authentication with access and refresh token system.

#### **1. User Registration**
```typescript
// POST /api/register
const registerUser = async (userData: {
  email: string;
  password: string;
  name: string;
}) => {
  const response = await fetch('/api/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(userData),
  });
  
  return await response.json();
};

// Response format:
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "User Name",
    "plan": "free",
    "credits": 200,
    "daily_credits_remaining": 200,
    "onboarding_completed": false,
    "created_at": "2025-01-01T00:00:00Z"
  },
  "access_token": "jwt_access_token",
  "refresh_token": "jwt_refresh_token",
  "expires_in": 86400
}
```

#### **2. User Login**
```typescript
// POST /api/login
const loginUser = async (credentials: {
  email: string;
  password: string;
}) => {
  const response = await fetch('/api/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(credentials),
  });
  
  return await response.json();
};

// Same response format as registration
```

#### **3. Token Refresh**
```typescript
// POST /api/refresh
const refreshToken = async (refreshToken: string) => {
  const response = await fetch('/api/refresh', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      refresh_token: refreshToken
    }),
  });
  
  return await response.json();
};

// Response format:
{
  "access_token": "new_jwt_access_token",
  "refresh_token": "new_jwt_refresh_token",
  "expires_in": 86400
}
```

#### **4. Using Authentication Headers**
```typescript
// Include this header in all authenticated requests
const makeAuthenticatedRequest = async (url: string, options: RequestInit = {}) => {
  const token = localStorage.getItem('access_token');
  
  return fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });
};
```

#### **5. Get Current User Info**
```typescript
// GET /api/me
const getCurrentUser = async () => {
  const response = await makeAuthenticatedRequest('/api/me');
  return await response.json();
};

// Response format: Same as user object in registration/login
```

---

## 👤 **USER MANAGEMENT**

### **Password Reset**
```typescript
// POST /api/request-password-reset
const requestPasswordReset = async (email: string) => {
  const response = await fetch('/api/request-password-reset', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email }),
  });
  
  return await response.json();
};

// POST /api/reset-password
const resetPassword = async (token: string, newPassword: string) => {
  const response = await fetch('/api/reset-password', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      token,
      new_password: newPassword
    }),
  });
  
  return await response.json();
};
```

### **Change Password**
```typescript
// POST /api/change-password
const changePassword = async (currentPassword: string, newPassword: string) => {
  const response = await makeAuthenticatedRequest('/api/change-password', {
    method: 'POST',
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword
    }),
  });
  
  return await response.json();
};
```

---

## 📁 **PROJECT MANAGEMENT**

### **Project Data Structure**
```typescript
interface Project {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  stage: 'idea' | 'prototype' | 'mvp' | 'early_revenue' | 'growth' | 'scale';
  category: 'fintech' | 'healthtech' | 'edtech' | 'proptech' | 'retail' | 'saas' | 'marketplace' | 'social' | 'gaming' | 'ai' | 'other';
  business_model?: string;
  revenue_model?: string;
  target_market?: string;
  funding_amount?: string;
  current_revenue?: string;
  projected_revenue?: string;
  team_size?: number;
  key_metrics?: object;
  achievements?: string;
  problem_solving?: string;
  completeness_score?: number;
  created_at: string;
  updated_at?: string;
}
```

### **Project Endpoints**
```typescript
// GET /api/projects - Get all user projects
const getProjects = async () => {
  const response = await makeAuthenticatedRequest('/api/projects');
  return await response.json();
};

// POST /api/projects - Create new project
const createProject = async (projectData: Partial<Project>) => {
  const response = await makeAuthenticatedRequest('/api/projects', {
    method: 'POST',
    body: JSON.stringify(projectData),
  });
  
  return await response.json();
};

// GET /api/projects/{project_id} - Get specific project
const getProject = async (projectId: string) => {
  const response = await makeAuthenticatedRequest(`/api/projects/${projectId}`);
  return await response.json();
};

// PUT /api/projects/{project_id} - Update project
const updateProject = async (projectId: string, updates: Partial<Project>) => {
  const response = await makeAuthenticatedRequest(`/api/projects/${projectId}`, {
    method: 'PUT',
    body: JSON.stringify(updates),
  });
  
  return await response.json();
};

// DELETE /api/projects/{project_id} - Delete project
const deleteProject = async (projectId: string) => {
  const response = await makeAuthenticatedRequest(`/api/projects/${projectId}`, {
    method: 'DELETE',
  });
  
  return await response.json();
};
```

---

## 💬 **CHAT SYSTEM**

### **Chat Data Structures**
```typescript
interface Conversation {
  id: string;
  user_id: string;
  project_id?: string;
  title?: string;
  message_count: number;
  last_message_at?: string;
  created_at: string;
  updated_at?: string;
}

interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  ai_extractions?: object;
  gemini_prompt_used?: string;
  credits_used: number;
  created_at: string;
}
```

### **Chat Endpoints**
```typescript
// GET /api/conversations - Get all user conversations
const getConversations = async () => {
  const response = await makeAuthenticatedRequest('/api/conversations');
  return await response.json();
};

// POST /api/conversations - Create new conversation
const createConversation = async (data: {
  title?: string;
  project_id?: string;
}) => {
  const response = await makeAuthenticatedRequest('/api/conversations', {
    method: 'POST',
    body: JSON.stringify(data),
  });
  
  return await response.json();
};

// GET /api/conversations/{conversation_id}/messages - Get conversation messages
const getMessages = async (conversationId: string) => {
  const response = await makeAuthenticatedRequest(`/api/conversations/${conversationId}/messages`);
  return await response.json();
};

// POST /api/chat - Send message to AI
const sendMessage = async (message: string, conversationId: string, projectId?: string) => {
  const response = await makeAuthenticatedRequest('/api/chat', {
    method: 'POST',
    body: JSON.stringify({
      content: message,
      conversation_id: conversationId,
      project_id: projectId,
    }),
  });
  
  return await response.json();
};

// Enhanced Chat Response Format (Updated January 2025)
interface ChatResponse {
  response: string;
  conversation_id: string;
  ai_extractions?: object;
  upsell_opportunity?: object;
  credits_used: number;
  action_taken: string;
  language_detected: 'spanish' | 'english' | 'other'; // NEW: Language detection
  anti_spam_triggered: boolean; // NEW: Anti-spam detection
  spam_score?: number; // NEW: Spam confidence score (if applicable)
}
```

### **✅ New Chat Features (January 2025)**

#### **1. Automatic Language Detection**
The chat system now automatically detects the user's language and responds accordingly:

```typescript
// Language detection is automatic - no action needed from frontend
// The AI will respond in the detected language:
// - Spanish input → Spanish response
// - English input → English response  
// - Other languages → English response (default)

// Example response with language detection:
{
  "response": "Perfecto, he encontrado varios inversores...", // Spanish response
  "conversation_id": "uuid",
  "language_detected": "spanish",
  "anti_spam_triggered": false,
  "credits_used": 10
}
```

#### **2. Intelligent Anti-Spam System**
The system detects spam/bullshit and responds with a professional but firm tone:

```typescript
// Anti-spam triggers automatically for:
// - Random/nonsensical content
// - Offensive or inappropriate messages
// - Attempts to "hack" or break the AI
// - Questions completely unrelated to startups/business

// Example anti-spam response:
{
  "response": "I'm designed to help serious entrepreneurs with fundraising. Please ask legitimate business questions.",
  "conversation_id": "uuid", 
  "anti_spam_triggered": true,
  "spam_score": 85,
  "credits_used": 0 // No credits charged for spam
}
```

#### **3. Enhanced Error Handling**
```typescript
// Handle new response fields in your chat component:
const handleChatResponse = (response: ChatResponse) => {
  // Check for anti-spam
  if (response.anti_spam_triggered) {
    // Show warning UI or different styling for anti-spam responses
    showAntiSpamWarning(response.spam_score);
  }
  
  // Handle language detection
  if (response.language_detected !== 'english') {
    // Update UI language preferences or show language indicator
    updateLanguageIndicator(response.language_detected);
  }
  
  // Display the message normally
  displayMessage(response.response);
};
```

---

## 🔍 **INVESTOR SEARCH**

### **Search Data Structures**
```typescript
interface Investor {
  id: string;
  name: string;
  linkedin_url?: string;
  email?: string;
  company?: string;
  title?: string;
  bio?: string;
  location?: string;
  investment_focus?: string;
  stage_preference?: string;
  check_size_min?: number;
  check_size_max?: number;
  portfolio_companies?: string[];
  categories?: string[];
  relevance_score?: number;
}

interface SearchRequest {
  project_id?: string;
  categories?: string[];
  stage?: string;
  location?: string;
  check_size_min?: number;
  check_size_max?: number;
  limit?: number; // Default: 15, Max: 50
}

interface SearchResults {
  results: Investor[];
  total_found: number;
  average_relevance: number;
  credits_used: number;
  query_params: object;
}
```

### **Search Endpoints**
```typescript
// POST /api/search/investors - Search for investors
const searchInvestors = async (searchParams: SearchRequest) => {
  const response = await makeAuthenticatedRequest('/api/search/investors', {
    method: 'POST',
    body: JSON.stringify(searchParams),
  });
  
  return await response.json() as SearchResults;
};

// GET /api/search/results - Get previous search results
const getSearchResults = async (page: number = 1, limit: number = 20) => {
  const response = await makeAuthenticatedRequest(`/api/search/results?page=${page}&limit=${limit}`);
  return await response.json();
};
```

---

## 💳 **PAYMENT SYSTEM**

### **Payment Data Structures**
```typescript
interface Subscription {
  id: string;
  user_id: string;
  stripe_subscription_id: string;
  plan: 'pro' | 'outreach';
  status: 'active' | 'canceled' | 'past_due' | 'unpaid';
  current_period_start: string;
  current_period_end: string;
  cancel_at_period_end: boolean;
  created_at: string;
}

interface CreditPurchase {
  id: string;
  user_id: string;
  credits_purchased: number;
  amount_usd: number;
  status: 'pending' | 'completed' | 'failed';
  stripe_payment_intent_id: string;
  created_at: string;
}
```

### **Payment Endpoints**
```typescript
// POST /api/payments/create-subscription - Create subscription
const createSubscription = async (plan: 'pro' | 'outreach', paymentMethodId: string) => {
  const response = await makeAuthenticatedRequest('/api/payments/create-subscription', {
    method: 'POST',
    body: JSON.stringify({
      plan,
      payment_method_id: paymentMethodId,
    }),
  });
  
  return await response.json();
};

// POST /api/payments/purchase-credits - Buy credits
const purchaseCredits = async (credits: number, paymentMethodId: string) => {
  const response = await makeAuthenticatedRequest('/api/payments/purchase-credits', {
    method: 'POST',
    body: JSON.stringify({
      credits,
      payment_method_id: paymentMethodId,
    }),
  });
  
  return await response.json();
};

// GET /api/payments/subscription - Get current subscription
const getSubscription = async () => {
  const response = await makeAuthenticatedRequest('/api/payments/subscription');
  return await response.json();
};

// POST /api/payments/cancel-subscription - Cancel subscription
const cancelSubscription = async () => {
  const response = await makeAuthenticatedRequest('/api/payments/cancel-subscription', {
    method: 'POST',
  });
  
  return await response.json();
};
```

### **Stripe Integration (Frontend)**
```typescript
// Install: npm install @stripe/stripe-js
import { loadStripe } from '@stripe/stripe-js';

const stripePromise = loadStripe('pk_test_...'); // Your Stripe publishable key

// Create payment method and subscribe
const handleSubscription = async (plan: string) => {
  const stripe = await stripePromise;
  
  // Create payment method
  const { error, paymentMethod } = await stripe!.createPaymentMethod({
    type: 'card',
    card: cardElement, // Stripe card element
  });
  
  if (error) {
    console.error('Payment method creation failed:', error);
    return;
  }
  
  // Create subscription
  const result = await createSubscription(plan, paymentMethod.id);
  
  if (result.requires_action) {
    // Handle 3D Secure authentication
    const { error: confirmError } = await stripe!.confirmCardPayment(
      result.client_secret
    );
    
    if (confirmError) {
      console.error('Payment confirmation failed:', confirmError);
    } else {
      console.log('Subscription successful!');
    }
  }
};
```

---

## 🏢 **COMPANIES SEARCH**

### **Company Data Structure**
```typescript
interface Company {
  id: string;
  nombre: string;
  descripcion_corta?: string;
  web_empresa?: string;
  sector_categorias?: string;
  service_category?: string;
  startup_relevance_score?: string;
  correo?: string;
  telefono?: string;
  ubicacion_general?: string;
  keywords_generales?: string;
  keywords_especificas?: string;
  created_at: string;
}

interface CompanySearchRequest {
  problem_context: string;
  categories?: string[];
  limit?: number; // Default: 10, Max: 50
}

interface CompanySearchResults {
  results: Company[];
  total_found: number;
  credits_used: number;
  query_params: object;
}
```

### **Companies Search Endpoints**
```typescript
// POST /api/search/companies - Search for B2B service companies
const searchCompanies = async (searchParams: CompanySearchRequest) => {
  const response = await makeAuthenticatedRequest('/api/search/companies', {
    method: 'POST',
    body: JSON.stringify(searchParams),
  });
  
  return await response.json() as CompanySearchResults;
};

// Example usage:
const searchForMarketingCompanies = async () => {
  const results = await searchCompanies({
    problem_context: "Need help with digital marketing and social media management for startup",
    categories: ["marketing", "digital marketing", "social media"],
    limit: 20
  });
  
  console.log(`Found ${results.total_found} companies`);
  results.results.forEach(company => {
    console.log(`${company.nombre} - ${company.descripcion_corta}`);
  });
};
```

### **Integration with Chat System**
The companies search is also integrated into the chat system. When users ask for help with specific business services, the AI will automatically search for relevant companies and include them in the chat response.

```typescript
// Companies search is triggered automatically by the AI when:
// - User asks for business services (legal, marketing, development, etc.)
// - AI detects need for external service providers
// - User explicitly requests company recommendations

// Example chat messages that trigger companies search:
// "I need help with legal services for my startup"
// "Can you recommend marketing agencies?"
// "Where can I find developers for my project?"
```

---

## 📊 **ANALYTICS**

### **Analytics Endpoints**
```typescript
// GET /api/analytics/user - Get user analytics
const getUserAnalytics = async () => {
  const response = await makeAuthenticatedRequest('/api/analytics/user');
  return await response.json();
};

// Response format:
{
  "total_credits_used": 1250,
  "total_searches": 45,
  "total_messages_generated": 123,
  "total_campaigns": 3,
  "average_response_rate": 0.23,
  "most_active_day": "monday",
  "last_30_days_activity": {
    "2025-01-01": 15,
    "2025-01-02": 8,
    // ... more days
  }
}

// GET /api/analytics/platform - Get platform analytics (admin only)
const getPlatformAnalytics = async () => {
  const response = await makeAuthenticatedRequest('/api/analytics/platform');
  return await response.json();
};
```

---

## 🔗 **LINKEDIN AUTOMATION**

### **LinkedIn Data Structures**
```typescript
interface LinkedInAccount {
  id: string;
  user_id: string;
  unipile_account_id: string;
  email: string;
  status: 'active' | 'disconnected' | 'error';
  last_sync?: string;
  created_at: string;
}

interface Campaign {
  id: string;
  user_id: string;
  project_id?: string;
  linkedin_account_id: string;
  name: string;
  status: 'draft' | 'active' | 'paused' | 'completed';
  sequence_type: 'standard' | 'aggressive' | 'conservative';
  target_count: number;
  sent_count: number;
  response_count: number;
  connection_count: number;
  created_at: string;
  updated_at?: string;
}
```

### **LinkedIn Endpoints**
```typescript
// POST /api/linkedin/connect - Connect LinkedIn account
const connectLinkedIn = async (email: string, password: string) => {
  const response = await makeAuthenticatedRequest('/api/linkedin/connect', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  
  return await response.json();
};

// GET /api/linkedin/accounts - Get connected accounts
const getLinkedInAccounts = async () => {
  const response = await makeAuthenticatedRequest('/api/linkedin/accounts');
  return await response.json();
};

// POST /api/campaigns - Create outreach campaign
const createCampaign = async (campaignData: {
  name: string;
  project_id?: string;
  linkedin_account_id: string;
  sequence_type?: string;
  target_investors: string[];
}) => {
  const response = await makeAuthenticatedRequest('/api/campaigns', {
    method: 'POST',
    body: JSON.stringify(campaignData),
  });
  
  return await response.json();
};

// GET /api/campaigns - Get user campaigns
const getCampaigns = async () => {
  const response = await makeAuthenticatedRequest('/api/campaigns');
  return await response.json();
};

// POST /api/campaigns/{campaign_id}/start - Start campaign
const startCampaign = async (campaignId: string) => {
  const response = await makeAuthenticatedRequest(`/api/campaigns/${campaignId}/start`, {
    method: 'POST',
  });
  
  return await response.json();
};

// POST /api/campaigns/{campaign_id}/pause - Pause campaign
const pauseCampaign = async (campaignId: string) => {
  const response = await makeAuthenticatedRequest(`/api/campaigns/${campaignId}/pause`, {
    method: 'POST',
  });
  
  return await response.json();
};
```

---

## ⚡ **REAL-TIME WEBSOCKET**

### **WebSocket Connection**
```typescript
// WebSocket URL: ws://your-backend-domain.com/ws/{user_id}
class WebSocketManager {
  private ws: WebSocket | null = null;
  private userId: string;
  private token: string;
  
  constructor(userId: string, token: string) {
    this.userId = userId;
    this.token = token;
  }
  
  connect() {
    const wsUrl = `ws://your-backend-domain.com/ws/${this.userId}?token=${this.token}`;
    this.ws = new WebSocket(wsUrl);
    
    this.ws.onopen = () => {
      console.log('WebSocket connected');
    };
    
    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };
    
    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      // Implement reconnection logic
      setTimeout(() => this.connect(), 5000);
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }
  
  private handleMessage(message: any) {
    switch (message.type) {
      case 'chat_message':
        // Handle real-time chat response
        this.onChatMessage(message.data);
        break;
        
      case 'search_progress':
        // Handle search progress updates
        this.onSearchProgress(message.data);
        break;
        
      case 'campaign_update':
        // Handle campaign status updates
        this.onCampaignUpdate(message.data);
        break;
        
      case 'notification':
        // Handle system notifications
        this.onNotification(message.data);
        break;
        
      case 'upsell_offer':
        // Handle upselling suggestions
        this.onUpsellOffer(message.data);
        break;
    }
  }
  
  sendMessage(type: string, data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, data }));
    }
  }
  
  // Event handlers (implement based on your UI needs)
  onChatMessage(data: any) { /* Update chat UI */ }
  onSearchProgress(data: any) { /* Update search progress */ }
  onCampaignUpdate(data: any) { /* Update campaign status */ }
  onNotification(data: any) { /* Show notification */ }
  onUpsellOffer(data: any) { /* Show upgrade suggestion */ }
}

// Usage
const wsManager = new WebSocketManager(userId, accessToken);
wsManager.connect();
```

---

## 🎯 **ERROR HANDLING**

### **Error Response Format**
```typescript
interface ErrorResponse {
  success: false;
  error: string;
  detail?: string;
}

// Standard error handling
const handleApiResponse = async (response: Response) => {
  if (!response.ok) {
    const errorData = await response.json();
    
    if (response.status === 401) {
      // Token expired, try to refresh
      await refreshToken();
      // Retry the original request
    } else if (response.status === 403) {
      // Insufficient permissions
      throw new Error('Access denied');
    } else if (response.status === 429) {
      // Rate limited
      throw new Error('Too many requests. Please try again later.');
    } else {
      throw new Error(errorData.error || 'An error occurred');
    }
  }
  
  return response.json();
};
```

### **Common Error Codes**
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (invalid/expired token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found (resource doesn't exist)
- `429` - Too Many Requests (rate limited)
- `500` - Internal Server Error

---

## 🚀 **BEST PRACTICES**

### **1. Token Management**
```typescript
// Token storage and automatic refresh
class AuthManager {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  
  setTokens(access: string, refresh: string) {
    this.accessToken = access;
    this.refreshToken = refresh;
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
  }
  
  async getValidToken(): Promise<string> {
    if (!this.accessToken) {
      this.accessToken = localStorage.getItem('access_token');
    }
    
    // Check if token needs refresh (implement JWT decode logic)
    if (this.isTokenExpired(this.accessToken)) {
      await this.refreshTokens();
    }
    
    return this.accessToken!;
  }
  
  private async refreshTokens() {
    const refresh = this.refreshToken || localStorage.getItem('refresh_token');
    if (!refresh) {
      throw new Error('No refresh token available');
    }
    
    const response = await refreshToken(refresh);
    this.setTokens(response.access_token, response.refresh_token);
  }
}
```

### **2. API Client Setup**
```typescript
// Create a centralized API client
class ApiClient {
  private baseUrl = 'https://your-backend-domain.com/api';
  private authManager = new AuthManager();
  
  async request(endpoint: string, options: RequestInit = {}) {
    const token = await this.authManager.getValidToken();
    
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        ...options.headers,
      },
    });
    
    return handleApiResponse(response);
  }
  
  // Convenience methods
  get(endpoint: string) {
    return this.request(endpoint);
  }
  
  post(endpoint: string, data: any) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
  
  put(endpoint: string, data: any) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }
  
  delete(endpoint: string) {
    return this.request(endpoint, {
      method: 'DELETE',
    });
  }
}

// Usage
const api = new ApiClient();
const projects = await api.get('/projects');
const newProject = await api.post('/projects', projectData);
```

### **3. Real-time Updates**
```typescript
// Integrate WebSocket with React state
const useChatWebSocket = (userId: string, conversationId: string) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  
  useEffect(() => {
    const wsManager = new WebSocketManager(userId, getToken());
    
    wsManager.onChatMessage = (data) => {
      if (data.conversation_id === conversationId) {
        setMessages(prev => [...prev, data]);
      }
    };
    
    wsManager.connect();
    
    return () => {
      wsManager.disconnect();
    };
  }, [userId, conversationId]);
  
  return { messages, isConnected };
};
```

---

## 📚 **EXAMPLE COMPONENTS**

### **Login Component (React)**
```typescript
import React, { useState } from 'react';

const LoginForm: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    try {
      const response = await loginUser({ email, password });
      
      // Store tokens
      localStorage.setItem('access_token', response.access_token);
      localStorage.setItem('refresh_token', response.refresh_token);
      
      // Redirect to dashboard
      window.location.href = '/dashboard';
    } catch (error) {
      console.error('Login failed:', error);
      // Show error message
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <form onSubmit={handleLogin}>
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
        required
      />
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
        required
      />
      <button type="submit" disabled={isLoading}>
        {isLoading ? 'Logging in...' : 'Login'}
      </button>
    </form>
  );
};
```

### **Chat Component (React)**
```typescript
import React, { useState, useEffect } from 'react';

const ChatComponent: React.FC<{ conversationId: string }> = ({ conversationId }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  useEffect(() => {
    loadMessages();
  }, [conversationId]);
  
  const loadMessages = async () => {
    try {
      const messagesData = await getMessages(conversationId);
      setMessages(messagesData);
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  };
  
  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;
    
    setIsLoading(true);
    const userMessage = inputValue;
    setInputValue('');
    
    // Add user message to UI immediately
    const newMessage: Message = {
      id: 'temp-' + Date.now(),
      conversation_id: conversationId,
      role: 'user',
      content: userMessage,
      credits_used: 0,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, newMessage]);
    
    try {
      const response = await sendMessage(userMessage, conversationId);
      
      // Replace temporary message and add AI response
      setMessages(prev => [
        ...prev.slice(0, -1), // Remove temporary message
        response.user_message,
        response.ai_response,
      ]);
    } catch (error) {
      console.error('Failed to send message:', error);
      // Remove temporary message on error
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`message ${message.role}`}
          >
            <div className="content">{message.content}</div>
            <div className="timestamp">
              {new Date(message.created_at).toLocaleTimeString()}
            </div>
          </div>
        ))}
      </div>
      
      <div className="input-area">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Type your message..."
          disabled={isLoading}
        />
        <button onClick={sendMessage} disabled={isLoading}>
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  );
};
```

---

## 🔧 **ENVIRONMENT SETUP**

### **Environment Variables (Frontend)**
```bash
# .env.local (Next.js) or .env (React)
NEXT_PUBLIC_API_URL=https://your-backend-domain.com/api
NEXT_PUBLIC_WS_URL=ws://your-backend-domain.com/ws
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
```

### **API Client Configuration**
```typescript
// config/api.ts
export const API_CONFIG = {
  BASE_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api',
  WS_URL: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws',
  STRIPE_PK: process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || '',
};
```

---

## 📝 **IMPORTANT NOTES**

### **1. Rate Limiting**
- The API has rate limiting enabled
- If you get 429 errors, implement exponential backoff
- Users have daily credit limits based on their plan

### **2. Credit System**
- Free users: 200 initial credits, 50 daily
- Pro users: Unlimited credits, 150 daily
- Outreach users: Unlimited credits, 200 daily
- Each AI chat message costs 1 credit
- Investor searches cost 5-10 credits depending on complexity

### **3. WebSocket Considerations**
- WebSocket connections require authentication
- Implement automatic reconnection with exponential backoff
- Handle connection drops gracefully
- Use heartbeat/ping mechanism to keep connections alive

### **4. Error Handling**
- Always handle network errors
- Implement retry logic for transient failures
- Show user-friendly error messages
- Log errors for debugging

### **5. Security**
- Never store sensitive data in localStorage in production
- Use HTTPS in production
- Validate all user inputs
- Implement CSRF protection

---

## 🚀 **DEPLOYMENT CHECKLIST**

### **Before Deployment:**
1. ✅ Update API URLs to production endpoints
2. ✅ Configure Stripe with production keys
3. ✅ Test authentication flow end-to-end
4. ✅ Test payment integration
5. ✅ Verify WebSocket connections work
6. ✅ Test error handling scenarios
7. ✅ Implement loading states for all API calls
8. ✅ Add proper error messages
9. ✅ Test responsive design
10. ✅ Performance optimization (lazy loading, caching)

### **Production Endpoints:**
- **API Base URL**: `https://your-production-api.com/api`
- **WebSocket URL**: `wss://your-production-api.com/ws`
- **Health Check**: `https://your-production-api.com/health`

---

## 📞 **SUPPORT**

If you have any questions or need clarification on any endpoint or integration pattern, please reach out. The backend is fully functional and tested, so all endpoints should work as documented.

**Key Points to Remember:**
- Always include authentication headers for protected endpoints
- Handle token refresh automatically
- Implement proper error handling
- Use WebSockets for real-time features
- Test payment flows thoroughly
- Follow the rate limiting guidelines

Good luck with the frontend development! 🚀

---

*Document created for Frontend Integration*  
*Last updated: January 2025*  
*Version: 1.0.0*
