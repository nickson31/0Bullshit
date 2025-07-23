-- ============================================
-- LIMPIEZA DE TABLAS DUPLICADAS EN SUPABASE
-- ============================================
-- Ejecutar cada bloque por separado en Supabase SQL Editor
-- ============================================

-- ============================================
-- PASO 1: VERIFICAR ESTADO ACTUAL
-- ============================================
-- Ejecutar este bloque primero para ver qué tablas duplicadas tenemos

SELECT table_name, count(*) as count
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('employee_funds', 'fund_employees')
GROUP BY table_name;

-- ============================================
-- PASO 2: ELIMINAR TABLA DUPLICADA INCORRECTA
-- ============================================
-- Eliminar employee_funds ya que fund_employees tiene más columnas y estructura correcta

DROP TABLE IF EXISTS public.employee_funds CASCADE;

-- ============================================
-- PASO 3: VERIFICAR QUE FUND_EMPLOYEES TIENE DATOS
-- ============================================
-- Verificar que fund_employees tiene datos antes de continuar

SELECT count(*) as total_rows FROM public.fund_employees;

-- ============================================
-- PASO 4: AÑADIR PRIMARY KEY MISSING A FUND_EMPLOYEES
-- ============================================
-- Tu Primary Key es linkedinUrl según el prompt

ALTER TABLE fund_employees
ADD CONSTRAINT fund_employees_pkey PRIMARY KEY ("linkedinUrl");

-- ============================================
-- PASO 5: CREAR ÍNDICES PARA FUND_EMPLOYEES
-- ============================================

CREATE INDEX IF NOT EXISTS idx_fund_employees_score ON fund_employees(score_combinado);
CREATE INDEX IF NOT EXISTS idx_fund_employees_fund_name ON fund_employees(fund_name);

-- ============================================
-- PASO 6: HABILITAR RLS EN FUND_EMPLOYEES
-- ============================================

ALTER TABLE fund_employees ENABLE ROW LEVEL SECURITY;

-- ============================================
-- PASO 7: CREAR POLÍTICA DE ACCESO PÚBLICO
-- ============================================

CREATE POLICY "Allow public read fund employees" ON fund_employees FOR SELECT TO public USING (true);

-- ============================================
-- PASO 8: VERIFICAR ESTADO FINAL
-- ============================================
-- Verificar que todo está correcto

SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name IN ('angel_investors', 'companies', 'investment_funds', 'fund_employees')
AND table_schema = 'public'
ORDER BY table_name, ordinal_position;

-- ============================================
-- PASO 9: VERIFICAR CONTEO DE DATOS
-- ============================================
-- Verificar que tienes datos en todas las tablas

SELECT 
    'angel_investors' as table_name, count(*) as rows FROM angel_investors
UNION ALL
SELECT 
    'companies' as table_name, count(*) as rows FROM companies  
UNION ALL
SELECT 
    'investment_funds' as table_name, count(*) as rows FROM investment_funds
UNION ALL
SELECT 
    'fund_employees' as table_name, count(*) as rows FROM fund_employees;

-- ============================================
-- ESTADO FINAL ESPERADO
-- ============================================
-- Después de ejecutar todo deberías tener:
-- ✅ angel_investors (con tu data + id, created_at, last_updated)
-- ✅ companies (con tu data + id, created_at, last_updated)  
-- ✅ investment_funds (con tu data + id, created_at, last_updated)
-- ✅ fund_employees (con tu data + id, created_at, last_updated)
-- ❌ employee_funds (eliminada)
-- ============================================