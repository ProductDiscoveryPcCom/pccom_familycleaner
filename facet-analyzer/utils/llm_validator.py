"""
LLM Validator Module - Stub
"""
import json
from typing import Dict, Optional

class LLMValidator:
    """Validador dual usando Claude y GPT"""
    
    def __init__(self, anthropic_key: str = None, openai_key: str = None):
        self.anthropic_key = anthropic_key
        self.openai_key = openai_key
    
    def validate_with_claude(self, analysis_data: Dict, analysis_type: str) -> Optional[Dict]:
        return {"error": "API not configured"}
    
    def validate_with_gpt(self, analysis_data: Dict, analysis_type: str) -> Optional[Dict]:
        return {"error": "API not configured"}
    
    def dual_validate(self, analysis_data: Dict, analysis_type: str) -> Dict:
        return {"error": "No API keys configured"}
