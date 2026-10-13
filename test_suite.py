import os
import sys
import unittest
import threading
from utils.file_utils import sanitize_folder_name, sanitize_filename, get_unique_filepath, ALLOWED_EXTENSIONS
from utils.icon_generator import generate_fallback_icon
from services.config_manager import ConfigManager
from services.email_watcher import parse_applicant_info
from services.startup_manager import get_startup_folder, enable_startup, disable_startup

class TestResumeDownloader(unittest.TestCase):
    def test_file_utils_sanitization(self):
        self.assertEqual(sanitize_folder_name("Google/HR?"), "Google_HR_")
        self.assertEqual(sanitize_folder_name(""), "Unnamed_Company")
        self.assertEqual(sanitize_filename("resume:test*.pdf"), "resume_test_.pdf")

    def test_allowed_extensions(self):
        self.assertIn(".pdf", ALLOWED_EXTENSIONS)
        self.assertIn(".docx", ALLOWED_EXTENSIONS)
        self.assertIn(".doc", ALLOWED_EXTENSIONS)
        self.assertNotIn(".exe", ALLOWED_EXTENSIONS)

    def test_unique_filename(self):
        tmp_dir = os.path.dirname(os.path.abspath(__file__))
        f1 = get_unique_filepath(tmp_dir, "test_file_never_exists_123.pdf")
        self.assertTrue(f1.endswith("test_file_never_exists_123.pdf"))

    def test_icon_generator(self):
        icon = generate_fallback_icon()
        self.assertEqual(icon.size, (64, 64))
        self.assertEqual(icon.mode, "RGBA")

    def test_config_manager(self):
        cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_config.json")
        cm = ConfigManager(cfg_path)
        data = cm.load_config()
        self.assertIn("companies", data)
        self.assertTrue(cm.save_config({"test_key": "test_val"}))
        loaded = cm.load_config()
        self.assertEqual(loaded.get("test_key"), "test_val")
        if os.path.exists(cfg_path):
            os.remove(cfg_path)

    def test_parse_applicant_info(self):
        name, addr = parse_applicant_info("John Doe <john.doe@example.com>")
        self.assertEqual(name, "John Doe")
        self.assertEqual(addr, "john.doe@example.com")

        name, addr = parse_applicant_info("Jane/Smith:HR? <jane@example.com>")
        self.assertEqual(name, "Jane_Smith_HR_")
        self.assertEqual(addr, "jane@example.com")

        name, addr = parse_applicant_info("only_email@example.com")
        self.assertEqual(name, "Applicant")
        self.assertEqual(addr, "only_email@example.com")

        name, addr = parse_applicant_info("")
        self.assertEqual(name, "Applicant")
        self.assertEqual(addr, "")

        name, addr = parse_applicant_info("Candidate\nName\t<cand@test.com>")
        self.assertEqual(name, "Candidate Name")
        self.assertEqual(addr, "cand@test.com")

    def test_keyword_matching_logic(self):
        companies = [
            {"name": "Google", "keyword": "google"},
            {"name": "Meta", "keyword": "meta"}
        ]
        
        # Test sender match
        sender = "recruiter@google.com".lower()
        subject = "Job Application".lower()
        matched = None
        for comp in companies:
            kw = comp.get("keyword", "").strip().lower()
            if kw and (kw in sender or kw in subject):
                matched = comp.get("name")
                break
        self.assertEqual(matched, "Google")

        # Test subject match
        sender = "john@example.com".lower()
        subject = "Applying for Meta Software Engineer".lower()
        matched = None
        for comp in companies:
            kw = comp.get("keyword", "").strip().lower()
            if kw and (kw in sender or kw in subject):
                matched = comp.get("name")
                break
        self.assertEqual(matched, "Meta")

    def test_startup_folder_resolution(self):
        folder = get_startup_folder()
        self.assertTrue(len(folder) > 0)
        self.assertTrue("Startup" in folder)

    def test_web_server_import_and_dynamic_path(self):
        import web_server
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.assertEqual(os.path.abspath(web_server.app_dir), current_dir)
        self.assertFalse("Imran parsonal" in web_server.app_dir)

    def test_thread_safe_web_logging(self):
        import web_server
        threads = []
        for i in range(10):
            t = threading.Thread(target=web_server.add_log, args=(f"Concurrent log test {i}", "INFO"))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        with web_server.state_lock:
            messages = [e["message"] for e in web_server.logs_history]
            self.assertTrue(any("Concurrent log test" in m for m in messages))

    def test_applicant_prefixing_logic(self):
        import re
        applicant_name = "John Doe"
        clean_att = "CV.pdf"
        norm_name = re.sub(r'\s+', '_', applicant_name)
        if norm_name.lower() not in clean_att.lower():
            chosen_name = f"{norm_name}_{clean_att}"
        else:
            chosen_name = clean_att
        self.assertEqual(norm_name, "John_Doe")
        self.assertEqual(chosen_name, "John_Doe_CV.pdf")

if __name__ == "__main__":
    unittest.main()
