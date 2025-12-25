from mistralai import Mistral
from config import (
    AGENT_API_KEY,
    MISTRAL_AGENT_ID
)
from .logger import (
    logger,
    log_llm_interaction,
    log_success,
    log_error,
    log_agent_action
)
from agent_manager import AgentManager, AgentModel
import asyncio


def chat_with_llm(message: str, model: str = "mistral-small-latest"):
    """Send a chat message to the LLM and get a response."""
    try:
        log_agent_action("Initializing Mistral client", f"Model: {model}")
        
        with Mistral(api_key=AGENT_API_KEY) as mistral:
            log_llm_interaction(model, len(message))
            
            res = mistral.agents.complete(
                messages=[
                    {
                        "content": message,  # Fixed: Use the parameter instead of hardcoded text
                        "role": "user",
                    },
                ], 
                agent_id=MISTRAL_AGENT_ID, 
                stream=False
            )
            
            # Get response length safely
            response_str = str(res)
            log_llm_interaction(model, len(message), len(response_str))
            log_success("Agent response received successfully")
            
            return res
            
    except Exception as e:
        log_error("Failed to get agent response", e)
        raise


async def async_example():
    """Example of asynchronous agent usage."""
    
    logger.info("=" * 60)
    logger.info("🏥 Clinical Trials Agent - Async Demo")
    logger.info("=" * 60)
    
    async with AgentManager(max_retries=3, retry_delay=5.0) as manager:
        
        # Create multiple agents
        agent1 = manager.create_agent(
            agent_id=MISTRAL_AGENT_ID,
            name="ClinicalAgent",
            model=AgentModel.SMALL.value,
            description="Clinical trials specialist"
        )
        
        agent2 = manager.create_agent(
            agent_id=MISTRAL_AGENT_ID,
            name="ResearchAgent",
            model=AgentModel.SMALL.value,
            description="Medical research specialist"
        )
        
        # Single async chat
        logger.info("\n🔹 Single async chat:")
        response = await manager.chat_with_retry_async(
            agent_name="ClinicalAgent",
            message="What is a clinical trial?"
        )
        print(f"\nResponse: {response}\n")
        
        # Multiple parallel requests
        logger.info("\n🔹 Parallel requests to multiple agents:")
        responses = await manager.chat_multiple_agents_async([
            {
                "agent_name": "ClinicalAgent",
                "message": "What are the phases of clinical trials?"
            },
            {
                "agent_name": "ResearchAgent", 
                "message": "What is placebo effect?"
            }
        ])
        
        print("\n" + "=" * 60)
        for i, resp in enumerate(responses, 1):
            if isinstance(resp, Exception):
                print(f"Request {i} failed: {resp}")
            else:
                print(f"Response {i}: {resp}")
        print("=" * 60)


def sync_example():
    """Example of synchronous agent usage."""
    
    logger.info("=" * 60)
    logger.info("🏥 Clinical Trials Agent - Sync Demo")
    logger.info("=" * 60)
    
    with AgentManager(max_retries=3, retry_delay=2.0) as manager:
        
        # Create agent
        agent = manager.create_agent(
            agent_id=MISTRAL_AGENT_ID,
            name="ClinicalAgent",
            model=AgentModel.SMALL.value,
            description="Clinical trials specialist"
        )
        
        # Simple chat
        logger.info("\n🔹 Synchronous chat:")
        response = manager.chat_with_retry(
            agent_name="ClinicalAgent",
            message="What is informed consent in clinical trials?"
        )
        
        print("\n" + "=" * 60)
        print("Response:", response)
        print("=" * 60)


def main():
    """Example usage of AgentManager."""
    
    logger.info("=" * 60)
    logger.info("🏥 Clinical Trials Agent - Manager Demo")
    logger.info("=" * 60)
    
    # Create agent manager
    with AgentManager(max_retries=3, retry_delay=3.0) as manager:
        
        # Create an agent
        clinical_agent = manager.create_agent(
            agent_id=MISTRAL_AGENT_ID,
            name="ClinicalTrialsAgent",
            model=AgentModel.SMALL.value,
            description="Agent specialized in clinical trials matching",
            temperature=0.7
        )
        
        # Simple chat
        logger.info("\n🔹 Simple chat test:")
        response = manager.chat_with_retry(
            agent_name="ClinicalTrialsAgent",
            message="what's the use of clinical trials? Answer in one short sentence."
        )
        
        print("\n" + "=" * 60)
        print("Response:", response)
        print("=" * 60)
        
        # Chat with history
        logger.info("\n🔹 Chat with history test:")
        response2 = manager.chat_with_retry(
            agent_name="ClinicalTrialsAgent",
            message="What was my previous question?",
            use_history=True
        )
        
        print("\n" + "=" * 60)
        print("Response with history:", response2)
        print("=" * 60)
        
        # Show agent info
        logger.info("\n📊 Agent Information:")
        info = clinical_agent.get_info()
        for key, value in info.items():
            logger.info(f"  {key}: {value}")


if __name__ == "__main__":
    import sys
    
    # Choose mode
    mode = sys.argv[1] if len(sys.argv) > 1 else "sync"
    
    if mode == "async":
        # Run async version
        asyncio.run(async_example())
    else:
        # Run sync version
        sync_example()
    
    logger.info("=" * 60)
    logger.info("🏥 Clinical Trials Agent - LLM Client Test")
    logger.info("=" * 60)
    
    result = chat_with_llm("what's the use of clinical trials? Answer in one short sentence.")
    
    print("\n" + "=" * 60)
    print("Response:", result)
    print("=" * 60)
    
    main()

