import os
import sys
import unittest
import threading
import pymupdf
import docx

from utils.file_utils import sanitize_folder_name, sanitize_filename, get_unique_filepath, ALLOWED_EXTENSIONS
from utils.icon_generator import generate_fallback_icon
from services.config_manager import ConfigManager
from services.startup_manager import get_startup_folder, is_startup_enabled, enable_startup, disable_startup
from services.email_watcher import parse_applicant_info
from web_server import read_resume_document, save_resume_document

class ComprehensiveTestSuite(unittest.TestCase):
    def test_file_utils_sanitization(self):
        self.assertEqual(sanitize_folder_name("Google/HR?"), "Google_HR_")
        self.assertEqual(sanitize_folder_name(""), "Unnamed_Company")
        self.assertEqual(sanitize_filename("resume:test*.pdf"), "resume_test_.pdf")

    def test_allowed_extensions(self):
        self.assertIn(".pdf", ALLOWED_EXTENSIONS)
        self.assertIn(".docx", ALLOWED_EXTENSIONS)
        self.assertIn(".doc", ALLOWED_EXTENSIONS)
        self.assertIn(".rtf", ALLOWED_EXTENSIONS)
        self.assertNotIn(".exe", ALLOWED_EXTENSIONS)

    def test_unique_filename(self):
        tmp_dir = os.path.dirname(os.path.abspath(__file__))
        f1 = get_unique_filepath(tmp_dir, "test_nonexistent_file_xyz.pdf")
        self.assertTrue(f1.endswith("test_nonexistent_file_xyz.pdf"))

    def test_icon_generator(self):
        icon = generate_fallback_icon()
        self.assertEqual(icon.size, (64, 64))
        self.assertEqual(icon.mode, "RGBA")

    def test_config_manager_normalization(self):
        cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_norm_config.json")
        cm = ConfigManager(cfg_path)
        cm.save_config({"gmail_address": "recruiter@gmail.com", "telegram_token": "123:ABC"})
        loaded = cm.load_config()
        self.assertEqual(loaded.get("email"), "recruiter@gmail.com")
        self.assertEqual(loaded.get("gmail_address"), "recruiter@gmail.com")
        self.assertEqual(loaded.get("telegram_token"), "123:ABC")
        self.assertEqual(loaded.get("telegram_bot_token"), "123:ABC")
        if os.path.exists(cfg_path):
            os.remove(cfg_path)

    def test_applicant_info_parser(self):
        name, addr = parse_applicant_info("Tanvir Hasan <tanvir.hasan@example.com>")
        self.assertEqual(name, "Tanvir Hasan")
        self.assertEqual(addr, "tanvir.hasan@example.com")

        name2, addr2 = parse_applicant_info("simple@example.com")
        self.assertEqual(name2, "Applicant")
        self.assertEqual(addr2, "simple@example.com")

    def test_document_editor_pdf(self):
        tmp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_temp_docs")
        os.makedirs(tmp_dir, exist_ok=True)
        test_pdf = os.path.join(tmp_dir, "test_resume.pdf")

        doc = pymupdf.open()
        p = doc.new_page()
        p.insert_text((50, 72), "Candidate Name: Pervez Mollik\nRole: Lead Developer", fontsize=12)
        doc.save(test_pdf)
        doc.close()

        read_res = read_resume_document(test_pdf)
        self.assertTrue(read_res["success"])
        self.assertEqual(read_res["format"], "PDF")
        self.assertIn("Pervez Mollik", read_res["content"])

        save_res = save_resume_document(test_pdf, "Candidate Name: Pervez Mollik\nRole: Lead Developer\nStatus: Approved")
        self.assertTrue(save_res["success"], msg=f"PDF Save Error: {save_res.get('error')}")

        v_res = read_resume_document(test_pdf)
        self.assertIn("Status: Approved", v_res["content"])

        if os.path.exists(test_pdf):
            os.remove(test_pdf)
        if os.path.exists(tmp_dir):
            os.rmdir(tmp_dir)

    def test_document_editor_docx(self):
        tmp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_temp_docx")
        os.makedirs(tmp_dir, exist_ok=True)
        test_docx = os.path.join(tmp_dir, "test_resume.docx")

        doc = docx.Document()
        doc.add_paragraph("Applicant: Imran Islam")
        doc.save(test_docx)

        read_res = read_resume_document(test_docx)
        self.assertTrue(read_res["success"])
        self.assertEqual(read_res["format"], "DOCX")
        self.assertIn("Imran Islam", read_res["content"])

        save_res = save_resume_document(test_docx, "Applicant: Imran Islam\nRating: 5/5")
        self.assertTrue(save_res["success"])

        v_res = read_resume_document(test_docx)
        self.assertIn("Rating: 5/5", v_res["content"])

        if os.path.exists(test_docx):
            os.remove(test_docx)
        if os.path.exists(tmp_dir):
            os.rmdir(tmp_dir)

    def test_startup_manager_default_args(self):
        success = enable_startup()
        self.assertTrue(success)
        self.assertTrue(is_startup_enabled())
        dis_success = disable_startup()
        self.assertTrue(dis_success)
        self.assertFalse(is_startup_enabled())

    def test_startup_folder_resolution(self):
        folder = get_startup_folder()
        self.assertTrue(len(folder) > 0)
        self.assertTrue("Startup" in folder)

    def test_keyword_matching_logic(self):
        companies = [
            {"name": "Google", "keyword": "google"},
            {"name": "Meta", "keyword": "meta"}
        ]
        sender = "recruiter@google.com".lower()
        subject = "Job Application".lower()
        matched = None
        for comp in companies:
            kw = comp.get("keyword", "").strip().lower()
            if kw and (kw in sender or kw in subject):
                matched = comp.get("name")
                break
        self.assertEqual(matched, "Google")

    def test_parse_cloud_filename(self):
        from services.folder_watcher import parse_cloud_filename
        name, orig, time_str = parse_cloud_filename("20261017_1030_Sarah Jenkins_Resume.pdf")
        self.assertEqual(name, "Sarah Jenkins")
        self.assertEqual(orig, "Resume.pdf")
        self.assertEqual(time_str, "20261017_1030")

        # Test fallback
        name2, orig2, _ = parse_cloud_filename("John_Doe_CV.pdf")
        self.assertEqual(name2, "John Doe CV")

    def test_folder_watcher_scan(self):
        from services.folder_watcher import FolderWatcher
        test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_folder_watcher_dir")
        os.makedirs(test_dir, exist_ok=True)
        
        test_file = os.path.join(test_dir, "20261017_1030_Tanvir Hasan_TestResume.pdf")
        with open(test_file, "wb") as f:
            f.write(b"%PDF-1.4 test dummy resume content")

        logs = []
        watcher = FolderWatcher(
            watch_dir=test_dir,
            companies=[{"name": "Tech Corp", "keyword": "testresume"}],
            enable_desktop_toasts=False,
            log_callback=lambda m, l: logs.append(m)
        )
        watcher.scan_directory()

        manifest_file = os.path.join(test_dir, "resumes_manifest.csv")
        self.assertTrue(os.path.exists(manifest_file))
        with open(manifest_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Tanvir Hasan", content)
        self.assertIn("Tech Corp", content)

        # Verify auto-move to company/title subfolder
        sorted_file = os.path.join(test_dir, "Tech Corp", "20261017_1030_Tanvir Hasan_TestResume.pdf")
        self.assertTrue(os.path.exists(sorted_file))

        # Cleanup
        import shutil
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_multi_account_config_synchronization(self):
        cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_multi_config.json")
        cm = ConfigManager(cfg_path)
        accounts_data = [
            {"email": "inbox1@gmail.com", "app_password": "pass one"},
            {"email": "inbox2@gmail.com", "app_password": "pass two"},
            {"email": "inbox3@gmail.com", "app_password": "pass three"}
        ]
        cm.save_config({"accounts": accounts_data})
        loaded = cm.load_config()
        self.assertEqual(len(loaded.get("accounts", [])), 3)
        self.assertEqual(loaded.get("email"), "inbox1@gmail.com")
        self.assertEqual(loaded.get("app_password"), "pass one")
        if os.path.exists(cfg_path):
            os.remove(cfg_path)

    def test_email_watcher_multi_account_initialization(self):
        from services.email_watcher import EmailWatcher
        accounts = [
            {"email": "primary@gmail.com", "app_password": "abcd efgh ijkl mnop"},
            {"email": "secondary@gmail.com", "app_password": "qrst uvwx yz12 3456"}
        ]
        watcher = EmailWatcher(
            accounts=accounts,
            base_dir=os.path.dirname(os.path.abspath(__file__)),
            companies=[{"name": "Python Developer", "keyword": "python"}],
            create_subfolders=True
        )
        self.assertEqual(len(watcher.accounts), 2)
        self.assertEqual(watcher.email_addr, "primary@gmail.com")
        self.assertEqual(watcher.app_pwd, "abcdefghijklmnop")

    def test_web_server_authentication_flow(self):
        from web_server import app, MASTER_PASSWORD
        self.assertEqual(MASTER_PASSWORD, "Parvez7221")
        
        client = app.test_client()

        # 1. Initially unauthenticated
        auth_status = client.get('/api/auth_status').get_json()
        self.assertFalse(auth_status.get('authenticated'))

        # 2. Protected endpoint returns 401
        res = client.get('/api/config')
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertTrue(data.get('auth_required'))

        # 3. Login with wrong password fails
        bad_login = client.post('/api/login', json={'password': 'WrongPassword123'})
        self.assertEqual(bad_login.status_code, 401)
        self.assertFalse(bad_login.get_json().get('success'))

        # 4. Login with correct master password succeeds
        good_login = client.post('/api/login', json={'password': 'Parvez7221'})
        self.assertEqual(good_login.status_code, 200)
        self.assertTrue(good_login.get_json().get('success'))

        # 5. Auth status is now True
        auth_status_after = client.get('/api/auth_status').get_json()
        self.assertTrue(auth_status_after.get('authenticated'))

        # 6. Protected endpoint now accessible
        cfg_res = client.get('/api/config')
        self.assertEqual(cfg_res.status_code, 200)

        # 7. Logout revokes session
        logout_res = client.post('/api/logout')
        self.assertEqual(logout_res.status_code, 200)

        # 8. Re-verification: unauthenticated again
        auth_status_final = client.get('/api/auth_status').get_json()
        self.assertFalse(auth_status_final.get('authenticated'))

        cfg_res_final = client.get('/api/config')
        self.assertEqual(cfg_res_final.status_code, 401)

    def test_config_manager_safe_merge(self):
        cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_merge_config.json")
        cm = ConfigManager(cfg_path)
        # 1. Initial save with telegram token and desktop toasts
        cm.save_config({
            "telegram_token": "token_123",
            "telegram_chat_id": "chat_456",
            "enable_desktop_toasts": True,
            "poll_interval": 15
        })
        # 2. Subsequent save with only companies and directory (partial save like web dashboard)
        cm.save_config({
            "base_directory": "D:\\Resumes_Test",
            "companies": [{"name": "Apple", "keyword": "apple"}]
        })
        # 3. Verify telegram_token and other fields were not erased
        loaded = cm.load_config()
        self.assertEqual(loaded.get("telegram_token"), "token_123")
        self.assertEqual(loaded.get("telegram_chat_id"), "chat_456")
        self.assertEqual(loaded.get("poll_interval"), 15)
        self.assertEqual(loaded.get("base_directory"), "D:\\Resumes_Test")
        if os.path.exists(cfg_path):
            os.remove(cfg_path)

    def test_parse_cloud_filename_4_parts(self):
        from services.folder_watcher import parse_cloud_filename
        # 4-part Google Apps Script filename: Timestamp_Sender_Subject_Original.pdf
        fname = "20261021_1200_Sarah Jenkins_Senior Python Developer_Sarah_CV.pdf"
        name, orig, time_str = parse_cloud_filename(fname)
        self.assertEqual(name, "Sarah Jenkins")
        self.assertEqual(orig, "Sarah_CV.pdf")
        self.assertEqual(time_str, "20261021_1200")

    def test_update_manifest_row_isolation(self):
        from web_server import update_manifest_row
        test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_manifest_dir")
        os.makedirs(test_dir, exist_ok=True)
        manifest_file = os.path.join(test_dir, "resumes_manifest.csv")

        # Two different candidates both submitted "Resume.pdf" in different company folders
        with open(manifest_file, "w", newline="", encoding="utf-8") as f:
            f.write("Downloaded At,Company,Applicant Name,Applicant Email,Email Subject,Filename,File Size (KB),File Path,SHA256,Status,Notes\n")
            f.write("2026-10-21 10:00:00,Google,Alice,alice@example.com,CV,Resume.pdf,120,D:\\Resumes\\Google\\Resume.pdf,hash1,New,Initial note\n")
            f.write("2026-10-21 10:05:00,Microsoft,Bob,bob@example.com,CV,Resume.pdf,130,D:\\Resumes\\Microsoft\\Resume.pdf,hash2,New,Initial note\n")

        # Update Alice's status
        updated = update_manifest_row(test_dir, "D:\\Resumes\\Google\\Resume.pdf", "Shortlisted", "Promising candidate")
        self.assertTrue(updated)

        # Read back and verify Bob's status was NOT overwritten
        with open(manifest_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        self.assertIn("Shortlisted", lines[1]) # Alice is Shortlisted
        self.assertIn("New", lines[2])         # Bob must remain New!
        self.assertNotIn("Shortlisted", lines[2])

        if os.path.exists(test_dir):
            import shutil
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_is_safe_doc_path(self):
        from web_server import is_safe_doc_path, app_dir
        # Valid resume inside app_dir
        valid_path = os.path.join(app_dir, "test.pdf")
        self.assertTrue(is_safe_doc_path(valid_path))

        # Path outside allowed directories
        self.assertFalse(is_safe_doc_path(r"C:\Windows\System32\notepad.exe"))
        self.assertFalse(is_safe_doc_path(r"C:\arbitrary\unauthorized\secret.pdf"))

        # Sibling directory bypass attempt (e.g. app_dir + "_secret")
        sibling_path = f"{app_dir}_secret\\resume.pdf"
        self.assertFalse(is_safe_doc_path(sibling_path))

    def test_reserved_names_and_traversal_sanitization(self):
        # Traversal attempts
        self.assertEqual(sanitize_folder_name(".."), "Unnamed_Company")
        self.assertEqual(sanitize_folder_name("."), "Unnamed_Company")
        
        # Windows DOS device reserved names
        self.assertEqual(sanitize_folder_name("CON"), "_CON")
        self.assertEqual(sanitize_folder_name("aux"), "_aux")
        self.assertEqual(sanitize_folder_name("NUL"), "_NUL")
        self.assertEqual(sanitize_filename("CON.pdf"), "_CON.pdf")
        self.assertEqual(sanitize_filename("prn.docx"), "_prn.docx")

    def test_parse_cloud_filename_with_subject(self):
        from services.folder_watcher import parse_cloud_filename
        # Format: YYYYMMDD_HHmm_ApplicantName__Subject__OriginalFilename.ext
        fname = "20261107_1105_John Doe__Software Engineer__John_CV.pdf"
        parsed = parse_cloud_filename(fname)
        app_name, orig, ts = parsed
        self.assertEqual(app_name, "John Doe")
        self.assertEqual(orig, "John_CV.pdf")
        self.assertEqual(ts, "20261107_1105")
        self.assertEqual(parsed.subject, "Software Engineer")

        # Format without subject: YYYYMMDD_HHmm_ApplicantName__OriginalFilename.ext
        fname2 = "20261107_1105_Alice Smith__Alice_Resume.docx"
        parsed2 = parse_cloud_filename(fname2)
        app_name2, orig2, ts2 = parsed2
        self.assertEqual(app_name2, "Alice Smith")
        self.assertEqual(orig2, "Alice_Resume.docx")
        self.assertEqual(parsed2.subject, "")

    def test_config_manager_partial_update_single_email(self):
        cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_partial_config.json")
        cm = ConfigManager(cfg_path)
        # 1. Initial save with one account
        cm.save_config({"accounts": [{"email": "old@gmail.com", "app_password": "oldpassword"}]})
        
        # 2. Update only email/app_password without accounts key
        cm.save_config({"email": "new@gmail.com", "app_password": "newpassword1234"})
        loaded = cm.load_config()
        self.assertEqual(loaded.get("email"), "new@gmail.com")
        self.assertEqual(loaded.get("accounts")[0]["email"], "new@gmail.com")
        self.assertEqual(loaded.get("accounts")[0]["app_password"], "newpassword1234")

        # 3. Clearing telegram token
        cm.save_config({"telegram_token": "token123"})
        self.assertEqual(cm.load_config().get("telegram_token"), "token123")
        cm.save_config({"telegram_token": ""})
        self.assertEqual(cm.load_config().get("telegram_token"), "")

        if os.path.exists(cfg_path):
            os.remove(cfg_path)

    def test_desktop_app_master_password_constant(self):
        import app
        self.assertEqual(app.MASTER_PASSWORD, "Parvez7221")

    def test_master_login_and_auth_status(self):
        from web_server import app as flask_app
        client = flask_app.test_client()

        # 1. Initially unauthenticated
        res = client.get("/api/auth_status")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json.get("authenticated"))

        # 2. Login with wrong password
        fail_res = client.post("/api/login", json={"password": "WrongPassword"})
        self.assertEqual(fail_res.status_code, 401)
        self.assertFalse(fail_res.json.get("success"))

        # 3. Login with correct master password
        ok_res = client.post("/api/login", json={"password": "Parvez7221"})
        self.assertEqual(ok_res.status_code, 200)
        self.assertTrue(ok_res.json.get("success"))

        # 4. Check auth status now
        auth_res = client.get("/api/auth_status")
        self.assertTrue(auth_res.json.get("authenticated"))

        # 5. Access protected endpoint
        cfg_res = client.get("/api/config")
        self.assertEqual(cfg_res.status_code, 200)

        # 6. Logout
        logout_res = client.post("/api/logout")
        self.assertEqual(logout_res.status_code, 200)
        auth_after = client.get("/api/auth_status")
        self.assertFalse(auth_after.json.get("authenticated"))

    def test_export_zip_and_manifest_endpoints(self):
        from web_server import app as flask_app
        import zipfile
        import io

        client = flask_app.test_client()
        # Authenticate first
        client.post("/api/login", json={"password": "Parvez7221"})

        # Export manifest CSV header test
        m_res = client.get("/api/manifest/export")
        self.assertEqual(m_res.status_code, 200)
        self.assertIn("attachment; filename=resumes_manifest.csv", m_res.headers.get("Content-Disposition", ""))

        # Export ZIP archive test
        z_res = client.get("/api/manifest/export_zip")
        self.assertEqual(z_res.status_code, 200)
        self.assertEqual(z_res.mimetype, "application/zip")

        # Verify ZIP structure
        zf = zipfile.ZipFile(io.BytesIO(z_res.data))
        self.assertIn("resumes_manifest_summary.csv", zf.namelist())

    def test_change_master_password_flow(self):
        from web_server import app as flask_app, config_manager
        client = flask_app.test_client()

        # 1. Unauthenticated change attempt blocked
        unauth_res = client.post("/api/change_password", json={
            "old_password": "Parvez7221",
            "new_password": "NewSecretPass7221",
            "confirm_password": "NewSecretPass7221"
        })
        self.assertEqual(unauth_res.status_code, 401)

        # 2. Authenticate
        client.post("/api/login", json={"password": "Parvez7221"})

        # 3. Mismatched confirmation
        mismatch_res = client.post("/api/change_password", json={
            "old_password": "Parvez7221",
            "new_password": "NewSecretPass7221",
            "confirm_password": "DifferentPass"
        })
        self.assertEqual(mismatch_res.status_code, 400)
        self.assertIn("do not match", mismatch_res.json.get("error", ""))

        # 4. Wrong old password
        wrong_old_res = client.post("/api/change_password", json={
            "old_password": "WrongOldPassword",
            "new_password": "NewSecretPass7221",
            "confirm_password": "NewSecretPass7221"
        })
        self.assertEqual(wrong_old_res.status_code, 400)
        self.assertIn("Old password does not match", wrong_old_res.json.get("error", ""))

        # 5. Successful change
        success_res = client.post("/api/change_password", json={
            "old_password": "Parvez7221",
            "new_password": "NewSecretPass7221",
            "confirm_password": "NewSecretPass7221"
        })
        self.assertEqual(success_res.status_code, 200)
        self.assertTrue(success_res.json.get("success"))

        # 6. Verify old password fails to log in
        client.post("/api/logout")
        fail_login = client.post("/api/login", json={"password": "Parvez7221"})
        self.assertEqual(fail_login.status_code, 401)

        # 7. Verify new password succeeds
        ok_login = client.post("/api/login", json={"password": "NewSecretPass7221"})
        self.assertEqual(ok_login.status_code, 200)
        self.assertTrue(ok_login.json.get("success"))

        # 8. Reset back to original password Parvez7221 to keep workspace clean
        reset_res = client.post("/api/change_password", json={
            "old_password": "NewSecretPass7221",
            "new_password": "Parvez7221",
            "confirm_password": "Parvez7221"
        })
        self.assertEqual(reset_res.status_code, 200)

if __name__ == "__main__":
    unittest.main()
