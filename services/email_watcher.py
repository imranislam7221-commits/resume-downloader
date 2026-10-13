import os
import re
import csv
import email.utils
import threading
from datetime import datetime
from typing import List, Dict, Callable, Optional, Set
from imap_tools import MailBox, AND, MailMessageFlags
from imap_tools.errors import MailboxLoginError, ImapToolsError

from utils.file_utils import sanitize_folder_name, sanitize_filename, get_unique_filepath, ALLOWED_EXTENSIONS
from services.notification_service import send_windows_toast, send_telegram_alert

EXTENSIONS = ALLOWED_EXTENSIONS + ('.rtf',)

def parse_applicant_info(from_header: str):
    name, addr = email.utils.parseaddr(from_header or "")
    clean_name = re.sub(r'[\\/*?:"<>|]', '_', name).strip()
    return clean_name if clean_name else "Applicant", addr or from_header

class EmailWatcher:
    def __init__(
        self,
        email_addr: str,
        app_pwd: str,
        base_dir: str,
        companies: List[Dict[str, str]],
        create_subfolders: bool = True,
        prefix_applicant_name: bool = True,
        enable_desktop_toasts: bool = True,
        telegram_token: str = "",
        telegram_chat_id: str = "",
        log_callback: Callable[[str, str], None] = None,
        on_error_callback: Optional[Callable[[str], None]] = None,
        poll_interval: int = 10
    ):
        self.email_addr = email_addr.strip()
        self.app_pwd = "".join(app_pwd.split())
        self.base_dir = base_dir.strip()
        self.companies = companies
        self.create_subfolders = create_subfolders
        self.prefix_applicant_name = prefix_applicant_name
        self.enable_desktop_toasts = enable_desktop_toasts
        self.telegram_token = telegram_token.strip()
        self.telegram_chat_id = telegram_chat_id.strip()
        self.log = log_callback or (lambda m, l: None)
        self.on_error = on_error_callback
        self.poll_interval = max(5, poll_interval)
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.inspected_uids: Set[str] = set()

    def start(self):
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)

    def _record_manifest(self, company: str, app_name: str, app_email: str, subject: str, fname: str, size_kb: float, full_path: str):
        try:
            os.makedirs(self.base_dir, exist_ok=True)
            manifest_file = os.path.join(self.base_dir, "resumes_manifest.csv")
            needs_header = not os.path.exists(manifest_file)
            with open(manifest_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if needs_header:
                    writer.writerow(["Downloaded At", "Company", "Applicant Name", "Applicant Email", "Email Subject", "Filename", "File Size (KB)", "File Path"])
                writer.writerow([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    company,
                    app_name,
                    app_email,
                    subject,
                    fname,
                    size_kb,
                    full_path
                ])
        except Exception as e:
            self.log(f"Notice: Could not write to resumes_manifest.csv: {e}", "WARNING")

    def _run_loop(self):
        self.log(f"Connecting securely to imap.gmail.com:993 for account: {self.email_addr}...", "INFO")

        while not self.stop_event.is_set():
            try:
                with MailBox("imap.gmail.com").login(self.email_addr, self.app_pwd) as mailbox:
                    self.log("Authenticated with Gmail IMAP. Actively listening for applicant emails...", "SUCCESS")

                    while not self.stop_event.is_set():
                        try:
                            unread_messages = list(mailbox.fetch(AND(seen=False), limit=30, mark_seen=False, reverse=True))

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
                                            f"Applicant identified for '{matched_company}'! Name: '{applicant_name}' | Email: '{applicant_email}'",
                                            "INFO"
                                        )

                                        if self.create_subfolders:
                                            target_folder = os.path.join(self.base_dir, sanitize_folder_name(matched_company))
                                        else:
                                            target_folder = self.base_dir

                                        os.makedirs(target_folder, exist_ok=True)

                                        downloaded_this_email = 0
                                        for att in msg.attachments:
                                            ext = os.path.splitext(att.filename)[1].lower()
                                            if ext in EXTENSIONS:
                                                clean_att = sanitize_filename(att.filename)
                                                if self.prefix_applicant_name and applicant_name != "Applicant":
                                                    norm_name = re.sub(r'\\s+', '_', applicant_name)
                                                    if norm_name.lower() not in clean_att.lower():
                                                        chosen_name = f"{norm_name}_{clean_att}"
                                                    else:
                                                        chosen_name = clean_att
                                                else:
                                                    chosen_name = clean_att

                                                save_path = get_unique_filepath(target_folder, chosen_name)
                                                final_fname = os.path.basename(save_path)

                                                with open(save_path, "wb") as f:
                                                    f.write(att.payload)

                                                size_kb = round(len(att.payload) / 1024, 1)
                                                self._record_manifest(
                                                    company=matched_company,
                                                    app_name=applicant_name,
                                                    app_email=applicant_email,
                                                    subject=msg.subject or "",
                                                    fname=final_fname,
                                                    size_kb=size_kb,
                                                    full_path=save_path
                                                )

                                                downloaded_this_email += 1
                                                folder_lbl = f"{matched_company}/" if self.create_subfolders else "Selected Directory/"
                                                self.log(f"Saved resume: '{final_fname}' ({size_kb} KB) -> [{folder_lbl}]", "SUCCESS")

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
                                                        f"📁 *Saved As:* `{final_fname}` ({size_kb} KB)"
                                                    )
                                                    send_telegram_alert(self.telegram_token, self.telegram_chat_id, tele_msg)

                                        if downloaded_this_email > 0:
                                            self.log(f"Extracted {downloaded_this_email} resume file(s) for '{matched_company}'.", "SUCCESS")
                                        else:
                                            self.log(f"Email matched '{matched_company}', but no attached resume (.pdf/.docx/.doc) found.", "WARNING")

                                        try:
                                            mailbox.flag(msg.uid, MailMessageFlags.SEEN, True)
                                            self.log(f"Email marked as read on Gmail (UID {msg.uid}).", "INFO")
                                        except Exception as flag_err:
                                            self.log(f"Notice: Could not flag email {msg.uid} as read: {flag_err}", "WARNING")

                                    self.inspected_uids.add(msg.uid)

                        except ImapToolsError as fetch_err:
                            self.log(f"IMAP Fetch Warning: {fetch_err}", "WARNING")
                        except Exception as inner_err:
                            self.log(f"Inbox parsing warning: {inner_err}", "WARNING")

                        if self.stop_event.wait(timeout=self.poll_interval):
                            break

            except MailboxLoginError as login_err:
                msg = f"Gmail Authentication Failed: {login_err}. Please ensure 2-Step Verification is active and use a 16-character App Password."
                self.log(msg, "ERROR")
                if self.on_error:
                    self.on_error(msg)
                break
            except Exception as conn_err:
                if self.stop_event.is_set():
                    break
                self.log(f"Connection dropped: {conn_err}. Reconnecting in 10s...", "WARNING")
                if self.stop_event.wait(timeout=10):
                    break

        self.log("Background email monitoring thread terminated cleanly.", "INFO")
