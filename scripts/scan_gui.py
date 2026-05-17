"""Tkinter front-end for ``scripts/run_scan.py``.

Lets the user pick a Stray Scanner capture folder, fill in sewer
identity (name, birthday) and a few export choices, then launches the
full pipeline as a subprocess and streams the log into the window.

Run::

    .venv/bin/python scripts/scan_gui.py

Tkinter is stdlib so no extra deps. ``tkcalendar`` is optional — if
installed the birthday/scan-date fields become real date pickers,
otherwise they fall back to plain text entries with ``yyyy-mm-dd``
format validation.
"""
from __future__ import annotations

import datetime as dt
import queue
import re
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

REPO_ROOT = Path(__file__).resolve().parent.parent
RUN_SCAN = REPO_ROOT / "scripts" / "run_scan.py"
DEFAULT_RESULTS_DIR = REPO_ROOT / "data" / "results"
# Always launch the pipeline with the project venv so we get torch /
# smplx / open3d / etc. even when the GUI itself runs under a system
# Python (the pyenv build often lacks _tkinter, so users may end up
# starting the GUI via /usr/bin/python3).
VENV_PY = REPO_ROOT / ".venv" / "bin" / "python"
PIPELINE_PY = str(VENV_PY) if VENV_PY.is_file() else sys.executable

# Color presets — must match body_scanner.preprocess.waist_string.COLOR_PRESETS.
WAIST_COLOR_CHOICES = (
    "(none)", "red", "cyan", "green", "magenta", "yellow", "blue", "orange",
)

# UI label → run_scan --pattern-system value.
PATTERN_SYSTEMS = {
    "Aldrich (5th ed.)": "aldrich",
    "dpm (Diane Penner)": "dpm",
    "Both (Aldrich + dpm)": "all",
    "Seamly catalog only": "seamly_only",
}

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _slugify(name: str) -> str:
    """Lowercase, ascii-ish, underscore-separated stem for the output prefix."""
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s or "scan"


def _validate_iso_date(value: str) -> bool:
    if not DATE_RE.match(value):
        return False
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True


class _DateField(ttk.Frame):
    """Date entry. Uses tkcalendar.DateEntry if available, else a plain Entry."""

    def __init__(self, parent: tk.Misc, default: dt.date) -> None:
        super().__init__(parent)
        self._fallback = True
        try:  # noqa: SIM105 — explicit fall-through is clearer than suppress.
            from tkcalendar import DateEntry  # type: ignore
            self._widget = DateEntry(
                self, date_pattern="yyyy-mm-dd", width=12,
                year=default.year, month=default.month, day=default.day,
            )
            self._fallback = False
        except ImportError:
            self._var = tk.StringVar(value=default.isoformat())
            self._widget = ttk.Entry(self, textvariable=self._var, width=14)
        self._widget.pack(side="left")
        if self._fallback:
            ttk.Label(self, text="yyyy-mm-dd", foreground="grey").pack(
                side="left", padx=4)

    def get(self) -> str:
        if self._fallback:
            return self._var.get().strip()
        return self._widget.get_date().isoformat()  # type: ignore[union-attr]

    def is_valid(self) -> bool:
        v = self.get()
        return not v or _validate_iso_date(v)


class ScanGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MyFit — Body Scan")
        self.geometry("760x620")
        self.minsize(680, 520)

        # State.
        self.capture_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.scan_date = _DateField  # placeholder, real widget created below
        self.color_var = tk.StringVar(value=WAIST_COLOR_CHOICES[0])
        self.system_var = tk.StringVar(value="Aldrich (5th ed.)")
        self.export_csv = tk.BooleanVar(value=True)
        self.export_obj = tk.BooleanVar(value=True)
        self.export_smis = tk.BooleanVar(value=True)
        self.out_prefix_var = tk.StringVar()
        self._prefix_user_edited = False
        self._proc: subprocess.Popen[str] | None = None
        self._log_q: queue.Queue[str] = queue.Queue()

        self._build_form()
        self._build_log()
        self._poll_log()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_form(self) -> None:
        frm = ttk.Frame(self, padding=12)
        frm.pack(side="top", fill="x")
        row = 0

        ttk.Label(frm, text="Stray capture folder").grid(
            row=row, column=0, sticky="w")
        e = ttk.Entry(frm, textvariable=self.capture_var, width=60)
        e.grid(row=row, column=1, sticky="we", padx=4)
        ttk.Button(frm, text="Browse…", command=self._pick_capture).grid(
            row=row, column=2)
        row += 1

        ttk.Label(frm, text="Person name").grid(row=row, column=0, sticky="w")
        ne = ttk.Entry(frm, textvariable=self.name_var, width=40)
        ne.grid(row=row, column=1, sticky="w", padx=4)
        self.name_var.trace_add("write", lambda *_: self._refresh_prefix())
        row += 1

        ttk.Label(frm, text="Birthday").grid(row=row, column=0, sticky="w")
        self.birthday_field = _DateField(frm, default=dt.date(1990, 1, 1))
        self.birthday_field.grid(row=row, column=1, sticky="w", padx=4)
        row += 1

        ttk.Label(frm, text="Scan date").grid(row=row, column=0, sticky="w")
        self.scan_date_field = _DateField(frm, default=dt.date.today())
        self.scan_date_field.grid(row=row, column=1, sticky="w", padx=4)
        # Refresh prefix when scan date changes (tkcalendar fires <<DateEntrySelected>>).
        self.scan_date_field.bind_all(
            "<<DateEntrySelected>>",
            lambda _e: self._refresh_prefix(), add="+")
        row += 1

        ttk.Label(frm, text="Waist band colour").grid(
            row=row, column=0, sticky="w")
        cb = ttk.Combobox(frm, textvariable=self.color_var,
                          values=WAIST_COLOR_CHOICES, state="readonly",
                          width=18)
        cb.grid(row=row, column=1, sticky="w", padx=4)
        ttk.Label(frm, foreground="grey",
                  text="Optional. Without it the SMPL-X anatomical waist "
                       "is used.").grid(row=row, column=2, sticky="w")
        row += 1

        ttk.Label(frm, text="Pattern system").grid(
            row=row, column=0, sticky="w")
        sb = ttk.Combobox(frm, textvariable=self.system_var,
                          values=list(PATTERN_SYSTEMS),
                          state="readonly", width=22)
        sb.grid(row=row, column=1, sticky="w", padx=4)
        ttk.Label(frm, foreground="grey",
                  text="Controls the filtered named CSV.").grid(
                      row=row, column=2, sticky="w")
        row += 1

        ttk.Label(frm, text="Export artifacts").grid(
            row=row, column=0, sticky="w")
        ex = ttk.Frame(frm)
        ex.grid(row=row, column=1, columnspan=2, sticky="w", padx=4)
        ttk.Checkbutton(ex, text="CSV", variable=self.export_csv).pack(
            side="left", padx=(0, 12))
        ttk.Checkbutton(ex, text="Fitted OBJ", variable=self.export_obj).pack(
            side="left", padx=(0, 12))
        ttk.Checkbutton(ex, text="SMIS", variable=self.export_smis).pack(
            side="left")
        row += 1

        ttk.Label(frm, text="Output prefix").grid(
            row=row, column=0, sticky="w")
        pe = ttk.Entry(frm, textvariable=self.out_prefix_var, width=60)
        pe.grid(row=row, column=1, sticky="we", padx=4)
        pe.bind("<Key>", lambda _e: self._mark_prefix_edited())
        row += 1

        frm.columnconfigure(1, weight=1)

        # Buttons.
        btns = ttk.Frame(self, padding=(12, 0))
        btns.pack(side="top", fill="x")
        self.run_btn = ttk.Button(
            btns, text="Run scan", command=self._on_run)
        self.run_btn.pack(side="right")
        self.cancel_btn = ttk.Button(
            btns, text="Cancel", command=self._on_cancel, state="disabled")
        self.cancel_btn.pack(side="right", padx=(0, 8))

        self._refresh_prefix()

    def _build_log(self) -> None:
        wrap = ttk.LabelFrame(self, text="Log", padding=6)
        wrap.pack(side="top", fill="both", expand=True, padx=12, pady=12)
        self.log = tk.Text(wrap, height=18, wrap="word", state="disabled",
                           font=("Menlo", 11))
        self.log.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.log.yview)
        sb.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=sb.set)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _pick_capture(self) -> None:
        path = filedialog.askdirectory(title="Pick Stray capture folder")
        if path:
            self.capture_var.set(path)
            self._refresh_prefix()

    def _mark_prefix_edited(self) -> None:
        self._prefix_user_edited = True

    def _refresh_prefix(self) -> None:
        if self._prefix_user_edited:
            return
        name = _slugify(self.name_var.get())
        try:
            scan_date = self.scan_date_field.get() or dt.date.today().isoformat()
        except AttributeError:
            scan_date = dt.date.today().isoformat()
        date_compact = scan_date.replace("-", "")
        prefix = DEFAULT_RESULTS_DIR / f"{name}_{date_compact}"
        self.out_prefix_var.set(str(prefix))

    def _append_log(self, line: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", line)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _poll_log(self) -> None:
        try:
            while True:
                line = self._log_q.get_nowait()
                self._append_log(line)
        except queue.Empty:
            pass
        # Detect process termination.
        if self._proc is not None and self._proc.poll() is not None:
            rc = self._proc.returncode
            self._append_log(f"\n[exit {rc}]\n")
            self._proc = None
            self.run_btn.configure(state="normal")
            self.cancel_btn.configure(state="disabled")
        self.after(120, self._poll_log)

    # ------------------------------------------------------------------
    # Run / cancel
    # ------------------------------------------------------------------

    def _validate(self) -> str | None:
        cap = self.capture_var.get().strip()
        if not cap:
            return "Pick a Stray capture folder."
        if not Path(cap).is_dir():
            return f"Capture folder does not exist: {cap}"
        if not self.name_var.get().strip():
            return "Enter a person name."
        if not self.birthday_field.is_valid():
            return "Birthday must be yyyy-mm-dd."
        if not self.scan_date_field.is_valid():
            return "Scan date must be yyyy-mm-dd."
        if not (self.export_csv.get() or self.export_obj.get()
                or self.export_smis.get()):
            return "Pick at least one export artifact."
        return None

    def _build_cmd(self) -> list[str]:
        out_prefix = self.out_prefix_var.get().strip()
        name = self.name_var.get().strip().split()
        given = name[0] if name else ""
        family = " ".join(name[1:]) if len(name) > 1 else ""
        system = PATTERN_SYSTEMS[self.system_var.get()]
        cmd = [
            PIPELINE_PY, str(RUN_SCAN),
            self.capture_var.get().strip(),
            "--out-prefix", out_prefix,
            "--pattern-system", system,
            f"--{'export' if self.export_csv.get() else 'no-export'}-csv",
            f"--{'export' if self.export_obj.get() else 'no-export'}-obj",
            f"--{'export' if self.export_smis.get() else 'no-export'}-smis",
        ]
        color = self.color_var.get()
        if color and color != "(none)":
            cmd.extend(["--waist-color", color])
        bday = self.birthday_field.get()
        if bday:
            cmd.extend(["--person-birth-date", bday])
        if given:
            cmd.extend(["--person-given-name", given])
        if family:
            cmd.extend(["--person-family-name", family])
        return cmd

    def _on_run(self) -> None:
        err = self._validate()
        if err:
            messagebox.showerror("Missing input", err)
            return
        cmd = self._build_cmd()
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self._append_log("$ " + " ".join(cmd) + "\n\n")
        self.run_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self._proc = subprocess.Popen(  # noqa: S603 — args list, no shell.
            cmd, cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self) -> None:
        assert self._proc is not None
        assert self._proc.stdout is not None
        for line in self._proc.stdout:
            self._log_q.put(line)

    def _on_cancel(self) -> None:
        if self._proc is None:
            return
        self._proc.terminate()
        self._append_log("\n[cancelled by user]\n")


def main() -> int:
    app = ScanGUI()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
