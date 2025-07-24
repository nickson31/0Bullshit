# 🧪 **CURSOR TESTING SYSTEM - 0BULLSHIT BACKEND**

## 🎯 **Descripción**

Sistema de testing optimizado para ser ejecutado directamente por el asistente IA de Cursor, diseñado para testear de manera autónoma todas las funcionalidades de tu SaaS **0Bullshit**.

### **¿Qué testea?**
- ✅ **Autenticación y seguridad**
- ✅ **Sistema de chat con IA** (Judge, Mentor, Librarian)
- ✅ **Detección de idiomas y anti-spam**
- ✅ **Búsquedas de inversores y companies**
- ✅ **Sistema de créditos y pagos**
- ✅ **Gestión de proyectos**
- ✅ **WebSockets en tiempo real**
- ✅ **LinkedIn automation** (si está configurado)

---

## 🚀 **Inicio Rápido (Para Cursor AI)**

### **Opción 1: Todo Automático**
```bash
# Instalar dependencias, iniciar backend, y ejecutar todos los tests
python testing/start_backend_and_test.py
```

### **Opción 2: Solo Tests (Backend ya corriendo)**
```bash
# Ejecutar todos los tests
python testing/cursor_test_runner.py --all

# Test rápido (solo auth + chat)
python testing/cursor_test_runner.py --quick

# Test de feature específica
python testing/cursor_test_runner.py --feature auth
```

### **Opción 3: Preparación Manual**
```bash
# 1. Instalar dependencias
python testing/install_testing_deps.py

# 2. Iniciar backend (en otra terminal)
python main.py

# 3. Ejecutar tests
python testing/cursor_test_runner.py --all
```

---

## 📋 **Comandos Disponibles**

### **🔧 Instalación y Setup**
```bash
# Instalar todas las dependencias de testing
python testing/install_testing_deps.py

# Crear archivo de configuración
cp testing/.env.testing.example testing/.env.testing
```

### **🧪 Ejecutar Tests**
```bash
# Test completo de todas las funcionalidades
python testing/cursor_test_runner.py --all

# Test rápido (auth + chat básico)
python testing/cursor_test_runner.py --quick

# Test de funcionalidad específica
python testing/cursor_test_runner.py --feature auth      # Autenticación
python testing/cursor_test_runner.py --feature chat     # Sistema de chat
python testing/cursor_test_runner.py --feature search   # Búsquedas
python testing/cursor_test_runner.py --feature projects # Proyectos
python testing/cursor_test_runner.py --feature websockets # WebSockets
python testing/cursor_test_runner.py --feature payments # Pagos

# Modo silencioso (menos output)
python testing/cursor_test_runner.py --all --quiet
```

### **🚀 Auto-Start Backend + Tests**
```bash
# Iniciar backend automáticamente y ejecutar tests
python testing/start_backend_and_test.py

# Test rápido con auto-start
python testing/start_backend_and_test.py --quick

# Mantener backend corriendo después de tests
python testing/start_backend_and_test.py --keep-backend

# No iniciar backend automáticamente
python testing/start_backend_and_test.py --no-auto-start
```

---

## 📊 **Interpretación de Resultados**

### **Estados de Test**
- ✅ **PASS** - Test exitoso
- ❌ **FAIL** - Test falló
- ⚠️ **PARTIAL** - Algunos tests pasaron, otros fallaron
- ℹ️ **INFO** - Información adicional
- 🔍 **DEBUG** - Información de debugging

### **Ejemplo de Output**
```
🧪 CURSOR TEST RUNNER - 0BULLSHIT BACKEND
================================================================================
[10:30:15] ℹ️ Backend URL: http://localhost:8000
[10:30:15] ℹ️ Test User: test@0bullshit.com
[10:30:15] ℹ️ Starting comprehensive testing suite...

[10:30:16] ✅ Backend is healthy and ready
[10:30:17] ✅ Authentication: All 3 tests passed
[10:30:18] ✅ Projects: All 3 tests passed
[10:30:20] ✅ Chat System: All 4 tests passed
[10:30:22] ✅ Search System: All 2 tests passed
[10:30:23] ✅ WebSockets: All 2 tests passed
[10:30:24] ✅ Payments: All 3 tests passed

📊 TEST RESULTS SUMMARY
================================================================================
Authentication  - ✅ PASS (3/3) - 100.0%
    ✅ User authentication successful
    ✅ Profile access - Plan: free
       Credits: 200
    ✅ Token refresh working

Projects        - ✅ PASS (3/3) - 100.0%
Chat System     - ✅ PASS (4/4) - 100.0%
Search System   - ✅ PASS (2/2) - 100.0%
WebSockets      - ✅ PASS (2/2) - 100.0%
Payments        - ✅ PASS (3/3) - 100.0%

OVERALL RESULT: 17/17 tests passed (100.0%)
Execution time: 8.45 seconds
🎉 ALL TESTS PASSED! Your SaaS is working correctly.
```

