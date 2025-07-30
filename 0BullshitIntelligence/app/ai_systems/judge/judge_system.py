"""
Judge System - Enhanced user intent analysis and action routing.
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from uuid import UUID
import google.generativeai as genai

from app.core.config import settings
from app.core.logging import get_logger, log_ai_performance, ai_decision_logger
from app.models import (
    JudgeDecision, JudgeProbabilities, ExtractedData, 
    Project, ConversationContext, Language
)
from .context_analyzer import ContextAnalyzer
from .decision_engine import DecisionEngine

logger = get_logger(__name__)


class JudgeSystem:
    """
    Enhanced Judge System for 0BullshitIntelligence.
    
    Analyzes user intent and decides what action to take based on:
    - User message content
    - Project context and completeness
    - Conversation history
    - User behavior patterns
    """
    
    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(
            model_name=settings.gemini_model,
            generation_config={
                "temperature": 0.3,  # Conservative for decision making
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 2000,
            }
        )
        
        self.context_analyzer = ContextAnalyzer()
        self.decision_engine = DecisionEngine()
        
        # Y-Combinator principles for context
        self.yc_principles = """
        PRINCIPIOS Y-COMBINATOR PARA ANÁLISIS:
        
        1. ENFOQUE EN EJECUCIÓN: Prioriza acciones sobre planificación
        2. HABLAR CON USUARIOS: La validación del mercado es clave
        3. MÉTRICAS IMPORTANTES: ARR, MRR, crecimiento, churn
        4. PROBLEM-SOLUTION FIT: ¿Resuelve un problema real?
        5. EQUIPO ES TODO: Experiencia técnica y de negocio
        6. CONCISIÓN: Explicar clara y brevemente
        7. TRACCIÓN > IDEAS: Resultados sobre conceptos
        8. SER DIRECTO: Preguntas y respuestas directas
        9. PRODUCT-MARKET FIT: Lo más importante antes de escalar
        10. PEDIR DINERO: Si necesita financiación, sea explícito
        """
    
    @log_ai_performance("judge")
    async def analyze_user_intent(
        self,
        user_message: str,
        project: Optional[Project] = None,
        conversation_context: Optional[ConversationContext] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_language: Language = Language.SPANISH
    ) -> JudgeDecision:
        """
        Analyze user intent and decide what action to take.
        
        Args:
            user_message: The user's message
            project: Current project context
            conversation_context: Conversation state and context
            conversation_history: Recent conversation messages
            user_language: User's detected language
            
        Returns:
            JudgeDecision with analysis results and recommended action
        """
        try:
            logger.info("Starting judge analysis", 
                       message_length=len(user_message),
                       has_project=project is not None,
                       has_context=conversation_context is not None)
            
            # Analyze context
            context_analysis = await self.context_analyzer.analyze_context(
                project=project,
                conversation_context=conversation_context,
                conversation_history=conversation_history
            )
            
            # Create comprehensive prompt for Gemini
            prompt = self._create_judge_prompt(
                user_message=user_message,
                context_analysis=context_analysis,
                user_language=user_language
            )
            
            # Get decision from Gemini
            response = await self.model.generate_content_async(prompt)
            
            # Parse and validate response
            decision_data = self._parse_gemini_response(response.text)
            
            # Enhance decision with business logic
            enhanced_decision = await self.decision_engine.enhance_decision(
                decision_data=decision_data,
                context_analysis=context_analysis,
                user_message=user_message
            )
            
            # Log decision for transparency
            ai_decision_logger.log_judge_decision(
                user_message=user_message,
                decision=enhanced_decision.decision,
                confidence=enhanced_decision.confidence,
                reasoning=enhanced_decision.reasoning,
                user_id=str(conversation_context.user_id) if conversation_context else None,
                project_id=str(project.id) if project else None
            )
            
            logger.info("Judge analysis completed",
                       decision=enhanced_decision.decision,
                       confidence=enhanced_decision.confidence)
            
            return enhanced_decision
            
        except Exception as e:
            logger.error(f"Judge analysis failed: {e}", exc_info=True)
            
            # Return fallback decision
            return self._create_fallback_decision(user_message, user_language)
    
    def _create_judge_prompt(
        self,
        user_message: str,
        context_analysis: Dict[str, Any],
        user_language: Language
    ) -> str:
        """Create the comprehensive prompt for Gemini analysis."""
        
        # Get language-specific prompts
        prompt_language = "spanish" if user_language == Language.SPANISH else "english"
        
        if prompt_language == "spanish":
            base_prompt = self._get_spanish_prompt()
        else:
            base_prompt = self._get_english_prompt()
        
        # Build context section
        context_section = self._build_context_section(context_analysis)
        
        # Final prompt
        prompt = f"""
{base_prompt}

