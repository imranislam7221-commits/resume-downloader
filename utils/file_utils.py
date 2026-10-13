import os
import re
import time
from typing import Tuple

ALLOWED_EXTENSIONS: Tuple[str, ...] = ('.pdf', '.docx', '.doc')

def sanitize_folder_name(name: str) -> str:
    cleaned = re.sub(r'[\\/*?:"<>|]', '_', name).strip()
    return cleaned if cleaned else 'Unnamed_Company'

def sanitize_filename(filename: str) -> str:
    base = os.path.basename(filename)
    cleaned = re.sub(r'[\\/*?:"<>|]', '_', base).strip()
    return cleaned if cleaned else f'attachment_{int(time.time())}'

def get_unique_filepath(directory: str, filename: str) -> str:
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(directory, filename)
    counter = 1
    while os.path.exists(candidate):
        candidate = os.path.join(directory, f"{base}_{counter}{ext}")
        counter += 1
    return candidate