---

## ⚙️ **Configuración**

### **Variables de Entorno (testing/.env.testing)**
```bash
# API Configuration
API_BASE_URL=http://localhost:8000
WS_BASE_URL=ws://localhost:8000

# Test User
TEST_USER_EMAIL=test@0bullshit.com
TEST_USER_PASSWORD=TestPassword123!

# Testing Limits (para ahorrar créditos)
MAX_SEARCH_RESULTS=5
MAX_INVESTOR_SEARCH_RESULTS=3
TEST_CREDITS_LIMIT=100

# Feature Flags
TEST_PAYMENTS=true
TEST_LINKEDIN=false
TEST_WEBSOCKETS=true
```

### **Personalización de Tests**
Puedes modificar `testing/cursor_test_runner.py` para:
- Agregar nuevos tests
- Cambiar límites de búsqueda
- Modificar mensajes de prueba
- Ajustar timeouts

---

## 🔍 **Troubleshooting**

### **Error: "Backend not responding"**
```bash
# Verificar que el backend esté corriendo
curl http://localhost:8000/health

# Si no responde, usar auto-start:
python testing/start_backend_and_test.py
```

### **Error: "Missing dependencies"**
```bash
# Instalar dependencias automáticamente
python testing/install_testing_deps.py
```

### **Error: "Authentication failed"**
```bash
# Verificar configuración en .env.testing
# El sistema creará automáticamente el usuario de test si no existe
```

### **Error: "Insufficient credits"**
```bash
# Los tests están optimizados para usar pocos créditos
# Si el usuario de test se queda sin créditos, el sistema lo indicará
# Puedes usar un usuario diferente o resetear créditos manualmente
```

### **Tests Fallan Intermitentemente**
```bash
# Ejecutar con más tiempo de espera
export TEST_TIMEOUT=60
python testing/cursor_test_runner.py --all
```

---

## 📈 **Optimizaciones para Cursor**

### **Características Específicas para IA**
1. **Auto-detección de backend** - No requiere intervención manual
2. **Auto-instalación de dependencias** - Setup automático
3. **Cleanup automático** - Limpia datos de test
4. **Reportes detallados** - Output fácil de interpretar
5. **Manejo de errores robusto** - Continúa aunque fallen algunos tests
6. **Timeouts inteligentes** - No se cuelga esperando respuestas
7. **Logging con timestamps** - Fácil debugging

### **Uso Recomendado desde Cursor**
```bash
# Para testing completo y confiable:
python testing/start_backend_and_test.py

# Para debugging rápido:
python testing/cursor_test_runner.py --quick

# Para feature específica:
python testing/cursor_test_runner.py --feature chat
```

---

## 🎯 **Casos de Uso Específicos**

### **Después de Cambios en el Código**
```bash
# Test rápido para verificar que no rompiste nada
python testing/cursor_test_runner.py --quick
```

### **Antes de Deploy**
```bash
# Test completo de todas las funcionalidades
python testing/start_backend_and_test.py
```

### **Testing de Feature Nueva**
```bash
# Test específico de la feature que desarrollaste
python testing/cursor_test_runner.py --feature [feature_name]
```

### **Debugging de Problemas**
```bash
# Test con output detallado
python testing/cursor_test_runner.py --all --verbose
```

---

## 📝 **Logs y Debugging**

### **Archivos de Log**
- `testing_results.log` - Log detallado de ejecución
- `app.log` - Log del backend (si DEBUG=True)

### **Interpretación de Logs**
```
[10:30:15] 🔍 Checking backend health...
[10:30:16] ✅ Backend is healthy and ready
[10:30:17] 🔍 Testing authentication system...
[10:30:17] ✅ Authenticated as user: 123e4567-e89b-12d3-a456-426614174000
```

---

## 🚀 **Próximos Pasos**

Después de ejecutar los tests exitosamente:

1. **Si todos los tests pasan** ✅
   - Tu SaaS está funcionando correctamente
   - Puedes proceder con confianza

2. **Si algunos tests fallan** ⚠️
   - Revisa los detalles en el output
   - Los errores más comunes son configuración o créditos insuficientes

3. **Si muchos tests fallan** ❌
   - Verifica que el backend esté configurado correctamente
   - Revisa las variables de entorno
   - Asegúrate de que las dependencias estén instaladas

---

*Testing System optimizado para Cursor AI - Versión 1.0*  
*Diseñado para testing autónomo y confiable del backend 0Bullshit*