"""Versioned prompt specifications.

A prompt is treated like code: stored on disk under ``prompts/<workflow>/<version>/``, loaded
verbatim, and **content-hashed**. The hash goes into the run manifest, so "Claude vs Gemini" is
a comparison of two models under *the same* frozen instructions rather than an accident of
prompt wording.

Rendering is deliberately simple ``{{placeholder}}`` substitution rather than a template
engine: the system prompt contains literal JSON braces (which would break ``str.format``), the
substitution set is tiny and fixed, and a dependency-free renderer keeps the core install lean.
Document ordering is normalized so the same case always renders byte-identically.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from ai_eval.domain import content_hash


class PromptSpec(BaseModel):
    """An immutable, content-addressed instruction pair."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    prompt_spec_id: str
    version: str
    system: str
    user_template: str
    content_hash: str

    @property
    def ref(self) -> str:
        return f"{self.prompt_spec_id}.{self.version}"


class RenderedPrompt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    system: str
    user: str
    prompt_spec_ref: str
    prompt_spec_hash: str
    request_hash: str


def load_prompt_spec(root: Path, prompt_spec_id: str, version: str) -> PromptSpec:
    """Load ``<root>/<prompt_spec_id>/<version>/{system,user}.txt`` and hash its content."""
    directory = root / prompt_spec_id / version
    system = (directory / "system.txt").read_text(encoding="utf-8")
    user_template = (directory / "user.txt").read_text(encoding="utf-8")
    digest = content_hash(
        {"prompt_spec_id": prompt_spec_id, "version": version,
         "system": system, "user_template": user_template}
    )
    return PromptSpec(
        prompt_spec_id=prompt_spec_id,
        version=version,
        system=system,
        user_template=user_template,
        content_hash=digest,
    )


def _render_documents(documents: list[dict[str, Any]]) -> str:
    """Deterministic document block: sorted by document_id, version pinned."""
    if not documents:
        return "(none)"
    lines = []
    for doc in sorted(documents, key=lambda d: str(d.get("document_id", ""))):
        doc_id = doc.get("document_id", "?")
        version = doc.get("document_version", "?")
        text = str(doc.get("text", "")).strip()
        lines.append(f"- {doc_id} (v{version}): {text}")
    return "\n".join(lines)


def render_prompt(spec: PromptSpec, case_input: dict[str, Any]) -> RenderedPrompt:
    """Render the user message for one case input. Pure and deterministic."""
    metadata = case_input.get("metadata") or {}
    substitutions = {
        "request_id": str(case_input.get("request_id", "")),
        "received_at": str(case_input.get("received_at", "")),
        "reference_timezone": str(case_input.get("reference_timezone", "")),
        "metadata": json.dumps(metadata, sort_keys=True),
        "message": str(case_input.get("message", "")),
        "documents": _render_documents(case_input.get("documents") or []),
    }
    user = spec.user_template
    for key, value in substitutions.items():
        user = user.replace("{{" + key + "}}", value)

    return RenderedPrompt(
        system=spec.system,
        user=user,
        prompt_spec_ref=spec.ref,
        prompt_spec_hash=spec.content_hash,
        request_hash=content_hash({"system": spec.system, "user": user}),
    )
