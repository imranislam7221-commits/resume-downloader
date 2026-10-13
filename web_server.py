import os
import sys
import csv
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from flask import Flask, request, jsonify, render_template_string, send_file, Response

app_dir = r"D:\Imran parsonal\pervez vi mollik\Resume downloader"
sys.path.insert(0, app_dir)

from services.config_manager import ConfigManager
from services.email_watcher import EmailWatcher
from utils.file_utils import sanitize_folder_name, sanitize_filename, ALLOWED_EXTENSIONS
from imap_tools import MailBox
from imap_tools.errors import MailboxLoginError

app = Flask(__name__)

CONFIG_PATH = os.path.join(app_dir, "config.json")
config_manager = ConfigManager(CONFIG_PATH)

logs_history = []
is_monitoring = False
active_watcher: Optional[EmailWatcher] = None

def add_log(message: str, level: str = "INFO"):
    entry = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "level": level.upper(),
        "message": message
    }
    logs_history.append(entry)
    if len(logs_history) > 400:
        logs_history.pop(0)

add_log("Resume Downloader Intelligence Engine initialized.", "INFO")

def get_manifest_records(base_dir: str) -> List[Dict[str, Any]]:
    records = []
    manifest_path = os.path.join(base_dir, "resumes_manifest.csv")
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append(row)
        except Exception:
            pass
    return list(reversed(records))

