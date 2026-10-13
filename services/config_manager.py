import os
import json
from typing import Dict, Any, List

class ConfigManager:
    def __init__(self, config_path: str):
        self.config_path = config_path

    def get_defaults(self) -> Dict[str, Any]:
        return {
            "email": "",
            "gmail_address": "",
            "app_password": "",
            "base_directory": os.path.dirname(os.path.abspath(self.config_path)),
            "create_subfolders": True,
            "prefix_applicant_name": True,
            "enable_desktop_toasts": True,
            "telegram_token": "",
            "telegram_bot_token": "",
            "telegram_chat_id": "",
            "auto_start_monitoring": True,
            "auto_start_with_windows": True,
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
            
            # Synchronize email keys
            email_val = data.get("email") or data.get("gmail_address", "")
            data["email"] = email_val
            data["gmail_address"] = email_val

            # Synchronize telegram token keys
            tele_tok = data.get("telegram_token") or data.get("telegram_bot_token", "")
            data["telegram_token"] = tele_tok
            data["telegram_bot_token"] = tele_tok

            for k, v in defaults.items():
                if k not in data:
                    data[k] = v
            return data
        except Exception:
            return defaults

    def save_config(self, data: Dict[str, Any]) -> bool:
        try:
            # Synchronize email and telegram fields before writing
            email_val = data.get("email") or data.get("gmail_address", "")
            data["email"] = email_val
            data["gmail_address"] = email_val

            tele_tok = data.get("telegram_token") or data.get("telegram_bot_token", "")
            data["telegram_token"] = tele_tok
            data["telegram_bot_token"] = tele_tok

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
        except Exception:
            return False
