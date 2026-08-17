"""
Ekumen - Output Cache Service
Manages storage and retrieval of Ansible execution outputs across processes.
"""

import datetime
import os
import re
import tempfile
import threading
import time
import logging

logger = logging.getLogger(__name__)


class OutputCache:
    """Multi-process / multi-worker safe execution output store."""

    def __init__(self, cache_dir: str = None, max_age_seconds: int = 7200):
        if not cache_dir:
            self.cache_dir = os.path.join(tempfile.gettempdir(), 'ekumen_output_cache')
        else:
            self.cache_dir = cache_dir

        self.max_age_seconds = max_age_seconds
        self._lock = threading.Lock()
        self._ensure_dir()

    def _ensure_dir(self):
        """Ensure cache directory exists."""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except OSError as e:
            logger.warning("Could not create output cache directory %s: %s", self.cache_dir, e)

    def _cleanup_old_files(self):
        """Remove output files older than max_age_seconds."""
        if not os.path.exists(self.cache_dir):
            return

        now = time.time()
        try:
            for fname in os.listdir(self.cache_dir):
                if fname.startswith('output_') and fname.endswith('.txt'):
                    fpath = os.path.join(self.cache_dir, fname)
                    try:
                        if os.path.isfile(fpath) and (now - os.path.getmtime(fpath)) > self.max_age_seconds:
                            os.remove(fpath)
                    except OSError:
                        pass
        except OSError:
            pass

    def store(self, content: str) -> str:
        """
        Store an execution output string and return timestamp ID.
        """
        self._ensure_dir()
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:19] # YYYYMMDD_HHMMSS
        filename = f"output_{timestamp}.txt"
        filepath = os.path.join(self.cache_dir, filename)

        with self._lock:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                # Also update latest symlink or pointer file
                latest_path = os.path.join(self.cache_dir, 'output_latest.txt')
                with open(latest_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self._cleanup_old_files()
            except Exception as e:
                logger.error("Failed to write output cache file: %s", e)

        return timestamp

    def get_latest(self) -> tuple[str, str]:
        """
        Get the most recent output content and its timestamp.
        Returns (content, timestamp).
        """
        if not os.path.exists(self.cache_dir):
            return '', ''

        latest_path = os.path.join(self.cache_dir, 'output_latest.txt')
        if os.path.exists(latest_path):
            try:
                with open(latest_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                mtime = os.path.getmtime(latest_path)
                ts = datetime.datetime.fromtimestamp(mtime).strftime('%Y%m%d_%H%M%S')
                return content, ts
            except Exception as e:
                logger.error("Failed to read latest output: %s", e)

        return '', ''

    def get_by_id(self, run_id: str) -> tuple[str, str]:
        """
        Get output content by run timestamp/id.
        """
        if not run_id or not re.match(r'^[\w\-]+$', run_id):
            return self.get_latest()

        filepath = os.path.join(self.cache_dir, f"output_{run_id}.txt")
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f.read(), run_id
            except Exception as e:
                logger.error("Failed to read output for ID %s: %s", run_id, e)

        return self.get_latest()
