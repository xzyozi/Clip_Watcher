import json
import os
import logging

logger = logging.getLogger(__name__)

class Translator:
    """
    Handles translation of UI strings.
    """
    def __init__(self, settings_manager, locales_dir="locales", default_lang="en"):
        """
        Initializes the Translator.
        Args:
            settings_manager: The application's settings manager instance.
            locales_dir (str): The directory where locale json files are stored.
            default_lang (str): The fallback language.
        """
        self.settings_manager = settings_manager
        self.default_lang = default_lang
        self.translations = self._load_translations(locales_dir)
        self.current_lang = self.settings_manager.get_setting("language", self.default_lang)
        
        self.settings_manager.event_dispatcher.subscribe("SETTINGS_CHANGED", self._update_language)
        logger.info(f"Translator initialized. Current language: {self.current_lang}")

    def _load_translations(self, locales_dir):
        """Loads all .json translation files from the specified directory."""
        translations = {}
        if not os.path.isdir(locales_dir):
            logger.error(f"Locales directory not found: {locales_dir}")
            return translations
            
        for filename in os.listdir(locales_dir):
            if filename.endswith(".json"):
                lang_code = os.path.splitext(filename)[0]
                filepath = os.path.join(locales_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        translations[lang_code] = json.load(f)
                    logger.info(f"Loaded translation file: {filename}")
                except (json.JSONDecodeError, IOError) as e:
                    logger.error(f"Failed to load or parse {filepath}: {e}")
        return translations

    def _update_language(self, settings):
        """Callback for when settings change."""
        new_lang = settings.get("language", self.default_lang)
        if new_lang != self.current_lang:
            self.current_lang = new_lang
            logger.info(f"Language changed to: {self.current_lang}")
            self.settings_manager.event_dispatcher.dispatch("LANGUAGE_CHANGED")

    def translate(self, key):
        """
        Translates a given key into the current language.
        Falls back to the default language if the key is not found in the current one.
        Returns the key itself if not found in the default language either.
        """
        return self.translations.get(self.current_lang, {}).get(key, 
               self.translations.get(self.default_lang, {}).get(key, key))

    # Alias for translate for shorter calls
    def __call__(self, key):
        return self.translate(key)
