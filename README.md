# ⚡ Enterprise Resume Downloader & Recruitment Hub (24/7 Autonomous)

A modern, automated Desktop Application built with **CustomTkinter**, **imap_tools**, and **pystray** to automatically monitor Gmail inboxes in real-time, extract resumes (`.pdf`, `.docx`, `.doc`), and sort them into company-specific folders.

---

## 📁 Project Architecture (Modular Structure)

```
Resume downloader/
│
├── components/                  # UI Components (Alada Alada Component)
│   ├── header.py               # Header title, subtitle, and dynamic status badge
│   ├── credentials.py          # Gmail address, App Password, directory picker
│   ├── rules_table.py          # Dynamic company rules grid (Add / Remove rows)
│   ├── log_console.py          # Real-time console activity logger
│   └── __init__.py
│
├── services/                    # Background Services
│   ├── config_manager.py       # Auto-saves and loads config.json
│   ├── email_watcher.py        # Background IMAP thread for monitoring & downloading
│   ├── tray_service.py         # System tray (minimize to tray, context menu)
│   └── __init__.py
│
├── utils/                       # Helper Utilities
│   ├── file_utils.py           # Filename sanitization, duplicate renaming
│   ├── icon_generator.py       # PIL dynamic fallback icon generator
│   └── __init__.py
│
├── app.py                       # Main application entry point
├── config.json                  # Auto-saved user configurations
├── requirements.txt             # Project dependencies
├── run.bat                      # 1-Click launcher for Windows
└── test_suite.py                # Unit test verification suite
```

---

## 🚀 Quick Start Guide

### 1. Requirements
Ensure Python 3.10+ is installed:
```bash
pip install -r requirements.txt
```

### 2. App Launch
- Direct double-click on `run.bat`
- Or terminal theke:
```bash
python app.py
```

### 3. Launch Option B: Web Dashboard (Browser)
- Direct double-click on `run_web.bat`
- Or terminal theke:
```bash
python web_server.py
```
- Open browser at: [http://localhost:5000](http://localhost:5000)

### 4. Run Unit Tests
```bash
python test_suite.py
```

---

## 🔑 Gmail App Password Setup (Google Setup Guide)

Gmail er standard password ekhane kaj korbe na, Google er security policy onujayi **16-character App Password** proyojon:

1. Apnar Google Account-e jan: [myaccount.google.com](https://myaccount.google.com)
2. **Security** tab-e giye **2-Step Verification** ON koren.
3. Search bar-e likhun **"App passwords"** ba Security theke **App passwords** select koren.
4. App name din (e.g., `Resume Downloader`) ebong **Create** click koren.
5. 16-character er ekta password paben (e.g., `abcd efgh ijkl mnop`).
6. Ei password-ti app-er **App Password** field-e paste korun.

---

## 🛠 Key Features

1. **Multi-Account Concurrent Ingestion**: Connect 2, 3, or unlimited Gmail inboxes simultaneously. Each inbox is monitored concurrently.
2. **24/7 Cloud Resume Downloader**: Deploy `google_apps_script.js` to Google Cloud to ingest resumes 24/7 directly to Google Drive even when your PC is turned off.
3. **Automated Title & Role Subfolder Sorting**: Resumes are automatically sorted into role/company-specific folders based on subject line keywords (e.g. `Developer/`, `Designer/`).
4. **Hardware-Level SHA-256 Deduplication**: Prevents duplicate downloads even if the same candidate emails multiple accounts or you move/cut previously downloaded files.
5. **Universal Document Editor & Previewer**: View and edit `.pdf` and `.docx` resumes directly in the browser dashboard without Microsoft Word or Adobe Acrobat.
6. **Modern Dark Theme Web Dashboard & Desktop GUI**: Choose between running the browser-based Recruitment Hub (`run_web.bat`) or the native desktop application (`run.bat`).
7. **Instant Desktop & Telegram Alerts**: Get immediate Windows notifications with sound and optional instant Telegram alerts when a new candidate applies.
8. **System Tray & Windows Boot Auto-Start**: Minimize to system tray or toggle automatic silent startup on Windows boot.
