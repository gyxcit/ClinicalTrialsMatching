"""Service for language detection and translation"""
from typing import Dict, Any, Optional
from ..agent_manager import AgentManager, AgentModel
from ..config import MISTRAL_AGENT_ID
from ..logger import logger


class LanguageService:
    """Handles language detection and translation"""
    
    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'fr': 'French',
        'es': 'Spanish',
        'de': 'German',
        'it': 'Italian',
        'pt': 'Portuguese',
        'zh': 'Chinese',
        'ja': 'Japanese',
        'ar': 'Arabic'
    }
    
    def __init__(self, agent_id: str = MISTRAL_AGENT_ID):
        self.agent_id = agent_id
    
    async def detect_language(self, text: str) -> Dict[str, str]:
        """
        Detect the language of input text.
        
        Args:
            text (str): Input text
            
        Returns:
            Dict with 'code' (ISO 639-1) and 'name'
        """
        async with AgentManager(max_retries=2, retry_delay=3.0) as manager:
            agent = manager.create_agent(
                agent_id=self.agent_id,
                name="LanguageDetector",
                model=AgentModel.SMALL.value,
                description="Detects language of text"
            )
            
            prompt = f"""
Detect the language of this text and return ONLY a JSON object.

Text: {text[:500]}

Return format:
{{"language_code": "en", "language_name": "English", "confidence": "high"}}

Supported codes: {', '.join(self.SUPPORTED_LANGUAGES.keys())}
If unsure, return "en" (English) as default.
"""
            
            response = await manager.chat_with_retry_async(
                agent_name="LanguageDetector",
                message=prompt
            )
            
            # Parse response
            result = self._parse_detection_response(response)
            logger.info(f"🌍 Detected language: {result['name']} ({result['code']})")
            return result
    
    async def translate_text(
        self, 
        text: str, 
        target_language: str,
        context: str = "medical"
    ) -> str:
        """
        Translate text to target language.
        
        Args:
            text (str): Text to translate
            target_language (str): Target language code (e.g., 'fr', 'es')
            context (str): Context for translation (e.g., 'medical', 'question')
            
        Returns:
            Translated text
        """
        # Don't translate if already in target language or if English
        if target_language == 'en':
            return text
        
        target_lang_name = self.SUPPORTED_LANGUAGES.get(target_language, 'English')
        
        async with AgentManager(max_retries=2, retry_delay=3.0) as manager:
            agent = manager.create_agent(
                agent_id=self.agent_id,
                name="Translator",
                model=AgentModel.SMALL.value,
                description=f"Translates {context} text"
            )
            
            prompt = f"""
Translate the following {context} text to {target_lang_name}.

IMPORTANT RULES:
1. Maintain medical accuracy - do NOT simplify medical terms
2. Keep the same sentence structure and format
3. If it's a question, keep it as a question
4. Preserve any special formatting (bullet points, numbers, etc.)
5. Return ONLY the translated text, no explanations

Text to translate:
{text}

Translation in {target_lang_name}:"""
            
            response = await manager.chat_with_retry_async(
                agent_name="Translator",
                message=prompt
            )
            
            translated = self._extract_text(response).strip()
            logger.info(f"🌐 Translated to {target_lang_name}")
            return translated
    
    async def translate_questions_batch(
        self,
        questions: Dict[str, Dict[str, str]],
        target_language: str
    ) -> Dict[str, Dict[str, str]]:
        """
        Translate a batch of questions efficiently.
        
        Args:
            questions: Dict of {question_id: {"question": "...", ...}}
            target_language: Target language code
            
        Returns:
            Dict with translated questions
        """
        if target_language == 'en':
            return questions
        
        # Extract all question texts
        question_texts = [q_data['question'] for q_data in questions.values()]
        question_ids = list(questions.keys())
        
        # Batch translate
        target_lang_name = self.SUPPORTED_LANGUAGES.get(target_language, 'English')
        
        async with AgentManager(max_retries=2, retry_delay=3.0) as manager:
            agent = manager.create_agent(
                agent_id=self.agent_id,
                name="BatchTranslator",
                model=AgentModel.SMALL.value,
                description="Batch translator for questions"
            )
            
            # Format questions with numbers
            numbered_questions = "\n".join([
                f"{i+1}. {q}" for i, q in enumerate(question_texts)
            ])
            
            prompt = f"""
Translate these medical eligibility questions to {target_lang_name}.

RULES:
1. Maintain medical accuracy
2. Keep as yes/no questions
3. Preserve the numbering
4. Return ONLY the translations, one per line
5. Format: "1. [translation]"

Questions:
{numbered_questions}

Translations in {target_lang_name}:"""
            
            response = await manager.chat_with_retry_async(
                agent_name="BatchTranslator",
                message=prompt
            )
            
            # Parse numbered responses
            translated_texts = self._parse_numbered_translations(
                self._extract_text(response),
                len(question_texts)
            )
            
            # Reconstruct questions dict
            translated_questions = {}
            for q_id, original_data, translated_text in zip(
                question_ids, 
                questions.values(), 
                translated_texts
            ):
                translated_questions[q_id] = {
                    **original_data,
                    'question': translated_text,
                    'original_question': original_data['question']  # Keep original
                }
            
            logger.info(f"📝 Batch translated {len(translated_questions)} questions to {target_lang_name}")
            return translated_questions
    
    def _parse_detection_response(self, response: Any) -> Dict[str, str]:
        """Parse language detection response"""
        text = self._extract_text(response)
        
        # Try to parse JSON
        import json
        import re
        
        # Extract JSON object
        json_match = re.search(r'\{[^}]+\}', text)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                code = data.get('language_code', 'en')
                return {
                    'code': code,
                    'name': self.SUPPORTED_LANGUAGES.get(code, 'English')
                }
            except json.JSONDecodeError:
                pass
        
        # Fallback: look for language codes
        for code, name in self.SUPPORTED_LANGUAGES.items():
            if code in text.lower() or name.lower() in text.lower():
                return {'code': code, 'name': name}
        
        # Default to English
        return {'code': 'en', 'name': 'English'}
    
    def _parse_numbered_translations(self, text: str, expected_count: int) -> list:
        """Parse numbered translation responses"""
        import re
        
        # Extract numbered lines
        lines = []
        for line in text.split('\n'):
            # Match patterns like "1. ", "1) ", or just number at start
            match = re.match(r'^\s*\d+[\.\)]\s*(.+)$', line.strip())
            if match:
                lines.append(match.group(1).strip())
        
        # If we got the expected count, return them
        if len(lines) == expected_count:
            return lines
        
        # Fallback: split by newlines and take first N non-empty lines
        all_lines = [l.strip() for l in text.split('\n') if l.strip()]
        return all_lines[:expected_count]
    
    def _extract_text(self, response: Any) -> str:
        """Extract text from response"""
        if hasattr(response, 'choices') and len(response.choices) > 0:
            return response.choices[0].message.content
        elif hasattr(response, 'content'):
            return response.content
        elif isinstance(response, str):
            return response
        else:
            return str(response)