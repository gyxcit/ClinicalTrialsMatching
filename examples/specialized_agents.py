"""Example: Creating specialized agents by extending the base Agent class."""
import os
from typing import Optional
from dotenv import load_dotenv

from src.Agent import Agent
from src.tools import register_tool

load_dotenv()


class MedicalAgent(Agent):
    """Specialized agent for medical information and clinical trials."""
    
    def __init__(
        self,
        name: str = "MedicalAssistant",
        model: str = "groq/llama-3.3-70b-versatile",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ):
        # Custom system prompt for medical context
        system_prompt = """You are a medical information assistant. 
        You help users find information about clinical trials and medical conditions.
        Always provide accurate, evidence-based information and cite sources when possible.
        If you're unsure, say so - medical information requires precision."""
        
        super().__init__(
            name=name,
            system_prompt=system_prompt,
            model=model,
            api_key=api_key,
            api_base=api_base,
            max_tool_iterations=10  # More iterations for complex medical queries
        )
    
    def search_trials(self, condition: str, max_results: int = 5) -> str:
        """Search for clinical trials on a specific condition.
        
        Args:
            condition: Medical condition to search for
            max_results: Maximum number of trials to return
            
        Returns:
            Summary of found trials
        """
        from src.get_trials import fetch_trials
        
        try:
            trials = fetch_trials(condition, max_studies=max_results)
            
            if not trials:
                return f"No clinical trials found for: {condition}"
            
            summary = f"Found {len(trials)} clinical trials for {condition}:\n\n"
            for i, trial in enumerate(trials[:max_results], 1):
                protocol = trial.get('protocolSection', {})
                identification = protocol.get('identificationModule', {})
                title = identification.get('briefTitle', 'No title')
                nct_id = identification.get('nctId', 'Unknown ID')
                summary += f"{i}. {title} (NCT ID: {nct_id})\n"
            
            return summary
        except Exception as e:
            return f"Error searching trials: {str(e)}"


class CodeAssistantAgent(Agent):
    """Specialized agent for coding assistance."""
    
    def __init__(
        self,
        name: str = "CodeAssistant",
        model: str = "groq/llama-3.3-70b-versatile",
        api_key: Optional[str] = None,
    ):
        system_prompt = """You are an expert programming assistant.
        You help users with:
        - Writing clean, efficient code
        - Debugging errors
        - Explaining programming concepts
        - Reviewing code for best practices
        - Suggesting optimizations
        
        Always provide code examples when relevant and explain your reasoning."""
        
        super().__init__(
            name=name,
            system_prompt=system_prompt,
            model=model,
            api_key=api_key,
            max_tool_iterations=5
        )


class ResearchAgent(Agent):
    """Specialized agent for research and information gathering."""
    
    def __init__(
        self,
        name: str = "Researcher",
        model: str = "groq/llama-3.3-70b-versatile",
        api_key: Optional[str] = None,
    ):
        system_prompt = """You are a research assistant specialized in gathering and synthesizing information.
        You help users by:
        - Finding relevant information on topics
        - Summarizing complex documents
        - Comparing different sources
        - Identifying key insights
        - Providing well-structured research summaries
        
        Always be thorough and cite sources when possible."""
        
        super().__init__(
            name=name,
            system_prompt=system_prompt,
            model=model,
            api_key=api_key,
            max_tool_iterations=8
        )


# Example: Register custom tools for specialized agents
def register_medical_tools():
    """Register tools specific to medical agents."""
    
    def get_drug_info(drug_name: str) -> str:
        """Get information about a drug (placeholder)."""
        return f"Information about {drug_name}: This would contain drug details from a medical database."
    
    register_tool(
        name="get_drug_info",
        function=get_drug_info,
        description="Get detailed information about a pharmaceutical drug",
        parameters={
            "type": "object",
            "properties": {
                "drug_name": {
                    "type": "string",
                    "description": "Name of the drug to look up"
                }
            },
            "required": ["drug_name"]
        }
    )


def register_code_tools():
    """Register tools specific to code assistant agents."""
    
    def run_python_code(code: str) -> str:
        """Execute Python code safely (placeholder - would need sandboxing)."""
        return f"Executing code: {code[:50]}... (This is a placeholder)"
    
    register_tool(
        name="run_python_code",
        function=run_python_code,
        description="Execute Python code in a safe environment",
        parameters={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute"
                }
            },
            "required": ["code"]
        }
    )


# Demo usage
def demo_specialized_agents():
    """Demonstrate specialized agents in action."""
    api_key = os.getenv("GROQ_API_KEY")
    
    print("\n=== Medical Agent Demo ===")
    medical_agent = MedicalAgent(api_key=api_key)
    response = medical_agent.chat("What are the current clinical trials for diabetes?")
    print(f"Medical Agent: {response}\n")
    
    print("\n=== Code Assistant Demo ===")
    code_agent = CodeAssistantAgent(api_key=api_key)
    response = code_agent.chat("How do I implement a binary search in Python?")
    print(f"Code Agent: {response}\n")
    
    print("\n=== Research Agent Demo ===")
    research_agent = ResearchAgent(api_key=api_key)
    response = research_agent.chat("Summarize the key benefits of using type hints in Python")
    print(f"Research Agent: {response}\n")


if __name__ == "__main__":
    # Register specialized tools
    register_medical_tools()
    register_code_tools()
    
    # Run demo
    demo_specialized_agents()
