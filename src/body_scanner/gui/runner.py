"""Subprocess runner: spawns ``run_scan.py`` and streams its output.

State machine:

    idle  ──start()──▶ running  ──proc exits──▶ idle (emits {'done', rc})
                          │
                          └──cancel()──▶ terminating ──▶ idle

Only one scan can be in flight at a time; :meth:`Runner.start` raises
:class:`RuntimeError` if called while a subprocess is already running.
A thread-safe queue accumulates dict messages (``{'line': str}`` or
``{'done': True, 'rc': int}``) that the SSE route drains.
"""
from __future__ import annotations

import queue
import subprocess
import threading
from pathlib import Path
from typing import Sequence


class Runner:
    """Owns the pipeline subprocess + a thread-safe message queue."""

    def __init__(self, cwd: Path | str) -> None:
        self.cwd = str(cwd)
        self.proc: subprocess.Popen[str] | None = None
        self.q: queue.Queue[dict] = queue.Queue()
        self._lock = threading.Lock()

    def is_running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def start(self, cmd: Sequence[str]) -> None:
        """Spawn the subprocess. Raises if one is already running."""
        with self._lock:
            if self.is_running():
                raise RuntimeError("a scan is already running")
            self.q = queue.Queue()
            self.proc = subprocess.Popen(  # noqa: S603 — list args, no shell.
                list(cmd), cwd=self.cwd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
            self.q.put({"line": "$ " + " ".join(cmd) + "\n\n"})
            threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self) -> None:
        proc = self.proc
        assert proc is not None and proc.stdout is not None
        for line in proc.stdout:
            self.q.put({"line": line})
        rc = proc.wait()
        self.q.put({"done": True, "rc": rc})

    def cancel(self) -> None:
        """Terminate the subprocess if running; no-op otherwise."""
        with self._lock:
            if self.is_running():
                assert self.proc is not None
                self.proc.terminate()
                self.q.put({"line": "\n[cancelled by user]\n"})
