"""Test suite for Agent functionality."""
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from src.Agent import Agent
from src.logging_config import setup_logging

# Load environment and setup logging
load_dotenv()
setup_logging()


def test_agent_with_tools():
    """Test agent with tool usage (get_time)."""
    print("\n=== Test 1: Agent with Tools ===")
    
    agent = Agent(
        name="TestAgent",
        model="groq/llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
    )
    
    response = agent.chat("Quelle heure est-il ?")
    print(f"User: Quelle heure est-il ?")
    print(f"Agent: {response}\n")
    
    assert response is not None
    assert len(response) > 0


def test_agent_conversation():
    """Test multi-turn conversation with memory."""
    print("\n=== Test 2: Multi-turn Conversation ===")
    
    agent = Agent(
        name="ConversationAgent",
        model="groq/llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
    )
    
    # First message
    response1 = agent.chat("Bonjour, je m'appelle Alice.")
    print(f"User: Bonjour, je m'appelle Alice.")
    print(f"Agent: {response1}")
    
    # Second message - should remember the name
    response2 = agent.chat("Comment m'appelles-je ?")
    print(f"User: Comment m'appelles-je ?")
    print(f"Agent: {response2}\n")
    
    assert "Alice" in response2 or "alice" in response2.lower()


def test_agent_without_tools():
    """Test agent simple conversation without tools."""
    print("\n=== Test 3: Simple Conversation ===")
    
    agent = Agent(
        name="SimpleAgent",
        model="groq/llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
    )
    
    response = agent.chat("Quelle est la capitale de la France ?")
    print(f"User: Quelle est la capitale de la France ?")
    print(f"Agent: {response}\n")
    
    assert "Paris" in response


def main():
    """Run all tests."""
    try:
        print("Starting Agent Tests...")
        
        test_agent_with_tools()
        test_agent_conversation()
        test_agent_without_tools()
        
        print("✅ All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()