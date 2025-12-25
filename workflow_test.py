"""Test the workflow with structured responses"""
import asyncio
from src.agent_manager import AgentManager, AgentModel, ResponseFormat
from src.response_models import IllnessInfo
from src.config import MISTRAL_AGENT_ID
from src.logger import logger
from src.trials import fetch_trials_async


async def get_illness_type_structured(user_illness: str):
    """Get illness type with structured response."""
    logger.info("=" * 60)
    logger.info("🏥 GET ILLNESS TYPE (STRUCTURED)")
    logger.info("=" * 60)
    
    async with AgentManager(max_retries=3, retry_delay=5.0) as manager:
        # Create an agent with structured response format
        agent = manager.create_agent(
            agent_id=MISTRAL_AGENT_ID,
            name="IllnessTypeAgent",
            model=AgentModel.SMALL.value,
            response_format=ResponseFormat.JSON,
            response_model=IllnessInfo  # Define expected structure
        )
        
        prompt = f"""
        The response MUST be in English.
        Analyze the following patient description and return a JSON object compatible with the IllnessInfo model.
        Patient input: {user_illness}
        Rules:
        - illness_name: general illness name only (no types, subtypes, stages, variants, or anatomical locations). 
            If it contains numbers, stages, or variants, replace with the general term.
        - type: specific type or subtype if mentioned, else null
        - subtype: specific variant if mentioned, else null
        - stage: disease stage if explicitly mentioned (e.g., early, late, stage IV), else null
        - anatomical_location: primary affected body part or system if mentioned, else null
        - organ_touched: specific organ or tissue affected if mentioned, else null
        - category: medical category (e.g., chronic, acute, infectious, genetic, autoimmune)
        - severity: mild/moderate/severe if mentioned, else null
        - affected_systems: list affected body systems (e.g., urinary, nervous, visual)
        - keywords: include any types, stages, variants, organs, or other relevant terms
        - confidence_score: optional numeric confidence if applicable, else null
        - Use null for unknown fields.
        - Output must be valid JSON only; do not add explanations or extra text.
        """
        
        # Get structured response
        response = await manager.chat_with_retry_async(
            agent_name="IllnessTypeAgent",
            message=prompt,
            response_model=IllnessInfo  # Override if needed
        )
        
        logger.info(f"Structured Illness Info: {response}")
        return response


async def get_illness(user_input: str = None):
    """Compare different response formats."""
    # Test structured format
    structured_result = await get_illness_type_structured(user_input)
    print("\n" + "=" * 60)
    print("STRUCTURED FORMAT RESULT:")
    if isinstance(structured_result, IllnessInfo):
        print(f"Illness Name: {structured_result.illness_name}")
        print(f"Type: {structured_result.type}")
        print(f"Subtype: {structured_result.subtype}")
        print(f"Stage: {structured_result.stage}")
        print(f"Anatomical Location: {structured_result.anatomical_location}")
        print(f"Organ Touched: {structured_result.organ_touched}")
        print(f"Category: {structured_result.category}")
        print(f"Affected Systems: {', '.join(structured_result.affected_systems)}")
        print(f"Keywords: {', '.join(structured_result.keywords)}")
    else:
        print(structured_result)
    print("=" * 60)
    return structured_result


async def get_trials_for_illness(illness_: str):
    """Fetch clinical trials for a given illness (async).
    
    Args:
        illness_name (str): Name of the illness to search trials for.
    """
    logger.info("=" * 60)
    logger.info(f"🔍 FETCH CLINICAL TRIALS FOR: {illness_}")
    logger.info("=" * 60)
    
    trials = await fetch_trials_async(  # Changed to async version
        condition=illness_,
        max_studies=100,
        return_status=True,
        json_output=True,
        output_name=f"trials_for_{illness_.replace(' ', '_')}.json",
        timeout=10,
    )
    
    logger.info(f"Found {len(trials) if trials else 0} trials for {illness_}")
    if trials:
        study=0
        logger.info("Sample trials:")
        for trial in trials[:5]:
            study+=1
            logger.info(f"Trial {study}:")
            protocol = trial.get('protocolSection', {})
            identification = protocol.get('identificationModule', {})
            status_module = protocol.get('statusModule', {})
            
            title = identification.get('briefTitle', 'N/A')
            status = status_module.get('overallStatus', 'N/A')
            
            logger.info(f"- {title} (Status: {status})")
    
    return trials



if __name__ == "__main__":
    txt="""
    I have diabetes type 2 with complications affecting my kidneys and eyes
    """
    # get illness information
    
    print("\nTesting illness extraction with structured response...\n")
    structured_result = asyncio.run(get_illness(user_input=txt))
    
    print("\nTesting clinical trials fetching...\n")
    if isinstance(structured_result, IllnessInfo):
        illness_name = structured_result.illness_name
        asyncio.run(get_trials_for_illness(
            illness_=illness_name,
        ))

