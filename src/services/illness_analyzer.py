"""Service for analyzing patient illness descriptions"""
from typing import Dict, Any
from ..agent_manager import AgentManager, AgentModel, ResponseFormat
from ..response_models import IllnessInfo
from ..config import MISTRAL_AGENT_ID
from ..logger import logger


class IllnessAnalyzer:
    """Analyzes patient descriptions to extract structured illness information"""
    
    def __init__(self, agent_id: str = MISTRAL_AGENT_ID):
        self.agent_id = agent_id
    
    async def analyze(self, user_description: str) -> IllnessInfo:
        """
        Analyze patient description and extract structured illness info.
        
        Args:
            user_description (str): Patient's description of their condition
            
        Returns:
            IllnessInfo: Structured illness information
        """
        logger.info("🏥 Analyzing patient description...")
        
        async with AgentManager(max_retries=3, retry_delay=5.0) as manager:
            agent = manager.create_agent(
                agent_id=self.agent_id,
                name="IllnessTypeAgent",
                model=AgentModel.SMALL.value,
                response_format=ResponseFormat.JSON,
                response_model=IllnessInfo
            )
            
            prompt = self._build_analysis_prompt(user_description)
            
            response = await manager.chat_with_retry_async(
                agent_name="IllnessTypeAgent",
                message=prompt,
                response_model=IllnessInfo
            )
            
            return response
    
    def _build_analysis_prompt(self, user_description: str) -> str:
        """Build the prompt for illness analysis"""
        return f"""
        The response MUST be in English.
        Analyze the following patient description and return a JSON object compatible with the IllnessInfo model.
        Patient input: {user_description}
        
        Rules:
        - illness_name: general illness name only (no types, subtypes, stages, variants, or anatomical locations)
        - type: specific type or subtype if mentioned, else null
        - subtype: specific variant if mentioned, else null
        - stage: disease stage if explicitly mentioned, else null
        - anatomical_location: primary affected body part or system if mentioned, else null
        - organ_touched: specific organ or tissue affected if mentioned, else null
        - category: medical category (e.g., chronic, acute, infectious, genetic, autoimmune)
        - severity: mild/moderate/severe if mentioned, else null
        - affected_systems: list affected body systems
        - keywords: include any types, stages, variants, organs, or other relevant terms
        - Use null for unknown fields
        
        Normalization rules:
        - All medical terms MUST be in canonical singular form
        - "diabetes" → "diabetes", "kidneys" → "kidney", "eyes" → "eye"
        """