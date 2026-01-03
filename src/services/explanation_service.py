"""Service for generating and evaluating trial result explanations"""
from typing import Dict, Any
from ..agent_manager import AgentManager, AgentModel, ResponseFormat
from ..response_models import ExplanationEvaluation
from ..config import MISTRAL_AGENT_ID
from ..logger import logger
from ..utils.response_extractor import ResponseExtractor


class ExplanationService:
    """Generates and evaluates explanations for trial results"""
    
    def __init__(self, agent_id: str = MISTRAL_AGENT_ID):
        self.agent_id = agent_id
        self.extractor = ResponseExtractor()
    
    async def generate_with_validation(
        self,
        nct_id: str,
        trial_data: Dict[str, Any],
        user_responses: Dict[str, bool],
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Generate explanation with automatic validation and rewriting.
        
        Args:
            nct_id (str): Trial NCT ID
            trial_data (Dict[str, Any]): Trial data including questions
            user_responses (Dict[str, bool]): User's responses to questions
            max_retries (int): Maximum number of rewrite attempts
            
        Returns:
            Dict[str, Any]: Explanation with quality metrics
        """
        trial_context = f"Trial {trial_data['nct_id']}: {trial_data['title'][:100]}..."
        
        for attempt in range(max_retries):
            logger.info(f"Generating explanation (Attempt {attempt + 1}/{max_retries})...")
            
            # Generate explanation
            explanation = await self._generate_explanation(nct_id, trial_data, user_responses)
            
            # Evaluate
            logger.info("Evaluating explanation comprehension...")
            evaluation = await self._evaluate_explanation(explanation, trial_context)
            
            logger.info(f"Comprehension score: {evaluation.comprehension_score}/100")
            
            # Check if acceptable
            if evaluation.is_acceptable:
                logger.info("✅ Explanation is comprehensible enough")
                return {
                    'explanation': explanation,
                    'comprehension_score': evaluation.comprehension_score,
                    'attempts': attempt + 1,
                    'evaluation': {
                        'score': evaluation.comprehension_score,
                        'is_acceptable': True
                    }
                }
            
            # Log issues and retry
            logger.warning(f"⚠️ Explanation needs improvement (Score: {evaluation.comprehension_score}/100)")
            logger.warning(f"Issues: {', '.join(evaluation.issues)}")
            
            if attempt < max_retries - 1:
                explanation = await self._rewrite_with_feedback(
                    nct_id, trial_data, user_responses, explanation, evaluation
                )
        
        # All retries failed
        logger.error(f"❌ Failed to achieve acceptable comprehension after {max_retries} attempts")
        return {
            'explanation': explanation,
            'comprehension_score': evaluation.comprehension_score,
            'attempts': max_retries,
            'evaluation': {
                'score': evaluation.comprehension_score,
                'is_acceptable': False,
                'issues': evaluation.issues
            },
            'warning': 'Explanation may be difficult to understand'
        }
    
    async def _generate_explanation(
        self,
        nct_id: str,
        trial_data: Dict[str, Any],
        user_responses: Dict[str, bool]
    ) -> str:
        """Generate initial explanation"""
        async with AgentManager(max_retries=3, retry_delay=5.0) as manager:
            agent = manager.create_agent(
                agent_id=self.agent_id,
                name="ExplanationAgent",
                model=AgentModel.SMALL.value,
                description="Medical results explanation specialist"
            )
            
            prompt = self._build_explanation_prompt(trial_data, user_responses)
            response = await manager.chat_with_retry_async(
                agent_name="ExplanationAgent",
                message=prompt
            )
            
            return self.extractor.extract_text(response)
    
    async def _evaluate_explanation(self, explanation: str, trial_context: str) -> ExplanationEvaluation:
        """Evaluate explanation quality"""
        async with AgentManager(max_retries=2, retry_delay=3.0) as manager:
            evaluator = manager.create_agent(
                agent_id=self.agent_id,
                name="ExplanationEvaluator",
                model=AgentModel.SMALL.value,
                response_format=ResponseFormat.JSON,
                response_model=ExplanationEvaluation,
                description="Evaluates medical explanations for patient comprehension"
            )
            
            prompt = self._build_evaluation_prompt(explanation, trial_context)
            evaluation = await manager.chat_with_retry_async(
                agent_name="ExplanationEvaluator",
                message=prompt,
                response_model=ExplanationEvaluation
            )
            
            return evaluation
    
    async def _rewrite_with_feedback(
        self,
        nct_id: str,
        trial_data: Dict[str, Any],
        user_responses: Dict[str, bool],
        previous_explanation: str,
        evaluation: ExplanationEvaluation
    ) -> str:
        """Rewrite explanation based on feedback"""
        async with AgentManager(max_retries=3, retry_delay=5.0) as manager:
            agent = manager.create_agent(
                agent_id=self.agent_id,
                name="ExplanationRewriter",
                model=AgentModel.SMALL.value,
                description="Rewrites medical explanations based on feedback"
            )
            
            prompt = self._build_rewrite_prompt(
                trial_data, user_responses, previous_explanation, evaluation
            )
            
            response = await manager.chat_with_retry_async(
                agent_name="ExplanationRewriter",
                message=prompt
            )
            
            return self.extractor.extract_text(response)
    
    def _build_explanation_prompt(self, trial_data: Dict[str, Any], user_responses: Dict[str, bool]) -> str:
        """Build prompt for initial explanation"""
        inclusion_qa, exclusion_qa = self._format_qa(trial_data, user_responses)
        
        return f"""
        You are a medical assistant explaining clinical trial eligibility results to a patient.
        
        **Trial Information:**
        - Trial ID: {trial_data['nct_id']}
        - Title: {trial_data['title']}
        
        **Patient's Responses to Exclusion Criteria:**
        {exclusion_qa}
        
        **Patient's Responses to Inclusion Criteria:**
        {inclusion_qa}
        
        **Task:**
        Provide a clear, empathetic explanation in 3-4 paragraphs covering:
        1. Eligibility Summary
        2. Key Factors
        3. What This Means
        4. Next Steps
        
        **Guidelines:**
        - Simple, patient-friendly language
        - Empathetic and encouraging
        - Avoid medical jargon
        - 150-200 words
        - No medical advice, only explain assessment
        """
    
    def _build_evaluation_prompt(self, explanation: str, trial_context: str) -> str:
        """Build prompt for evaluation"""
        return f"""
        Evaluate this explanation for patient comprehension.
        
        **Context:** {trial_context}
        **Explanation:** {explanation}
        
        **Criteria (0-100):**
        - Clarity (0-25): Simple language?
        - Structure (0-25): Well-organized?
        - Completeness (0-25): Addresses all aspects?
        - Empathy (0-25): Patient-friendly?
        
        **Scoring:**
        - 80-100: Excellent
        - 60-79: Good (acceptable)
        - 40-59: Fair (needs improvement)
        - 0-39: Poor
        
        Return JSON with: comprehension_score, is_acceptable (≥60), issues, suggestions
        """
    
    def _build_rewrite_prompt(
        self,
        trial_data: Dict[str, Any],
        user_responses: Dict[str, bool],
        previous_explanation: str,
        evaluation: ExplanationEvaluation
    ) -> str:
        """Build prompt for rewriting"""
        inclusion_qa, exclusion_qa = self._format_qa(trial_data, user_responses)
        issues_text = "\n".join([f"- {issue}" for issue in evaluation.issues])
        suggestions_text = evaluation.get_suggestions_text() if hasattr(evaluation, 'get_suggestions_text') else str(evaluation.suggestions)
        
        return f"""
        Rewrite this explanation to improve comprehension.
        
        **Trial:** {trial_data['nct_id']} - {trial_data['title']}
        
        **Responses:**
        Exclusion: {exclusion_qa}
        Inclusion: {inclusion_qa}
        
        **Previous Explanation:** {previous_explanation}
        **Score:** {evaluation.comprehension_score}/100
        **Issues:** {issues_text}
        **Suggestions:** {suggestions_text}
        
        **Focus on:**
        1. Simpler language
        2. Shorter sentences (max 15 words)
        3. Clear structure
        4. Be specific
        5. Be encouraging
        
        Write improved 150-200 word explanation (no meta-commentary):
        """
    
    def _format_qa(self, trial_data: Dict[str, Any], user_responses: Dict[str, bool]) -> tuple:
        """Format questions and answers for prompts"""
        inclusion_qa = []
        exclusion_qa = []
        
        for q_id, q_data in trial_data['questions']['inclusion'].items():
            answer = user_responses.get(q_id)
            if answer is not None:
                inclusion_qa.append(f"- {q_data['question']}: {'Yes' if answer else 'No'}")
        
        for q_id, q_data in trial_data['questions']['exclusion'].items():
            answer = user_responses.get(q_id)
            if answer is not None:
                exclusion_qa.append(f"- {q_data['question']}: {'Yes' if answer else 'No'}")
        
        inclusion_text = "\n".join(inclusion_qa) if inclusion_qa else "No inclusion questions answered"
        exclusion_text = "\n".join(exclusion_qa) if exclusion_qa else "No exclusion questions answered"
        
        return inclusion_text, exclusion_text