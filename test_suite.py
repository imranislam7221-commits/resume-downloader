import os
import sys
import unittest
from utils.file_utils import sanitize_folder_name, sanitize_filename, get_unique_filepath, ALLOWED_EXTENSIONS
from utils.icon_generator import generate_fallback_icon
from services.config_manager import ConfigManager

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

if __name__ == "__main__":
    unittest.main()
