"""Example usage demonstrating the 3 main usage patterns for ModelClient."""
import os
from dotenv import load_dotenv
from src.ModelClient import ModelClient

load_dotenv()


def example_remote_api():
    """CASE 1 — Remote API (Groq, OpenAI, Mistral, etc.)"""
    API_KEY = os.getenv("GROQ_API_KEY")
    model_name = "groq/llama-3.3-70b-versatile"
    client = ModelClient(model=model_name, api_key=API_KEY)
    messages = [{"role": "user", "content": "Quelle est la capitale de l'Allemagne ?"}]
    response = client.generate_response(messages)
    print(response["choices"][0]["message"]["content"])


def example_litellm_proxy():
    """CASE 2 — Local LiteLLM Proxy (http://localhost:4000)"""
    model_name = "your-model-name"
    API_KEY = os.getenv("YOUR_API_KEY")
    client = ModelClient(
        model=model_name,
        api_key=API_KEY,
        api_base="http://localhost:4000/"
    )
    messages = [{"role": "user", "content": "Quelle est la capitale de la Belgique ?"}]
    response = client.generate_response(messages)
    print(response["choices"][0]["message"]["content"])


def example_ollama():
    """CASE 3 — Local Ollama Server (http://localhost:11434)"""
    client = ModelClient(
        model="ollama/mistral:latest",
        api_key=None,
        api_base="http://localhost:11434"
    )
    messages = [{"role": "user", "content": "Quelle est la capitale de l'Italie ?"}]
    response = client.generate_response(messages)
    print(response["choices"][0]["message"]["content"])


if __name__ == "__main__":
    # Run the example you want to test
    example_remote_api()
    # example_litellm_proxy()
    # example_ollama()
