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
            "accounts": [],
            "base_directory": os.path.dirname(os.path.abspath(self.config_path)),
            "create_subfolders": True,
            "prefix_applicant_name": True,
            "enable_desktop_toasts": True,
            "telegram_token": "",
            "telegram_bot_token": "",
            "telegram_chat_id": "",
            "auto_start_monitoring": True,
            "auto_start_with_windows": True,
            "monitoring_mode": "cloud_sync",
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
            
            # Synchronize accounts list and single email/pwd fields
            accounts = data.get("accounts")
            if not isinstance(accounts, list):
                accounts = []

            email_val = (data.get("email") or data.get("gmail_address", "")).strip()
            pwd_val = (data.get("app_password", "")).strip()

            if not accounts and (email_val or pwd_val):
                accounts = [{"email": email_val, "app_password": pwd_val}]

            data["accounts"] = accounts
            if accounts and isinstance(accounts[0], dict):
                data["email"] = accounts[0].get("email", "")
                data["gmail_address"] = accounts[0].get("email", "")
                data["app_password"] = accounts[0].get("app_password", "")
            else:
                data["email"] = email_val
                data["gmail_address"] = email_val
                data["app_password"] = pwd_val

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
            # Synchronize accounts and top-level fields
            accounts = data.get("accounts")
            if isinstance(accounts, list) and accounts and isinstance(accounts[0], dict):
                data["email"] = accounts[0].get("email", "")
                data["gmail_address"] = accounts[0].get("email", "")
                data["app_password"] = accounts[0].get("app_password", "")
            else:
                email_val = (data.get("email") or data.get("gmail_address", "")).strip()
                data["email"] = email_val
                data["gmail_address"] = email_val
                if email_val or data.get("app_password"):
                    data["accounts"] = [{"email": email_val, "app_password": data.get("app_password", "")}]

            tele_tok = data.get("telegram_token") or data.get("telegram_bot_token", "")
            data["telegram_token"] = tele_tok
            data["telegram_bot_token"] = tele_tok

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
        except Exception:
            return False
