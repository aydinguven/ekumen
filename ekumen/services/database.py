"""
Ekumen - Job Database Service (SQLite)
Handles persistent storage of execution history, output logs, durations, and play recap metrics.
"""

import json
import logging
import os
import sqlite3
import tempfile
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class JobDatabase:
    """Manages persistent SQLite job execution database."""

    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            # Default to a persistent path in user/app dir or temp
            base_dir = os.environ.get('EKUMEN_DATA_DIR', '')
            if not base_dir or not os.path.exists(base_dir):
                base_dir = tempfile.gettempdir()
            self.db_path = os.path.join(base_dir, 'ekumen_jobs.db')
        else:
            self.db_path = os.path.abspath(db_path)

        self._ensure_dir()
        self._init_db()

    def _ensure_dir(self):
        """Ensure parent directory exists."""
        parent = os.path.dirname(self.db_path)
        if parent:
            try:
                os.makedirs(parent, exist_ok=True)
            except OSError as e:
                logger.warning("Could not create DB directory %s: %s", parent, e)

    def _get_connection(self) -> sqlite3.Connection:
        """Create a sqlite connection with dict row factory."""
        conn = sqlite3.connect(self.db_path, timeout=15.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize database schema if not present."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    mode TEXT NOT NULL,
                    target_name TEXT,
                    status TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration REAL DEFAULT 0.0,
                    host_count INTEGER DEFAULT 0,
                    hosts_summary TEXT,
                    recap_ok INTEGER DEFAULT 0,
                    recap_changed INTEGER DEFAULT 0,
                    recap_unreachable INTEGER DEFAULT 0,
                    recap_failed INTEGER DEFAULT 0,
                    recap_skipped INTEGER DEFAULT 0,
                    output TEXT DEFAULT '',
                    params_json TEXT DEFAULT '{}'
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_start_time ON jobs(start_time DESC)")
            conn.commit()

    def create_job(self, data: Dict[str, Any]) -> str:
        """Insert a new job execution record."""
        job_id = str(data['id'])
        params = data.get('params', {})
        # Filter sensitive fields before saving
        safe_params = {k: v for k, v in params.items() if 'password' not in k.lower() and 'key' not in k.lower()}

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO jobs (
                    id, mode, target_name, status, start_time, end_time, duration,
                    host_count, hosts_summary, recap_ok, recap_changed,
                    recap_unreachable, recap_failed, recap_skipped, output, params_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                data.get('mode', 'adhoc'),
                data.get('target_name', ''),
                data.get('status', 'running'),
                data.get('start_time', ''),
                data.get('end_time'),
                data.get('duration', 0.0),
                data.get('host_count', 0),
                data.get('hosts_summary', ''),
                data.get('recap_ok', 0),
                data.get('recap_changed', 0),
                data.get('recap_unreachable', 0),
                data.get('recap_failed', 0),
                data.get('recap_skipped', 0),
                data.get('output', ''),
                json.dumps(safe_params)
            ))
            conn.commit()

        return job_id

    def update_job(self, job_id: str, updates: Dict[str, Any]) -> bool:
        """Update fields of an existing job record."""
        if not updates:
            return True

        fields = []
        values = []

        for k, v in updates.items():
            if k == 'params':
                fields.append("params_json = ?")
                safe_params = {pk: pv for pk, pv in v.items() if 'password' not in pk.lower() and 'key' not in pk.lower()}
                values.append(json.dumps(safe_params))
            else:
                fields.append(f"{k} = ?")
                values.append(v)

        values.append(job_id)
        query = f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?"

        with self._get_connection() as conn:
            cursor = conn.execute(query, values)
            conn.commit()
            return cursor.rowcount > 0

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific job record by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            if not row:
                return None

            result = dict(row)
            try:
                result['params'] = json.loads(result.get('params_json') or '{}')
            except Exception:
                result['params'] = {}
            return result

    def list_jobs(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List job history with pagination (excluding full output for lightweight list)."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, mode, target_name, status, start_time, end_time, duration,
                       host_count, hosts_summary, recap_ok, recap_changed,
                       recap_unreachable, recap_failed, recap_skipped, params_json
                FROM jobs
                ORDER BY start_time DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))

            jobs = []
            for row in cursor.fetchall():
                item = dict(row)
                try:
                    item['params'] = json.loads(item.get('params_json') or '{}')
                except Exception:
                    item['params'] = {}
                jobs.append(item)

            return jobs

    def delete_job(self, job_id: str) -> bool:
        """Delete a single job execution from history."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_jobs(self) -> bool:
        """Delete all job history."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM jobs")
            conn.commit()
            return True
