from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.core.config.settings_manager import SettingsManager

logger = logging.getLogger(__name__)

_DEFAULT_LOCALES_DIR = str(Path(__file__).resolve().parents[2] / "locales")


class Translator:
    """
    Handles translation of UI strings.
    """

    def __init__(
        self,
        settings_manager: SettingsManager,
        locales_dir: str | os.PathLike[str] | None = None,
        default_lang: str = "en",
    ) -> None:
        """
        Initializes the Translator.
        Args:
            settings_manager: The application's settings manager instance.
            locales_dir: The directory where locale json files are stored.
                Defaults to the repository's ``locales`` directory resolved from ``__file__``.
            default_lang (str): The fallback language.
        """
        self.settings_manager = settings_manager
        self.default_lang = default_lang
        resolved_dir = (
            _DEFAULT_LOCALES_DIR if locales_dir is None else os.fspath(locales_dir)
        )
        self.locales_dir: str = str(Path(resolved_dir).resolve())
        self.translations: dict[str, dict[str, str]] = self._load_translations(
            self.locales_dir
        )
        raw_lang = self.settings_manager.get_setting("language", self.default_lang)
        self.current_lang: str = (
            raw_lang if isinstance(raw_lang, str) and raw_lang else self.default_lang
        )

        self.settings_manager.event_dispatcher.subscribe(
            "SETTINGS_CHANGED", self._update_language
        )
        logger.info(f"Translator initialized. Current language: {self.current_lang}")

    def _load_translations(self, locales_dir: str) -> dict[str, dict[str, str]]:
        """Loads all .json translation files from the specified directory."""
        translations: dict[str, dict[str, str]] = {}
        if not os.path.isdir(locales_dir):
            logger.error(f"Locales directory not found: {locales_dir}")
            return translations

        for filename in sorted(os.listdir(locales_dir)):
            if filename.endswith(".json"):
                lang_code = os.path.splitext(filename)[0]
                filepath = os.path.join(locales_dir, filename)
                try:
                    with open(filepath, encoding="utf-8") as f:
                        raw_data = json.load(f)
                except (OSError, json.JSONDecodeError) as e:
                    logger.error(f"Failed to load or parse {filepath}: {e}")
                    continue

                if not isinstance(raw_data, dict):
                    logger.warning(
                        "Skipping invalid translation file %s: expected dict, got %s",
                        filepath,
                        type(raw_data).__name__,
                    )
                    continue

                valid_entries: dict[str, str] = {}
                for k, v in raw_data.items():
                    if isinstance(k, str) and isinstance(v, str):
                        valid_entries[k] = v
                    else:
                        logger.warning(
                            "Skipping non-string translation entry in %s: key=%r (%s), value=%s",
                            filepath,
                            k,
                            type(k).__name__,
                            type(v).__name__,
                        )

                translations[lang_code] = valid_entries
                logger.info(f"Loaded translation file: {filename}")
        return translations

    def _update_language(self, settings: dict[str, Any]) -> None:
        """Callback for when settings change."""
        raw_lang = settings.get("language", self.default_lang)
        new_lang = (
            raw_lang if isinstance(raw_lang, str) and raw_lang else self.default_lang
        )
        if new_lang != self.current_lang:
            self.current_lang = new_lang
            logger.info(f"Language changed to: {self.current_lang}")
            self.settings_manager.event_dispatcher.dispatch("LANGUAGE_CHANGED")

    def translate(self, key: str) -> str:
        """
        Translates a given key into the current language.
        Falls back to the default language if the key is not found in the current one.
        Returns the key itself if not found in the default language either.
        """
        return self.translations.get(self.current_lang, {}).get(
            key, self.translations.get(self.default_lang, {}).get(key, key)
        )

    def get(self, key: str, default: str | None = None) -> str:
        """Translates a key with an optional default fallback, similar to dict.get."""
        translated = self.translate(key)
        if translated == key and default is not None:
            return default
        return translated

    # Alias for translate for shorter calls
    def __call__(self, key: str) -> str:
        return self.translate(key)
