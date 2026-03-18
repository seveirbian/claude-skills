"""Translation service module."""

import time
from typing import Optional
from deep_translator import GoogleTranslator, MicrosoftTranslator, MyMemoryTranslator

from .config import config


class TranslationService:
    """Service for translating text using multiple providers with fallback."""

    def __init__(self):
        """Initialize translation service with configuration."""
        self.translation_config = config.get_translation_config()
        self.enabled = self.translation_config.get('enabled', True)
        self.target_language = self.translation_config.get('target_language', 'zh-CN')
        self.chunk_size = self.translation_config.get('chunk_size', 1000)
        self.services = self.translation_config.get('services', ['google', 'microsoft', 'mymemory'])
        self.retry_attempts = self.translation_config.get('retry_attempts', 3)
        self.delay = self.translation_config.get('delay_between_requests', 1.0)

        # Get service-specific language mappings
        self.language_mappings = self.translation_config.get('language_mappings', {
            'google': 'zh-CN',
            'microsoft': 'zh-Hans',
            'mymemory': 'zh-CN'
        })

        # Initialize translators with appropriate language codes
        self.translators = {
            'google': lambda: GoogleTranslator(source='en', target=self.language_mappings.get('google', 'zh-CN')),
            'microsoft': lambda: MicrosoftTranslator(source='en', target=self.language_mappings.get('microsoft', 'zh-Hans')),
            'mymemory': lambda: MyMemoryTranslator(source='en', target=self.language_mappings.get('mymemory', 'zh-CN'))
        }

    def translate(self, text: str) -> str:
        """Translate text with fallback to multiple services.

        Args:
            text: Text to translate

        Returns:
            Translated text
        """
        if not self.enabled or not text.strip():
            return text

        # Split text into chunks if too long
        if len(text) > self.chunk_size:
            return self._translate_long_text(text)

        return self._translate_chunk(text)

    def _translate_long_text(self, text: str) -> str:
        """Translate long text by splitting into chunks."""
        sentences = text.split('. ')
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk + sentence) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += sentence + ". " if current_chunk else sentence

        if current_chunk:
            chunks.append(current_chunk.strip())

        translated_chunks = []
        for i, chunk in enumerate(chunks):
            print(f"Translating chunk {i+1}/{len(chunks)}...")
            translated = self._translate_chunk(chunk)
            translated_chunks.append(translated)
            time.sleep(self.delay)  # Rate limiting

        return ' '.join(translated_chunks)

    def _translate_chunk(self, text: str) -> str:
        """Translate a single chunk with fallback services."""
        for service_name in self.services:
            translator_factory = self.translators.get(service_name)
            if not translator_factory:
                continue

            for attempt in range(self.retry_attempts):
                try:
                    print(f"Attempting translation with {service_name} (attempt {attempt + 1})...")
                    translator = translator_factory()
                    result = translator.translate(text)

                    if result and result.strip() and result != text:
                        print(f"✅ Translation successful with {service_name}")
                        return result
                    else:
                        print(f"⚠️ {service_name} returned empty/unchanged result")

                except Exception as e:
                    print(f"❌ {service_name} failed (attempt {attempt + 1}): {e}")
                    if attempt < self.retry_attempts - 1:
                        time.sleep(self.delay)

        print("⚠️ All translation services failed, returning original text")
        return text