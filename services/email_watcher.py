import os
import re
import csv
import email.utils
import hashlib
import threading
from datetime import datetime
from typing import List, Dict, Callable, Optional, Set
try:
    from imap_tools import MailBox, AND, MailMessageFlags
    from imap_tools.errors import MailboxLoginError, ImapToolsError
except ImportError:
    MailBox = AND = MailMessageFlags = None
    class MailboxLoginError(Exception): pass
    class ImapToolsError(Exception): pass

from utils.file_utils import sanitize_folder_name, sanitize_filename, get_unique_filepath, ALLOWED_EXTENSIONS
from services.notification_service import send_windows_toast, send_telegram_alert

EXTENSIONS = ALLOWED_EXTENSIONS + ('.rtf',)
MANIFEST_HEADERS = [
    "Downloaded At", "Company", "Applicant Name", "Applicant Email",
    "Email Subject", "Filename", "File Size (KB)", "File Path",
    "SHA256", "Status", "Notes"
]

def parse_applicant_info(from_header: str):
    header_str = (from_header or "").strip()
    name, addr = email.utils.parseaddr(header_str)
    # If parseaddr missed parts of display name due to colons or non-RFC quoting
    if "<" in header_str and ">" in header_str:
        prefix = header_str[:header_str.rfind("<")].strip().strip('"\'')
        if prefix:
            name = prefix

    clean_name = re.sub(r'[\r\n\t]', ' ', name)
    clean_name = re.sub(r'[\\/*?:"<>|]', '_', clean_name).strip()
    return clean_name if clean_name else "Applicant", addr or header_str

