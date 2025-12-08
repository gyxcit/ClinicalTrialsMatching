"""Main entry point for the application."""
import os
import logging
from dotenv import load_dotenv

from src.logging_config import setup_logging
from src.Agent import Agent
from src.get_trials import fetch_trials

# Load environment variables
load_dotenv()

# Setup logging
setup_logging(level=logging.INFO, log_file="logs/app.log")
logger = logging.getLogger(__name__)


def demo_agent():
    """Demo of agent with tool usage."""
    logger.info("Starting agent demo")
    
    agent = Agent(
        name="HealthAssistant",
        model="groq/llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        system_prompt="You are a helpful assistant specialized in health information."
    )
    
    # Test conversation
    print("\n=== Agent Demo ===")
    response = agent.chat("Quelle heure est-il ?")
    print(f"Agent: {response}")
    
    response = agent.chat("Merci ! Quel jour sommes-nous ?")
    print(f"Agent: {response}")


def demo_clinical_trials():
    """Demo of clinical trials data fetching."""
    logger.info("Starting clinical trials demo")
    
    print("\n=== Clinical Trials Demo ===")
    condition = "diabetes"
    
    # Fetch and save as JSON
    logger.info(f"Fetching clinical trials for: {condition}")
    fetch_trials(
        condition=condition,
        max_studies=100,
        return_status=False,
        json_output=True,
        output_name=condition
    )
    print(f"Clinical trials data saved to {condition}.json")


def main():
    """Main application entry point."""
    try:
        logger.info("Application started")
        
        # Run demos
        demo_agent()
        demo_clinical_trials()
        
        logger.info("Application completed successfully")
        
    except Exception as e:
        logger.error(f"Application error: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()  