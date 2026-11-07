import os
import re
import time
import threading
from typing import Tuple

ALLOWED_EXTENSIONS: Tuple[str, ...] = ('.pdf', '.docx', '.doc', '.rtf')

# Shared global lock for all resume manifest CSV operations across threads/services
MANIFEST_LOCK = threading.RLock()

WINDOWS_RESERVED_NAMES = {
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
}

def sanitize_folder_name(name: str) -> str:
    cleaned = re.sub(r'[\\/*?:"<>|]', '_', name).strip().rstrip('. ')
    # Guard against relative traversal like '..' or '.'
    if cleaned in ('.', '..', ''):
        return 'Unnamed_Company'
    # Guard against Windows DOS reserved device names
    if cleaned.upper() in WINDOWS_RESERVED_NAMES:
        cleaned = f"_{cleaned}"
    return cleaned if cleaned else 'Unnamed_Company'

def sanitize_filename(filename: str) -> str:
    base = os.path.basename(filename)
    cleaned = re.sub(r'[\\/*?:"<>|]', '_', base).strip().rstrip('. ')
    stem, ext = os.path.splitext(cleaned)
    if stem.upper() in WINDOWS_RESERVED_NAMES:
        stem = f"_{stem}"
    if not stem or stem in ('.', '..'):
        stem = f"attachment_{int(time.time())}"
    result = f"{stem}{ext}" if ext else stem
    return result if result else f'attachment_{int(time.time())}'

def get_unique_filepath(directory: str, filename: str) -> str:
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(directory, filename)
    counter = 1
    while os.path.exists(candidate):
        candidate = os.path.join(directory, f"{base}_{counter}{ext}")
        counter += 1
    return candidate