class EmailWatcher:
    def __init__(
        self,
        email_addr: str = "",
        app_pwd: str = "",
        accounts: Optional[List[Dict[str, str]]] = None,
        base_dir: str = "",
        companies: Optional[List[Dict[str, str]]] = None,
        create_subfolders: bool = True,
        prefix_applicant_name: bool = True,
        enable_desktop_toasts: bool = True,
        telegram_token: str = "",
        telegram_chat_id: str = "",
        log_callback: Optional[Callable[[str, str], None]] = None,
        on_error_callback: Optional[Callable[[str], None]] = None,
        poll_interval: int = 10
    ):
        raw_accounts = accounts if (accounts and isinstance(accounts, list)) else []
        self.accounts = [
            {"email": a.get("email", "").strip(), "app_password": "".join((a.get("app_password", "")).split())}
            for a in raw_accounts
            if a.get("email") and a.get("app_password")
        ]
        if not self.accounts and email_addr and app_pwd:
            self.accounts = [{"email": email_addr.strip(), "app_password": "".join(app_pwd.split())}]

        self.email_addr = self.accounts[0]["email"] if self.accounts else (email_addr.strip() if email_addr else "")
        self.app_pwd = self.accounts[0]["app_password"] if self.accounts else ("".join(app_pwd.split()) if app_pwd else "")
        self.base_dir = base_dir.strip()
        self.companies = companies or []
        self.create_subfolders = create_subfolders
        self.prefix_applicant_name = prefix_applicant_name
        self.enable_desktop_toasts = enable_desktop_toasts
        self.telegram_token = telegram_token.strip()
        self.telegram_chat_id = telegram_chat_id.strip()
        self.log = log_callback or (lambda m, l: None)
        self.on_error = on_error_callback
        self.poll_interval = max(5, poll_interval)
        self.stop_event = threading.Event()
        self.scan_now_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.worker_threads: List[threading.Thread] = []
        self.inspected_uids: Set[str] = set()
        self.known_hashes: Set[str] = set()
        self.hash_lock = threading.Lock()
        self.manifest_lock = threading.Lock()
        self.duplicates_prevented = 0
        self._load_existing_hashes()

    def _load_existing_hashes(self):
        """Loads SHA256 hashes of previously downloaded files to prevent duplicate downloads."""
        manifest_file = os.path.join(self.base_dir, "resumes_manifest.csv")
        if os.path.exists(manifest_file):
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        sha = row.get("SHA256", "").strip()
                        if sha:
                            with self.hash_lock:
                                self.known_hashes.add(sha)
            except Exception as e:
                self.log(f"Notice: Could not index existing resume hashes: {e}", "WARNING")

    def start(self):
        self.stop_event.clear()
        self.scan_now_event.clear()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.scan_now_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        for w in self.worker_threads:
            if w.is_alive():
                w.join(timeout=2.0)

    def trigger_scan_now(self):
        """Wake up all account worker threads immediately to scan inboxes without waiting."""
        self.scan_now_event.set()
        threading.Timer(0.5, self.scan_now_event.clear).start()

    def _record_manifest(
        self,
        company: str,
        app_name: str,
        app_email: str,
        subject: str,
        fname: str,
        size_kb: float,
        full_path: str,
        sha256_hash: str,
        status: str = "New",
        notes: str = ""
    ):
        with self.manifest_lock:
            try:
                os.makedirs(self.base_dir, exist_ok=True)
                manifest_file = os.path.join(self.base_dir, "resumes_manifest.csv")
                needs_header = not os.path.exists(manifest_file)
                
                # If manifest exists but with old header format, migrate it seamlessly
                if os.path.exists(manifest_file):
                    with open(manifest_file, "r", encoding="utf-8") as f:
                        first_line = f.readline()
                    if "SHA256" not in first_line:
                        self._migrate_manifest_file(manifest_file)
                        needs_header = False

                with open(manifest_file, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    if needs_header:
                        writer.writerow(MANIFEST_HEADERS)
                    writer.writerow([
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        company,
                        app_name,
                        app_email,
                        subject,
                        fname,
                        size_kb,
                        full_path,
                        sha256_hash,
                        status,
                        notes
                    ])
            except Exception as e:
                self.log(f"Notice: Could not write to resumes_manifest.csv: {e}", "WARNING")

    def _migrate_manifest_file(self, manifest_file: str):
        """Migrate legacy CSV without breaking previous candidate history."""
        try:
            rows = []
            with open(manifest_file, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                for r in reader:
                    if r:
                        # Old format has 8 columns: [Downloaded At, Company, Applicant Name, Applicant Email, Email Subject, Filename, File Size (KB), File Path]
                        while len(r) < len(MANIFEST_HEADERS):
                            r.append("") # Pad missing columns (SHA256, Status, Notes)
                        if len(r) >= 10 and not r[9]:
                            r[9] = "New" # Default status
                        rows.append(r[:len(MANIFEST_HEADERS)])

            with open(manifest_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(MANIFEST_HEADERS)
                writer.writerows(rows)
            self.log("Upgraded resumes_manifest.csv to professional schema (SHA256, Status, Notes).", "INFO")
        except Exception as e:
            self.log(f"Notice during manifest upgrade: {e}", "WARNING")

    def _run_loop(self):
        if MailBox is None:
            msg = "imap-tools is not installed. Please install required dependencies: pip install -r requirements.txt"
            self.log(msg, "ERROR")
            if self.on_error:
                self.on_error(msg)
            return

        if not self.accounts:
            self.log("No valid Gmail accounts configured for monitoring.", "ERROR")
            return

        acc_count = len(self.accounts)
        self.log(f"⚡ Multi-Account Monitoring Engine active for {acc_count} Gmail account(s).", "SUCCESS")

        if acc_count == 1:
            acc = self.accounts[0]
            self._monitor_account(acc["email"], acc["app_password"])
        else:
            self.worker_threads = []
            for acc in self.accounts:
                t = threading.Thread(
                    target=self._monitor_account,
                    args=(acc["email"], acc["app_password"]),
                    daemon=True,
                    name=f"Worker-{acc['email']}"
                )
                self.worker_threads.append(t)
                t.start()

            for t in self.worker_threads:
                t.join()

    def _monitor_account(self, email_addr: str, app_pwd: str):
        tag = f"[{email_addr}]" if len(self.accounts) > 1 else ""
        self.log(f"{tag} Connecting securely to imap.gmail.com:993...", "INFO")

        while not self.stop_event.is_set():
            try:
                with MailBox("imap.gmail.com").login(email_addr, app_pwd) as mailbox:
                    self.log(f"{tag} Authenticated with Gmail IMAP. Actively listening for applicant emails...", "SUCCESS")

                    while not self.stop_event.is_set():
                        try:
                            unread_messages = list(mailbox.fetch(AND(seen=False), limit=50, mark_seen=False, reverse=True))

                            if unread_messages:
                                for msg in unread_messages:
                                    if self.stop_event.is_set():
                                        break

                                    if msg.uid in self.inspected_uids:
                                        continue

                                    sender_raw = msg.from_ or ""
                                    applicant_name, applicant_email = parse_applicant_info(sender_raw)
                                    sender = sender_raw.lower()
                                    subject = (msg.subject or "").lower()
                                    matched_company = None

                                    for comp in self.companies:
                                        kw = comp.get("keyword", "").strip().lower()
                                        if kw and (kw in sender or kw in subject):
                                            matched_company = comp.get("name", "").strip()
                                            break

                                    if matched_company:
                                        self.log(
                                            f"{tag} Applicant identified for '{matched_company}'! Name: '{applicant_name}' | Email: '{applicant_email}'",
                                            "INFO"
                                        )

                                        if self.create_subfolders:
                                            target_folder = os.path.join(self.base_dir, sanitize_folder_name(matched_company))
                                        else:
                                            target_folder = self.base_dir

                                        os.makedirs(target_folder, exist_ok=True)

                                        downloaded_this_email = 0
                                        for att in msg.attachments:
                                            if not att.filename:
                                                continue
                                            ext = os.path.splitext(att.filename)[1].lower()
                                            if ext in EXTENSIONS:
                                                payload = att.payload
                                                payload_len = len(payload)
                                                
                                                # Reject empty (0-byte) or abnormally large (> 30MB) files
                                                if payload_len < 512:
                                                    self.log(f"{tag} Skipped corrupt/empty attachment '{att.filename}' (<512 bytes).", "WARNING")
                                                    continue
                                                if payload_len > 30 * 1024 * 1024:
                                                    self.log(f"{tag} Skipped oversize attachment '{att.filename}' (>30 MB).", "WARNING")
                                                    continue

                                                # Calculate SHA-256 checksum for professional deduplication across accounts
                                                file_sha = hashlib.sha256(payload).hexdigest()
                                                with self.hash_lock:
                                                    is_dup = file_sha in self.known_hashes
                                                    if is_dup:
                                                        self.duplicates_prevented += 1

                                                if is_dup:
                                                    self.log(
                                                        f"{tag} ⚡ [DEDUPLICATION] Skipped duplicate resume '{att.filename}' from {applicant_name} (SHA-256 matched an already downloaded CV).",
                                                        "WARNING"
                                                    )
                                                    continue

                                                clean_att = sanitize_filename(att.filename)
                                                if self.prefix_applicant_name and applicant_name != "Applicant":
                                                    norm_name = re.sub(r'\s+', '_', applicant_name)
                                                    if norm_name.lower() not in clean_att.lower():
                                                        chosen_name = f"{norm_name}_{clean_att}"
                                                    else:
                                                        chosen_name = clean_att
                                                else:
                                                    chosen_name = clean_att

                                                save_path = get_unique_filepath(target_folder, chosen_name)
                                                final_fname = os.path.basename(save_path)

                                                with open(save_path, "wb") as f:
                                                    f.write(payload)

                                                with self.hash_lock:
                                                    self.known_hashes.add(file_sha)

                                                size_kb = round(payload_len / 1024, 1)

                                                self._record_manifest(
                                                    company=matched_company,
                                                    app_name=applicant_name,
                                                    app_email=applicant_email,
                                                    subject=msg.subject or "",
                                                    fname=final_fname,
                                                    size_kb=size_kb,
                                                    full_path=save_path,
                                                    sha256_hash=file_sha,
                                                    status="New",
                                                    notes=f"Downloaded via {email_addr}"
                                                )

                                                downloaded_this_email += 1
                                                folder_lbl = f"{matched_company}/" if self.create_subfolders else "Selected Directory/"
                                                self.log(f"{tag} Saved resume: '{final_fname}' ({size_kb} KB) -> [{folder_lbl}]", "SUCCESS")

                                                # 1. Trigger Windows Desktop Toast Notification
                                                if self.enable_desktop_toasts:
                                                    send_windows_toast(
                                                        title=f"📄 New Resume ({matched_company})",
                                                        message=f"Applicant: {applicant_name}\nSaved: {final_fname}"
                                                    )

                                                # 2. Trigger Telegram Mobile Alert (if configured)
                                                if self.telegram_token and self.telegram_chat_id:
                                                    tele_msg = (
                                                        f"📄 *New Resume Downloaded!*\n\n"
                                                        f"🏢 *Company:* `{matched_company}`\n"
                                                        f"👤 *Applicant:* {applicant_name}\n"
                                                        f"✉️ *Email:* `{applicant_email}`\n"
                                                        f"📥 *Account:* `{email_addr}`\n"
                                                        f"📁 *Saved As:* `{final_fname}` ({size_kb} KB)"
                                                    )
                                                    send_telegram_alert(self.telegram_token, self.telegram_chat_id, tele_msg)

                                        if downloaded_this_email > 0:
                                            self.log(f"{tag} Extracted {downloaded_this_email} resume file(s) for '{matched_company}'.", "SUCCESS")
                                        else:
                                            self.log(f"{tag} Email matched '{matched_company}', but no new attached resume (.pdf/.docx/.doc) found.", "WARNING")

                                        try:
                                            mailbox.flag(msg.uid, MailMessageFlags.SEEN, True)
                                            self.log(f"{tag} Email marked as read on Gmail (UID {msg.uid}).", "INFO")
                                        except Exception as flag_err:
                                            self.log(f"{tag} Notice: Could not flag email {msg.uid} as read: {flag_err}", "WARNING")

                                    self.inspected_uids.add(msg.uid)
                                    if len(self.inspected_uids) > 10000:
                                        self.inspected_uids = set(list(self.inspected_uids)[-5000:])

                        except ImapToolsError as fetch_err:
                            self.log(f"{tag} IMAP Fetch Warning: {fetch_err}", "WARNING")
                        except Exception as inner_err:
                            self.log(f"{tag} Inbox parsing warning: {inner_err}", "WARNING")

                        # Wait for poll_interval OR scan_now trigger
                        if self.scan_now_event.wait(timeout=self.poll_interval):
                            self.log(f"{tag} ⚡ Instant scan triggered! Checking inbox right now...", "INFO")

            except MailboxLoginError as login_err:
                msg = f"{tag} Gmail Authentication Failed: {login_err}. Please ensure 2-Step Verification is active and use a 16-character App Password."
                self.log(msg, "ERROR")
                if self.on_error:
                    self.on_error(msg)
                break
            except Exception as conn_err:
                if self.stop_event.is_set():
                    break
                self.log(f"{tag} Connection dropped: {conn_err}. Reconnecting in 10s...", "WARNING")
                if self.stop_event.wait(timeout=10):
                    break

        self.log(f"{tag} Background email monitoring worker terminated.", "INFO")
