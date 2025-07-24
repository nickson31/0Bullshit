# chat/language_detector.py
import google.generativeai as genai
import logging
from typing import Dict, Optional
from config.settings import GEMINI_API_KEY

logger = logging.getLogger(__name__)

class LanguageDetector:
    """
    Sistema de detección de idioma para 0Bullshit
    Detecta español, inglés u otros idiomas según requerimientos
    """
    
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    async def detect_language(self, text: str) -> Dict[str, str]:
        """
        Detecta el idioma del texto del usuario
        Returns: {"language": "spanish|english|other", "response_language": "spanish|english"}
        """
        try:
            prompt = f"""
            Analiza el siguiente texto y determina su idioma principal:

            TEXTO: "{text}"

            INSTRUCCIONES:
            1. Lee este texto y determina si es español, inglés u otro idioma
            2. Responde EXACTAMENTE con este formato JSON:

            {{
                "language": "spanish|english|other",
                "confidence": 0-100,
                "detected_phrases": ["frase1", "frase2"] (máximo 3 frases clave que indican el idioma)
            }}

            REGLAS:
            - Español: Texto principalmente en español
            - English: Texto principalmente en inglés  
            - Other: Cualquier otro idioma (francés, alemán, etc.)
            - Si hay mezcla de idiomas, usa el idioma PREDOMINANTE
            - Si no estás seguro, marca como "other"
            """
            
            response = await self.model.generate_content_async(prompt)
            
            if response and response.text:
                # Extraer JSON de la respuesta
                response_text = response.text.strip()
                if response_text.startswith('```json'):
                    response_text = response_text[7:-3].strip()
                elif response_text.startswith('```'):
                    response_text = response_text[3:-3].strip()
                
                import json
                detection_result = json.loads(response_text)
                
                # Determinar idioma de respuesta según reglas
                detected_lang = detection_result.get("language", "other")
                
                if detected_lang == "spanish":
                    response_language = "spanish"
                elif detected_lang == "english":
                    response_language = "english"
                else:  # other
                    response_language = "english"  # Default para otros idiomas
                
                return {
                    "language": detected_lang,
                    "response_language": response_language,
                    "confidence": detection_result.get("confidence", 50),
                    "detected_phrases": detection_result.get("detected_phrases", [])
                }
            
            # Fallback si falla la detección
            return {
                "language": "other",
                "response_language": "english",
                "confidence": 0,
                "detected_phrases": []
            }
            
        except Exception as e:
            logger.error(f"Error detecting language: {e}")
            # Fallback básico basado en palabras clave
            return self._basic_language_detection(text)
    
    def _basic_language_detection(self, text: str) -> Dict[str, str]:
        """
        Detección básica de idioma como fallback
        """
        text_lower = text.lower()
        
        # Palabras clave en español
        spanish_keywords = [
            'qué', 'cómo', 'dónde', 'cuándo', 'por', 'para', 'con', 'sin', 'desde',
            'hasta', 'muy', 'más', 'menos', 'también', 'además', 'pero', 'sino',
            'porque', 'aunque', 'mientras', 'durante', 'después', 'antes',
            'empresa', 'startup', 'negocio', 'inversores', 'inversión', 'dinero',
            'ayuda', 'buscar', 'encontrar', 'necesito', 'quiero', 'puedo'
        ]
        
        # Palabras clave en inglés
        english_keywords = [
            'what', 'how', 'where', 'when', 'why', 'the', 'and', 'or', 'but',
            'with', 'from', 'to', 'for', 'in', 'on', 'at', 'by', 'about',
            'company', 'startup', 'business', 'investors', 'investment', 'money',
            'help', 'search', 'find', 'need', 'want', 'can', 'could', 'would'
        ]
        
        spanish_count = sum(1 for word in spanish_keywords if word in text_lower)
        english_count = sum(1 for word in english_keywords if word in text_lower)
        
        if spanish_count > english_count:
            return {
                "language": "spanish",
                "response_language": "spanish", 
                "confidence": min(90, spanish_count * 10),
                "detected_phrases": []
            }
        elif english_count > spanish_count:
            return {
                "language": "english",
                "response_language": "english",
                "confidence": min(90, english_count * 10),
                "detected_phrases": []
            }
        else:
            return {
                "language": "other",
                "response_language": "english",
                "confidence": 25,
                "detected_phrases": []
            }
    
    async def get_response_instructions(self, detected_language: str) -> str:
        """
        Obtiene las instrucciones para el idioma de respuesta
        """
        if detected_language == "spanish":
            return """
            IMPORTANTE: Responde COMPLETAMENTE en español. 
            - Usa terminología de startups en español cuando sea apropiado
            - Mantén un tono profesional pero cercano
            - Incluye ejemplos relevantes para el mercado hispano
            """
        elif detected_language == "english":
            return """
            IMPORTANT: Respond COMPLETELY in English.
            - Use professional startup terminology
            - Maintain a professional but approachable tone
            - Include relevant examples for English-speaking markets
            """
        else:  # other
            return """
            IMPORTANT: Respond COMPLETELY in English (default language).
            - Use clear, simple English for non-native speakers
            - Avoid complex terminology when possible
            - Be extra clear and explicit in explanations
            """

# Global instance
language_detector = LanguageDetector()