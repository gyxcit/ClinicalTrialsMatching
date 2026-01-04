"""Service for simplifying complex medical questions"""
from typing import Dict, Any
from ..agent_manager import AgentManager, AgentModel
from ..config import MISTRAL_AGENT_ID
from ..logger import logger
from .language_service import LanguageService


class QuestionSimplifier:
    """Simplifies medical questions to everyday language"""
    
    def __init__(self, agent_id: str = MISTRAL_AGENT_ID):
        self.agent_id = agent_id
        self.language_service = LanguageService()  # ✅ Ajout
    
    async def simplify(
        self, 
        question: str, 
        context: Dict[str, Any] = None,
        user_language: str = 'en'  # ✅ Nouveau paramètre
    ) -> str:
        """
        Simplify a medical question to be more understandable.
        
        Args:
            question (str): Original question
            context (Dict[str, Any]): Optional context (trial info)
            user_language (str): Language of the user (default: 'en')
            
        Returns:
            str: Simplified question
        """
        # ✅ If question is in user's language, translate to English first
        original_question = question
        if user_language != 'en':
            logger.info(f"🌐 Translating question to English for processing...")
            question = await self.language_service.translate_text(
                question,
                'en',
                context="medical question"
            )
        
        # Simplify in English
        async with AgentManager(max_retries=2, retry_delay=3.0) as manager:
            agent = manager.create_agent(
                agent_id=self.agent_id,
                name="QuestionSimplifier",
                model=AgentModel.SMALL.value,
                description="Simplifies medical questions for patients"
            )
            
            prompt = self._build_simplification_prompt(question, context)
            
            response = await manager.chat_with_retry_async(
                agent_name="QuestionSimplifier",
                message=prompt
            )
            
            simplified = self._extract_text(response).strip()
        
        # ✅ Translate back to user's language
        if user_language != 'en':
            logger.info(f"🌐 Translating simplified question back to user's language...")
            simplified = await self.language_service.translate_text(
                simplified,
                user_language,
                context="simplified medical question"
            )
        
        return simplified

    def _build_simplification_prompt(self, question: str, context: Dict[str, Any] = None) -> str:
        """Build prompt for question simplification"""
        context_info = ""
        if context:
            context_info = f"""
**Trial Context:**
- Trial ID: {context.get('nct_id', 'N/A')}
- Title: {context.get('trial_title', 'N/A')}
"""
        
        return f"""
You are a medical communication expert. Simplify the following medical question so that anyone can understand it, even without medical knowledge.

{context_info}

**Original Question:**
{question}

**Instructions:**
1. **Use everyday language** - Replace ALL medical terms with simple words
2. **Keep it short** - Use sentences of 10-15 words maximum
3. **Maintain meaning** - Don't change what the question asks
4. **Be specific** - Keep important details (numbers, conditions)
5. **One question only** - Do not add explanations or multiple questions

**Examples:**

Original: "Do you have a history of myocardial infarction?"
Simplified: "Have you ever had a heart attack?"

Original: "Are you currently receiving anticoagulation therapy?"
Simplified: "Are you taking blood thinning medication?"

Original: "Do you have diabetic retinopathy with macular edema?"
Simplified: "Do you have diabetes that has caused swelling in your eyes?"

**Rules:**
- Remove medical jargon completely
- Use "you" language
- Start with "Do you...", "Have you...", or "Are you..."
- No explanations in parentheses
- Maximum 20 words

Return ONLY the simplified question, nothing else.
"""