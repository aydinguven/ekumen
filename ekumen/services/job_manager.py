"""
Ekumen - Job Manager Service
Coordinates asynchronous job execution, real-time SSE streaming, process cancellation, and SQLite tracking.
"""

import datetime
import json
import logging
import queue
import threading
import time
import uuid
from typing import Dict, Any, Generator, Optional

from ekumen.services.runner import AnsibleRunner
from ekumen.services.database import JobDatabase
from ekumen.services.output_cache import OutputCache

logger = logging.getLogger(__name__)


class JobManager:
    """Manages active running Ansible jobs, real-time SSE queues, and SQLite updates."""

    def __init__(
        self,
        runner: AnsibleRunner,
        db: JobDatabase,
        output_cache: OutputCache
    ):
        self.runner = runner
        self.db = db
        self.output_cache = output_cache
        self.active_jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def start_job(self, payload: Dict[str, Any]) -> str:
        """
        Initiate an asynchronous Ansible execution and register in active jobs and SQLite.
        """
        job_id = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_') + uuid.uuid4().hex[:6]
        start_time_iso = datetime.datetime.now().isoformat()

        mode = payload.get('mode', 'adhoc')
        target_name = payload.get('playbook_name') or (
            payload.get('module') if mode == 'adhoc' else 'Custom Playbook'
        )

        inventory_raw = str(payload.get('inventory', ''))
        host_lines = [l.strip() for l in inventory_raw.splitlines() if l.strip() and not l.startswith('#') and not l.startswith('[')]
        host_count = len(host_lines)
        hosts_summary = ", ".join(host_lines[:3]) + (f" (+{len(host_lines)-3} more)" if len(host_lines) > 3 else "")

        # Initial database record
        self.db.create_job({
            'id': job_id,
            'mode': mode,
            'target_name': target_name,
            'status': 'running',
            'start_time': start_time_iso,
            'host_count': host_count,
            'hosts_summary': hosts_summary,
            'params': payload
        })

        cancel_event = threading.Event()

        job_info = {
            'id': job_id,
            'mode': mode,
            'target_name': target_name,
            'status': 'running',
            'start_time': time.time(),
            'start_time_iso': start_time_iso,
            'cancel_event': cancel_event,
            'listeners': [],
            'output_chunks': [],
            'result': None
        }

        with self._lock:
            self.active_jobs[job_id] = job_info

        # Spawn execution in worker thread
        thread = threading.Thread(
            target=self._run_job_thread,
            args=(job_id, payload, cancel_event),
            daemon=True
        )
        job_info['thread'] = thread
        thread.start()

        return job_id

    def _broadcast(self, job_id: str, event_data: Dict[str, Any]):
        """Send event payload to all SSE subscribers of this job."""
        with self._lock:
            job_info = self.active_jobs.get(job_id)
            if not job_info:
                return
            listeners = list(job_info['listeners'])

        msg = f"data: {json.dumps(event_data)}\n\n"
        for q in listeners:
            try:
                q.put_nowait(msg)
            except Exception:
                pass

    def _run_job_thread(self, job_id: str, payload: Dict[str, Any], cancel_event: threading.Event):
        """Worker thread executing Ansible and updating state."""
        start_t = time.time()

        def output_cb(chunk: str):
            with self._lock:
                if job_id in self.active_jobs:
                    self.active_jobs[job_id]['output_chunks'].append(chunk)
            self._broadcast(job_id, {'type': 'chunk', 'text': chunk})

        def check_cancel():
            return cancel_event.is_set()

        try:
            result = self.runner.run(
                data=payload,
                output_callback=output_cb,
                check_cancel=check_cancel
            )
        except Exception as e:
            logger.error("Job %s runner exception: %s", job_id, e)
            result = {
                'success': False,
                'output': '',
                'error': str(e),
                'recap': {}
            }

        end_t = time.time()
        duration = round(end_t - start_t, 2)
        end_time_iso = datetime.datetime.now().isoformat()

        if cancel_event.is_set():
            status = 'cancelled'
        elif result.get('success'):
            status = 'success'
        else:
            status = 'failed'

        full_output = result.get('output', '')
        if result.get('error') and result['error'] not in full_output:
            if full_output:
                full_output += f"\n\n--- STDERR / ERROR ---\n{result['error']}"
            else:
                full_output = f"--- ERROR ---\n{result['error']}"

        recap = result.get('recap') or {}

        # Save to output cache file
        self.output_cache.store(full_output)

        # Update SQLite DB
        self.db.update_job(job_id, {
            'status': status,
            'end_time': end_time_iso,
            'duration': duration,
            'recap_ok': recap.get('ok', 0),
            'recap_changed': recap.get('changed', 0),
            'recap_unreachable': recap.get('unreachable', 0),
            'recap_failed': recap.get('failed', 0),
            'recap_skipped': recap.get('skipped', 0),
            'output': full_output
        })

        with self._lock:
            if job_id in self.active_jobs:
                self.active_jobs[job_id]['status'] = status
                self.active_jobs[job_id]['result'] = result

        # Broadcast completion
        self._broadcast(job_id, {
            'type': 'done',
            'status': status,
            'duration': duration,
            'success': (status == 'success'),
            'recap': recap,
            'error': result.get('error', '')
        })

    def cancel_job(self, job_id: str) -> bool:
        """Signal an active job to terminate."""
        with self._lock:
            job_info = self.active_jobs.get(job_id)
            if not job_info or job_info['status'] != 'running':
                return False

            job_info['cancel_event'].set()
            return True

    def subscribe(self, job_id: str) -> Generator[str, None, None]:
        """
        Generator yielding SSE formatted strings for the job.
        First replays any buffered chunks, then streams live chunks until 'done'.
        """
        q = queue.Queue()
        buffered = []
        is_done = False
        final_status = None

        with self._lock:
            job_info = self.active_jobs.get(job_id)
            if not job_info:
                # Fallback to database if job already completed
                db_job = self.db.get_job(job_id)
                if db_job:
                    output = db_job.get('output', '')
                    recap = {
                        'ok': db_job.get('recap_ok', 0),
                        'changed': db_job.get('recap_changed', 0),
                        'unreachable': db_job.get('recap_unreachable', 0),
                        'failed': db_job.get('recap_failed', 0),
                        'skipped': db_job.get('recap_skipped', 0),
                    }
                    yield f"data: {json.dumps({'type': 'chunk', 'text': output})}\n\n"
                    yield f"data: {json.dumps({'type': 'done', 'status': db_job['status'], 'recap': recap, 'duration': db_job.get('duration', 0)})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Job not found'})}\n\n"
                return

            buffered = list(job_info['output_chunks'])
            if job_info['status'] != 'running':
                is_done = True
                final_status = job_info['status']
            else:
                job_info['listeners'].append(q)

        # Replay past buffer
        if buffered:
            combined = ''.join(buffered)
            yield f"data: {json.dumps({'type': 'chunk', 'text': combined})}\n\n"

        if is_done:
            db_job = self.db.get_job(job_id) or {}
            recap = {
                'ok': db_job.get('recap_ok', 0),
                'changed': db_job.get('recap_changed', 0),
                'unreachable': db_job.get('recap_unreachable', 0),
                'failed': db_job.get('recap_failed', 0),
                'skipped': db_job.get('recap_skipped', 0),
            }
            yield f"data: {json.dumps({'type': 'done', 'status': final_status, 'recap': recap, 'duration': db_job.get('duration', 0)})}\n\n"
            return

        # Stream live events
        try:
            while True:
                try:
                    msg = q.get(timeout=25.0)
                    yield msg
                    # If this was the done message, break
                    if '"type": "done"' in msg or '"type": "error"' in msg:
                        break
                except queue.Empty:
                    # Keep-alive heartbeat
                    yield ": ping\n\n"
        finally:
            with self._lock:
                if job_id in self.active_jobs and q in self.active_jobs[job_id]['listeners']:
                    self.active_jobs[job_id]['listeners'].remove(q)
