-- ============================================
-- 0BULLSHIT SUPABASE SETUP - PASO A PASO
-- ============================================
-- Ejecuta cada sección por separado en Supabase SQL Editor
-- Estado actual: Solo existen tablas del schema 'auth'
-- ============================================

-- ============================================
-- PASO 1: HABILITAR EXTENSIONES NECESARIAS
-- ============================================
-- Ejecutar este bloque primero

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- PASO 2: CREAR TABLA USERS (extiende auth.users)
-- ============================================
-- Ejecutar este bloque segundo

CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    plan VARCHAR(20) DEFAULT 'free' CHECK (plan IN ('free', 'pro', 'outreach')),
    credits INTEGER DEFAULT 200,
    daily_credits_used INTEGER DEFAULT 0,
    daily_credits_limit INTEGER DEFAULT 200,
    last_credit_reset TIMESTAMP DEFAULT NOW(),
    stripe_customer_id VARCHAR(255) UNIQUE,
    onboarding_completed BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- PASO 3: CREAR TABLA PROJECTS
-- ============================================
-- Ejecutar este bloque tercero

CREATE TABLE IF NOT EXISTS public.projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    stage VARCHAR(50) DEFAULT 'idea' CHECK (stage IN ('idea', 'prototype', 'mvp', 'early_revenue', 'growth', 'scale')),
    category VARCHAR(50) DEFAULT 'other' CHECK (category IN ('fintech', 'healthtech', 'edtech', 'proptech', 'retail', 'saas', 'marketplace', 'social', 'gaming', 'ai', 'other')),
    business_model TEXT,
    revenue_model TEXT,
    target_market TEXT,
    funding_amount VARCHAR(100),
    current_revenue VARCHAR(100),
    projected_revenue VARCHAR(100),
    team_size INTEGER,
    key_metrics JSONB,
    achievements TEXT,
    problem_solving TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- PASO 4: CREAR TABLAS DE CONVERSACIONES Y MENSAJES
-- ============================================
-- Ejecutar este bloque cuarto

CREATE TABLE IF NOT EXISTS public.conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES public.projects(id) ON DELETE SET NULL,
    title VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    ai_extractions JSONB,
    gemini_prompt_used VARCHAR(100),
    credits_used INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- PASO 5: CREAR TABLAS DE INVERSORES
-- ============================================
-- Ejecutar este bloque quinto

CREATE TABLE IF NOT EXISTS public.angel_investors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    linkedin_url VARCHAR(500),
    email VARCHAR(255),
    company VARCHAR(255),
    title VARCHAR(255),
    bio TEXT,
    location VARCHAR(255),
    investment_focus TEXT,
    stage_preference VARCHAR(100),
    check_size_min INTEGER,
    check_size_max INTEGER,
    portfolio_companies TEXT[],
    categories JSONB,
    last_updated TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.investment_funds (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    website VARCHAR(500),
    linkedin_url VARCHAR(500),
    description TEXT,
    investment_focus TEXT,
    stage_preference VARCHAR(100),
    check_size_min BIGINT,
    check_size_max BIGINT,
    portfolio_companies TEXT[],
    categories JSONB,
    location VARCHAR(255),
    founded_year INTEGER,
    aum_usd BIGINT,
    last_updated TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.fund_employees (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fund_id UUID NOT NULL REFERENCES public.investment_funds(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    linkedin_url VARCHAR(500),
    email VARCHAR(255),
    title VARCHAR(255),
    bio TEXT,
    seniority_level VARCHAR(50) CHECK (seniority_level IN ('analyst', 'associate', 'principal', 'partner', 'managing_partner')),
    investment_focus TEXT,
    categories JSONB,
    last_updated TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- PASO 6: CREAR TABLA COMPANIES Y SEARCH RESULTS
-- ============================================
-- Ejecutar este bloque sexto

CREATE TABLE IF NOT EXISTS public.companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    website VARCHAR(500),
    linkedin_url VARCHAR(500),
    description TEXT,
    industry VARCHAR(100),
    size_range VARCHAR(50),
    location VARCHAR(255),
    founded_year INTEGER,
    revenue_range VARCHAR(100),
    technologies TEXT[],
    contact_email VARCHAR(255),
    phone VARCHAR(50),
    last_updated TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.search_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES public.projects(id) ON DELETE SET NULL,
    search_type VARCHAR(50) NOT NULL CHECK (search_type IN ('investors', 'companies')),
    query_params JSONB,
    results JSONB NOT NULL,
    total_found INTEGER DEFAULT 0,
    average_relevance DECIMAL(5,2),
    credits_used INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- PASO 7: CREAR TABLAS DE PAGOS
-- ============================================
-- Ejecutar este bloque séptimo

CREATE TABLE IF NOT EXISTS public.subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    stripe_subscription_id VARCHAR(255) UNIQUE NOT NULL,
    plan VARCHAR(20) NOT NULL CHECK (plan IN ('pro', 'outreach')),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'canceled', 'past_due', 'unpaid')),
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.credit_purchases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    stripe_payment_intent_id VARCHAR(255) UNIQUE NOT NULL,
    credits_purchased INTEGER NOT NULL,
    amount_usd DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed')),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- PASO 8: CREAR TABLAS DE LINKEDIN AUTOMATION
-- ============================================
-- Ejecutar este bloque octavo

CREATE TABLE IF NOT EXISTS public.linkedin_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    unipile_account_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'disconnected', 'error')),
    last_sync TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.outreach_campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES public.projects(id) ON DELETE SET NULL,
    linkedin_account_id UUID REFERENCES public.linkedin_accounts(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'paused', 'completed')),
    sequence_type VARCHAR(20) DEFAULT 'standard' CHECK (sequence_type IN ('standard', 'aggressive', 'conservative')),
    target_count INTEGER DEFAULT 0,
    sent_count INTEGER DEFAULT 0,
    response_count INTEGER DEFAULT 0,
    connection_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- PASO 9: CREAR TABLAS DE OUTREACH TARGETS Y MESSAGES