{self.yc_principles}

CONTEXTO ACTUAL:
{context_section}

MENSAJE DEL USUARIO: "{user_message}"

Analiza este mensaje y responde con el JSON solicitado.
"""
        
        return prompt
    
    def _get_spanish_prompt(self) -> str:
        """Get the Spanish language prompt for judge analysis."""
        return """
Eres el JUDGE de 0Bullshit, un sistema experto que analiza la intención del usuario y decide qué acción tomar.

Tu trabajo es determinar qué necesita el usuario y dirigirlo a la acción correcta siguiendo los principios de Y-Combinator.

ACCIONES DISPONIBLES:
1. "chat" - Conversación general de mentoría Y-Combinator
2. "search_investors" - Buscar inversores (requiere proyecto ≥50% completo)
3. "search_companies" - Buscar empresas para servicios B2B
4. "welcome" - Sistema de bienvenida y onboarding
5. "upsell" - Oportunidad de upgrade de plan
6. "completeness" - Revisar y mejorar completitud del proyecto

CRITERIOS DE DECISIÓN:
- search_investors: Menciona inversión, financiación, capital, inversores, VC, angels
- search_companies: Busca servicios, herramientas, proveedores, partners B2B
- welcome: Usuario nuevo, primera vez, no sabe qué hacer
- upsell: Ha alcanzado límites del plan actual
- completeness: Proyecto incompleto, faltan datos importantes
- chat: Mentoría general, consejos, estrategia, validación

RESPONDE EXACTAMENTE con este formato JSON:
{
    "decision": "acción_elegida",
    "confidence": 0.85,
    "reasoning": "Explicación clara de por qué elegiste esta acción",
    "probabilities": {
        "chat": 0.15,
        "search_investors": 0.75,
        "search_companies": 0.05,
        "welcome": 0.02,
        "upsell": 0.02,
        "completeness": 0.01
    },
    "extracted_data": {
        "categories": ["fintech", "saas"],
        "stage": "mvp",
        "funding_amount": "500k",
        "additional_fields": {}
    },
    "urgency_level": 3,
    "requires_context": false
}
"""
    
    def _get_english_prompt(self) -> str:
        """Get the English language prompt for judge analysis."""
        return """
You are the JUDGE of 0Bullshit, an expert system that analyzes user intent and decides what action to take.

Your job is to determine what the user needs and direct them to the correct action following Y-Combinator principles.

AVAILABLE ACTIONS:
1. "chat" - General Y-Combinator mentorship conversation
2. "search_investors" - Search for investors (requires project ≥50% complete)
3. "search_companies" - Search for B2B service companies
4. "welcome" - Welcome system and onboarding
5. "upsell" - Plan upgrade opportunity
6. "completeness" - Review and improve project completeness

DECISION CRITERIA:
- search_investors: Mentions investment, funding, capital, investors, VC, angels
- search_companies: Looking for services, tools, providers, B2B partners
- welcome: New user, first time, doesn't know what to do
- upsell: Has reached current plan limits
- completeness: Incomplete project, missing important data
- chat: General mentorship, advice, strategy, validation

