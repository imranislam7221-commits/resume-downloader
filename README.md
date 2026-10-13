# ⚡ Enterprise Resume Downloader & Recruitment Hub (24/7 Autonomous)

A production-grade, autonomous Desktop & Web Recruitment Platform built with **Python**, **CustomTkinter**, **Flask**, **imap_tools**, and **winotify** to monitor Gmail in real-time, extract applicant resumes (`.pdf`, `.docx`, `.doc`, `.rtf`), and organize them into company-specific folders completely hands-free on your local PC.

---

## 🌟 Professional & Enterprise Features

### 1. ⚡ 24/7 Autonomous Background Execution & Auto-Start
- Runs 24/7 in the background scanning for unread applicant emails.
- **Windows Boot Auto-Start**: Automatically launches on Windows startup via `%APPDATA%\...\Startup` silently in the system tray without any command prompt window.
- **Zero-Touch Automation**: Leave your PC on; new incoming resumes are parsed, organized, and cataloged automatically.

### 2. 🛡️ SHA-256 Deduplication Engine (Disk & Storage Optimization)
- Uses cryptographic **SHA-256 payload hashing** to detect duplicate resume files.
- If a candidate re-applies or an email with an identical CV arrives, the system prevents duplicate file downloads, saving hard drive space and keeping HR folders clean.

### 3. 👥 Candidate Recruitment Pipeline & HR Notes
- **Status Workflow**: Interactive candidate pipeline (`New` ➔ `Shortlisted` ➔ `Interview` ➔ `Hired` ➔ `Rejected`) with color-coded status badges directly on the dashboard.
- **Recruiter Candidate Notes**: Add and edit recruiter notes (e.g. salary expectation, screening feedback, technical rating) stored persistently in the local manifest.
- **Live Search & Filters**: Search candidates instantly by name, email, company, notes, or filter by recruitment status.

### 4. 📦 1-Click Company ZIP Archiver & CSV Export
- **Export ZIP**: Download all resumes for any specific company (or all candidates) packaged into a `.zip` archive alongside a summary CSV with a single click.
- **Export CSV**: Instant export of `resumes_manifest.csv` containing full applicant intake metadata.

### 5. ✏️ In-Dashboard Universal Resume Document Editor & Redactor
- **Direct Editing from Browser**: Edit any downloaded resume directly inside the Web Dashboard regardless of whether it was downloaded as .pdf, .docx, .doc, .rtf, or .txt!
- **Auto-Redact Contact Info**: 1-Click redaction of candidate phone numbers and email addresses before submitting CVs to clients.
- **Find & Replace**: Quickly search and modify text inside the candidate document.
- **Save to Local Disk**: Save changes directly overwriting the original file or as a clean new copy (_edited) on your local drive.
- **Open in Desktop App**: 1-Click option to open directly in Microsoft Word or Adobe Acrobat for deep formatting.

### 6. 👁️ In-Dashboard Fullscreen PDF Viewer
- Read and evaluate candidate resumes directly in your browser with a single click on **"👁️ Preview"**.
- No need to switch windows or open File Explorer!

### 6. 🔔 Real-Time Desktop & Mobile Notifications
- **Windows Desktop Toast**: Native audio toast notification in the bottom-right corner when a new resume is downloaded.
- **Telegram Mobile Alerts**: Instant alert sent to your mobile Telegram bot with candidate name, email, company, and file size.

### 7. 🔒 100% Local Privacy (No Cloud Required)
- User privacy first: All emails, attachments, metadata, and applicant notes are saved **100% locally** on your computer. No external cloud sync (no Google Drive, no S3).

---

## 📂 Project Architecture

```
Resume downloader/
│
├── app.py                     # CustomTkinter Desktop GUI application
├── web_server.py              # Flask Enterprise Web Dashboard & Recruitment Hub
│
├── services/                  # Core Business Logic & Background Engines
│   ├── email_watcher.py       # IMAP SSL client, SHA-256 deduplication, manifest engine
│   ├── notification_service.py# Windows toast notifications & Telegram bot alerts
│   ├── startup_manager.py     # Windows Startup folder VBS silent launcher manager
│   ├── config_manager.py      # Thread-safe persistent JSON configuration
│   └── tray_service.py        # System tray icon & background runner
│
├── components/                # Modular Desktop UI Components
│   ├── header.py              # Status badges, title banner
│   ├── credentials.py         # Gmail, App Password, directory selector
│   ├── rules_table.py         # Dynamic company keyword rules table
│   └── log_console.py         # Desktop live log console
│
├── utils/                     # Helper Utilities
│   ├── file_utils.py          # Windows path sanitization & unique file naming
│   └── icon_generator.py      # Dynamic fallback icon generator
│
├── run_web.bat                # 1-Click launcher for Web Dashboard (http://127.0.0.1:5000)
├── run.bat                    # 1-Click launcher for Desktop GUI
├── run_silent.vbs             # Silent background startup launcher
└── requirements.txt           # Python dependencies
```

---

## 🚀 Quick Start Guide

### 1. Requirements
Ensure Python 3.10+ is installed:
```bash
pip install -r requirements.txt
```

### 2. Launch the Web Recruitment Hub
Double-click `run_web.bat` or run in terminal:
```bash
python web_server.py
```
Open your browser at: **`http://127.0.0.1:5000`**

### 3. Launch the Desktop GUI
Double-click `run.bat` or run:
```bash
python app.py
```

---

## 🔐 Google Gmail Configuration Guide

To allow the app to securely monitor your Gmail inbox:
1. Go to your [Google Account Security](https://myaccount.google.com/security).
2. Enable **2-Step Verification**.
3. Under **App Passwords**, generate a new password (select App name: "Resume Downloader").
4. Copy the generated **16-character App Password** (e.g. `abcd efgh ijkl mnop`) and enter it in the dashboard.
