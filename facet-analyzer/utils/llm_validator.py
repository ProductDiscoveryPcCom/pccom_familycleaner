"""
LLM Validator Module - CORREGIDO
Validación dual con contexto específico de arquitectura de facetas
"""
import json
from typing import Dict, List, Optional

# Imports condicionales para manejar cuando no hay API keys
try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import openai
except ImportError:
    openai = None


# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXTO EXPERTO PARA LOS PROMPTS
# ═══════════════════════════════════════════════════════════════════════════════

EXPERT_CONTEXT = """
Eres un experto en SEO técnico y arquitectura de información para ecommerce.
Estás analizando la estructura de facetas de navegación de PcComponentes.

═══════════════════════════════════════════════════════════════════════════════
ARQUITECTURA DE FACETAS - REGLAS FUNDAMENTALES
═══════════════════════════════════════════════════════════════════════════════

ESTRUCTURA DE URLs:
- FILTROS: /categoria/{faceta1}/{faceta2} → Capturan tráfico TRANSACCIONAL
- ARTÍCULOS: /{slug-descriptivo} → Capturan tráfico INFORMACIONAL
- Los artículos NUNCA están dentro de /categoria/

ORDEN DE FACETAS EN URL (por importancia de uso interno):
1. Tamaño (40.7% del uso) → /televisores/55-pulgadas
2. Marca (20.3%) → /televisores/55-pulgadas/samsung  
3. Tecnología (4.3%) → /televisores/55-pulgadas/oled
* El precio (18.9%) NO genera URL, se maneja con AJAX

REGLAS DE INDEXACIÓN:
┌─────────────────────┬──────────┬────────────────────────────────────┐
│ Tipo                │ Indexar  │ Condición                          │
├─────────────────────┼──────────┼────────────────────────────────────┤
│ /categoria          │ ✅ SÍ    │ Siempre, con contenido             │
│ N1 (1 faceta)       │ ✅ SÍ    │ Siempre, con contenido             │
│ N2 (2 facetas)      │ ⚠️ SEGÚN │ Si demanda >200 ó clicks >500      │
│ N3+ (3+ facetas)    │ ❌ NO    │ Canonical al padre N2              │
│ ?order=*            │ ❌ NO    │ Canonical sin parámetro            │
│ ?page=*             │ ❌ NO    │ Canonical a página 1               │
│ precio=*            │ ❌ NO    │ No genera URL, usar AJAX           │
└─────────────────────┴──────────┴────────────────────────────────────┘

CANIBALIZACIÓN:
- Ocurre cuando un ARTÍCULO rankea para una query TRANSACCIONAL
- Query TRANSACCIONAL: Sin modificadores ("tv 55 pulgadas", "televisor samsung")
- Query INFORMACIONAL: Con modificadores ("mejor tv 55", "qled vs oled", "guía compra")

MODIFICADORES INFORMACIONALES:
mejor/mejores, guía, cómo, diferencia, vs, comparar, elegir, qué, cuál, 
para qué, medidas, opiniones, review, top, ranking, 2024, 2025

SOLUCIÓN A CANIBALIZACIÓN:
1. Crear el filtro que falta
2. Enlazar desde el artículo al filtro
3. Revisar TITLE del artículo (debe tener modificador informacional)

═══════════════════════════════════════════════════════════════════════════════
"""