HTML_ULTIMATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resume Downloader & Gmail Auto-Sorter | Pro Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #060911;
            --bg-card: rgba(15, 23, 42, 0.75);
            --border-card: rgba(255, 255, 255, 0.08);
            --border-focus: #38bdf8;
            --accent-primary: #38bdf8;
            --accent-indigo: #6366f1;
            --accent-emerald: #10b981;
            --accent-rose: #f43f5e;
            --accent-amber: #f59e0b;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --surface-input: #090e1c;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Plus Jakarta Sans', sans-serif;
        }

        body {
            background-color: var(--bg-base);
            background-image: 
                radial-gradient(circle at 10% 0%, rgba(56, 189, 248, 0.12) 0%, transparent 40%),
                radial-gradient(circle at 90% 10%, rgba(99, 102, 241, 0.14) 0%, transparent 45%),
                radial-gradient(circle at 50% 100%, rgba(16, 185, 129, 0.08) 0%, transparent 50%);
            background-attachment: fixed;
            color: var(--text-primary);
            min-height: 100vh;
            padding: 30px 20px;
        }

        .container {
            max-width: 1240px;
            margin: 0 auto;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 22px 30px;
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 20px;
            backdrop-filter: blur(24px);
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.4);
            margin-bottom: 26px;
        }

        .logo-wrap {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .logo-icon {
            width: 52px;
            height: 52px;
            border-radius: 14px;
            background: linear-gradient(135deg, #0284c7, #6366f1);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 26px;
            box-shadow: 0 8px 20px rgba(2, 132, 199, 0.35);
        }

        .logo-text h1 {
            font-size: 23px;
            font-weight: 800;
            letter-spacing: -0.5px;
            background: linear-gradient(135deg, #ffffff 40%, #94a3b8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .logo-text p {
            font-size: 13px;
            color: var(--text-secondary);
            font-weight: 400;
            margin-top: 2px;
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .status-badge {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 20px;
            border-radius: 9999px;
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            transition: all 0.3s ease;
        }

        .status-idle {
            background: rgba(148, 163, 184, 0.1);
            color: #94a3b8;
            border: 1px solid rgba(148, 163, 184, 0.25);
        }

        .status-active {
            background: rgba(16, 185, 129, 0.16);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.4);
            box-shadow: 0 0 25px rgba(16, 185, 129, 0.25);
        }

        .dot-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: currentColor;
        }

        .status-active .dot-indicator {
            animation: pulse-ring 1.8s infinite;
        }

        @keyframes pulse-ring {
            0% { transform: scale(0.9); opacity: 0.8; }
            50% { transform: scale(1.4); opacity: 1; }
            100% { transform: scale(0.9); opacity: 0.8; }
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 18px;
            margin-bottom: 26px;
        }

        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 18px;
            padding: 20px;
            backdrop-filter: blur(20px);
            position: relative;
            overflow: hidden;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }

        .stat-card:hover {
            transform: translateY(-2px);
            border-color: rgba(255, 255, 255, 0.16);
        }

        .stat-label {
            font-size: 12px;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.8px;
        }

        .stat-value {
            font-size: 32px;
            font-weight: 800;
            color: var(--text-primary);
            margin: 8px 0 2px;
            letter-spacing: -1px;
        }

        .stat-sub {
            font-size: 12px;
            color: var(--text-secondary);
        }

        .action-banner {
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 20px;
            padding: 22px 28px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 26px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
        }

        .action-info h3 { font-size: 18px; font-weight: 700; }
        .action-info p { font-size: 13px; color: var(--text-secondary); margin-top: 3px; }

        .btn-hero {
            padding: 16px 36px;
            border-radius: 14px;
            border: none;
            font-size: 16px;
            font-weight: 800;
            letter-spacing: 0.5px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 12px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .btn-hero-start {
            background: linear-gradient(135deg, #10b981, #059669);
            color: #ffffff;
            box-shadow: 0 8px 25px rgba(16, 185, 129, 0.4);
        }

        .btn-hero-start:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 30px rgba(16, 185, 129, 0.55);
        }

        .btn-hero-stop {
            background: linear-gradient(135deg, #f43f5e, #e11d48);
            color: #ffffff;
            box-shadow: 0 8px 25px rgba(244, 63, 94, 0.4);
        }

        .btn-hero-stop:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 30px rgba(244, 63, 94, 0.55);
        }

        .main-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 26px;
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 20px;
            padding: 24px;
            backdrop-filter: blur(20px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .card-title {
            font-size: 16px;
            font-weight: 700;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .form-group {
            margin-bottom: 16px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        label {
            font-size: 13px;
            font-weight: 600;
            color: var(--text-secondary);
            display: flex;
            justify-content: space-between;
        }

        .input-wrap {
            position: relative;
            display: flex;
            align-items: center;
        }

        input[type="text"], input[type="password"] {
            width: 100%;
            background: var(--surface-input);
            border: 1px solid var(--border-card);
            border-radius: 12px;
            padding: 12px 16px;
            color: var(--text-primary);
            font-size: 14px;
            outline: none;
            transition: all 0.2s ease;
        }

        input:focus {
            border-color: var(--border-focus);
            box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.15);
        }

        .btn-toggle-pwd {
            position: absolute;
            right: 12px;
            background: transparent;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            font-size: 16px;
        }

        .toggle-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 16px;
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--border-card);
            border-radius: 12px;
            margin-top: 8px;
        }

        .toggle-text h4 { font-size: 13px; font-weight: 600; }
        .toggle-text p { font-size: 11px; color: var(--text-muted); margin-top: 1px; }

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
            background-color: #334155;
            transition: .3s;
            border-radius: 34px;
        }

        .slider:before {
            position: absolute;
            content: "";
            height: 16px;
            width: 16px;
            left: 4px;
            bottom: 4px;
            background-color: white;
            transition: .3s;
            border-radius: 50%;
        }

        input:checked + .slider { background-color: var(--accent-emerald); }
        input:checked + .slider:before { transform: translateX(20px); }

        .company-preset-bar {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 14px;
        }

        .preset-badge {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-card);
            padding: 5px 10px;
            border-radius: 8px;
            font-size: 11.5px;
            font-weight: 500;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.2s;
        }

        .preset-badge:hover {
            background: rgba(56, 189, 248, 0.15);
            color: var(--accent-primary);
            border-color: rgba(56, 189, 248, 0.3);
        }

        .rules-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0 8px;
            margin-bottom: 12px;
        }

        .rules-table th {
            text-align: left;
            font-size: 11px;
            font-weight: 700;
            color: var(--text-muted);
            padding: 0 10px 4px;
            text-transform: uppercase;
            letter-spacing: 0.6px;
        }

        .rule-row td {
            background: rgba(15, 23, 42, 0.55);
            border-top: 1px solid var(--border-card);
            border-bottom: 1px solid var(--border-card);
            padding: 6px 8px;
        }

        .rule-row td:first-child {
            border-left: 1px solid var(--border-card);
            border-radius: 10px 0 0 10px;
        }

        .rule-row td:last-child {
            border-right: 1px solid var(--border-card);
            border-radius: 0 10px 10px 0;
            text-align: center;
            width: 48px;
        }

        .rule-row input {
            background: transparent !important;
            border: none !important;
            padding: 8px 10px !important;
            color: var(--text-primary);
            font-size: 13px;
        }

        .btn-delete-rule {
            background: rgba(244, 63, 94, 0.12);
            color: var(--accent-rose);
            border: 1px solid rgba(244, 63, 94, 0.25);
            border-radius: 8px;
            padding: 6px 10px;
            cursor: pointer;
            font-weight: 700;
            transition: all 0.2s;
        }

        .btn-delete-rule:hover {
            background: rgba(244, 63, 94, 0.25);
            transform: scale(1.08);
        }

        .btn-ghost {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-card);
            padding: 8px 14px;
            border-radius: 10px;
            font-size: 12.5px;
            font-weight: 600;
            color: var(--text-primary);
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn-ghost:hover { background: rgba(255, 255, 255, 0.1); }

        .btn-primary-small {
            background: linear-gradient(135deg, #0284c7, #2563eb);
            border: none;
            color: #fff;
            padding: 8px 14px;
            border-radius: 10px;
            font-size: 12.5px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn-primary-small:hover { filter: brightness(1.15); }

        /* Manifest / Downloaded Resumes Card */
        .manifest-card {
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 20px;
            padding: 24px;
            margin-bottom: 26px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
        }

        .manifest-toolbar {
            display: flex;
            gap: 12px;
            align-items: center;
        }

        .search-input {
            width: 220px !important;
            padding: 8px 12px !important;
            font-size: 13px !important;
        }

        .manifest-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0 8px;
            margin-top: 10px;
        }

        .manifest-table th {
            text-align: left;
            font-size: 11px;
            font-weight: 700;
            color: var(--text-muted);
            padding: 0 12px 6px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .m-row td {
            background: rgba(15, 23, 42, 0.6);
            border-top: 1px solid var(--border-card);
            border-bottom: 1px solid var(--border-card);
            padding: 10px 12px;
            font-size: 13px;
        }

        .m-row td:first-child {
            border-left: 1px solid var(--border-card);
            border-radius: 10px 0 0 10px;
        }

        .m-row td:last-child {
            border-right: 1px solid var(--border-card);
            border-radius: 0 10px 10px 0;
        }

        .company-pill {
            display: inline-block;
            background: rgba(56, 189, 248, 0.15);
            color: var(--accent-primary);
            border: 1px solid rgba(56, 189, 248, 0.3);
            border-radius: 6px;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: 700;
        }

        .empty-placeholder {
            text-align: center;
            padding: 30px;
            color: var(--text-muted);
            font-size: 13px;
        }

        .terminal-card {
            background: #02050e;
            border: 1px solid rgba(255, 255, 255, 0.09);
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 15px 40px rgba(0, 0, 0, 0.5);
        }

        .terminal-header {
            background: rgba(15, 23, 42, 0.6);
            border-bottom: 1px solid var(--border-card);
            padding: 14px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .traffic-lights {
            display: flex;
            gap: 8px;
            align-items: center;
        }

        .traffic-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }

        .td-red { background: #ef4444; }
        .td-yellow { background: #f59e0b; }
        .td-green { background: #10b981; }

        .terminal-title {
            font-size: 12.5px;
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-muted);
            font-weight: 500;
        }

        .terminal-actions {
            display: flex;
            gap: 12px;
        }

        .terminal-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            font-size: 12px;
            font-family: 'JetBrains Mono', monospace;
            cursor: pointer;
            transition: color 0.2s;
        }

        .terminal-btn:hover { color: var(--text-primary); }

        .terminal-body {
            height: 260px;
            overflow-y: auto;
            padding: 18px 22px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12.5px;
            line-height: 1.7;
        }

        .log-row {
            display: flex;
            gap: 12px;
            margin-bottom: 6px;
        }

        .lr-time { color: #475569; }
        .lr-level { font-weight: 700; width: 75px; }
        .lr-level.INFO { color: #38bdf8; }
        .lr-level.SUCCESS { color: #34d399; }
        .lr-level.WARNING { color: #fbbf24; }
        .lr-level.ERROR { color: #f87171; }
        .lr-msg { color: #cbd5e1; flex: 1; word-break: break-all; }

        #toast {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: rgba(15, 23, 42, 0.95);
            border: 1px solid var(--border-card);
            color: var(--text-primary);
            padding: 14px 22px;
            border-radius: 12px;
            font-size: 14px;
            font-weight: 600;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(12px);
            opacity: 0;
            transform: translateY(20px);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            pointer-events: none;
            z-index: 999;
        }

        #toast.show {
            opacity: 1;
            transform: translateY(0);
        }

        @media (max-width: 900px) {
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            .main-grid { grid-template-columns: 1fr; }
            .action-banner { flex-direction: column; gap: 16px; text-align: center; }
            .btn-hero { width: 100%; justify-content: center; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo-wrap">
                <div class="logo-icon">📂</div>
                <div class="logo-text">
                    <h1>Resume Downloader & Gmail Auto-Sorter</h1>
                    <p>Real-time applicant routing, smart naming & automated folder ingestion</p>
                </div>
            </div>
            <div class="header-actions">
                <div id="statusBadge" class="status-badge status-idle">
                    <span class="dot-indicator"></span>
                    <span id="statusText">IDLE / STOPPED</span>
                </div>
            </div>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Emails Scanned</div>
                <div class="stat-value" id="statScanned">0</div>
                <div class="stat-sub">From Gmail Inbox</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Matched Company Emails</div>
                <div class="stat-value" id="statMatched">0</div>
                <div class="stat-sub">Applicant emails identified</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Resumes Downloaded</div>
                <div class="stat-value" id="statResumes">0</div>
                <div class="stat-sub">.pdf, .docx, .doc files</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Active Company Rules</div>
                <div class="stat-value" id="statCompanies">0</div>
                <div class="stat-sub">Dynamic filters active</div>
            </div>
        </div>

        <div class="action-banner">
            <div class="action-info">
                <h3 id="heroTitle">Gmail Ingestion Engine Ready</h3>
                <p id="heroSubtitle">Click Start to connect to Gmail and begin real-time applicant scanning & downloading</p>
            </div>
            <button id="heroBtn" class="btn-hero btn-hero-start" onclick="toggleMonitoring()">
                <span>▶ START MONITORING</span>
            </button>
        </div>

        <div class="main-grid">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">🔑 Credentials & Destination Path</div>
                    <button class="btn-ghost" onclick="testConnection()">⚡ Test Connection</button>
                </div>

                <div class="form-group">
                    <label>Gmail Address</label>
                    <input type="text" id="gmailAddress" placeholder="e.g. yourname@gmail.com">
                </div>

                <div class="form-group">
                    <label>
                        <span>Google App Password (16 chars)</span>
                        <a href="https://myaccount.google.com/apppasswords" target="_blank" style="color: var(--accent-primary); text-decoration: none; font-size: 11px;">Generate 16-char Password ↗</a>
                    </label>
                    <div class="input-wrap">
                        <input type="password" id="appPassword" placeholder="e.g. abcd efgh ijkl mnop">
                        <button class="btn-toggle-pwd" onclick="togglePasswordVisibility()">👁</button>
                    </div>
                </div>

                <div class="form-group">
                    <label>Base Download Directory (On Your PC)</label>
                    <input type="text" id="baseDirectory" placeholder="e.g. D:\\Resumes">
                </div>

                <div class="toggle-row">
                    <div class="toggle-text">
                        <h4>Create Company Subfolders</h4>
                        <p>Save into <code>[Base Directory]/[Company Name]/</code></p>
                    </div>
                    <label class="switch">
                        <input type="checkbox" id="createSubfolders" checked onchange="saveConfig(true)">
                        <span class="slider"></span>
                    </label>
                </div>

                <div class="toggle-row">
                    <div class="toggle-text">
                        <h4>Prepend Applicant Name to Filename</h4>
                        <p>E.g. <code>Karim_Hasan_Resume.pdf</code> instead of generic names</p>
                    </div>
                    <label class="switch">
                        <input type="checkbox" id="prefixApplicantName" checked onchange="saveConfig(true)">
                        <span class="slider"></span>
                    </label>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <div class="card-title">📋 Company Filtering Rules</div>
                    <button class="btn-primary-small" onclick="addRuleRow('', '')">+ Add Custom Rule</button>
                </div>

                <div class="company-preset-bar">
                    <span style="font-size: 11px; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Quick Add:</span>
                    <span class="preset-badge" onclick="addPresetRule('Google', 'google')">+ Google</span>
                    <span class="preset-badge" onclick="addPresetRule('Microsoft', 'microsoft')">+ Microsoft</span>
                    <span class="preset-badge" onclick="addPresetRule('Amazon', 'amazon')">+ Amazon</span>
                    <span class="preset-badge" onclick="addPresetRule('Netflix', 'netflix')">+ Netflix</span>
                    <span class="preset-badge" onclick="addPresetRule('HR Applicant', 'resume')">+ Resume Keyword</span>
                </div>

                <table class="rules-table">
                    <thead>
                        <tr>
                            <th style="width: 42%;">Company Name</th>
                            <th style="width: 48%;">Keyword / Sender Email</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody id="rulesBody"></tbody>
                </table>
            </div>
        </div>

        <!-- Downloaded Resumes Manifest Table -->
        <div class="manifest-card">
            <div class="card-header">
                <div class="card-title">📁 Downloaded Resumes & Applicant Index</div>
                <div class="manifest-toolbar">
                    <input type="text" id="manifestSearch" class="search-input" placeholder="Search applicant, company..." oninput="filterManifestTable()">
                    <button class="btn-ghost" onclick="openBaseFolder()">📂 Open Folder</button>
                    <a href="/api/manifest/export" class="btn-primary-small" style="text-decoration: none; display: flex; align-items: center; gap: 6px;">
                        <span>📥 Export CSV</span>
                    </a>
                </div>
            </div>
            <div style="overflow-x: auto;">
                <table class="manifest-table">
                    <thead>
                        <tr>
                            <th>Downloaded At</th>
                            <th>Company</th>
                            <th>Applicant Name</th>
                            <th>Applicant Email</th>
                            <th>Filename</th>
                            <th>Size</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody id="manifestBody">
                        <tr><td colspan="7" class="empty-placeholder">No resumes downloaded yet. Start monitoring to begin!</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <div class="terminal-card">
            <div class="terminal-header">
                <div class="traffic-lights">
                    <div class="traffic-dot td-red"></div>
                    <div class="traffic-dot td-yellow"></div>
                    <div class="traffic-dot td-green"></div>
                </div>
                <div class="terminal-title">TERMINAL // REAL-TIME INGESTION STREAM</div>
                <div class="terminal-actions">
                    <button class="terminal-btn" onclick="clearLogs()">CLEAR STREAM</button>
                </div>
            </div>
            <div class="terminal-body" id="terminalConsole"></div>
        </div>
    </div>

    <div id="toast">Settings Saved</div>

    <script>
        let isMonitoring = false;
        let allManifestRecords = [];

        function showToast(msg) {
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.classList.add('show');
            setTimeout(() => t.classList.remove('show'), 2500);
        }

        function togglePasswordVisibility() {
            const pwd = document.getElementById('appPassword');
            pwd.type = pwd.type === 'password' ? 'text' : 'password';
        }

        async function loadConfig() {
            try {
                const res = await fetch('/api/config');
                const data = await res.json();
                document.getElementById('gmailAddress').value = data.gmail_address || '';
                document.getElementById('appPassword').value = data.app_password || '';
                document.getElementById('baseDirectory').value = data.base_directory || 'D:\\\\Resumes';
                
                if (data.create_subfolders !== undefined) {
                    document.getElementById('createSubfolders').checked = data.create_subfolders;
                }
                if (data.prefix_applicant_name !== undefined) {
                    document.getElementById('prefixApplicantName').checked = data.prefix_applicant_name;
                }

                const tbody = document.getElementById('rulesBody');
                tbody.innerHTML = '';
                if (data.companies && data.companies.length > 0) {
                    data.companies.forEach(c => addRuleRow(c.name, c.keyword));
                } else {
                    addRuleRow('Google', 'google');
                    addRuleRow('Microsoft', 'microsoft');
                }
                updateStatsCards();
            } catch (err) {
                console.error(err);
            }
        }

        function addRuleRow(name = '', keyword = '') {
            const tbody = document.getElementById('rulesBody');
            const tr = document.createElement('tr');
            tr.className = 'rule-row';
            tr.innerHTML = `
                <td><input type="text" class="rule-name" value="${name}" placeholder="e.g. Google" oninput="saveConfig(true)"></td>
                <td><input type="text" class="rule-keyword" value="${keyword}" placeholder="e.g. hr@google.com" oninput="saveConfig(true)"></td>
                <td><button class="btn-delete-rule" onclick="this.closest('tr').remove(); saveConfig(true); updateStatsCards();">✕</button></td>
            `;
            tbody.appendChild(tr);
            updateStatsCards();
        }

        function addPresetRule(name, kw) {
            addRuleRow(name, kw);
            saveConfig(true);
            showToast(`Added ${name} Rule`);
        }

        function getRules() {
            const rows = document.querySelectorAll('.rule-row');
            const rules = [];
            rows.forEach(r => {
                const name = r.querySelector('.rule-name').value.trim();
                const keyword = r.querySelector('.rule-keyword').value.trim();
                if (name || keyword) {
                    rules.push({ name, keyword });
                }
            });
            return rules;
        }

        async function saveConfig(silent = false) {
            const payload = {
                gmail_address: document.getElementById('gmailAddress').value.trim(),
                app_password: document.getElementById('appPassword').value.trim(),
                base_directory: document.getElementById('baseDirectory').value.trim(),
                create_subfolders: document.getElementById('createSubfolders').checked,
                prefix_applicant_name: document.getElementById('prefixApplicantName').checked,
                companies: getRules()
            };
            await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (!silent) {
                showToast('Settings Saved Successfully');
            }
            updateStatsCards();
        }

        async function testConnection() {
            const email = document.getElementById('gmailAddress').value.trim();
            const pwd = document.getElementById('appPassword').value.trim();
            if (!email || !pwd) {
                alert('Please enter your Gmail address and 16-character App Password first.');
                return;
            }
            showToast('Testing IMAP Connection...');
            const res = await fetch('/api/test_connection', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password: pwd })
            });
            const data = await res.json();
            if (data.success) {
                showToast('✅ Connection Successful!');
            } else {
                alert('Connection Failed: ' + data.error);
            }
        }

        async function toggleMonitoring() {
            await saveConfig(true);
            const endpoint = isMonitoring ? '/api/monitoring/stop' : '/api/monitoring/start';
            const res = await fetch(endpoint, { method: 'POST' });
            const data = await res.json();
            if (data.error) {
                alert(data.error);
            } else {
                showToast(isMonitoring ? 'Monitoring Stopped' : 'Monitoring Started');
            }
            fetchStatus();
        }

        async function openBaseFolder() {
            const res = await fetch('/api/open_folder', { method: 'POST' });
            const data = await res.json();
            if (!data.success) {
                alert(data.error || 'Failed to open folder.');
            }
        }

        async function openSpecificFile(path) {
            await fetch('/api/open_file', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path })
            });
        }

        async function fetchManifest() {
            try {
                const res = await fetch('/api/manifest');
                const data = await res.json();
                allManifestRecords = data.records || [];
                renderManifestTable(allManifestRecords);
                document.getElementById('statResumes').innerText = allManifestRecords.length;
            } catch (err) {
                console.error(err);
            }
        }

        function filterManifestTable() {
            const q = document.getElementById('manifestSearch').value.toLowerCase();
            if (!q) {
                renderManifestTable(allManifestRecords);
                return;
            }
            const filtered = allManifestRecords.filter(r => 
                (r['Applicant Name'] && r['Applicant Name'].toLowerCase().includes(q)) ||
                (r['Company'] && r['Company'].toLowerCase().includes(q)) ||
                (r['Filename'] && r['Filename'].toLowerCase().includes(q)) ||
                (r['Applicant Email'] && r['Applicant Email'].toLowerCase().includes(q))
            );
            renderManifestTable(filtered);
        }

        function renderManifestTable(records) {
            const tbody = document.getElementById('manifestBody');
            if (!records || records.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="empty-placeholder">No resumes downloaded yet. Start monitoring to begin!</td></tr>';
                return;
            }
            tbody.innerHTML = records.map(r => `
                <tr class="m-row">
                    <td style="color: #64748b;">${escapeHtml(r['Downloaded At'] || '')}</td>
                    <td><span class="company-pill">${escapeHtml(r['Company'] || 'General')}</span></td>
                    <td style="font-weight: 600;">${escapeHtml(r['Applicant Name'] || 'Applicant')}</td>
                    <td style="color: #94a3b8;">${escapeHtml(r['Applicant Email'] || '')}</td>
                    <td style="font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #38bdf8;">${escapeHtml(r['Filename'] || '')}</td>
                    <td style="color: #64748b;">${escapeHtml(r['File Size (KB)'] || '0')} KB</td>
                    <td>
                        <button class="btn-ghost" style="padding: 4px 8px; font-size: 11px;" onclick="openSpecificFile('${escapeJs(r['File Path'])}')">📂 Open</button>
                    </td>
                </tr>
            `).join('');
        }

        async function fetchStatus() {
            try {
                const res = await fetch('/api/monitoring/status');
                const data = await res.json();
                isMonitoring = data.is_monitoring;

                const badge = document.getElementById('statusBadge');
                const statusText = document.getElementById('statusText');
                const heroBtn = document.getElementById('heroBtn');
                const heroTitle = document.getElementById('heroTitle');
                const heroSubtitle = document.getElementById('heroSubtitle');

                if (isMonitoring) {
                    badge.className = 'status-badge status-active';
                    statusText.innerText = 'MONITORING ACTIVE';
                    heroBtn.className = 'btn-hero btn-hero-stop';
                    heroBtn.innerHTML = '<span>⏹ STOP MONITORING</span>';
                    heroTitle.innerText = 'Live Gmail Scanning Active';
                    heroSubtitle.innerText = 'Actively fetching unread emails, routing applicants, and saving resumes.';
                } else {
                    badge.className = 'status-badge status-idle';
                    statusText.innerText = 'IDLE / STOPPED';
                    heroBtn.className = 'btn-hero btn-hero-start';
                    heroBtn.innerHTML = '<span>▶ START MONITORING</span>';
                    heroTitle.innerText = 'Gmail Ingestion Engine Ready';
                    heroSubtitle.innerText = 'Click Start to connect to Gmail and begin real-time applicant scanning & downloading';
                }

                if (data.stats) {
                    document.getElementById('statScanned').innerText = data.stats.scanned_emails || 0;
                    document.getElementById('statMatched').innerText = data.stats.matched_emails || 0;
                }
                updateStatsCards();

                const terminal = document.getElementById('terminalConsole');
                const atBottom = terminal.scrollHeight - terminal.scrollTop <= terminal.clientHeight + 60;
                terminal.innerHTML = data.logs.map(l => `
                    <div class="log-row">
                        <span class="lr-time">[${l.time}]</span>
                        <span class="lr-level ${l.level}">[${l.level}]</span>
                        <span class="lr-msg">${escapeHtml(l.message)}</span>
                    </div>
                `).join('');
                if (atBottom) {
                    terminal.scrollTop = terminal.scrollHeight;
                }
            } catch (err) {
                console.error(err);
            }
        }

        function updateStatsCards() {
            const rules = getRules();
            document.getElementById('statCompanies').innerText = rules.length;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.innerText = text;
            return div.innerHTML;
        }

        function escapeJs(str) {
            return (str || '').replace(/\\\\/g, '\\\\\\\\').replace(/'/g, "\\\\'");
        }

        async function clearLogs() {
            await fetch('/api/logs/clear', { method: 'POST' });
            fetchStatus();
        }

        document.getElementById('gmailAddress').addEventListener('input', () => saveConfig(true));
        document.getElementById('appPassword').addEventListener('input', () => saveConfig(true));
        document.getElementById('baseDirectory').addEventListener('input', () => saveConfig(true));

        loadConfig();
        fetchStatus();
        fetchManifest();
        setInterval(fetchStatus, 2000);
        setInterval(fetchManifest, 5000);
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_ULTIMATE)

@app.route("/api/config", methods=["GET"])
def get_config():
    cfg = config_manager.load_config()
    return jsonify(cfg)

@app.route("/api/config", methods=["POST"])
def save_config_endpoint():
    data = request.json or {}
    config_manager.save_config(data)
    return jsonify({"status": "ok"})

@app.route("/api/test_connection", methods=["POST"])
def test_connection_endpoint():
    data = request.json or {}
    email_addr = data.get("email", "").strip()
    pwd = "".join(data.get("password", "").split())
    try:
        with MailBox("imap.gmail.com").login(email_addr, pwd):
            return jsonify({"success": True})
    except MailboxLoginError as e:
        return jsonify({"success": False, "error": f"Invalid credentials: {e}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/manifest", methods=["GET"])
def get_manifest():
    cfg = config_manager.load_config()
    base_dir = cfg.get("base_directory", app_dir)
    records = get_manifest_records(base_dir)
    return jsonify({"records": records})

@app.route("/api/manifest/export", methods=["GET"])
def export_manifest():
    cfg = config_manager.load_config()
    base_dir = cfg.get("base_directory", app_dir)
    manifest_path = os.path.join(base_dir, "resumes_manifest.csv")
    if os.path.exists(manifest_path):
        return send_file(manifest_path, as_attachment=True, download_name="resumes_manifest.csv")
    # Return empty csv
    return Response("Downloaded At,Company,Applicant Name,Applicant Email,Email Subject,Filename,File Size (KB),File Path\\n",
                    mimetype="text/csv",
                    headers={"Content-disposition": "attachment; filename=resumes_manifest.csv"})

@app.route("/api/open_folder", methods=["POST"])
def open_base_folder():
    cfg = config_manager.load_config()
    base_dir = cfg.get("base_directory", app_dir)
    if os.path.exists(base_dir):
        try:
            if sys.platform == "win32":
                os.startfile(base_dir)
            else:
                os.system(f'open "{base_dir}"')
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    return jsonify({"success": False, "error": "Folder does not exist yet."})

@app.route("/api/open_file", methods=["POST"])
def open_file():
    data = request.json or {}
    fpath = data.get("path", "")
    if fpath and os.path.exists(fpath):
        try:
            if sys.platform == "win32":
                os.startfile(fpath)
            else:
                os.system(f'open "{fpath}"')
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    return jsonify({"success": False, "error": "File not found."})

@app.route("/api/monitoring/status", methods=["GET"])
def monitoring_status():
    global is_monitoring, logs_history
    cfg = config_manager.load_config()
    base_dir = cfg.get("base_directory", app_dir)
    records = get_manifest_records(base_dir)
    return jsonify({
        "is_monitoring": is_monitoring,
        "logs": logs_history,
        "stats": {
            "downloaded_resumes": len(records),
            "matched_emails": len(records),
            "scanned_emails": len(records)
        }
    })

@app.route("/api/monitoring/start", methods=["POST"])
def start_monitoring():
    global is_monitoring, active_watcher
    cfg = config_manager.load_config()

    email_addr = cfg.get("gmail_address", "").strip()
    app_pwd = cfg.get("app_password", "").strip()
    base_dir = cfg.get("base_directory", "").strip()
    create_subfolders = cfg.get("create_subfolders", True)
    prefix_applicant_name = cfg.get("prefix_applicant_name", True)
    companies = cfg.get("companies", [])

    if not email_addr:
        return jsonify({"error": "Please enter your Gmail address."}), 400
    if not app_pwd:
        return jsonify({"error": "Please enter your 16-character Google App Password."}), 400
    if not base_dir:
        return jsonify({"error": "Please enter a Base Download Directory."}), 400
    if not companies:
        return jsonify({"error": "Please add at least one company sorting rule."}), 400

    os.makedirs(base_dir, exist_ok=True)

    if active_watcher:
        active_watcher.stop()

    active_watcher = EmailWatcher(
        email_addr=email_addr,
        app_pwd=app_pwd,
        base_dir=base_dir,
        companies=companies,
        create_subfolders=create_subfolders,
        prefix_applicant_name=prefix_applicant_name,
        log_callback=add_log,
        on_error_callback=lambda err: stop_monitoring_internal()
    )
    active_watcher.start()
    is_monitoring = True
    add_log("Resume Downloader Engine started. Real-time applicant ingestion active.", "INFO")
    return jsonify({"status": "started"})

def stop_monitoring_internal():
    global is_monitoring, active_watcher
    is_monitoring = False
    if active_watcher:
        active_watcher.stop()
        active_watcher = None

@app.route("/api/monitoring/stop", methods=["POST"])
def stop_monitoring():
    stop_monitoring_internal()
    add_log("Monitoring stopped by user via Dashboard.", "INFO")
    return jsonify({"status": "stopped"})

@app.route("/api/logs/clear", methods=["POST"])
def clear_logs():
    global logs_history
    logs_history.clear()
    add_log("Terminal stream cleared.", "INFO")
    return jsonify({"status": "cleared"})

if __name__ == "__main__":
    print("Serving Pro Resume Downloader Dashboard at http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
