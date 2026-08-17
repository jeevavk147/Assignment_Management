import shutil
import tempfile
import unittest
from pathlib import Path

import database


class IsolatedDBTestCase(unittest.TestCase):
    """Points database.DB_PATH / database.UPLOADS_DIR at a throwaway temp
    location for the duration of each test, so tests can never read or write
    the real assignment_app.db or uploads/ folder — every database.py
    function reads these as module globals on each call, so reassigning them
    here redirects every function without touching database.py itself."""

    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp(prefix="ama_test_")
        self._original_db_path = database.DB_PATH
        self._original_uploads_dir = database.UPLOADS_DIR
        database.DB_PATH = str(Path(self._tmp_dir) / "test.db")
        database.UPLOADS_DIR = str(Path(self._tmp_dir) / "uploads")
        database.initialize_db()

    def tearDown(self):
        database.DB_PATH = self._original_db_path
        database.UPLOADS_DIR = self._original_uploads_dir
        shutil.rmtree(self._tmp_dir, ignore_errors=True)
