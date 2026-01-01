"""Generate eligibility questions from clinical trial criteria"""
import asyncio
import json
from typing import List, Dict, Any
from src.agent_manager import AgentManager, AgentModel, ResponseFormat
from src.response_models import EligibilityQuestions
from src.config import MISTRAL_AGENT_ID
from src.logger import logger




async def generate_eligibility_questions(nct_id: str, title: str, eligibility_criteria: str) -> EligibilityQuestions:
    """Generate inclusion and exclusion questions from eligibility criteria.
    
    Args:
        nct_id (str): NCT ID of the trial
        title (str): Title of the trial
        eligibility_criteria (str): Raw eligibility criteria text
    
    Returns:
        EligibilityQuestions: Structured questions for inclusion and exclusion
    """
    logger.info(f"Generating questions for {nct_id}")
    
    async with AgentManager(max_retries=3, retry_delay=5.0) as manager:
        # Create an agent for question generation
        agent = manager.create_agent(
            agent_id=MISTRAL_AGENT_ID,
            name="QuestionGeneratorAgent",
            model=AgentModel.SMALL.value,
            response_format=ResponseFormat.JSON,
            response_model=EligibilityQuestions
        )
        profanne_prompt=f"""
        You are a medical research assistant. Generate clear, yes/no questions from clinical trial eligibility criteria for patients.

        Trial ID: {nct_id}
        Trial Title: {title}

        Eligibility Criteria:
        {eligibility_criteria}

        Instructions:
        1. Read the eligibility criteria carefully.
        2. Identify INCLUSION criteria (what qualifies someone) and EXCLUSION criteria (what disqualifies someone).
        3. Generate simple, plain language yes/no questions for each criterion.
        4. Questions must be understandable by patients with no medical background.
        5. Avoid medical jargon. If a term is complex, rewrite it in simple words (e.g., "peripheral arterial disease" → "serious blood flow problems in your legs").
        6. Each question should address ONE specific criterion.
        7. Use short sentences (<15 words) and clear wording.
        8. Start questions with "Do you have...", "Have you ever...", or "Are you...".
        9. For exclusion criteria, frame as "Do you have [disqualifying condition]?"
        10. For inclusion criteria, frame as "Do you have [qualifying condition]?"

        Return a JSON object:
        
        -"nct_id": "{nct_id}",
        -"inclusion_questions": ["list of simplified yes/no questions for inclusion"],
        -"exclusion_questions": ["list of simplified yes/no questions for exclusion"]

        Examples:
        - Inclusion criterion: "Type 2 diabetes diagnosed within last 5 years"  
        Question: "Have you been diagnosed with type 2 diabetes in the last 5 years?"

        - Exclusion criterion: "History of cancer"  
        Question: "Have you ever been diagnosed with cancer?"

        - Exclusion criterion: "Severe peripheral arterial disease"  
        Question: "Do you have serious blood flow problems in your legs?"
        """
        
        expert_prompt=f"""
        You are a medical research assistant. Generate yes/no questions from clinical trial eligibility criteria for someone familiar with basic medical terms, but who is not a doctor.

        Trial ID: {nct_id}
        Trial Title: {title}

        Eligibility Criteria:
        {eligibility_criteria}

        Instructions:
        1. Read the eligibility criteria carefully.
        2. Identify INCLUSION criteria (what qualifies someone) and EXCLUSION criteria (what disqualifies someone).
        3. Generate clear yes/no questions for each criterion.
        4. Use medical terms when appropriate (e.g., "Type 2 diabetes", "neuropathy"), but avoid unnecessary jargon or abbreviations.
        5. Each question should address ONE specific criterion.
        6. Use present tense for current conditions and past tense for historical conditions.
        7. Start questions with "Do you have...", "Have you ever...", or "Are you...".
        8. For exclusion criteria, frame as "Do you have [disqualifying condition]?"
        9. For inclusion criteria, frame as "Do you have [qualifying condition]?"
        10. Keep questions concise and unambiguous, suitable for someone with basic medical knowledge.

        Return a JSON object:
        
        -"nct_id": "{nct_id}",
        -"inclusion_questions": ["list of yes/no questions for inclusion criteria"],
        -"exclusion_questions": ["list of yes/no questions for exclusion criteria"]
        

        Examples:
        - Inclusion criterion: "Type 2 diabetes diagnosed within last 5 years"
        Question: "Have you been diagnosed with Type 2 diabetes in the last 5 years?"

        - Exclusion criterion: "History of cancer"
        Question: "Have you ever been diagnosed with cancer?"

        - Exclusion criterion: "Severe peripheral arterial disease"
        Question: "Do you have severe peripheral arterial disease?"
        """
        
        
        prompt = profanne_prompt.strip()
        
        response = await manager.chat_with_retry_async(
            agent_name="QuestionGeneratorAgent",
            message=prompt,
            response_model=EligibilityQuestions
        )
        
        return response