-- ============================================
-- Ejecutar este bloque noveno

CREATE TABLE IF NOT EXISTS public.outreach_targets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES public.outreach_campaigns(id) ON DELETE CASCADE,
    investor_type VARCHAR(20) NOT NULL CHECK (investor_type IN ('angel', 'fund_employee')),
    investor_id UUID NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'connected', 'responded', 'not_interested', 'error')),
    sent_at TIMESTAMP,
    connected_at TIMESTAMP,
    responded_at TIMESTAMP,
    last_message_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.generated_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    investor_id VARCHAR(255) NOT NULL,
    message_type VARCHAR(50) NOT NULL CHECK (message_type IN ('connection_request', 'first_message', 'follow_up', 'pitch_message')),
    message_content TEXT NOT NULL,
    personalization_score DECIMAL(5,2),
    generated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- PASO 10: CREAR TABLAS DE ONBOARDING Y UPSELLING
-- ============================================
-- Ejecutar este bloque décimo

CREATE TABLE IF NOT EXISTS public.user_onboarding (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    current_stage VARCHAR(50) DEFAULT 'welcome',
    completed_stages TEXT[] DEFAULT '{}',
    completed BOOLEAN DEFAULT FALSE,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.upsell_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    target_plan VARCHAR(20) NOT NULL,
    trigger VARCHAR(100),
    confidence DECIMAL(5,2),
    priority INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- PASO 11: CREAR ÍNDICES PRINCIPALES
-- ============================================
-- Ejecutar este bloque undécimo

CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_stripe_customer ON public.users(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON public.projects(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_category ON public.projects(category);
CREATE INDEX IF NOT EXISTS idx_projects_stage ON public.projects(stage);

-- ============================================
-- PASO 12: CREAR ÍNDICES DE CONVERSACIONES
-- ============================================
-- Ejecutar este bloque duodécimo

CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON public.conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_project_id ON public.conversations(project_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON public.messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON public.messages(created_at);

-- ============================================
-- PASO 13: CREAR ÍNDICES DE INVERSORES
-- ============================================
-- Ejecutar este bloque decimotercero

CREATE INDEX IF NOT EXISTS idx_angel_investors_categories ON public.angel_investors USING GIN(categories);
CREATE INDEX IF NOT EXISTS idx_angel_investors_location ON public.angel_investors(location);
CREATE INDEX IF NOT EXISTS idx_fund_employees_fund_id ON public.fund_employees(fund_id);
CREATE INDEX IF NOT EXISTS idx_fund_employees_seniority ON public.fund_employees(seniority_level);

-- ============================================
-- PASO 14: CREAR ÍNDICES DE BÚSQUEDA Y CAMPAÑAS
-- ============================================
-- Ejecutar este bloque decimocuarto

CREATE INDEX IF NOT EXISTS idx_search_results_user_id ON public.search_results(user_id);
CREATE INDEX IF NOT EXISTS idx_search_results_type ON public.search_results(search_type);
CREATE INDEX IF NOT EXISTS idx_campaigns_user_id ON public.outreach_campaigns(user_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON public.outreach_campaigns(status);
CREATE INDEX IF NOT EXISTS idx_outreach_targets_campaign ON public.outreach_targets(campaign_id);
CREATE INDEX IF NOT EXISTS idx_outreach_targets_status ON public.outreach_targets(status);

-- ============================================
-- PASO 15: HABILITAR ROW LEVEL SECURITY
-- ============================================
-- Ejecutar este bloque decimoquinto

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.search_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.credit_purchases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.linkedin_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.outreach_campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.outreach_targets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.generated_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_onboarding ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.upsell_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.refresh_tokens ENABLE ROW LEVEL SECURITY;

-- ============================================
-- PASO 16: CREAR POLÍTICAS RLS BÁSICAS (USUARIOS)
-- ============================================
-- Ejecutar este bloque decimosexto

CREATE POLICY "Users can view own profile" ON public.users FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON public.users FOR UPDATE USING (auth.uid() = id);

-- ============================================
-- PASO 17: CREAR POLÍTICAS RLS (PROYECTOS)
-- ============================================
-- Ejecutar este bloque decimoséptimo

CREATE POLICY "Users can view own projects" ON public.projects FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own projects" ON public.projects FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own projects" ON public.projects FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own projects" ON public.projects FOR DELETE USING (auth.uid() = user_id);

-- ============================================
-- PASO 18: CREAR POLÍTICAS RLS (CONVERSACIONES)
-- ============================================
-- Ejecutar este bloque decimoctavo

CREATE POLICY "Users can view own conversations" ON public.conversations FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own conversations" ON public.conversations FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own conversations" ON public.conversations FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can view own messages" ON public.messages FOR SELECT USING (
    auth.uid() = (SELECT user_id FROM public.conversations WHERE id = conversation_id)
);
CREATE POLICY "Users can create own messages" ON public.messages FOR INSERT WITH CHECK (
    auth.uid() = (SELECT user_id FROM public.conversations WHERE id = conversation_id)
);

-- ============================================
-- PASO 19: CREAR POLÍTICAS RLS (BÚSQUEDAS Y SUSCRIPCIONES)
-- ============================================
-- Ejecutar este bloque decimonoveno

CREATE POLICY "Users can view own searches" ON public.search_results FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own searches" ON public.search_results FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view own subscriptions" ON public.subscriptions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own subscriptions" ON public.subscriptions FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own subscriptions" ON public.subscriptions FOR UPDATE USING (auth.uid() = user_id);

-- ============================================
-- PASO 20: CREAR POLÍTICAS RLS (CAMPAÑAS)
-- ============================================
-- Ejecutar este bloque vigésimo

CREATE POLICY "Users can view own campaigns" ON public.outreach_campaigns FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own campaigns" ON public.outreach_campaigns FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own campaigns" ON public.outreach_campaigns FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own campaigns" ON public.outreach_campaigns FOR DELETE USING (auth.uid() = user_id);

-- ============================================
-- PASO 21: CREAR POLÍTICAS RLS (ACCESO PÚBLICO INVERSORES)
-- ============================================
-- Ejecutar este bloque vigésimo primero

CREATE POLICY "Allow public read investors" ON public.angel_investors FOR SELECT TO public USING (true);
CREATE POLICY "Allow public read funds" ON public.investment_funds FOR SELECT TO public USING (true);
CREATE POLICY "Allow public read fund employees" ON public.fund_employees FOR SELECT TO public USING (true);
CREATE POLICY "Allow public read companies" ON public.companies FOR SELECT TO public USING (true);

-- ============================================
-- PASO 22: CREAR FUNCIÓN PARA TIMESTAMPS AUTOMÁTICOS
-- ============================================
-- Ejecutar este bloque vigésimo segundo

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- PASO 23: CREAR TRIGGERS PARA UPDATED_AT
-- ============================================
-- Ejecutar este bloque vigésimo tercero

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON public.projects FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON public.conversations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON public.subscriptions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_linkedin_accounts_updated_at BEFORE UPDATE ON public.linkedin_accounts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_campaigns_updated_at BEFORE UPDATE ON public.outreach_campaigns FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_onboarding_updated_at BEFORE UPDATE ON public.user_onboarding FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- PASO 24: VERIFICAR SETUP COMPLETADO
-- ============================================
-- Ejecutar este bloque vigésimo cuarto para verificar

SELECT 
    table_schema, 
    table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- ============================================
-- SETUP COMPLETADO
-- ============================================
-- Si ves todas las tablas listadas, el setup está completo:
-- 1. angel_investors
-- 2. companies  
-- 3. conversations
-- 4. credit_purchases
-- 5. fund_employees
-- 6. generated_messages
-- 7. investment_funds
-- 8. linkedin_accounts
-- 9. messages
-- 10. outreach_campaigns
-- 11. outreach_targets
-- 12. projects
-- 13. refresh_tokens
-- 14. search_results
-- 15. subscriptions
-- 16. upsell_attempts
-- 17. user_onboarding
-- 18. users
-- ============================================