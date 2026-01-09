"""
LLM Validator - Validación Dual en Dos Fases
Fase 1: Análisis independiente por cada IA
Fase 2: Revisión cruzada y reprocesamiento
"""
import json
from typing import Dict, Optional, Any
from dataclasses import dataclass, field

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


@dataclass
class DualValidationResult:
    """Resultado de validación dual"""
    phase1_claude: Optional[Dict] = None
    phase1_gpt: Optional[Dict] = None
    phase2_claude_review: Optional[Dict] = None
    phase2_gpt_review: Optional[Dict] = None
    consolidated: Dict = field(default_factory=dict)
    sources_used: list = field(default_factory=list)
    confidence: float = 0.0
    dual_validation: bool = False
    consensus_points: list = field(default_factory=list)
    divergence_points: list = field(default_factory=list)


class LLMValidator:
    """
    Validador dual con revisión en DOS FASES:
    
    FASE 1 - Análisis Independiente:
    - Claude analiza los datos
    - GPT analiza los datos (en paralelo conceptualmente)
    
    FASE 2 - Revisión Cruzada y Reprocesamiento:
    - Claude revisa el resultado de GPT y genera análisis consolidado
    - GPT revisa el resultado de Claude y genera análisis consolidado
    - Se fusionan ambas revisiones para el resultado final
    """
    
    def __init__(self, anthropic_key: str = None, openai_key: str = None):
        self.anthropic_key = anthropic_key
        self.openai_key = openai_key
        self.anthropic_client = None
        self.openai_client = None
        
        if anthropic_key and HAS_ANTHROPIC:
            try:
                self.anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
            except Exception as e:
                print(f"Error Anthropic: {e}")
        
        if openai_key and HAS_OPENAI:
            try:
                self.openai_client = openai.OpenAI(api_key=openai_key)
            except Exception as e:
                print(f"Error OpenAI: {e}")
    
    def is_configured(self) -> bool:
        return self.anthropic_client is not None or self.openai_client is not None
    
    def get_status(self) -> Dict:
        return {
            "anthropic_configured": self.anthropic_client is not None,
            "openai_configured": self.openai_client is not None,
            "dual_validation_available": self.anthropic_client is not None and self.openai_client is not None
        }
    
    def _phase1_prompt(self, data: Dict, analysis_type: str) -> str:
        """Prompt para Fase 1: Análisis inicial independiente"""
        return f"""Eres un experto en SEO y arquitectura de ecommerce.

ANÁLISIS REQUERIDO: {analysis_type}

DATOS A ANALIZAR:
{json.dumps(data, indent=2, ensure_ascii=False)[:4000]}

TAREAS:
1. Validar el orden de prioridad de facetas propuesto
2. Identificar oportunidades SEO no explotadas
3. Detectar riesgos en la arquitectura
4. Generar recomendaciones priorizadas (HIGH/MEDIUM/LOW)

RESPONDE ÚNICAMENTE EN JSON VÁLIDO con esta estructura exacta:
{{
    "validated_order": ["faceta1", "faceta2", "faceta3"],
    "opportunities": [
        {{"title": "título", "description": "descripción", "priority": "HIGH"}}
    ],
    "recommendations": [
        {{"action": "acción concreta", "reason": "razón", "impact": "HIGH"}}
    ],
    "risks": ["riesgo1", "riesgo2"],
    "architecture_score": 0-100,
    "confidence": 0.0-1.0
}}"""
    
    def _phase2_prompt(self, original_data: Dict, my_analysis: Dict, other_analysis: Dict, other_name: str) -> str:
        """Prompt para Fase 2: Revisión cruzada y reprocesamiento"""
        return f"""FASE 2: REVISIÓN CRUZADA Y REPROCESAMIENTO

Tu análisis previo (Fase 1):
{json.dumps(my_analysis, indent=2, ensure_ascii=False)[:2000]}

Análisis de {other_name} (Fase 1):
{json.dumps(other_analysis, indent=2, ensure_ascii=False)[:2000]}

Datos originales (referencia):
{json.dumps({k: v for k, v in original_data.items() if k in ['facet_order', 'metrics', 'summary']}, ensure_ascii=False)[:1000]}

TAREAS DE REVISIÓN:
1. Comparar ambos análisis e identificar puntos de ACUERDO
2. Identificar puntos de DESACUERDO y razonar cuál es correcto
3. Generar un análisis CONSOLIDADO final mejorado
4. Ajustar recomendaciones basándote en ambas perspectivas

RESPONDE ÚNICAMENTE EN JSON VÁLIDO:
{{
    "agreements": ["punto de acuerdo 1", "punto de acuerdo 2"],
    "disagreements": [
        {{"point": "punto", "my_view": "mi opinión", "other_view": "opinión del otro", "resolution": "resolución"}}
    ],
    "final_order": ["faceta1", "faceta2", "faceta3"],
    "final_recommendations": [
        {{"action": "acción", "priority": "HIGH/MEDIUM/LOW", "consensus": true}}
    ],
    "revised_score": 0-100,
    "final_confidence": 0.0-1.0,
    "improvements_made": ["mejora1", "mejora2"]
}}"""
    
    def _call_claude(self, prompt: str) -> Optional[Dict]:
        """Ejecuta llamada a Claude API"""
        if not self.anthropic_client:
            return None
        try:
            message = self.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2500,
                messages=[{"role": "user", "content": prompt}]
            )
            text = message.content[0].text
            import re
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                return json.loads(match.group())
            return {"raw_response": text[:500], "parse_error": True}
        except Exception as e:
            return {"error": str(e)}
    
    def _call_gpt(self, prompt: str) -> Optional[Dict]:
        """Ejecuta llamada a GPT API"""
        if not self.openai_client:
            return None
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Eres experto en SEO y ecommerce. Responde SOLO en JSON válido, sin texto adicional."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2500,
                response_format={"type": "json_object"}
            )
            text = response.choices[0].message.content
            return json.loads(text)
        except Exception as e:
            return {"error": str(e)}
    
    def dual_validate(self, data: Dict, analysis_type: str = "facet_priority") -> Dict:
        """
        Ejecuta validación dual completa en DOS FASES:
        
        FASE 1: Análisis independiente
        FASE 2: Revisión cruzada y reprocesamiento
        
        Returns: Dict con resultados de ambas fases y análisis consolidado
        """
        result = DualValidationResult()
        
        # ══════════════════════════════════════════════════════════════════════
        # FASE 1: ANÁLISIS INDEPENDIENTE
        # ══════════════════════════════════════════════════════════════════════
        prompt_p1 = self._phase1_prompt(data, analysis_type)
        
        # Claude Fase 1
        claude_p1 = self._call_claude(prompt_p1)
        if claude_p1 and "error" not in claude_p1:
            result.phase1_claude = claude_p1
            result.sources_used.append("Claude")
        
        # GPT Fase 1
        gpt_p1 = self._call_gpt(prompt_p1)
        if gpt_p1 and "error" not in gpt_p1:
            result.phase1_gpt = gpt_p1
            result.sources_used.append("GPT")
        
        # Si no hay ninguna fuente, retornar error
        if not result.sources_used:
            return {
                "error": "No API keys configured or all requests failed",
                "sources_used": [],
                "confidence": 0.0,
                "dual_validation": False
            }
        
        # Si solo hay una fuente, usar esa sin fase 2
        if len(result.sources_used) == 1:
            single_result = result.phase1_claude or result.phase1_gpt
            return {
                "phase1": {"single_source": single_result},
                "phase2": None,
                "consolidated": single_result,
                "sources_used": result.sources_used,
                "confidence": single_result.get("confidence", 0.7),
                "dual_validation": False,
                "note": "Solo una IA disponible - sin revisión cruzada"
            }
        
        # ══════════════════════════════════════════════════════════════════════
        # FASE 2: REVISIÓN CRUZADA Y REPROCESAMIENTO
        # ══════════════════════════════════════════════════════════════════════
        result.dual_validation = True
        
        # Claude revisa el análisis de GPT
        prompt_claude_p2 = self._phase2_prompt(data, result.phase1_claude, result.phase1_gpt, "GPT")
        claude_p2 = self._call_claude(prompt_claude_p2)
        if claude_p2 and "error" not in claude_p2:
            result.phase2_claude_review = claude_p2
        
        # GPT revisa el análisis de Claude
        prompt_gpt_p2 = self._phase2_prompt(data, result.phase1_gpt, result.phase1_claude, "Claude")
        gpt_p2 = self._call_gpt(prompt_gpt_p2)
        if gpt_p2 and "error" not in gpt_p2:
            result.phase2_gpt_review = gpt_p2
        
        # ══════════════════════════════════════════════════════════════════════
        # CONSOLIDACIÓN FINAL
        # ══════════════════════════════════════════════════════════════════════
        result.consolidated = self._consolidate_phase2(result)
        
        # Calcular confianza basada en consenso
        result.confidence = self._calculate_confidence(result)
        
        # Extraer puntos de consenso y divergencia
        if result.phase2_claude_review:
            result.consensus_points = result.phase2_claude_review.get("agreements", [])
            result.divergence_points = [d.get("point", "") for d in result.phase2_claude_review.get("disagreements", [])]
        
        return {
            "phase1": {
                "claude": result.phase1_claude,
                "gpt": result.phase1_gpt
            },
            "phase2": {
                "claude_review": result.phase2_claude_review,
                "gpt_review": result.phase2_gpt_review
            },
            "consolidated": result.consolidated,
            "sources_used": result.sources_used,
            "confidence": result.confidence,
            "dual_validation": result.dual_validation,
            "consensus_points": result.consensus_points,
            "divergence_points": result.divergence_points
        }
    
    def _consolidate_phase2(self, result: DualValidationResult) -> Dict:
        """Consolida los resultados de Fase 2 de ambas IAs"""
        consolidated = {
            "validated_order": [],
            "recommendations": [],
            "architecture_score": 0,
            "improvements": []
        }
        
        p2_claude = result.phase2_claude_review or {}
        p2_gpt = result.phase2_gpt_review or {}
        
        # Orden de facetas: preferir el que tenga consenso
        if p2_claude.get("final_order"):
            consolidated["validated_order"] = p2_claude["final_order"]
        elif p2_gpt.get("final_order"):
            consolidated["validated_order"] = p2_gpt["final_order"]
        elif result.phase1_claude and result.phase1_claude.get("validated_order"):
            consolidated["validated_order"] = result.phase1_claude["validated_order"]
        
        # Combinar recomendaciones con consenso
        all_recs = []
        seen_actions = set()
        
        for source in [p2_claude, p2_gpt]:
            for rec in source.get("final_recommendations", []):
                action_key = rec.get("action", "")[:40].lower()
                if action_key not in seen_actions:
                    rec["has_consensus"] = rec.get("consensus", False)
                    all_recs.append(rec)
                    seen_actions.add(action_key)
        
        # Ordenar por prioridad
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        all_recs.sort(key=lambda x: priority_order.get(x.get("priority", "LOW"), 2))
        consolidated["recommendations"] = all_recs[:10]
        
        # Score promedio
        scores = []
        if p2_claude.get("revised_score"):
            scores.append(p2_claude["revised_score"])
        if p2_gpt.get("revised_score"):
            scores.append(p2_gpt["revised_score"])
        if scores:
            consolidated["architecture_score"] = sum(scores) / len(scores)
        
        # Mejoras aplicadas
        improvements = set()
        for source in [p2_claude, p2_gpt]:
            for imp in source.get("improvements_made", []):
                improvements.add(imp)
        consolidated["improvements"] = list(improvements)[:5]
        
        return consolidated
    
    def _calculate_confidence(self, result: DualValidationResult) -> float:
        """Calcula confianza basada en consenso entre IAs"""
        base_confidence = 0.5
        
        # Bonus por tener ambas fases
        if result.phase2_claude_review and result.phase2_gpt_review:
            base_confidence += 0.2
        
        # Bonus por consenso
        if result.phase2_claude_review:
            agreements = len(result.phase2_claude_review.get("agreements", []))
            disagreements = len(result.phase2_claude_review.get("disagreements", []))
            if agreements > disagreements:
                base_confidence += 0.15
            elif agreements == disagreements:
                base_confidence += 0.05
        
        # Usar confianza reportada por las IAs
        confidences = []
        if result.phase2_claude_review and result.phase2_claude_review.get("final_confidence"):
            confidences.append(result.phase2_claude_review["final_confidence"])
        if result.phase2_gpt_review and result.phase2_gpt_review.get("final_confidence"):
            confidences.append(result.phase2_gpt_review["final_confidence"])
        
        if confidences:
            base_confidence = (base_confidence + sum(confidences) / len(confidences)) / 2
        
        return min(0.95, base_confidence)
    
    def validate_facet_priority(self, facet_data: Dict) -> Dict:
        """Valida prioridad de facetas con revisión dual"""
        return self.dual_validate(facet_data, "facet_priority")
    
    def validate_architecture(self, arch_data: Dict) -> Dict:
        """Valida arquitectura de URLs con revisión dual"""
        return self.dual_validate(arch_data, "url_architecture")
