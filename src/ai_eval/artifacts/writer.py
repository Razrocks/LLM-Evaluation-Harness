"""Per-run artifact storage.

Everything a run produces lands under ``runs/<run_id>/`` as append-only evidence. Writes are
atomic (temp file + ``os.replace``) so a crashed run never leaves a half-written manifest. The
cardinal rule (ADR 0002) is enforced by the orchestrator's call order: :meth:`write_raw` is
invoked for a case execution *before* any parsing of that output ever happens.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def _safe(name: str) -> str:
    return name.replace(":", "_").replace("/", "_").replace("\\", "_")


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class RunPaths:
    def __init__(self, runs_dir: Path, run_id: str) -> None:
        self.root = runs_dir / run_id
        self.raw = self.root / "raw"

    @property
    def manifest(self) -> Path:
        return self.root / "run_manifest.json"

    @property
    def case_executions(self) -> Path:
        return self.root / "case_executions.jsonl"

    @property
    def traces(self) -> Path:
        return self.root / "traces.jsonl"

    def raw_file(self, case_execution_id: str) -> Path:
        return self.raw / f"{_safe(case_execution_id)}.json"


class RunArtifactWriter:
    """Writes the M2 evidence artifacts for one run."""

    def __init__(self, runs_dir: Path, run_id: str) -> None:
        self.paths = RunPaths(runs_dir, run_id)
        self.paths.root.mkdir(parents=True, exist_ok=True)
        self.paths.raw.mkdir(parents=True, exist_ok=True)

    def write_manifest(self, manifest_json: dict[str, Any]) -> None:
        _atomic_write(
            self.paths.manifest, json.dumps(manifest_json, indent=2, ensure_ascii=False) + "\n"
        )

    def write_raw(self, case_execution_id: str, raw_output: str | None) -> Path:
        """Persist the raw target output verbatim, before any parsing. Returns its path."""
        path = self.paths.raw_file(case_execution_id)
        _atomic_write(path, raw_output if raw_output is not None else "")
        return path

    def append_case_execution(self, record: dict[str, Any]) -> None:
        self._append_jsonl(self.paths.case_executions, [record])

    def append_traces(self, events: list[dict[str, Any]]) -> None:
        self._append_jsonl(self.paths.traces, events)

    @staticmethod
    def _append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
