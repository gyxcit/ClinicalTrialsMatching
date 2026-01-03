# src/utils/response_extractor.py
"""
Utility for extracting text content from various AI response formats
"""
from typing import Any


class ResponseExtractor:
    """Extract text content from different response object types"""
    
    @staticmethod
    def extract_text(response: Any) -> str:
        """
        Extract text content from various response formats
        
        Args:
            response: Response object from AI agent (ChatCompletionResponse, str, etc.)
            
        Returns:
            Extracted text content as string
        """
        # Check if response has choices attribute (ChatCompletionResponse)
        if hasattr(response, 'choices') and len(response.choices) > 0:
            return response.choices[0].message.content
        
        # Check if response has content attribute
        if hasattr(response, 'content'):
            return response.content
        
        # If already a string, return as-is
        if isinstance(response, str):
            return response
        
        # Fallback: convert to string
        return str(response)