class LLMValidator:
    """Validador dual usando Claude y GPT"""
    
    def __init__(self, anthropic_key: str = None, openai_key: str = None):
        self.anthropic_key = anthropic_key
        self.openai_key = openai_key
        self.claude_client = None
        self.openai_client = None
        
        if anthropic_key and anthropic:
            self.claude_client = anthropic.Anthropic(api_key=anthropic_key)
        if openai_key and openai:
            self.openai_client = openai.OpenAI(api_key=openai_key)
    
    def _build_prompt(self, analysis_data: Dict, analysis_type: str) -> str:
        """Construye prompt con contexto experto"""
        
        if analysis_type == "cannibalization":
            task = """
TAREA: Validar casos de canibalización detectados

Para cada caso:
1. ¿Es realmente una query TRANSACCIONAL? (sin modificadores informacionales)
2. ¿El artículo está "robando" tráfico que debería ir a un filtro?
3. ¿Qué filtro específico debería crearse?
4. ¿Qué prioridad tiene (HIGH/MEDIUM/LOW)?

DATOS:
""" + json.dumps(analysis_data, indent=2, ensure_ascii=False) + """

Responde en JSON:
{
    "validation_summary": "resumen en español",
    "validated_cases": [
        {
            "query": "la query",
            "is_cannibalization": true/false,
            "confidence": 0-100,
            "reasoning": "explicación",
            "correct_filter": "/televisores/...",
            "priority": "HIGH/MEDIUM/LOW"
        }
    ],
    "total_real_cannibalization": número,
    "estimated_recoverable_clicks": número
}
"""
        
        elif analysis_type == "gaps":
            task = """
TAREA: Validar gaps de demanda detectados

Para cada gap:
1. ¿Es una keyword con intención transaccional clara?
2. ¿Tiene sentido crear un filtro dedicado?
3. ¿Cuál sería la URL exacta siguiendo la arquitectura?
4. ¿Qué prioridad tiene?

DATOS:
""" + json.dumps(analysis_data, indent=2, ensure_ascii=False) + """

Responde en JSON:
{
    "validation_summary": "resumen en español",
    "validated_gaps": [
        {
            "keyword": "la keyword",
            "needs_filter": true/false,
            "confidence": 0-100,
            "reasoning": "explicación",
            "suggested_url": "/televisores/...",
            "priority": "HIGH/MEDIUM/LOW"
        }
    ],
    "total_valid_gaps": número,
    "estimated_opportunity_volume": número
}
"""
        
        elif analysis_type == "architecture":
            task = """
TAREA: Evaluar arquitectura de facetas

Analiza:
1. ¿El orden de facetas es óptimo para UX?
2. ¿Las reglas de indexación son correctas?
3. ¿Hay problemas de canibalización sistémicos?
4. ¿Qué acciones prioritarias recomiendas?

DATOS:
""" + json.dumps(analysis_data, indent=2, ensure_ascii=False) + """

Responde en JSON:
{
    "architecture_score": 0-100,
    "ux_score": 0-100,
    "seo_score": 0-100,
    "main_issues": ["issue 1", "issue 2"],
    "priority_actions": [
        {
            "action": "descripción",
            "impact": "HIGH/MEDIUM/LOW",
            "effort": "HIGH/MEDIUM/LOW"
        }
    ],
    "overall_assessment": "evaluación general en español"
}
"""
        
        elif analysis_type == "ux_seo_matrix":
            task = """
TAREA: Analizar matriz UX vs SEO

Interpreta el cruce de datos:
- UX: Cómo navegan los usuarios internamente
- SEO: Cómo llegan desde buscadores

Identifica:
1. Facetas con alta navegación interna pero baja visibilidad SEO (oportunidad)
2. Facetas con alta SEO pero baja navegación (revisar UX)
3. Desalineaciones críticas

DATOS:
""" + json.dumps(analysis_data, indent=2, ensure_ascii=False) + """

Responde en JSON:
{
    "analysis_summary": "resumen en español",
    "critical_gaps": [
        {
            "facet": "nombre",
            "issue": "descripción del problema",
            "recommendation": "qué hacer"
        }
    ],
    "alignment_score": 0-100,
    "key_insights": ["insight 1", "insight 2"]
}
"""
        
        else:
            task = f"""
TAREA: Análisis general

DATOS:
{json.dumps(analysis_data, indent=2, ensure_ascii=False)}

Proporciona insights relevantes para optimizar la arquitectura de facetas.
Responde en JSON con tus hallazgos.
"""
        
        return EXPERT_CONTEXT + task
    
    def validate_with_claude(self, analysis_data: Dict, analysis_type: str) -> Optional[Dict]:
        """Validar con Claude"""
        if not self.claude_client:
            return {"error": "Claude API no configurada"}
        
        prompt = self._build_prompt(analysis_data, analysis_type)
        
        try:
            message = self.claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text
            
            # Extraer JSON
            try:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start != -1 and end > start:
                    return json.loads(response_text[start:end])
            except json.JSONDecodeError:
                pass
            
            return {"raw_response": response_text}
            
        except Exception as e:
            return {"error": str(e)}
    
    def validate_with_gpt(self, analysis_data: Dict, analysis_type: str) -> Optional[Dict]:
        """Validar con GPT-4"""
        if not self.openai_client:
            return {"error": "OpenAI API no configurada"}
        
        prompt = self._build_prompt(analysis_data, analysis_type)
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "Eres un experto en SEO técnico. Responde siempre en JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4096,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            return {"error": str(e)}
    
    def dual_validate(self, analysis_data: Dict, analysis_type: str) -> Dict:
        """
        Validación con doble pasada crítica:
        1. Primer análisis (IA principal)
        2. Crítica del análisis (IA secundaria o misma IA)
        3. Refinamiento final
        """
        results = {
            "pass_1_analysis": None,
            "pass_2_critique": None,
            "final_refined": None,
            "confidence": "LOW",
            "methodology": "dual_pass_critique"
        }
        
        # ═══════════════════════════════════════════════════════════════════
        # PASADA 1: Análisis inicial
        # ═══════════════════════════════════════════════════════════════════
        primary_client = "claude" if self.claude_client else ("gpt" if self.openai_client else None)
        
        if not primary_client:
            return {"error": "No hay API keys configuradas"}
        
        if primary_client == "claude":
            results["pass_1_analysis"] = self.validate_with_claude(analysis_data, analysis_type)
        else:
            results["pass_1_analysis"] = self.validate_with_gpt(analysis_data, analysis_type)
        
        if not results["pass_1_analysis"] or "error" in results["pass_1_analysis"]:
            return results
        
        # ═══════════════════════════════════════════════════════════════════
        # PASADA 2: Crítica del análisis
        # ═══════════════════════════════════════════════════════════════════
        critique_client = "gpt" if self.openai_client and primary_client == "claude" else "claude" if self.claude_client else primary_client
        
        critique_result = self._request_critique(
            original_data=analysis_data,
            first_analysis=results["pass_1_analysis"],
            analysis_type=analysis_type,
            use_client=critique_client
        )
        
        results["pass_2_critique"] = critique_result
        
        if not critique_result or "error" in critique_result:
            # Si falla la crítica, el primer análisis es el final
            results["final_refined"] = results["pass_1_analysis"]
            results["confidence"] = "MEDIUM"
            return results
        
        # ═══════════════════════════════════════════════════════════════════
        # PASADA 3: Refinamiento final
        # ═══════════════════════════════════════════════════════════════════
        refined = self._apply_refinement(
            original_analysis=results["pass_1_analysis"],
            critique=results["pass_2_critique"],
            analysis_type=analysis_type
        )
        
        results["final_refined"] = refined
        results["confidence"] = "HIGH"
        
        return results
    
    def _build_critique_prompt(self, original_data: Dict, first_analysis: Dict, 
                                analysis_type: str) -> str:
        """Construye prompt para la crítica del primer análisis"""
        
        return f"""
{EXPERT_CONTEXT}

═══════════════════════════════════════════════════════════════════════════════
TAREA: CRÍTICA Y REFINAMIENTO DE ANÁLISIS
═══════════════════════════════════════════════════════════════════════════════

Se ha realizado un primer análisis que necesita ser revisado críticamente.
Tu rol es actuar como un SEGUNDO ANALISTA que:

1. VERIFICA la lógica del primer análisis
2. IDENTIFICA errores, omisiones o conclusiones precipitadas
3. CUESTIONA las asunciones
4. PROPONE correcciones específicas

DATOS ORIGINALES:
{json.dumps(original_data, indent=2, ensure_ascii=False)[:3000]}

PRIMER ANÁLISIS A REVISAR:
{json.dumps(first_analysis, indent=2, ensure_ascii=False)}

═══════════════════════════════════════════════════════════════════════════════
INSTRUCCIONES DE CRÍTICA
═══════════════════════════════════════════════════════════════════════════════

Para cada conclusión del primer análisis, evalúa:

1. ¿Es CORRECTA según las reglas de arquitectura de facetas?
   - Orden de facetas: Tamaño > Tecnología > Marca
   - N2 indexar solo si demanda >200 ó clicks >500
   - Precio NUNCA genera URL
   
2. ¿La clasificación de intención es PRECISA?
   - TRANSACCIONAL: Sin modificadores ("tv 55 pulgadas")
   - INFORMACIONAL: Con modificadores ("mejor tv 55", "vs", "guía")

3. ¿Hay FALSOS POSITIVOS en canibalización?
   - ¿La query realmente es transaccional?
   - ¿El filtro sugerido tiene sentido?

4. ¿Hay OMISIONES importantes?
   - ¿Se detectaron todos los casos relevantes?
   - ¿Falta alguna recomendación obvia?

5. ¿Las PRIORIDADES son correctas?
   - ¿El orden de importancia es adecuado?
   - ¿El impacto estimado es realista?

Responde en JSON:
{{
    "critique_summary": "Resumen de la crítica en español",
    "errors_found": [
        {{
            "issue": "descripción del error",
            "location": "dónde está el error",
            "correction": "corrección propuesta"
        }}
    ],
    "false_positives": [
        {{
            "item": "elemento incorrecto",
            "reason": "por qué es falso positivo"
        }}
    ],
    "omissions": [
        {{
            "missing": "qué falta",
            "importance": "HIGH/MEDIUM/LOW"
        }}
    ],
    "priority_adjustments": [
        {{
            "item": "elemento",
            "current_priority": "actual",
            "suggested_priority": "sugerida",
            "reason": "razón"
        }}
    ],
    "validation_score": 0-100,
    "major_issues_count": número,
    "recommendation": "ACCEPT/REVISE/REJECT"
}}
"""
    
    def _request_critique(self, original_data: Dict, first_analysis: Dict,
                          analysis_type: str, use_client: str) -> Optional[Dict]:
        """Solicita crítica del primer análisis"""
        
        prompt = self._build_critique_prompt(original_data, first_analysis, analysis_type)
        
        try:
            if use_client == "claude" and self.claude_client:
                message = self.claude_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    messages=[{"role": "user", "content": prompt}]
                )
                response_text = message.content[0].text
            elif use_client == "gpt" and self.openai_client:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=[
                        {"role": "system", "content": "Eres un crítico experto en SEO técnico. Responde en JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=4096,
                    response_format={"type": "json_object"}
                )
                response_text = response.choices[0].message.content
            else:
                return {"error": "Cliente no disponible"}
            
            # Extraer JSON
            try:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start != -1 and end > start:
                    return json.loads(response_text[start:end])
            except json.JSONDecodeError:
                pass
            
            return {"raw_response": response_text}
            
        except Exception as e:
            return {"error": str(e)}
    
    def _apply_refinement(self, original_analysis: Dict, critique: Dict,
                          analysis_type: str) -> Dict:
        """Aplica las correcciones de la crítica al análisis original"""
        
        refined = original_analysis.copy()
        
        # Añadir metadatos de refinamiento
        refined["_refinement"] = {
            "was_refined": True,
            "critique_score": critique.get("validation_score", 0),
            "major_issues_fixed": critique.get("major_issues_count", 0),
            "recommendation": critique.get("recommendation", "UNKNOWN")
        }
        
        # Si hay errores encontrados, añadir notas
        if critique.get("errors_found"):
            refined["_corrections"] = critique["errors_found"]
        
        # Si hay falsos positivos, marcarlos
        if critique.get("false_positives") and "validated_cases" in refined:
            fp_items = {fp.get("item") for fp in critique["false_positives"]}
            for case in refined.get("validated_cases", []):
                if case.get("query") in fp_items:
                    case["flagged_as_false_positive"] = True
                    case["validation_confidence"] = "LOW"
        
        # Ajustar prioridades si se sugieren
        if critique.get("priority_adjustments"):
            refined["_priority_adjustments"] = critique["priority_adjustments"]
        
        # Añadir omisiones detectadas
        if critique.get("omissions"):
            refined["_omissions_to_review"] = critique["omissions"]
        
        # Resumen de la crítica
        refined["_critique_summary"] = critique.get("critique_summary", "")
        
        return refined
    
    def _reconcile(self, claude: Dict, gpt: Dict, analysis_type: str) -> Dict:
        """Reconcilia diferencias entre análisis"""
        consensus = {
            "source": "dual_validation",
            "agreement_level": "full" if self._check_agreement(claude, gpt) else "partial"
        }
        
        if analysis_type == "cannibalization":
            # Merge validated cases, tomar el más conservador
            claude_cases = {c.get('query'): c for c in claude.get('validated_cases', [])}
            gpt_cases = {c.get('query'): c for c in gpt.get('validated_cases', [])}
            
            merged = []
            all_queries = set(claude_cases.keys()) | set(gpt_cases.keys())
            
            for query in all_queries:
                c_case = claude_cases.get(query, {})
                g_case = gpt_cases.get(query, {})
                
                # Si ambos coinciden, alta confianza
                if c_case.get('is_cannibalization') == g_case.get('is_cannibalization'):
                    merged.append({
                        **c_case,
                        "validation_confidence": "HIGH"
                    })
                else:
                    # Ser conservador: si uno dice que sí, investigar
                    merged.append({
                        **(c_case if c_case.get('is_cannibalization') else g_case),
                        "validation_confidence": "MEDIUM",
                        "needs_review": True
                    })
            
            consensus["validated_cases"] = merged
        
        # Copiar sumarios
        for key in ['validation_summary', 'analysis_summary', 'overall_assessment']:
            if key in claude:
                consensus[f"claude_{key}"] = claude[key]
            if key in gpt:
                consensus[f"gpt_{key}"] = gpt[key]
        
        return consensus
    
    def _check_agreement(self, claude: Dict, gpt: Dict) -> bool:
        """Verifica si ambos análisis están de acuerdo en lo esencial"""
        # Comparar scores si existen
        for score_key in ['architecture_score', 'alignment_score', 'total_real_cannibalization']:
            c_score = claude.get(score_key)
            g_score = gpt.get(score_key)
            if c_score and g_score:
                if isinstance(c_score, (int, float)) and isinstance(g_score, (int, float)):
                    if abs(c_score - g_score) > 20:  # Diferencia > 20 puntos = desacuerdo
                        return False
        
        return True
