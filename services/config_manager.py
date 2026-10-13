import os
import json
from typing import Dict, Any, List

class ConfigManager:
    def __init__(self, config_path: str):
        self.config_path = config_path

    def get_defaults(self) -> Dict[str, Any]:
        return {
            "gmail_address": "",
            "app_password": "",
            "base_directory": os.path.dirname(os.path.abspath(self.config_path)),
            "poll_interval": 10,
            "companies": [
                {"name": "Google", "keyword": "google"},
                {"name": "Microsoft", "keyword": "microsoft"}
            ]
        }

    def load_config(self) -> Dict[str, Any]:
        defaults = self.get_defaults()
        if not os.path.exists(self.config_path):
            self.save_config(defaults)
            return defaults
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in defaults.items():
                if k not in data:
                    data[k] = v
            return data
        except Exception:
            return defaults

    def save_config(self, data: Dict[str, Any]) -> bool:
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
        except Exception:
            return False
