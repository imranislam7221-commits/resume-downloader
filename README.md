# ⚡ Resume Downloader & Gmail Auto-Sorter

A modern, automated Application built with **CustomTkinter**, **Flask**, **imap_tools**, and **pystray** to automatically monitor Gmail inboxes in real-time, extract resumes (`.pdf`, `.docx`, `.doc`, `.rtf`), and sort them into company-specific folders.

---

## 📁 Project Architecture (Modular Structure)

```
Resume downloader/
│
├── components/                  # UI Components (Desktop GUI)
│   ├── header.py               # Header title, subtitle, and dynamic status badge
│   ├── credentials.py          # Gmail address, App Password, directory picker
│   ├── rules_table.py          # Dynamic company rules grid (Add / Remove rows)
│   ├── log_console.py          # Real-time console activity logger
│   └── __init__.py
│
├── services/                    # Background Services
│   ├── config_manager.py       # Auto-saves and loads config.json
│   ├── email_watcher.py        # Background IMAP thread for monitoring & downloading
│   ├── startup_manager.py      # Windows auto-startup management
│   ├── tray_service.py         # System tray (minimize to tray, context menu)
│   └── __init__.py
│
├── utils/                       # Helper Utilities
│   ├── file_utils.py           # Filename sanitization, duplicate renaming
│   ├── icon_generator.py       # PIL dynamic fallback icon generator
│   └── __init__.py
│
├── app.py                       # Desktop application entry point (CustomTkinter)
├── web_server.py                # Web Dashboard & REST API server (Flask)
├── config.json                  # Auto-saved user configurations
├── config.example.json          # Example template for configurations
├── requirements.txt             # Project dependencies (Flask, customtkinter, imap-tools, etc.)
├── run.bat                      # 1-Click launcher for Desktop GUI
├── run_web.bat                  # 1-Click launcher for Web Dashboard
├── run_silent.vbs               # Silent background runner for Windows
└── test_suite.py                # Unit test verification suite
```

---

## 🚀 How to Run (Kivabe Run Korben)

### 1. Requirements Install
```bash
pip install -r requirements.txt
```

### 2. Launch Option A: Desktop GUI
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

1. **Dual Interface**: Desktop GUI (CustomTkinter dark theme) & Web Dashboard (Flask + REST API).
2. **Dynamic Company Table**: Joto iccha company name ar keyword/email rule jog ba delete korte parben.
3. **Smart Email Filtering**: Sender email address ebong Subject line check kore correct company detect kore.
4. **Auto Attachment Extraction**: `.pdf`, `.docx`, `.doc`, ebong `.rtf` files download kore company folder-e sort kore.
5. **Applicant Name Normalization**: Prothome applicant er name parse kore attachment filename-e prefix hishebe jog kore (`Name_OriginalFile.pdf`).
6. **Mark as Read**: Download shesh hole Gmail-e email-ti 'SEEN' mark kore dey jate bar bar process na hoy.
7. **System Tray Integration**: Window 'X' (close) korle app bondho hoy na, background-e system tray-te minimize thake. Tray theke restore ba exit kora jay.
8. **Auto Config Save & Manifest**: Folder path, email credentials, ar company rules automatic `config.json`-e save hoy ebong shob downloads `resumes_manifest.csv`-te record hoy.
