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
            # Load existing config to merge and avoid wiping omitted fields
            existing = self.load_config()
            merged = {**existing, **data}

            # Synchronize accounts and top-level fields
            if "accounts" in data:
                accounts = data["accounts"]
                if isinstance(accounts, list) and accounts and isinstance(accounts[0], dict):
                    merged["accounts"] = accounts
                    merged["email"] = accounts[0].get("email", "")
                    merged["gmail_address"] = accounts[0].get("email", "")
                    merged["app_password"] = accounts[0].get("app_password", "")
                else:
                    merged["accounts"] = []
                    merged["email"] = ""
                    merged["gmail_address"] = ""
                    merged["app_password"] = ""
            else:
                # If accounts was not in data, check if email/pwd were passed in data
                email_in_data = "email" in data or "gmail_address" in data
                pwd_in_data = "app_password" in data
                if email_in_data or pwd_in_data:
                    email_val = (data.get("email") if "email" in data else data.get("gmail_address", existing.get("email", ""))).strip()
                    pwd_val = (data.get("app_password") if "app_password" in data else existing.get("app_password", "")).strip()
                    merged["email"] = email_val
                    merged["gmail_address"] = email_val
                    merged["app_password"] = pwd_val
                    existing_accounts = existing.get("accounts", [])
                    if existing_accounts and isinstance(existing_accounts, list):
                        new_accounts = [dict(acc) for acc in existing_accounts]
                        new_accounts[0] = {"email": email_val, "app_password": pwd_val}
                        merged["accounts"] = new_accounts
                    else:
                        merged["accounts"] = [{"email": email_val, "app_password": pwd_val}] if (email_val or pwd_val) else []

            # Synchronize telegram token keys, allowing explicit clearing to empty string
            if "telegram_token" in data or "telegram_bot_token" in data:
                tele_tok = data.get("telegram_token") if "telegram_token" in data else data.get("telegram_bot_token", "")
                merged["telegram_token"] = tele_tok
                merged["telegram_bot_token"] = tele_tok
            else:
                tele_tok = existing.get("telegram_token") or existing.get("telegram_bot_token", "")
                merged["telegram_token"] = tele_tok
                merged["telegram_bot_token"] = tele_tok

            if "telegram_chat_id" not in data and "telegram_chat_id" in existing:
                merged["telegram_chat_id"] = existing["telegram_chat_id"]

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(merged, f, indent=4)
            return True
        except Exception:
            return False
