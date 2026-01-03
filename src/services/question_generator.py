"""Service for generating eligibility questions from trial criteria"""
import asyncio
from typing import List, Dict, Any
from ..agent_manager import AgentManager, AgentModel, ResponseFormat
from ..response_models import EligibilityQuestions
from ..config import MISTRAL_AGENT_ID
from ..logger import logger


class QuestionGenerator:
    """Generates eligibility questions from clinical trial criteria"""
    
    def __init__(self, agent_id: str = MISTRAL_AGENT_ID):
        self.agent_id = agent_id
    
    async def generate_for_trial(self, nct_id: str, title: str, criteria: str) -> EligibilityQuestions:
        """
        Generate eligibility questions for a single trial.
        
        Args:
            nct_id (str): Trial NCT ID
            title (str): Trial title
            criteria (str): Raw eligibility criteria text
            
        Returns:
            EligibilityQuestions: Generated questions
        """
        async with AgentManager(max_retries=3, retry_delay=5.0) as manager:
            agent = manager.create_agent(
                agent_id=self.agent_id,
                name="QuestionGeneratorAgent",
                model=AgentModel.SMALL.value,
                response_format=ResponseFormat.JSON,
                response_model=EligibilityQuestions
            )
            
            prompt = self._build_question_prompt(nct_id, title, criteria)
            
            response = await manager.chat_with_retry_async(
                agent_name="QuestionGeneratorAgent",
                message=prompt,
                response_model=EligibilityQuestions
            )
            
            return response
    
    async def generate_for_all_trials(self, trials_eligibility: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate questions for all trials.
        
        Args:
            trials_eligibility (List[Dict[str, Any]]): Trials with eligibility criteria
            
        Returns:
            List[Dict[str, Any]]: Trials with generated questions
        """
        logger.info("📝 Generating eligibility questions...")
        
        trials_with_questions = []
        for trial in trials_eligibility:
            criteria = trial['eligibility']['criteria']
            if criteria == 'N/A' or not criteria.strip():
                continue
            
            try:
                questions = await self.generate_for_trial(
                    trial['nct_id'],
                    trial['title'],
                    criteria
                )
                
                # Structure questions with IDs
                trial_with_questions = self._structure_questions(trial, questions)
                trials_with_questions.append(trial_with_questions)
                
                await asyncio.sleep(1)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Error processing {trial['nct_id']}: {e}")
                continue
        
        logger.info(f"Generated questions for {len(trials_with_questions)} trials")
        return trials_with_questions
    
    def _build_question_prompt(self, nct_id: str, title: str, criteria: str) -> str:
        """Build the prompt for question generation"""
        return f"""
        You are a medical research assistant. Generate clear, yes/no questions from clinical trial eligibility criteria for patients.

        Trial ID: {nct_id}
        Trial Title: {title}

        Eligibility Criteria:
        {criteria}

        Instructions:
        1. Read the eligibility criteria carefully.
        2. Identify INCLUSION criteria (what qualifies someone) and EXCLUSION criteria (what disqualifies someone).
        3. Generate simple, plain language yes/no questions for each criterion.
        4. Questions must be understandable by patients with no medical background.
        5. Avoid medical jargon. If a term is complex, rewrite it in simple words.
        6. Each question should address ONE specific criterion.
        7. Use short sentences (<15 words) and clear wording.
        8. Start questions with "Do you have...", "Have you ever...", or "Are you...".
        
        Important:
        - Do NOT include explanations, just the questions.
        - If a criterion is vague or ambiguous, skip it.
        - Keep specific medical condition names.
        - Limit to a maximum of 10 questions per category.

        Return a JSON object:
        {{"nct_id": "{nct_id}",
        "inclusion_questions": ["list of simplified yes/no questions for inclusion"],
        "exclusion_questions": ["list of simplified yes/no questions for exclusion"]}}

        Examples:
        - Inclusion: "Type 2 diabetes diagnosed within last 5 years"  
            Question: "Have you been diagnosed with type 2 diabetes in the last 5 years?"

        - Exclusion: "History of cancer"  
            Question: "Have you ever been diagnosed with cancer?"
        """
    
    def _structure_questions(self, trial: Dict[str, Any], questions: EligibilityQuestions) -> Dict[str, Any]:
        """Structure questions with unique IDs"""
        inclusion_questions = {}
        for idx, question in enumerate(questions.inclusion_questions, start=1):
            q_id = f"{trial['nct_id']}_INC_{idx:03d}"
            inclusion_questions[q_id] = {"question": question, "response": None}
        
        exclusion_questions = {}
        for idx, question in enumerate(questions.exclusion_questions, start=1):
            q_id = f"{trial['nct_id']}_EXC_{idx:03d}"
            exclusion_questions[q_id] = {"question": question, "response": None}
        
        return {
            **trial,
            'questions': {
                'inclusion': inclusion_questions,
                'exclusion': exclusion_questions
            }
        }