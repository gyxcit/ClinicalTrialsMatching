"""
ModelClient
-----------
A simple and extensible client to interact with various LLM backends using LiteLLM.

Supported usage patterns:
    1. Remote API (e.g., Groq, OpenAI, Mistral, etc.)
    2. Local LiteLLM proxy (e.g., local router exposing models)
    3. Local Ollama server

This class allows you to easily configure:
    - model identifier
    - API key (optional for Ollama)
    - Base API URL (online or local)

The `generate_response()` method returns the raw LiteLLM response object.
"""

import logging
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from litellm import completion

load_dotenv()
logger = logging.getLogger(__name__)


class ModelClient:
    """
    A client to interact with any LLM endpoint through LiteLLM.

    This class abstracts the connection parameters and message format so you can use:
        - Online API providers (Groq, OpenAI, Mistral, etc.)
        - Local LiteLLM proxy (your router at http://localhost:4000/)
        - Local Ollama server (http://localhost:11434)

    Parameters
    ----------
    model : str
        Identifier of the model to use. Examples:
            - "groq/llama-3.3-70b-versatile"
            - "openai/gpt-4o"
            - "ollama/mistral:latest"

    api_key : str, optional
        Authentication token for online APIs.
        Not required for Ollama or unsecured local proxies.

    api_base : str, optional
        Base URL of the API.
        Examples:
            - None (default for online APIs)
            - "http://localhost:4000/" (LiteLLM proxy)
            - "http://localhost:11434" (Ollama)

    Attributes
    ----------
    system_role : str
        Default system instruction applied to each request.
    """

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None
    ):
        """Initialize the ModelClient with model configuration.
        
        Args:
            model: Model identifier (e.g., "groq/llama-3.3-70b-versatile")
            api_key: API key for authentication (optional for local models)
            api_base: Base URL for API endpoint (optional)
            
        Raises:
            ValueError: If model is not provided
        """
        self.model = model
        self.api_key = api_key
        self.api_base = api_base
        self.system_role = "You are a helpful assistant."
        self._check_model()

    def _check_model(self) -> None:
        """Ensure essential model parameters are provided.
        
        Raises:
            ValueError: If model is not set
        """
        if not self.model:
            raise ValueError("Model is not set. Please provide a valid model identifier.")
        
        logger.info(f"Initialized ModelClient with model: {self.model}")

    def generate_response(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate a response from the model based on the messages.

        Parameters
        ----------
        messages : list
            List of message dictionaries with 'role' and 'content' keys.
        tools : list, optional
            List of tool definitions for function calling.
        temperature : float, optional
            Sampling temperature (default: 0.7)
        max_tokens : int, optional
            Maximum tokens to generate (default: None - model default)

        Returns
        -------
        dict
            Full LiteLLM completion response.
            
        Raises
        ------
        Exception
            If the API call fails
        """
        try:
            logger.debug(f"Generating response with {len(messages)} messages")
            
            response = completion(
                model=self.model,
                api_key=self.api_key,
                api_base=self.api_base,
                messages=messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise



# ======================================================================
# Example usage demonstrating the 3 main usage patterns
# ======================================================================
# if __name__ == "__main__":

    #-----------------------------------------------------------
    #CASE 1 — Remote API (Groq, OpenAI, Mistral, etc.)
    #-----------------------------------------------------------
    # API_KEY = os.getenv("GROQ_API_KEY")
    # model_name = "groq/llama-3.3-70b-versatile"
    # client = ModelClient(model=model_name, api_key=API_KEY)
    # message=[{"role": "user", "content": "Quelle est la capitale de l'Allemagne ?"}]
    # print(client.generate_response(message))

    # -----------------------------------------------------------
    # CASE 2 — Local LiteLLM Proxy (http://localhost:4000)
    # -----------------------------------------------------------
    # model_name = "openai/groq/openai/gpt-oss-120b"
    # API_KEY = os.getenv("LITE_LLM_GROQ_GPTOSS_120B_DEV")
    # client = ModelClient(
    #     model=model_name,
    #     api_key=API_KEY,
    #     api_base="http://localhost:4000/"
    # )
    # print(client.generate_response("Quelle est la capitale de la Belgique ?"))

    # -----------------------------------------------------------
    # CASE 3 — Local Ollama Server (http://localhost:11434)
    # -----------------------------------------------------------
    # client = ModelClient(
    #     model="ollama/mistral:latest",
    #     api_key=None,
    #     api_base="http://localhost:11434"
    # )
    # print(client.generate_response("Quelle est la capitale de l’Italie ?"))
