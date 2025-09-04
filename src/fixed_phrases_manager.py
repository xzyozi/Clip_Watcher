import json
import os

class FixedPhrasesManager:
    def __init__(self, file_path="fixed_phrases.json"):
        self.file_path = file_path
        self.phrases = self._load_phrases()

    def _load_phrases(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return [] # Return empty list if JSON is malformed
        return []

    def _save_phrases(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.phrases, f, ensure_ascii=False, indent=4)

    def get_phrases(self):
        return self.phrases

    def add_phrase(self, phrase):
        if phrase and phrase not in self.phrases:
            self.phrases.append(phrase)
            self._save_phrases()
            return True
        return False

    def update_phrase(self, old_phrase, new_phrase):
        try:
            index = self.phrases.index(old_phrase)
            if new_phrase and new_phrase not in self.phrases:
                self.phrases[index] = new_phrase
                self._save_phrases()
                return True
            elif new_phrase == old_phrase:
                return True # No change needed
        except ValueError:
            pass # old_phrase not found
        return False

    def delete_phrase(self, phrase):
        if phrase in self.phrases:
            self.phrases.remove(phrase)
            self._save_phrases()
            return True
        return False
