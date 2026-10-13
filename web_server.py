import os
import sys
import re
import csv
import json
import time
import io
import zipfile
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional

from flask import Flask, jsonify, request, Response, send_file
from imap_tools import MailBox

from services.config_manager import ConfigManager
from services.email_watcher import EmailWatcher
from services.notification_service import send_windows_toast, send_telegram_alert
from services.startup_manager import is_startup_enabled, enable_startup, disable_startup

app_dir = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(app_dir, "config.json")
config_manager = ConfigManager(config_file)

app = Flask(__name__)

log_messages = []
log_lock = threading.Lock()
email_watcher: Optional[EmailWatcher] = None
watcher_lock = threading.Lock()

MANIFEST_HEADERS = [
    "Downloaded At", "Company", "Applicant Name", "Applicant Email",
    "Email Subject", "Filename", "File Size (KB)", "File Path",
    "SHA256", "Status", "Notes"
]

def add_log(message: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = {"timestamp": timestamp, "level": level, "message": message}
    with log_lock:
        log_messages.append(entry)
        if len(log_messages) > 300:
            log_messages.pop(0)

def get_manifest_records(base_dir: str) -> List[Dict[str, Any]]:
    records = []
    manifest_path = os.path.join(base_dir, "resumes_manifest.csv")
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not row.get("Status"):
                        row["Status"] = "New"
                    if not row.get("Notes"):
                        row["Notes"] = ""
                    records.append(row)
        except Exception as e:
            add_log(f"Notice reading manifest: {e}", "WARNING")
    return list(reversed(records))

def update_manifest_row(base_dir: str, file_path: str, new_status: str, new_notes: str) -> bool:
    manifest_path = os.path.join(base_dir, "resumes_manifest.csv")
    if not os.path.exists(manifest_path):
        return False
    rows = []
    updated = False
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                return False
            col_map = {col.strip(): i for i, col in enumerate(header)}
            path_idx = col_map.get("File Path", 7)
            status_idx = col_map.get("Status", -1)
            notes_idx = col_map.get("Notes", -1)

            # Check if header needs status/notes columns appended
            if status_idx == -1:
                header.append("Status")
                status_idx = len(header) - 1
            if notes_idx == -1:
                header.append("Notes")
                notes_idx = len(header) - 1

            for row in reader:
                if not row:
                    continue
                while len(row) < len(header):
                    row.append("")
                row_path = row[path_idx] if path_idx < len(row) else ""
                
                # Check path match or filename match
                norm_target = os.path.normcase(os.path.abspath(file_path))
                norm_row = os.path.normcase(os.path.abspath(row_path)) if row_path else ""
                if norm_target == norm_row or os.path.basename(file_path) == os.path.basename(row_path):
                    row[status_idx] = new_status
                    row[notes_idx] = new_notes
                    updated = True
                rows.append(row)

        if updated:
            with open(manifest_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(rows)
        return updated
    except Exception as e:
        add_log(f"Error updating candidate status: {e}", "ERROR")
        return False

# Load frontend HTML
HTML_ENTERPRISE_DASHBOARD = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enterprise Resume Downloader & Recruitment Hub</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #060911;
            --bg-card: rgba(15, 23, 42, 0.78);
            --border-card: rgba(255, 255, 255, 0.08);
            --border-focus: #38bdf8;
            --accent-primary: #38bdf8;
            --accent-indigo: #6366f1;
            --accent-emerald: #10b981;
            --accent-rose: #f43f5e;
            --accent-amber: #f59e0b;
            --accent-purple: #a855f7;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --surface-input: #090e1c;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: var(--bg-base);
            color: var(--text-primary);
            min-height: 100vh;
            background-image: 
                radial-gradient(circle at 15% 15%, rgba(56, 189, 248, 0.07) 0%, transparent 40%),
                radial-gradient(circle at 85% 85%, rgba(99, 102, 241, 0.07) 0%, transparent 40%),
                radial-gradient(circle at 50% 50%, rgba(16, 185, 129, 0.04) 0%, transparent 60%);
            background-attachment: fixed;
            display: flex;
            flex-direction: column;
        }

        .header {
            background: rgba(11, 17, 32, 0.85);
            backdrop-filter: blur(16px);
            border-bottom: 1px solid var(--border-card);
            padding: 16px 36px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .brand-container {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .brand-icon {
            width: 42px;
            height: 42px;
            background: linear-gradient(135deg, #0284c7, #6366f1);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            box-shadow: 0 4px 16px rgba(56, 189, 248, 0.3);
        }

        .brand-title {
            font-size: 19px;
            font-weight: 700;
            background: linear-gradient(to right, #f8fafc, #94a3b8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.4px;
        }

        .brand-subtitle {
            font-size: 11px;
            color: var(--text-muted);
            letter-spacing: 0.8px;
            text-transform: uppercase;
            font-weight: 600;
        }

        .header-controls {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 7px 14px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 0.3px;
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid var(--border-card);
        }
        .status-badge.active {
            border-color: rgba(16, 185, 129, 0.4);
            color: #34d399;
            box-shadow: 0 0 16px rgba(16, 185, 129, 0.15);
        }
        .status-badge.inactive {
            border-color: rgba(244, 63, 94, 0.4);
            color: #fb7185;
        }
        .status-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }
        .status-badge.active .status-indicator {
            background-color: #10b981;
            box-shadow: 0 0 8px #10b981;
            animation: pulse-green 2s infinite;
        }
        .status-badge.inactive .status-indicator {
            background-color: #f43f5e;
        }

        @keyframes pulse-green {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(0.85); }
        }

        .btn-action {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 18px;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            border: none;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            font-family: inherit;
        }
        .btn-start {
            background: linear-gradient(135deg, #10b981, #059669);
            color: #ffffff;
            box-shadow: 0 4px 14px rgba(16, 185, 129, 0.3);
        }
        .btn-start:hover {
            box-shadow: 0 6px 20px rgba(16, 185, 129, 0.45);
            transform: translateY(-1px);
        }
        .btn-stop {
            background: linear-gradient(135deg, #f43f5e, #e11d48);
            color: #ffffff;
            box-shadow: 0 4px 14px rgba(244, 63, 94, 0.3);
        }
        .btn-stop:hover {
            box-shadow: 0 6px 20px rgba(244, 63, 94, 0.45);
            transform: translateY(-1px);
        }
        .btn-scan {
            background: linear-gradient(135deg, #0284c7, #2563eb);
            color: #ffffff;
            box-shadow: 0 4px 14px rgba(2, 132, 199, 0.3);
        }
        .btn-scan:hover {
            box-shadow: 0 6px 20px rgba(2, 132, 199, 0.45);
            transform: translateY(-1px);
        }

        .container {
            max-width: 1440px;
            width: 100%;
            margin: 0 auto;
            padding: 28px 36px 60px 36px;
            display: flex;
            flex-direction: column;
            gap: 28px;
        }

        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
        }
        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 14px;
            padding: 18px 20px;
            display: flex;
            flex-direction: column;
            gap: 6px;
            backdrop-filter: blur(12px);
            transition: border-color 0.2s ease, transform 0.2s ease;
        }
        .stat-card:hover {
            border-color: rgba(56, 189, 248, 0.3);
            transform: translateY(-2px);
        }
        .stat-label {
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.6px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .stat-val {
            font-size: 28px;
            font-weight: 800;
            color: #ffffff;
            font-family: 'JetBrains Mono', monospace;
        }
        .stat-sub {
            font-size: 11px;
            color: var(--text-muted);
        }

        /* Main Grid */
        .main-layout {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }

        @media (max-width: 1100px) {
            .main-layout { grid-template-columns: 1fr; }
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 16px;
            padding: 24px;
            backdrop-filter: blur(16px);
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--border-card);
            padding-bottom: 14px;
        }
        .card-title {
            font-size: 16px;
            font-weight: 700;
            letter-spacing: -0.2px;
            display: flex;
            align-items: center;
            gap: 10px;
            color: #ffffff;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .form-label {
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
            letter-spacing: 0.2px;
        }
        .form-input {
            background: var(--surface-input);
            border: 1px solid var(--border-card);
            border-radius: 10px;
            padding: 10px 14px;
            font-size: 13px;
            color: var(--text-primary);
            outline: none;
            transition: all 0.2s ease;
            font-family: inherit;
        }
        .form-input:focus {
            border-color: var(--border-focus);
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.2);
        }

        .toggle-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(9, 14, 28, 0.6);
            border: 1px solid var(--border-card);
            border-radius: 12px;
            padding: 12px 16px;
        }
        .toggle-info {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }
        .toggle-title {
            font-size: 13px;
            font-weight: 600;
            color: #ffffff;
        }
        .toggle-desc {
            font-size: 11px;
            color: var(--text-muted);
        }

        .switch {
            position: relative;
            display: inline-block;
            width: 44px;
            height: 24px;
        }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider {
            position: absolute;
            cursor: pointer;
            top: 0; left: 0; right: 0; bottom: 0;
            background-color: #1e293b;
            transition: .3s;
            border-radius: 24px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .slider:before {
            position: absolute;
            content: "";
            height: 16px; width: 16px;
            left: 3px; bottom: 3px;
            background-color: #94a3b8;
            transition: .3s;
            border-radius: 50%;
        }
        input:checked + .slider {
            background: linear-gradient(135deg, #0284c7, #38bdf8);
        }
        input:checked + .slider:before {
            transform: translateX(20px);
            background-color: #ffffff;
        }

        /* Rules Table */
        .rules-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            font-size: 12px;
        }
        .rules-table th {
            text-align: left;
            padding: 8px 12px;
            color: var(--text-muted);
            border-bottom: 1px solid var(--border-card);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 11px;
        }
        .rules-table td {
            padding: 10px 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            color: var(--text-secondary);
        }
        .rules-table tr:last-child td { border-bottom: none; }

        .btn-icon-danger {
            background: rgba(244, 63, 94, 0.1);
            color: #fb7185;
            border: 1px solid rgba(244, 63, 94, 0.2);
            border-radius: 6px;
            padding: 4px 8px;
            cursor: pointer;
            font-size: 11px;
            transition: all 0.2s ease;
        }
        .btn-icon-danger:hover {
            background: rgba(244, 63, 94, 0.25);
            color: #ffffff;
        }

        /* Candidate Roster Card */
        .roster-card {
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 16px;
            padding: 24px;
            backdrop-filter: blur(16px);
            display: flex;
            flex-direction: column;
            gap: 18px;
        }

        .filter-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            flex-wrap: wrap;
        }

        .search-box {
            position: relative;
            flex: 1;
            min-width: 260px;
        }
        .search-input {
            width: 100%;
            background: var(--surface-input);
            border: 1px solid var(--border-card);
            border-radius: 10px;
            padding: 9px 14px 9px 36px;
            font-size: 13px;
            color: var(--text-primary);
            outline: none;
            transition: all 0.2s ease;
        }
        .search-input:focus {
            border-color: var(--border-focus);
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.2);
        }
        .search-icon {
            position: absolute;
            left: 12px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-muted);
            font-size: 13px;
        }

        .filter-select {
            background: var(--surface-input);
            border: 1px solid var(--border-card);
            border-radius: 10px;
            padding: 9px 14px;
            font-size: 13px;
            color: var(--text-primary);
            outline: none;
            cursor: pointer;
        }

        .action-group {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-card);
            color: var(--text-primary);
            padding: 8px 14px;
            border-radius: 10px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            text-decoration: none;
        }
        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.1);
            border-color: rgba(255, 255, 255, 0.2);
        }

        /* Manifest Table */
        .manifest-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            font-size: 13px;
        }
        .manifest-table th {
            text-align: left;
            padding: 12px 14px;
            color: var(--text-muted);
            border-bottom: 1px solid var(--border-card);
            font-weight: 600;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            background: rgba(9, 14, 28, 0.4);
        }
        .manifest-table td {
            padding: 12px 14px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            vertical-align: middle;
        }
        .manifest-table tr:hover td {
            background: rgba(255, 255, 255, 0.02);
        }

        .company-pill {
            display: inline-block;
            background: rgba(56, 189, 248, 0.1);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.2);
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
        }

        /* Status Pills */
        .status-select-pill {
            padding: 4px 8px;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 700;
            border: 1px solid transparent;
            cursor: pointer;
            outline: none;
            text-transform: uppercase;
            letter-spacing: 0.4px;
        }
        .status-new {
            background: rgba(99, 102, 241, 0.15);
            color: #818cf8;
            border-color: rgba(99, 102, 241, 0.3);
        }
        .status-shortlisted {
            background: rgba(16, 185, 129, 0.18);
            color: #34d399;
            border-color: rgba(16, 185, 129, 0.4);
        }
        .status-interview {
            background: rgba(245, 158, 11, 0.18);
            color: #fbbf24;
            border-color: rgba(245, 158, 11, 0.4);
        }
        .status-hired {
            background: rgba(168, 85, 247, 0.18);
            color: #c084fc;
            border-color: rgba(168, 85, 247, 0.4);
        }
        .status-rejected {
            background: rgba(244, 63, 94, 0.15);
            color: #fb7185;
            border-color: rgba(244, 63, 94, 0.3);
        }

        .btn-note {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-card);
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 11px;
            color: var(--text-secondary);
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            max-width: 140px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .btn-note:hover {
            border-color: #38bdf8;
            color: #ffffff;
        }
        .btn-note.has-note {
            border-color: rgba(56, 189, 248, 0.4);
            color: #38bdf8;
            background: rgba(56, 189, 248, 0.08);
        }

        .btn-preview {
            background: rgba(56, 189, 248, 0.15);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.3);
            border-radius: 6px;
            padding: 5px 10px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .btn-preview:hover {
            background: #38bdf8;
            color: #000000;
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.4);
        }

        /* Terminal Console */
        .terminal-card {
            background: #040711;
            border: 1px solid var(--border-card);
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        }
        .terminal-header {
            background: #090e1c;
            padding: 10px 18px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--border-card);
        }
        .traffic-lights {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .traffic-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }
        .td-red { background-color: #ef4444; }
        .td-yellow { background-color: #f59e0b; }
        .td-green { background-color: #10b981; }

        .terminal-title {
            font-size: 11px;
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-muted);
            letter-spacing: 0.8px;
        }

        .terminal-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            font-family: 'JetBrains Mono', monospace;
            font-size: 10px;
            cursor: pointer;
            padding: 2px 6px;
            border-radius: 4px;
        }
        .terminal-btn:hover { color: #f8fafc; background: rgba(255, 255, 255, 0.05); }

        .terminal-body {
            padding: 14px 18px;
            height: 220px;
            overflow-y: auto;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            line-height: 1.6;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .log-line { display: flex; gap: 10px; }
        .log-time { color: #475569; }
        .log-level-INFO { color: #38bdf8; font-weight: 600; }
        .log-level-SUCCESS { color: #10b981; font-weight: 600; }
        .log-level-WARNING { color: #fbbf24; font-weight: 600; }
        .log-level-ERROR { color: #f43f5e; font-weight: 600; }
        .log-msg { color: #cbd5e1; word-break: break-word; }

        /* Modal styling */
        .modal-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(3, 7, 18, 0.85);
            backdrop-filter: blur(8px);
            z-index: 1000;
            display: none;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .modal-overlay.active { display: flex; }

        .modal-box {
            background: #0b1120;
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 16px;
            width: 100%;
            max-width: 520px;
            padding: 24px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        .modal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--border-card);
            padding-bottom: 12px;
        }
        .modal-title {
            font-size: 16px;
            font-weight: 700;
            color: #ffffff;
        }
        .btn-close {
            background: transparent;
            border: none;
            color: var(--text-muted);
            font-size: 18px;
            cursor: pointer;
        }
        .btn-close:hover { color: #ffffff; }

        /* Fullscreen PDF Modal */
        .pdf-modal-box {
            background: #0b1120;
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 16px;
            width: 92vw;
            height: 90vh;
            max-width: 1200px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.8);
        }
        .pdf-viewer-header {
            background: #090e1c;
            padding: 14px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--border-card);
        }
        .pdf-iframe-container {
            flex: 1;
            width: 100%;
            height: 100%;
            background: #1e293b;
        }
        .pdf-iframe-container iframe {
            width: 100%;
            height: 100%;
            border: none;
        }

        .toast-popup {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: #0f172a;
            border: 1px solid #38bdf8;
            color: #f8fafc;
            padding: 12px 20px;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 500;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
            z-index: 2000;
            display: none;
            animation: fadeIn 0.3s ease;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>
    <header class="header">
        <div class="brand-container">
            <div class="brand-icon">📂</div>
            <div>
                <div class="brand-title">Resume Downloader & Gmail Auto-Sorter</div>
                <div class="brand-subtitle">Autonomous Local Recruitment Engine</div>
            </div>
        </div>
        <div class="header-controls">
            <div id="statusBadge" class="status-badge inactive">
                <span class="status-indicator"></span>
                <span id="statusText">STOPPED</span>
            </div>
            <button id="btnScanNow" class="btn-action btn-scan" onclick="triggerScanNow()">
                <span>⚡ Scan Inbox Now</span>
            </button>
            <button id="btnToggleMonitoring" class="btn-action btn-start" onclick="toggleMonitoring()">
                <span>▶ Start Ingestion</span>
            </button>
        </div>
    </header>

    <div class="container">
        <!-- KPI Analytics -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Resumes Ingested <span>📄</span></div>
                <div class="stat-val" id="statResumes">0</div>
                <div class="stat-sub">100% saved in local drive</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Shortlisted Candidates <span>⭐</span></div>
                <div class="stat-val" id="statShortlisted" style="color: #34d399;">0</div>
                <div class="stat-sub">Ready for interview screening</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Duplicates Prevented <span>⚡</span></div>
                <div class="stat-val" id="statDuplicates" style="color: #38bdf8;">0</div>
                <div class="stat-sub">SHA-256 deduplicated CVs</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Company Sorting Rules <span>🏢</span></div>
                <div class="stat-val" id="statCompanies" style="color: #a855f7;">0</div>
                <div class="stat-sub">Keywords mapped to subfolders</div>
            </div>
        </div>

        <!-- Candidate Roster Table -->
        <div class="roster-card">
            <div class="card-header">
                <div class="card-title">
                    <span>👥</span> Candidate Intake Roster & Recruitment Pipeline
                </div>
                <div class="action-group">
                    <button class="btn-secondary" onclick="openBaseFolder()">
                        <span>📂 Open Folder</span>
                    </button>
                    <button class="btn-secondary" onclick="openZipExportModal()">
                        <span>📦 Export ZIP</span>
                    </button>
                    <a href="/api/manifest/export" class="btn-secondary">
                        <span>📥 Export CSV</span>
                    </a>
                </div>
            </div>

            <!-- Filters -->
            <div class="filter-bar">
                <div class="search-box">
                    <span class="search-icon">🔍</span>
                    <input type="text" id="searchInput" class="search-input" placeholder="Search applicant name, email, company, notes..." oninput="filterRoster()">
                </div>
                <select id="companyFilter" class="filter-select" onchange="filterRoster()">
                    <option value="">All Companies</option>
                </select>
                <select id="statusFilter" class="filter-select" onchange="filterRoster()">
                    <option value="">All Statuses</option>
                    <option value="New">New</option>
                    <option value="Shortlisted">Shortlisted</option>
                    <option value="Interview">Interview</option>
                    <option value="Hired">Hired</option>
                    <option value="Rejected">Rejected</option>
                </select>
            </div>

            <div style="overflow-x: auto;">
                <table class="manifest-table">
                    <thead>
                        <tr>
                            <th>Ingested At</th>
                            <th>Company</th>
                            <th>Applicant</th>
                            <th>Contact</th>
                            <th>File</th>
                            <th>Size</th>
                            <th>Status Pipeline</th>
                            <th>HR Notes</th>
                            <th style="text-align: center;">Actions</th>
                        </tr>
                    </thead>
                    <tbody id="manifestBody">
                        <tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 30px;">Loading candidates...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Main Configuration Layout -->
        <div class="main-layout">
            <!-- Left Card: System Config & Automation -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title"><span>⚙️</span> Automation & Alert Settings</div>
                </div>

                <div class="form-group">
                    <label class="form-label">Gmail Address</label>
                    <input type="email" id="emailAddr" class="form-input" placeholder="example@gmail.com">
                </div>

                <div class="form-group">
                    <label class="form-label">Google 16-Character App Password</label>
                    <input type="password" id="appPwd" class="form-input" placeholder="xxxx xxxx xxxx xxxx">
                </div>

                <div class="form-group">
                    <label class="form-label">Local Save Directory</label>
                    <input type="text" id="baseDir" class="form-input" placeholder="D:/Resumes">
                </div>

                <div class="toggle-row">
                    <div class="toggle-info">
                        <div class="toggle-title">Windows Desktop Toast Notifications</div>
                        <div class="toggle-desc">Native audio toast when a new resume is downloaded</div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <button class="btn-secondary" style="padding: 4px 10px; font-size: 11px;" onclick="testToast()">Test Toast</button>
                        <label class="switch">
                            <input type="checkbox" id="enableToasts" checked>
                            <span class="slider"></span>
                        </label>
                    </div>
                </div>

                <div class="toggle-row">
                    <div class="toggle-info">
                        <div class="toggle-title">Run Silently on Windows Boot</div>
                        <div class="toggle-desc">Background resume intake starts automatically with PC</div>
                    </div>
                    <label class="switch">
                        <input type="checkbox" id="autoStart" onchange="toggleStartup(this.checked)">
                        <span class="slider"></span>
                    </label>
                </div>

                <!-- Telegram Integration -->
                <div style="border-top: 1px solid var(--border-card); padding-top: 14px; display: flex; flex-direction: column; gap: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 13px; font-weight: 700; color: #ffffff;">📱 Telegram Mobile Alerts</span>
                        <button class="btn-secondary" style="padding: 4px 10px; font-size: 11px;" onclick="testTelegram()">Test Alert</button>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Bot Token (Optional)</label>
                        <input type="text" id="telegramToken" class="form-input" placeholder="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Chat ID (Optional)</label>
                        <input type="text" id="telegramChatId" class="form-input" placeholder="Your Telegram Chat ID">
                    </div>
                </div>

                <div style="display: flex; gap: 10px; margin-top: 8px;">
                    <button class="btn-action btn-scan" style="flex: 1;" onclick="saveConfig()">💾 Save Configuration</button>
                    <button class="btn-secondary" onclick="testConnection()">🔌 Test IMAP</button>
                </div>
            </div>

            <!-- Right Card: Company Rules Table -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title"><span>🏢</span> Company Sorting Rules</div>
                    <button class="btn-secondary" onclick="addRuleRow()">+ Add Rule</button>
                </div>
                <div style="font-size: 12px; color: var(--text-muted); line-height: 1.5;">
                    Matching emails from candidates will be sorted into dedicated subfolders based on these keywords.
                </div>
                <div style="max-height: 380px; overflow-y: auto;">
                    <table class="rules-table">
                        <thead>
                            <tr>
                                <th>Target Company</th>
                                <th>Subject/Sender Keyword</th>
                                <th style="width: 50px; text-align: center;">Action</th>
                            </tr>
                        </thead>
                        <tbody id="rulesBody"></tbody>
                    </table>
                </div>
                <button class="btn-secondary" style="align-self: flex-start;" onclick="saveConfig()">Save Rules</button>
            </div>
        </div>

        <!-- Terminal Console -->
        <div class="terminal-card">
            <div class="terminal-header">
                <div class="traffic-lights">
                    <div class="traffic-dot td-red"></div>
                    <div class="traffic-dot td-yellow"></div>
                    <div class="traffic-dot td-green"></div>
                </div>
                <div class="terminal-title">TERMINAL // REAL-TIME INGESTION STREAM</div>
                <div class="terminal-actions">
                    <button class="terminal-btn" onclick="clearLogs()">CLEAR CONSOLE</button>
                </div>
            </div>
            <div class="terminal-body" id="terminalConsole"></div>
        </div>
    </div>

    <!-- Recruiter Notes Modal -->
    <div id="notesModal" class="modal-overlay">
        <div class="modal-box">
            <div class="modal-header">
                <div class="modal-title">📝 Recruiter Candidate Notes</div>
                <button class="btn-close" onclick="closeNotesModal()">&times;</button>
            </div>
            <div id="notesCandidateMeta" style="font-size: 13px; color: #38bdf8; font-weight: 600;"></div>
            <textarea id="notesTextarea" class="form-input" style="height: 130px; resize: vertical;" placeholder="Add interview feedback, expected salary, screening notes..."></textarea>
            <div style="display: flex; justify-content: flex-end; gap: 10px;">
                <button class="btn-secondary" onclick="closeNotesModal()">Cancel</button>
                <button class="btn-action btn-scan" onclick="saveCandidateNote()">Save Note</button>
            </div>
        </div>
    </div>

    <!-- ZIP Export Modal -->
    <div id="zipModal" class="modal-overlay">
        <div class="modal-box">
            <div class="modal-header">
                <div class="modal-title">📦 Export Resumes ZIP Archive</div>
                <button class="btn-close" onclick="closeZipModal()">&times;</button>
            </div>
            <div style="font-size: 13px; color: var(--text-secondary);">
                Select which company archive you want to export. All matching resumes will be compressed into a single ZIP file.
            </div>
            <div class="form-group">
                <label class="form-label">Target Archive</label>
                <select id="zipCompanySelect" class="form-input">
                    <option value="all">All Companies & Resumes</option>
                </select>
            </div>
            <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 8px;">
                <button class="btn-secondary" onclick="closeZipModal()">Cancel</button>
                <button class="btn-action btn-start" onclick="downloadZipArchive()">Download ZIP</button>
            </div>
        </div>
    </div>

    <!-- PDF Viewer Modal -->
    <div id="pdfModal" class="modal-overlay">
        <div class="pdf-modal-box">
            <div class="pdf-viewer-header">
                <div>
                    <div id="pdfViewerTitle" style="font-weight: 700; color: #ffffff; font-size: 15px;">Resume Preview</div>
                    <div id="pdfViewerMeta" style="font-size: 12px; color: #94a3b8;"></div>
                </div>
                <button class="btn-close" onclick="closePdfModal()">&times;</button>
            </div>
            <div class="pdf-iframe-container">
                <iframe id="pdfIframe" src="about:blank"></iframe>
            </div>
        </div>
    </div>

    <!-- Toast Notification -->
    <div id="toastPopup" class="toast-popup"></div>

    <script>
        let allRecords = [];
        let isMonitoring = false;
        let currentNoteTarget = { filePath: '', status: '', notes: '' };

        function showToast(msg) {
            const t = document.getElementById('toastPopup');
            t.innerText = msg;
            t.style.display = 'block';
            setTimeout(() => { t.style.display = 'none'; }, 3500);
        }

        function escapeHtml(str) {
            if (!str) return '';
            return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }
        function escapeJs(str) {
            if (!str) return '';
            return String(str).replace(/\\\\/g, '\\\\\\\\').replace(/'/g, "\\\\'");
        }

        async function init() {
            await loadConfig();
            await loadStartupStatus();
            await fetchStatus();
            await fetchManifest();
            startLogStream();
            setInterval(fetchManifest, 15000);
            setInterval(fetchStatus, 8000);
        }

        async function loadConfig() {
            try {
                const res = await fetch('/api/config');
                const cfg = await res.json();
                document.getElementById('emailAddr').value = cfg.email || '';
                document.getElementById('appPwd').value = cfg.app_password || '';
                document.getElementById('baseDir').value = cfg.base_directory || '';
                document.getElementById('enableToasts').checked = cfg.enable_desktop_toasts !== false;
                document.getElementById('telegramToken').value = cfg.telegram_bot_token || '';
                document.getElementById('telegramChatId').value = cfg.telegram_chat_id || '';

                renderRules(cfg.companies || []);
                updateCompanyDropdowns(cfg.companies || []);
            } catch (e) {
                console.error(e);
            }
        }

        function renderRules(rules) {
            const tbody = document.getElementById('rulesBody');
            tbody.innerHTML = '';
            rules.forEach((r, idx) => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><input type="text" class="form-input rule-name" value="${escapeHtml(r.name || '')}" style="padding: 6px 10px; font-size: 12px;"></td>
                    <td><input type="text" class="form-input rule-kw" value="${escapeHtml(r.keyword || '')}" style="padding: 6px 10px; font-size: 12px;"></td>
                    <td style="text-align: center;"><button class="btn-icon-danger" onclick="removeRuleRow(${idx})">✕</button></td>
                `;
                tbody.appendChild(tr);
            });
            document.getElementById('statCompanies').innerText = rules.length;
        }

        function addRuleRow() {
            const tbody = document.getElementById('rulesBody');
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><input type="text" class="form-input rule-name" placeholder="e.g. Google" style="padding: 6px 10px; font-size: 12px;"></td>
                <td><input type="text" class="form-input rule-kw" placeholder="e.g. google" style="padding: 6px 10px; font-size: 12px;"></td>
                <td style="text-align: center;"><button class="btn-icon-danger" onclick="this.closest('tr').remove()">✕</button></td>
            `;
            tbody.appendChild(tr);
        }

        function removeRuleRow(idx) {
            const tbody = document.getElementById('rulesBody');
            if (tbody.children[idx]) {
                tbody.children[idx].remove();
            }
        }

        function updateCompanyDropdowns(companies) {
            const compFilter = document.getElementById('companyFilter');
            const zipCompSelect = document.getElementById('zipCompanySelect');
            const currentFilterVal = compFilter.value;

            compFilter.innerHTML = '<option value="">All Companies</option>';
            zipCompSelect.innerHTML = '<option value="all">All Companies & Resumes</option>';

            const compSet = new Set();
            companies.forEach(c => { if (c.name) compSet.add(c.name.trim()); });
            allRecords.forEach(r => { if (r.Company) compSet.add(r.Company.trim()); });

            compSet.forEach(c => {
                const opt1 = document.createElement('option');
                opt1.value = c; opt1.innerText = c;
                compFilter.appendChild(opt1);

                const opt2 = document.createElement('option');
                opt2.value = c; opt2.innerText = c;
                zipCompSelect.appendChild(opt2);
            });
            compFilter.value = currentFilterVal;
        }

        async function saveConfig() {
            const rules = [];
            document.querySelectorAll('#rulesBody tr').forEach(tr => {
                const name = tr.querySelector('.rule-name').value.trim();
                const kw = tr.querySelector('.rule-kw').value.trim();
                if (name || kw) rules.push({ name, keyword: kw });
            });

            const payload = {
                email: document.getElementById('emailAddr').value.trim(),
                app_password: document.getElementById('appPwd').value.trim(),
                base_directory: document.getElementById('baseDir').value.trim(),
                enable_desktop_toasts: document.getElementById('enableToasts').checked,
                telegram_bot_token: document.getElementById('telegramToken').value.trim(),
                telegram_chat_id: document.getElementById('telegramChatId').value.trim(),
                companies: rules
            };

            const res = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.success) {
                showToast('Configuration saved successfully!');
                updateCompanyDropdowns(rules);
            } else {
                alert('Save error: ' + data.error);
            }
        }

        async function loadStartupStatus() {
            try {
                const res = await fetch('/api/startup/status');
                const data = await res.json();
                document.getElementById('autoStart').checked = data.enabled;
            } catch (e) { console.error(e); }
        }

        async function toggleStartup(enable) {
            try {
                const res = await fetch('/api/startup/toggle', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ enable })
                });
                const data = await res.json();
                showToast(data.message || 'Startup updated');
            } catch (e) { console.error(e); }
        }

        async function testToast() {
            showToast('Sending test Windows Desktop Toast...');
            await fetch('/api/test_toast', { method: 'POST' });
        }

        async function testTelegram() {
            showToast('Sending Telegram alert...');
            const res = await fetch('/api/test_telegram', { method: 'POST' });
            const data = await res.json();
            if (data.success) showToast('Telegram alert sent!');
            else alert('Telegram error: ' + data.message);
        }

        async function testConnection() {
            showToast('Testing Gmail IMAP authentication...');
            const res = await fetch('/api/test_connection', { method: 'POST' });
            const data = await res.json();
            if (data.success) showToast('Gmail IMAP Connected successfully!');
            else alert('IMAP Connection Failed: ' + data.error);
        }

        async function triggerScanNow() {
            showToast('⚡ Triggering instant inbox scan...');
            const res = await fetch('/api/scan_now', { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                showToast('⚡ Scan triggered! Check terminal stream.');
                setTimeout(fetchManifest, 2000);
            } else {
                alert(data.message);
            }
        }

        async function fetchStatus() {
            try {
                const res = await fetch('/api/monitoring/status');
                const data = await res.json();
                isMonitoring = data.is_monitoring;

                const badge = document.getElementById('statusBadge');
                const statusText = document.getElementById('statusText');
                const btnToggle = document.getElementById('btnToggleMonitoring');

                if (isMonitoring) {
                    badge.className = 'status-badge active';
                    statusText.innerText = 'MONITORING ACTIVE';
                    btnToggle.className = 'btn-action btn-stop';
                    btnToggle.innerHTML = '<span>⏹ Stop Engine</span>';
                } else {
                    badge.className = 'status-badge inactive';
                    statusText.innerText = 'STOPPED';
                    btnToggle.className = 'btn-action btn-start';
                    btnToggle.innerHTML = '<span>▶ Start Ingestion</span>';
                }

                if (data.duplicates_prevented !== undefined) {
                    document.getElementById('statDuplicates').innerText = data.duplicates_prevented;
                }
            } catch (e) { console.error(e); }
        }

        async function toggleMonitoring() {
            const url = isMonitoring ? '/api/monitoring/stop' : '/api/monitoring/start';
            const res = await fetch(url, { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                await fetchStatus();
                showToast(isMonitoring ? 'Monitoring started' : 'Monitoring stopped');
            } else {
                alert(data.error);
            }
        }

        async function fetchManifest() {
            try {
                const res = await fetch('/api/manifest');
                const data = await res.json();
                allRecords = data.records || [];
                document.getElementById('statResumes').innerText = allRecords.length;

                const shortlisted = allRecords.filter(r => (r.Status || '').toLowerCase() === 'shortlisted').length;
                document.getElementById('statShortlisted').innerText = shortlisted;

                filterRoster();
            } catch (e) { console.error(e); }
        }

        function filterRoster() {
            const q = document.getElementById('searchInput').value.toLowerCase();
            const comp = document.getElementById('companyFilter').value;
            const status = document.getElementById('statusFilter').value;

            const filtered = allRecords.filter(r => {
                if (comp && r.Company !== comp) return false;
                if (status && (r.Status || 'New') !== status) return false;
                if (!q) return true;
                const matchStr = `${r['Applicant Name']} ${r['Applicant Email']} ${r.Company} ${r.Filename} ${r.Notes || ''}`.toLowerCase();
                return matchStr.includes(q);
            });

            renderManifestTable(filtered);
        }

        function getStatusClass(status) {
            switch ((status || '').toLowerCase()) {
                case 'shortlisted': return 'status-shortlisted';
                case 'interview': return 'status-interview';
                case 'hired': return 'status-hired';
                case 'rejected': return 'status-rejected';
                default: return 'status-new';
            }
        }

        function renderManifestTable(records) {
            const tbody = document.getElementById('manifestBody');
            if (!records || records.length === 0) {
                tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 30px;">No matching candidates found.</td></tr>';
                return;
            }

            tbody.innerHTML = records.map(r => {
                const status = r.Status || 'New';
                const notes = r.Notes || '';
                const hasNote = notes.trim().length > 0;
                const statusClass = getStatusClass(status);

                return `
                    <tr>
                        <td style="color: #64748b; font-size: 12px;">${escapeHtml(r['Downloaded At'] || '')}</td>
                        <td><span class="company-pill">${escapeHtml(r.Company || 'General')}</span></td>
                        <td style="font-weight: 700; color: #ffffff;">${escapeHtml(r['Applicant Name'] || 'Applicant')}</td>
                        <td style="color: #94a3b8; font-size: 12px;">${escapeHtml(r['Applicant Email'] || '')}</td>
                        <td style="font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #38bdf8;">
                            📄 ${escapeHtml(r.Filename || '')}
                        </td>
                        <td style="color: #64748b; font-size: 12px;">${escapeHtml(r['File Size (KB)'] || '0')} KB</td>
                        <td>
                            <select class="status-select-pill ${statusClass}" onchange="updateCandidateStatus('${escapeJs(r['File Path'])}', this.value, '${escapeJs(notes)}')">
                                <option value="New" ${status === 'New' ? 'selected' : ''}>New</option>
                                <option value="Shortlisted" ${status === 'Shortlisted' ? 'selected' : ''}>Shortlisted</option>
                                <option value="Interview" ${status === 'Interview' ? 'selected' : ''}>Interview</option>
                                <option value="Hired" ${status === 'Hired' ? 'selected' : ''}>Hired</option>
                                <option value="Rejected" ${status === 'Rejected' ? 'selected' : ''}>Rejected</option>
                            </select>
                        </td>
                        <td>
                            <button class="btn-note ${hasNote ? 'has-note' : ''}" onclick="openNotesModal('${escapeJs(r['File Path'])}', '${escapeJs(r['Applicant Name'])}', '${escapeJs(status)}', '${escapeJs(notes)}')">
                                📝 ${hasNote ? escapeHtml(notes.substring(0, 14) + (notes.length > 14 ? '...' : '')) : 'Add Note'}
                            </button>
                        </td>
                        <td style="text-align: center;">
                            <button class="btn-preview" onclick="previewPdf('${escapeJs(r['Applicant Name'])}', '${escapeJs(r.Company)}', '${escapeJs(r.Filename)}', '${escapeJs(r['File Path'])}')">👁️ Preview</button>
                            <button class="btn-secondary" style="padding: 4px 8px; font-size: 11px; margin-left: 4px;" onclick="openSpecificFile('${escapeJs(r['File Path'])}')">📂 Open</button>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        async function updateCandidateStatus(filePath, newStatus, currentNotes) {
            try {
                const res = await fetch('/api/manifest/update_status', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ file_path: filePath, status: newStatus, notes: currentNotes })
                });
                const data = await res.json();
                if (data.success) {
                    showToast(`Candidate status updated to: ${newStatus}`);
                    await fetchManifest();
                } else {
                    alert('Update failed: ' + data.error);
                }
            } catch (e) { console.error(e); }
        }

        function openNotesModal(filePath, appName, status, notes) {
            currentNoteTarget = { filePath, status, notes };
            document.getElementById('notesCandidateMeta').innerText = `Candidate: ${appName}`;
            document.getElementById('notesTextarea').value = notes || '';
            document.getElementById('notesModal').classList.add('active');
        }

        function closeNotesModal() {
            document.getElementById('notesModal').classList.remove('active');
        }

        async function saveCandidateNote() {
            const newNote = document.getElementById('notesTextarea').value.trim();
            try {
                const res = await fetch('/api/manifest/update_status', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        file_path: currentNoteTarget.filePath,
                        status: currentNoteTarget.status,
                        notes: newNote
                    })
                });
                const data = await res.json();
                if (data.success) {
                    closeNotesModal();
                    showToast('Candidate notes saved!');
                    await fetchManifest();
                } else {
                    alert('Save note error: ' + data.error);
                }
            } catch (e) { console.error(e); }
        }

        function openZipExportModal() {
            document.getElementById('zipModal').classList.add('active');
        }
        function closeZipModal() {
            document.getElementById('zipModal').classList.remove('active');
        }
        function downloadZipArchive() {
            const comp = document.getElementById('zipCompanySelect').value;
            closeZipModal();
            window.location.href = `/api/manifest/export_zip?company=${encodeURIComponent(comp)}`;
        }

        function previewPdf(appName, company, filename, filePath) {
            document.getElementById('pdfViewerTitle').innerText = `${appName} - ${filename}`;
            document.getElementById('pdfViewerMeta').innerText = `Company: ${company} | Path: ${filePath}`;
            document.getElementById('pdfIframe').src = `/api/view_pdf?path=${encodeURIComponent(filePath)}`;
            document.getElementById('pdfModal').classList.add('active');
        }
        function closePdfModal() {
            document.getElementById('pdfModal').classList.remove('active');
            document.getElementById('pdfIframe').src = 'about:blank';
        }

        async function openBaseFolder() {
            await fetch('/api/open_folder', { method: 'POST' });
        }
        async function openSpecificFile(path) {
            await fetch('/api/open_file', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path })
            });
        }

        function startLogStream() {
            const consoleDiv = document.getElementById('terminalConsole');
            const evtSource = new EventSource('/api/logs/stream');
            evtSource.onmessage = function(e) {
                try {
                    const entry = JSON.parse(e.data);
                    const line = document.createElement('div');
                    line.className = 'log-line';
                    line.innerHTML = `
                        <span class="log-time">[${entry.timestamp}]</span>
                        <span class="log-level-${entry.level}">[${entry.level}]</span>
                        <span class="log-msg">${escapeHtml(entry.message)}</span>
                    `;
                    consoleDiv.appendChild(line);
                    consoleDiv.scrollTop = consoleDiv.scrollHeight;
                } catch (err) {}
            };
        }

        async function clearLogs() {
            await fetch('/api/logs/clear', { method: 'POST' });
            document.getElementById('terminalConsole').innerHTML = '';
        }

        window.onload = init;
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return HTML_ENTERPRISE_DASHBOARD

@app.route("/api/config", methods=["GET"])
def get_config():
    cfg = config_manager.load_config()
    email_val = cfg.get("email") or cfg.get("gmail_address", "")
    cfg["email"] = email_val
    cfg["gmail_address"] = email_val
    cfg["telegram_bot_token"] = cfg.get("telegram_bot_token") or cfg.get("telegram_token", "")
    return jsonify(cfg)

@app.route("/api/config", methods=["POST"])
def save_config_endpoint():
    try:
        data = request.json or {}
        email_val = data.get("email") or data.get("gmail_address", "")
        data["email"] = email_val
        data["gmail_address"] = email_val
        if "telegram_bot_token" in data:
            data["telegram_token"] = data["telegram_bot_token"]
        config_manager.save_config(data)
        add_log("Configuration updated via recruitment hub.", "INFO")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/startup/status", methods=["GET"])
def startup_status():
    return jsonify({"enabled": is_startup_enabled()})

@app.route("/api/startup/toggle", methods=["POST"])
def startup_toggle():
    try:
        data = request.json or {}
        enable = data.get("enable", False)
        if enable:
            ok = enable_startup()
            msg = "Silent Windows Startup enabled." if ok else "Failed to enable startup."
        else:
            ok = disable_startup()
            msg = "Silent Windows Startup disabled." if ok else "Failed to disable startup."
        return jsonify({"success": ok, "message": msg, "enabled": is_startup_enabled()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/test_toast", methods=["POST"])
def test_toast_endpoint():
    send_windows_toast(
        title="📄 Resume Downloader Active",
        message="Windows Desktop Toast is working perfectly with sound!"
    )
    add_log("Dispatched test Windows Desktop Toast.", "INFO")
    return jsonify({"success": True})

@app.route("/api/test_telegram", methods=["POST"])
def test_telegram_endpoint():
    cfg = config_manager.load_config()
    tok = cfg.get("telegram_bot_token") or cfg.get("telegram_token", "")
    cid = cfg.get("telegram_chat_id", "")
    ok, msg = send_telegram_alert(tok, cid, "🚀 *Resume Downloader Alert Test*\n\nYour recruitment alert system is active!")
    add_log(f"Dispatched test Telegram alert. Result: {msg}", "INFO" if ok else "WARNING")
    return jsonify({"success": ok, "message": msg})

@app.route("/api/view_pdf", methods=["GET"])
def view_pdf_endpoint():
    file_path = request.args.get("path", "")
    if not file_path or not os.path.exists(file_path):
        return Response("Resume PDF file not found.", status=404)
    if not file_path.lower().endswith(".pdf"):
        return Response("Only PDF documents can be previewed directly.", status=400)
    return send_file(file_path, mimetype="application/pdf")

@app.route("/api/test_connection", methods=["POST"])
def test_connection_endpoint():
    cfg = config_manager.load_config()
    email_addr = (cfg.get("email") or cfg.get("gmail_address", "")).strip()
    app_pwd = "".join((cfg.get("app_password", "")).split())
    if not email_addr or not app_pwd:
        return jsonify({"success": False, "error": "Email and 16-character App Password are required."})
    try:
        with MailBox("imap.gmail.com").login(email_addr, app_pwd):
            pass
        add_log("IMAP connection test successful for " + email_addr, "SUCCESS")
        return jsonify({"success": True})
    except Exception as e:
        add_log(f"IMAP connection test failed: {e}", "ERROR")
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/manifest", methods=["GET"])
def get_manifest():
    cfg = config_manager.load_config()
    base_dir = cfg.get("base_directory", app_dir)
    records = get_manifest_records(base_dir)
    return jsonify({"records": records})

@app.route("/api/manifest/update_status", methods=["POST"])
def update_status_endpoint():
    try:
        data = request.json or {}
        file_path = data.get("file_path", "")
        new_status = data.get("status", "New")
        notes = data.get("notes", "")

        cfg = config_manager.load_config()
        base_dir = cfg.get("base_directory", app_dir)
        ok = update_manifest_row(base_dir, file_path, new_status, notes)
        if ok:
            add_log(f"Updated candidate '{os.path.basename(file_path)}' status to '{new_status}'.", "INFO")
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Could not find matching candidate record."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/manifest/export", methods=["GET"])
def export_manifest():
    cfg = config_manager.load_config()
    base_dir = cfg.get("base_directory", app_dir)
    manifest_path = os.path.join(base_dir, "resumes_manifest.csv")
    if os.path.exists(manifest_path):
        return send_file(manifest_path, as_attachment=True, download_name="resumes_manifest.csv")
    return Response("Downloaded At,Company,Applicant Name,Applicant Email,Email Subject,Filename,File Size (KB),File Path,SHA256,Status,Notes\n", mimetype="text/csv")

@app.route("/api/manifest/export_zip", methods=["GET"])
def export_zip_endpoint():
    try:
        company = request.args.get("company", "all").strip()
        cfg = config_manager.load_config()
        base_dir = cfg.get("base_directory", app_dir)

        records = get_manifest_records(base_dir)
        if company and company.lower() != "all":
            filtered_records = [r for r in records if r.get("Company", "").lower() == company.lower()]
            zip_filename = f"resumes_{company}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        else:
            filtered_records = records
            zip_filename = f"all_resumes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Summary CSV
            csv_str_io = io.StringIO()
            writer = csv.DictWriter(csv_str_io, fieldnames=MANIFEST_HEADERS)
            writer.writeheader()
            for r in filtered_records:
                writer.writerow(r)
            zip_file.writestr("resumes_manifest_summary.csv", csv_str_io.getvalue())

            # Add actual files
            added_paths = set()
            for r in filtered_records:
                fpath = r.get("File Path", "")
                if fpath and os.path.exists(fpath) and fpath not in added_paths:
                    arcname = os.path.join(r.get("Company", "General"), r.get("Filename", os.path.basename(fpath)))
                    zip_file.write(fpath, arcname=arcname)
                    added_paths.add(fpath)

        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name=zip_filename
        )
    except Exception as e:
        add_log(f"Error generating ZIP archive: {e}", "ERROR")
        return Response(f"Failed to generate ZIP: {e}", status=500)

@app.route("/api/scan_now", methods=["POST"])
def scan_now_endpoint():
    global email_watcher
    with watcher_lock:
        if email_watcher and email_watcher.thread and email_watcher.thread.is_alive():
            email_watcher.trigger_scan_now()
            add_log("Manual instant scan requested. Checking inbox right now...", "INFO")
            return jsonify({"success": True, "message": "Instant scan initiated!"})
        else:
            return jsonify({"success": False, "message": "Monitoring engine is stopped. Please start ingestion first."})

@app.route("/api/open_folder", methods=["POST"])
def open_base_folder():
    cfg = config_manager.load_config()
    base_dir = cfg.get("base_directory", app_dir)
    if os.path.exists(base_dir):
        os.startfile(base_dir)
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Base directory does not exist."})

@app.route("/api/open_file", methods=["POST"])
def open_file():
    data = request.json or {}
    fpath = data.get("path", "")
    if fpath and os.path.exists(fpath):
        os.startfile(fpath)
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "File not found."})

@app.route("/api/monitoring/status", methods=["GET"])
def monitoring_status():
    global email_watcher
    with watcher_lock:
        is_active = (email_watcher is not None and email_watcher.thread is not None and email_watcher.thread.is_alive())
        dups = email_watcher.duplicates_prevented if email_watcher else 0
    return jsonify({
        "is_monitoring": is_active,
        "log_count": len(log_messages),
        "duplicates_prevented": dups
    })

@app.route("/api/monitoring/start", methods=["POST"])
def start_monitoring():
    global email_watcher
    cfg = config_manager.load_config()

    email_addr = (cfg.get("email") or cfg.get("gmail_address", "")).strip()
    app_pwd = "".join((cfg.get("app_password", "")).split())
    base_dir = cfg.get("base_directory", "").strip()

    if not email_addr or not app_pwd or not base_dir:
        return jsonify({"success": False, "error": "Please configure Email, App Password, and Local Directory."})

    with watcher_lock:
        if email_watcher and email_watcher.thread and email_watcher.thread.is_alive():
            return jsonify({"success": True, "message": "Already monitoring."})

        email_watcher = EmailWatcher(
            email_addr=email_addr,
            app_pwd=app_pwd,
            base_dir=base_dir,
            companies=cfg.get("companies", []),
            create_subfolders=cfg.get("create_subfolders", True),
            prefix_applicant_name=cfg.get("prefix_applicant_name", True),
            enable_desktop_toasts=cfg.get("enable_desktop_toasts", True),
            telegram_token=cfg.get("telegram_bot_token") or cfg.get("telegram_token", ""),
            telegram_chat_id=cfg.get("telegram_chat_id", ""),
            log_callback=add_log,
            poll_interval=10
        )
        email_watcher.start()

    add_log(f"Autonomous background monitoring started for '{email_addr}'.", "SUCCESS")
    return jsonify({"success": True})

def stop_monitoring_internal():
    global email_watcher
    with watcher_lock:
        if email_watcher:
            email_watcher.stop()
            email_watcher = None

@app.route("/api/monitoring/stop", methods=["POST"])
def stop_monitoring():
    stop_monitoring_internal()
    add_log("Monitoring stopped.", "INFO")
    return jsonify({"success": True})

@app.route("/api/logs/clear", methods=["POST"])
def clear_logs():
    with log_lock:
        log_messages.clear()
    return jsonify({"success": True})

@app.route("/api/logs/stream")
def stream_logs():
    def event_stream():
        last_index = 0
        while True:
            with log_lock:
                current_len = len(log_messages)
                if last_index < current_len:
                    for i in range(last_index, current_len):
                        yield f"data: {json.dumps(log_messages[i])}\n\n"
                    last_index = current_len
            time.sleep(1)
    return Response(event_stream(), mimetype="text/event-stream")

if __name__ == "__main__":
    add_log("Enterprise Recruitment Hub initialized on http://127.0.0.1:5000", "SUCCESS")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