RESPOND EXACTLY with this JSON format:
{
    "decision": "chosen_action",
    "confidence": 0.85,
    "reasoning": "Clear explanation of why you chose this action",
    "probabilities": {
        "chat": 0.15,
        "search_investors": 0.75,
        "search_companies": 0.05,
        "welcome": 0.02,
        "upsell": 0.02,
        "completeness": 0.01
    },
    "extracted_data": {
        "categories": ["fintech", "saas"],
        "stage": "mvp",
        "funding_amount": "500k",
        "additional_fields": {}
    },
    "urgency_level": 3,
    "requires_context": false
}
"""
    
    def _build_context_section(self, context_analysis: Dict[str, Any]) -> str:
        """Build the context section for the prompt."""
        sections = []
        
        # Project information
        if context_analysis.get("project"):
            project_info = context_analysis["project"]
            sections.append(f"""
PROYECTO ACTUAL:
- Nombre: {project_info.get('name', 'Sin nombre')}
- Completitud: {project_info.get('completeness_score', 0):.1f}%
- Categorías: {', '.join(project_info.get('categories', []))}
- Etapa: {project_info.get('stage', 'No definida')}
- Descripción: {project_info.get('description', 'Sin descripción')[:200]}...
""")
        
        # User context
        if context_analysis.get("user"):
            user_info = context_analysis["user"]
            sections.append(f"""
USUARIO:
- Plan: {user_info.get('plan', 'free')}
- Créditos restantes: {user_info.get('credits_remaining', 0)}
- Onboarding completado: {user_info.get('onboarding_completed', False)}
- Búsquedas recientes: {user_info.get('recent_searches', 0)}
""")
        
        # Conversation context
        if context_analysis.get("conversation"):
            conv_info = context_analysis["conversation"]
            sections.append(f"""
CONVERSACIÓN:
- Mensajes: {conv_info.get('message_count', 0)}
- Idioma detectado: {conv_info.get('detected_language', 'spanish')}
- Intentos de upsell hoy: {conv_info.get('upsell_attempts_today', 0)}
""")
        
        # Recent messages
        if context_analysis.get("recent_messages"):
            messages = context_analysis["recent_messages"]
            sections.append(f"""
MENSAJES RECIENTES:
{chr(10).join([f"- {msg.get('role', 'user')}: {msg.get('content', '')[:100]}..." for msg in messages[-3:]])}
""")
        
        return "\n".join(sections) if sections else "Sin contexto disponible"
    
    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """Parse and validate Gemini's JSON response."""
        try:
            # Clean the response
            response_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1])
            
            # Parse JSON
            data = json.loads(response_text)
            
            # Validate required fields
            required_fields = ["decision", "confidence", "reasoning", "probabilities"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate probabilities sum approximately to 1.0
            prob_sum = sum(data["probabilities"].values())
            if abs(prob_sum - 1.0) > 0.1:
                logger.warning(f"Probabilities sum to {prob_sum}, normalizing")
                # Normalize probabilities
                for key in data["probabilities"]:
                    data["probabilities"][key] /= prob_sum
            
            return data
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            logger.debug(f"Raw response: {response_text}")
            raise ValueError(f"Invalid Gemini response format: {e}")
    
    def _create_fallback_decision(
        self, 
        user_message: str, 
        user_language: Language
    ) -> JudgeDecision:
        """Create a fallback decision when analysis fails."""
        logger.warning("Creating fallback decision due to analysis failure")
        
        # Simple keyword-based fallback
        message_lower = user_message.lower()
        
        if any(word in message_lower for word in ["inversor", "investment", "funding", "capital"]):
            decision = "search_investors"
            confidence = 0.6
        elif any(word in message_lower for word in ["empresa", "servicio", "company", "service"]):
            decision = "search_companies"
            confidence = 0.6
        else:
            decision = "chat"
            confidence = 0.8
        
        return JudgeDecision(
            decision=decision,
            confidence=confidence,
            reasoning="Fallback decision based on keyword analysis",
            probabilities=JudgeProbabilities(
                chat=0.8 if decision == "chat" else 0.2,
                search_investors=0.6 if decision == "search_investors" else 0.1,
                search_companies=0.6 if decision == "search_companies" else 0.1,
                welcome=0.05,
                upsell=0.05,
                completeness=0.1
            ),
            extracted_data=ExtractedData(),
            urgency_level=3
        )