async def process_trials_for_questions(trials_eligibility: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process all trials and generate questions for each.
    
    Args:
        trials_eligibility (List[Dict[str, Any]]): List of trials with eligibility criteria
    
    Returns:
        List of trials with generated questions
    """
    logger.info("=" * 60)
    logger.info("📝 GENERATING ELIGIBILITY QUESTIONS")
    logger.info("=" * 60)
    
    trials_with_questions = []
    
    for i, trial in enumerate(trials_eligibility):
        nct_id = trial['nct_id']
        title = trial['title']
        criteria = trial['eligibility']['criteria']
        
        if criteria == 'N/A' or not criteria.strip():
            logger.warning(f"Skipping {nct_id}: No eligibility criteria available")
            continue
        
        try:
            logger.info(f"Processing {i+1}/{len(trials_eligibility)}: {nct_id}")
            
            # Generate questions
            questions = await generate_eligibility_questions(nct_id, title, criteria)
            
            trial_with_questions = {
                'nct_id': nct_id,
                'title': title,
                'eligibility': trial['eligibility'],
                'questions': {
                    'inclusion': questions.inclusion_questions,
                    'exclusion': questions.exclusion_questions
                }
            }
            
            # Add relevance score if it exists
            if 'relevance_score' in trial:
                trial_with_questions['relevance_score'] = trial['relevance_score']
            
            trials_with_questions.append(trial_with_questions)
            
            logger.info(f"  ✓ Generated {len(questions.inclusion_questions)} inclusion and {len(questions.exclusion_questions)} exclusion questions")
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"  ✗ Error processing {nct_id}: {e}")
            continue
    
    logger.info(f"\nSuccessfully generated questions for {len(trials_with_questions)}/{len(trials_eligibility)} trials")
    
    return trials_with_questions


def display_sample_questions(trials_with_questions: List[Dict[str, Any]], num_samples: int = 3):
    """Display sample questions for review.
    
    Args:
        trials_with_questions (List[Dict[str, Any]]): Trials with generated questions
        num_samples (int): Number of samples to display
    """
    logger.info("\n" + "=" * 60)
    logger.info(f"SAMPLE QUESTIONS (First {num_samples} trials)")
    logger.info("=" * 60)
    
    for i, trial in enumerate(trials_with_questions[:num_samples]):
        logger.info(f"\n{i+1}. Trial: {trial['nct_id']}")
        logger.info(f"   Title: {trial['title'][:80]}...")
        
        logger.info(f"\n   INCLUSION QUESTIONS ({len(trial['questions']['inclusion'])}):")
        for j, question in enumerate(trial['questions']['inclusion'], 1):
            logger.info(f"   {j}. {question}")
        
        logger.info(f"\n   EXCLUSION QUESTIONS ({len(trial['questions']['exclusion'])}):")
        for j, question in enumerate(trial['questions']['exclusion'], 1):
            logger.info(f"   {j}. {question}")
        
        logger.info("-" * 60)


async def main():
    """Main function to generate questions from eligibility criteria."""
    
    # Load eligibility data
    logger.info("Loading trials eligibility data...")
    with open('trials_eligibility.json', 'r', encoding='utf-8') as f:
        trials_eligibility = json.load(f)
    
    logger.info(f"Loaded {len(trials_eligibility)} trials")
    
    # Process first 5 trials as a test (remove limit to process all)
    test_sample = trials_eligibility[:5]  # Remove [:5] to process all
    logger.info(f"Processing {len(test_sample)} trials for question generation...\n")
    
    # Generate questions
    trials_with_questions = await process_trials_for_questions(test_sample)
    
    if trials_with_questions:
        # Display samples
        display_sample_questions(trials_with_questions, num_samples=3)
        
        # Save results
        output_file = 'trials_with_questions.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(trials_with_questions, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n✅ Questions saved to '{output_file}'")
        
        # Statistics
        logger.info("\n" + "=" * 60)
        logger.info("STATISTICS")
        logger.info("=" * 60)
        
        total_inclusion = sum(len(t['questions']['inclusion']) for t in trials_with_questions)
        total_exclusion = sum(len(t['questions']['exclusion']) for t in trials_with_questions)
        
        logger.info(f"Total trials processed: {len(trials_with_questions)}")
        logger.info(f"Total inclusion questions: {total_inclusion}")
        logger.info(f"Total exclusion questions: {total_exclusion}")
        logger.info(f"Average inclusion questions per trial: {total_inclusion / len(trials_with_questions):.1f}")
        logger.info(f"Average exclusion questions per trial: {total_exclusion / len(trials_with_questions):.1f}")
        
        print(f"\n✅ Successfully generated questions for {len(trials_with_questions)} trials!")
    else:
        logger.error("No questions were generated. Check the logs for errors.")


if __name__ == "__main__":
    asyncio.run(main())

