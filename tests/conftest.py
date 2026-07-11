"""Point every test at a throwaway SQLite DB and force DRY_RUN before app import."""
import os
import tempfile

os.environ["DATABASE_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DRY_RUN"] = "true"
os.environ["QUIET_HOURS_START"] = "0"   # disable quiet-hours deferral in tests
os.environ["QUIET_HOURS_END"] = "24"
