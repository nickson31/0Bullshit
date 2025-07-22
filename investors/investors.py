import os
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
import logging
from datetime import datetime

from database.database import db
from models.schemas import InvestorResult, ProjectData, SearchProgress

logger = logging.getLogger(__name__)

class InvestorSearchEngine:
    """
    Sistema de búsqueda de inversores según especificaciones del prompt.
    Busca tanto ángeles como fondos basándose en:
    - Categories: keywords de industria/sector
    - Stage: etapa del proyecto 
    - Score mínimo: angels ≥40.0, employees ≥5.9
    """
    
    def __init__(self):
        self.min_angel_score = 40.0
        self.min_employee_score = 5.9
        
        # Pesos para algoritmo de relevancia
        self.category_weight = 0.4
        self.stage_weight = 0.6
        
    async def search_investors(
        self, 
        project_data: ProjectData, 
        completeness_score: float,
        search_type: str = "hybrid",  # "angels", "funds", "hybrid"
        limit: int = 15,
        websocket_callback=None
    ) -> Tuple[List[InvestorResult], Dict[str, Any]]:
        """
        Búsqueda principal de inversores.
        """
        try:
            # Validar completitud mínima (50%)
            if completeness_score < 50.0:
                raise ValueError("Project completeness must be at least 50% to search investors")
            
            if websocket_callback:
                await websocket_callback({
                    "type": "search_progress",
                    "data": {
                        "status": "starting",
                        "message": "🔍 Iniciando búsqueda de inversores...",
                        "progress_percentage": 0
                    }
                })
            
            start_time = datetime.now()
            
            # Extraer keywords de búsqueda
            search_keywords = self._extract_search_keywords(project_data)
            
            if websocket_callback:
                await websocket_callback({
                    "type": "search_progress", 
                    "data": {
                        "status": "searching",
                        "message": f"🎯 Buscando especialistas en {', '.join(search_keywords['categories'][:3])}...",
                        "progress_percentage": 20
                    }
                })
            
            # Ejecutar búsquedas según tipo
            results = []
            
            if search_type in ["angels", "hybrid"]:
                angel_results = await self._search_angels(search_keywords, limit)
                results.extend(angel_results)
                
                if websocket_callback:
                    await websocket_callback({
                        "type": "search_progress",
                        "data": {
                            "status": "searching", 
                            "message": f"👼 Encontrados {len(angel_results)} inversores ángeles...",
                            "progress_percentage": 50
                        }
                    })
            
            if search_type in ["funds", "hybrid"]:
                fund_results = await self._search_fund_employees(search_keywords, limit)
                results.extend(fund_results)
                
                if websocket_callback:
                    await websocket_callback({
                        "type": "search_progress",
                        "data": {
                            "status": "processing",
                            "message": f"🏢 Encontrados {len(fund_results)} empleados de fondos...",
                            "progress_percentage": 80
                        }
                    })
            
            # Combinar y ordenar resultados
            combined_results = self._combine_and_rank_results(
                results, 
                search_keywords, 
                project_data.stage,
                search_type
            )
            
            # Limitar resultados finales
            final_results = combined_results[:limit]
            
            end_time = datetime.now()
            query_time = (end_time - start_time).total_seconds() * 1000
            
            if websocket_callback:
                await websocket_callback({
                    "type": "search_progress",
                    "data": {
                        "status": "completed",
                        "message": f"✅ Búsqueda completada: {len(final_results)} inversores encontrados",
                        "progress_percentage": 100
                    }
                })
            
            # Metadata de la búsqueda
            search_metadata = {
                "query_time_ms": int(query_time),
                "total_found": len(combined_results),
                "angels_found": len([r for r in results if r.get("type") == "angel"]),
                "fund_employees_found": len([r for r in results if r.get("type") == "fund_employee"]),
                "search_quality": self._calculate_search_quality(final_results),
                "completeness_score": completeness_score,
                "search_keywords": search_keywords
            }
            
            logger.info(f"Investor search completed: {len(final_results)} results in {query_time:.0f}ms")
            
            return final_results, search_metadata
            
        except Exception as e:
            logger.error(f"Investor search error: {e}")
            if websocket_callback:
                await websocket_callback({
                    "type": "search_progress",
                    "data": {
                        "status": "error",
                        "message": f"❌ Error en búsqueda: {str(e)}",
                        "progress_percentage": 100
                    }
                })
            raise
    
    async def _search_angels(self, search_keywords: Dict[str, List[str]], limit: int) -> List[Dict[str, Any]]:
        """
        Buscar inversores ángeles según criterios.
        """
        try:
            # Construir query SQL para ángeles
            category_keywords = search_keywords["categories"]
            stage_keywords = search_keywords["stages"]
            
            # Query base con score mínimo
            base_query = """
            SELECT *,
                   (
                       -- Score por categorías (40%)
                       COALESCE(
                           (
                               SELECT COUNT(*)::float / GREATEST(1, array_length(string_to_array($1, ','), 1))
                               FROM unnest(string_to_array(
                                   COALESCE(categories_general_en, '') || ',' || 
                                   COALESCE(categories_general_es, '') || ',' ||
                                   COALESCE(categories_strong_en, '') || ',' ||
                                   COALESCE(categories_strong_es, ''), ','
                               )) AS angel_keyword
                               WHERE LOWER(angel_keyword) = ANY(string_to_array(LOWER($1), ','))
                           ), 0
                       ) * 0.4 +
                       
                       -- Score por etapa (60%)
                       COALESCE(
                           (
                               SELECT COUNT(*)::float / GREATEST(1, array_length(string_to_array($2, ','), 1))
                               FROM unnest(string_to_array(
                                   COALESCE(stage_general_en, '') || ',' || 
                                   COALESCE(stage_general_es, '') || ',' ||
                                   COALESCE(stage_strong_en, '') || ',' ||
                                   COALESCE(stage_strong_es, ''), ','
                               )) AS stage_keyword
                               WHERE LOWER(stage_keyword) = ANY(string_to_array(LOWER($2), ','))
                           ), 0
                       ) * 0.6
                   ) as relevance_score
            FROM angel_investors
            WHERE angel_score >= $3
              AND (
                  LOWER(categories_general_en) ~ ANY(string_to_array(LOWER($1), ',')) OR
                  LOWER(categories_general_es) ~ ANY(string_to_array(LOWER($1), ',')) OR
                  LOWER(categories_strong_en) ~ ANY(string_to_array(LOWER($1), ',')) OR
                  LOWER(categories_strong_es) ~ ANY(string_to_array(LOWER($1), ','))
              )
            ORDER BY relevance_score DESC, angel_score DESC
            LIMIT $4
            """
            
            # Ejecutar query
            category_str = ','.join(category_keywords)
            stage_str = ','.join(stage_keywords) if stage_keywords else ''
            
            result = db.supabase.rpc(
                'search_angels_by_keywords',
                {
                    'category_keywords': category_str,
                    'stage_keywords': stage_str,
                    'min_score': self.min_angel_score,
                    'result_limit': limit * 2  # Buscar más para filtrar mejor
                }
            ).execute()
            
            # Si no tenemos función RPC, usar query directa
            if not result.data:
                result = db.supabase.table("angel_investors").select("*").gte("angel_score", self.min_angel_score).limit(limit * 2).execute()
            
            angels = result.data or []
            
            # Procesar resultados
            processed_angels = []
            for angel in angels:
                # Calcular relevancia manualmente si no viene del RPC
                relevance_score = self._calculate_relevance_score(
                    angel, search_keywords, "angel"
                )
                
                # Solo incluir si tiene relevancia mínima
                if relevance_score >= 0.3:
                    processed_angel = {
                        "type": "angel",
                        "id": angel.get("linkedin_url", ""),
                        "full_name": angel.get("full_name", ""),
                        "headline": angel.get("headline", ""),
                        "email": angel.get("email", ""),
                        "linkedin_url": angel.get("linkedin_url", ""),
                        "profile_pic": angel.get("profile_pic", ""),
                        "company_name": None,
                        "fund_name": None,
                        "relevance_score": relevance_score,
                        "angel_score": float(angel.get("angel_score", 0)),
                        "validation_reasons": angel.get("validation_reasons_english", ""),
                        "categories_match": self._extract_matching_categories(angel, category_keywords),
                        "stage_match": self._check_stage_match(angel, stage_keywords),
                        "address_with_country": angel.get("address_with_country", "")
                    }
                    processed_angels.append(processed_angel)
            
            # Ordenar por relevancia
            processed_angels.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            return processed_angels[:limit]
            
        except Exception as e:
            logger.error(f"Angel search error: {e}")
            return []
    
    async def _search_fund_employees(self, search_keywords: Dict[str, List[str]], limit: int) -> List[Dict[str, Any]]:
        """
        Buscar empleados de fondos de inversión.
        """
        try:
            # Primero buscar fondos relevantes
            relevant_funds = await self._find_relevant_funds(search_keywords)
            
            if not relevant_funds:
                return []
            
            fund_names = [fund["name"] for fund in relevant_funds]
            
            # Buscar empleados de estos fondos
            employees_query = db.supabase.table("employee_funds").select("*").in_("fund_name", fund_names).gte("score_combinado", self.min_employee_score).order("score_combinado", desc=True).limit(limit * 2)
            
            result = employees_query.execute()
            employees = result.data or []
            
            # Procesar resultados
            processed_employees = []
            for employee in employees:
                # Encontrar el fondo correspondiente
                employee_fund = next(
                    (fund for fund in relevant_funds if fund["name"] == employee["fund_name"]), 
                    {}
                )
                
                relevance_score = self._calculate_employee_relevance(
                    employee, employee_fund, search_keywords
                )
                
                if relevance_score >= 0.3:
                    processed_employee = {
                        "type": "fund_employee",
                        "id": employee.get("linkedin_url", ""),
                        "full_name": employee.get("full_name", ""),
                        "headline": employee.get("headline", ""),
                        "email": employee.get("email", ""),
                        "linkedin_url": employee.get("linkedin_url", ""),
                        "profile_pic": employee.get("profile_pic", ""),
                        "company_name": None,
                        "fund_name": employee.get("fund_name", ""),
                        "job_title": employee.get("job_title", ""),
                        "relevance_score": relevance_score,
                        "angel_score": None,
                        "employee_score": float(employee.get("score_combinado", 0)),
                        "validation_reasons": f"Employee at {employee.get('fund_name', '')}",
                        "categories_match": self._extract_fund_categories(employee_fund),
                        "stage_match": True,  # Los fondos generalmente invierten en múltiples etapas
                        "address_with_country": employee.get("address_with_country", ""),
                        "fund_info": {
                            "name": employee_fund.get("name", ""),
                            "description": employee_fund.get("short_description", ""),
                            "website": employee_fund.get("website/value", ""),
                            "location": self._extract_fund_location(employee_fund)
                        }
                    }
                    processed_employees.append(processed_employee)
            
            return processed_employees[:limit]
            
        except Exception as e:
            logger.error(f"Fund employee search error: {e}")
            return []
    
    async def _find_relevant_funds(self, search_keywords: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """
        Encontrar fondos relevantes basados en keywords.
        """
        try:
            # Buscar fondos que tengan keywords relevantes
            result = db.supabase.table("investment_funds").select("*").execute()
            funds = result.data or []
            
            relevant_funds = []
            category_keywords = [kw.lower() for kw in search_keywords["categories"]]
            
            for fund in funds:
                # Verificar si tiene keywords de categoría
                fund_keywords = fund.get("category_keywords", "")
                if fund_keywords and fund_keywords != "[]":
                    # Extraer keywords del string (formato: "['keyword1', 'keyword2']")
                    try:
                        import ast
                        keywords_list = ast.literal_eval(fund_keywords)
                        if isinstance(keywords_list, list):
                            fund_keywords_lower = [kw.lower() for kw in keywords_list]
                            
                            # Verificar overlap con keywords de búsqueda
                            overlap = set(category_keywords) & set(fund_keywords_lower)
                            if overlap:
                                fund["relevance_keywords"] = list(overlap)
                                relevant_funds.append(fund)
                    except:
                        # Fallback: buscar por texto simple
                        fund_keywords_text = fund_keywords.lower()
                        for keyword in category_keywords:
                            if keyword in fund_keywords_text:
                                fund["relevance_keywords"] = [keyword]
                                relevant_funds.append(fund)
                                break
            
            return relevant_funds
            
        except Exception as e:
            logger.error(f"Find relevant funds error: {e}")
            return []
    
    def _extract_search_keywords(self, project_data: ProjectData) -> Dict[str, List[str]]:
        """
        Extraer keywords de búsqueda del proyecto.
        """
        keywords = {
            "categories": [],
            "stages": []
        }
        
        # Keywords de categorías
        if project_data.categories:
            keywords["categories"].extend([cat.lower().strip() for cat in project_data.categories])
        
        # Keywords de etapa
        if project_data.stage:
            stage = project_data.stage.lower().strip()
            keywords["stages"].append(stage)
            
            # Añadir variaciones de etapa
            stage_variations = {
                "idea": ["idea", "pre-seed", "concept"],
                "pre-seed": ["pre-seed", "idea", "early"],
                "seed": ["seed", "early-stage", "startup"],
                "serie_a": ["serie a", "series a", "a round", "growth"],
                "serie_b": ["serie b", "series b", "b round", "expansion"],
                "serie_c": ["serie c", "series c", "c round", "late-stage"]
            }
            
            if stage in stage_variations:
                keywords["stages"].extend(stage_variations[stage])
        
        # Keywords adicionales de métricas y contexto
        if project_data.metrics:
            if project_data.metrics.arr:
                try:
                    arr_value = float(project_data.metrics.arr.replace("$", "").replace(",", ""))
                    if arr_value >= 1000000:  # 1M+ ARR
                        keywords["stages"].extend(["growth", "scale", "expansion"])
                    elif arr_value >= 100000:  # 100K+ ARR
                        keywords["stages"].extend(["early-growth", "traction"])
                except:
                    pass
        
        return keywords
    
    def _calculate_relevance_score(self, investor: Dict[str, Any], search_keywords: Dict[str, List[str]], investor_type: str) -> float:
        """
        Calcular score de relevancia para un inversor.
        """
        try:
            category_score = 0.0
            stage_score = 0.0
            
            category_keywords = search_keywords["categories"]
            stage_keywords = search_keywords["stages"]
            
            # Score por categorías
            if category_keywords:
                investor_categories = []
                
                if investor_type == "angel":
                    # Combinar todas las categorías del ángel
                    for field in ["categories_general_en", "categories_general_es", "categories_strong_en", "categories_strong_es"]:
                        field_value = investor.get(field, "")
                        if field_value:
                            investor_categories.extend([cat.strip().lower() for cat in field_value.split(",")])
                
                # Calcular overlap
                if investor_categories:
                    matches = set(category_keywords) & set(investor_categories)
                    category_score = len(matches) / len(category_keywords)
            
            # Score por etapa
            if stage_keywords:
                investor_stages = []
                
                if investor_type == "angel":
                    for field in ["stage_general_en", "stage_general_es", "stage_strong_en", "stage_strong_es"]:
                        field_value = investor.get(field, "")
                        if field_value:
                            investor_stages.extend([stage.strip().lower() for stage in field_value.split(",")])
                
                if investor_stages:
                    matches = set(stage_keywords) & set(investor_stages)
                    stage_score = len(matches) / len(stage_keywords)
            
            # Score final ponderado
            final_score = (category_score * self.category_weight) + (stage_score * self.stage_weight)
            
            return min(1.0, final_score)
            
        except Exception as e:
            logger.error(f"Relevance calculation error: {e}")
            return 0.0
    
    def _calculate_employee_relevance(self, employee: Dict[str, Any], fund: Dict[str, Any], search_keywords: Dict[str, List[str]]) -> float:
        """
        Calcular relevancia de empleado de fondo.
        """
        try:
            # Score base del empleado
            base_score = float(employee.get("score_combinado", 0)) / 10.0  # Normalizar a 0-1
            
            # Score del fondo (si tiene keywords relevantes)
            fund_score = 0.5  # Score base para fondos
            if fund.get("relevance_keywords"):
                fund_score = 0.8
            
            # Score final combinado
            final_score = (base_score * 0.7) + (fund_score * 0.3)
            
            return min(1.0, final_score)
            
        except Exception as e:
            logger.error(f"Employee relevance calculation error: {e}")
            return 0.0
    
    def _combine_and_rank_results(self, results: List[Dict[str, Any]], search_keywords: Dict[str, List[str]], project_stage: str, search_type: str) -> List[InvestorResult]:
        """
        Combinar y rankear resultados finales.
        """
        try:
            # Convertir a InvestorResult objects
            investor_results = []
            
            for result in results:
                investor_result = InvestorResult(
                    id=UUID(result.get("id", str(uuid4()))),
                    full_name=result.get("full_name", ""),
                    headline=result.get("headline"),
                    email=result.get("email"),
                    linkedin_url=result.get("linkedin_url"),
                    company_name=result.get("company_name"),
                    fund_name=result.get("fund_name"),
                    relevance_score=result.get("relevance_score", 0.0),
                    categories_match=result.get("categories_match", []),
                    stage_match=result.get("stage_match", False)
                )
                investor_results.append(investor_result)
            
            # Ordenar por relevancia y después por score específico
            investor_results.sort(
                key=lambda x: (
                    x.relevance_score,
                    # Preferir ángeles para etapas tempranas, fondos para tardías
                    1.0 if self._should_prefer_angels(project_stage) and "angel" in str(x.id) else 0.5
                ),
                reverse=True
            )
            
            return investor_results
            
        except Exception as e:
            logger.error(f"Results combination error: {e}")
            return []
    
    def _should_prefer_angels(self, project_stage: str) -> bool:
        """
        Determinar si debe preferir ángeles según etapa del proyecto.
        """
        if not project_stage:
            return True
        
        early_stages = ["idea", "pre-seed", "seed", "mvp", "prototype"]
        return project_stage.lower() in early_stages
    
    def _extract_matching_categories(self, investor: Dict[str, Any], category_keywords: List[str]) -> List[str]:
        """
        Extraer categorías que coinciden.
        """
        matches = []
        
        for field in ["categories_general_en", "categories_general_es", "categories_strong_en", "categories_strong_es"]:
            field_value = investor.get(field, "")
            if field_value:
                investor_categories = [cat.strip().lower() for cat in field_value.split(",")]
                for keyword in category_keywords:
                    if keyword.lower() in investor_categories:
                        matches.append(keyword)
        
        return list(set(matches))  # Remove duplicates
    
    def _check_stage_match(self, investor: Dict[str, Any], stage_keywords: List[str]) -> bool:
        """
        Verificar si hay match de etapa.
        """
        if not stage_keywords:
            return False
        
        for field in ["stage_general_en", "stage_general_es", "stage_strong_en", "stage_strong_es"]:
            field_value = investor.get(field, "")
            if field_value:
                investor_stages = [stage.strip().lower() for stage in field_value.split(",")]
                for keyword in stage_keywords:
                    if keyword.lower() in investor_stages:
                        return True
        
        return False
    
    def _extract_fund_categories(self, fund: Dict[str, Any]) -> List[str]:
        """
        Extraer categorías del fondo.
        """
        categories = []
        
        relevance_keywords = fund.get("relevance_keywords", [])
        if relevance_keywords:
            categories.extend(relevance_keywords)
        
        return categories
    
    def _extract_fund_location(self, fund: Dict[str, Any]) -> str:
        """
        Extraer ubicación del fondo.
        """
        location_parts = []
        
        for i in range(3):  # Hasta 3 niveles de ubicación
            location_key = f"location_identifiers/{i}/value"
            location_value = fund.get(location_key)
            if location_value:
                location_parts.append(location_value)
        
        return ", ".join(location_parts) if location_parts else ""
    
    def _calculate_search_quality(self, results: List[InvestorResult]) -> str:
        """
        Calcular calidad de la búsqueda.
        """
        if not results:
            return "poor"
        
        avg_relevance = sum(r.relevance_score for r in results) / len(results)
        
        if avg_relevance >= 0.8:
            return "excellent"
        elif avg_relevance >= 0.6:
            return "good"
        elif avg_relevance >= 0.4:
            return "fair"
        else:
            return "poor"

# Instancia global del motor de búsqueda
investor_search_engine = InvestorSearchEngine()
