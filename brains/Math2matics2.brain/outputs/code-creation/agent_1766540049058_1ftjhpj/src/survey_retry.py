from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import os
from typing import Any, Dict, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, sort_keys=True) + "\n")


@dataclass(frozen=True)
class CanonicalPaths:
    outputs_dir: Path
    run_id: str

    @property
    def index_json(self) -> Path:
        return self.outputs_dir / "index.json"

    @property
    def run_dir(self) -> Path:
        return self.outputs_dir / "runs" / self.run_id

    @property
    def run_evidence_jsonl(self) -> Path:
        return self.run_dir / "run_evidence.jsonl"

    @property
    def survey_domain_dir(self) -> Path:
        return self.outputs_dir / "domain" / "survey"

    @property
    def survey_input_json(self) -> Path:
        return self.survey_domain_dir / "survey_input.json"

    @property
    def survey_result_json(self) -> Path:
        return self.survey_domain_dir / "survey_result.json"
def _update_outputs_index(paths: CanonicalPaths, artifact_key: str, rel_path: str, meta: Dict[str, Any]) -> None:
    """Upserts a single artifact entry in outputs/index.json (deterministic location)."""
    idx = _read_json(paths.index_json) or {"schema": "outputs-index.v1", "artifacts": {}}
    artifacts = idx.setdefault("artifacts", {})
    artifacts[artifact_key] = {"path": rel_path, "updated_at": _utc_now_iso(), **meta}
    _write_json(paths.index_json, idx)


def _record_run_event(paths: CanonicalPaths, event_type: str, payload: Dict[str, Any]) -> None:
    _append_jsonl(
        paths.run_evidence_jsonl,
        {"ts": _utc_now_iso(), "run_id": paths.run_id, "event": event_type, "payload": payload},
    )
def reattempt_blocked_survey(
    outputs_dir: Path,
    run_id: str,
    *,
    blocked_reason: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Re-attempt the previously blocked survey task using canonical /outputs artifacts.

    This implementation is offline/CI-safe: it reuses a local survey_input.json if present.
    If absent, it writes a stub input and records a blocked result while still producing evidence.
    """
    outputs_dir = Path(outputs_dir)
    paths = CanonicalPaths(outputs_dir=outputs_dir, run_id=run_id)
    ctx = context or {}

    _record_run_event(paths, "survey_retry_started", {"blocked_reason": blocked_reason, "context": ctx})

    survey_input = _read_json(paths.survey_input_json)
    if survey_input is None:
        survey_input = {
            "schema": "survey-input.v1",
            "note": "No input provided; retry runs in offline mode and cannot fetch external survey source.",
            "context": ctx,
        }
        _write_json(paths.survey_input_json, survey_input)
        _update_outputs_index(
            paths,
            "domain.survey.input",
            str(paths.survey_input_json.relative_to(outputs_dir)),
            {"schema": survey_input.get("schema"), "kind": "domain_artifact"},
        )
        _record_run_event(paths, "survey_retry_input_stub_written", {"path": str(paths.survey_input_json)})

    questions = survey_input.get("questions")
    answers = survey_input.get("answers")
    can_complete = isinstance(questions, list) and (answers is None or isinstance(answers, dict))

    if can_complete:
        status = "completed"
        summary = {"question_count": len(questions), "answered_count": len(answers or {})}
        result_payload: Dict[str, Any] = {
            "schema": "survey-result.v1",
            "status": status,
            "summary": summary,
            "input_path": str(paths.survey_input_json.relative_to(outputs_dir)),
            "blocked_reason": blocked_reason,
        }
    else:
        status = "blocked"
        result_payload = {
            "schema": "survey-result.v1",
            "status": status,
            "blocked_reason": blocked_reason or "missing_or_invalid_local_input",
            "input_path": str(paths.survey_input_json.relative_to(outputs_dir)),
            "hint": "Provide outputs/domain/survey/survey_input.json with a 'questions' list to complete offline.",
        }

    _write_json(paths.survey_result_json, result_payload)
    _update_outputs_index(
        paths,
        "domain.survey.result",
        str(paths.survey_result_json.relative_to(outputs_dir)),
        {"schema": result_payload.get("schema"), "kind": "domain_artifact", "status": status},
    )
    _record_run_event(
        paths,
        "survey_retry_finished",
        {"status": status, "result_path": str(paths.survey_result_json), "index_path": str(paths.index_json)},
    )
    return result_payload
def main(argv: Optional[list[str]] = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Re-attempt the blocked survey task using canonical outputs artifacts.")
    p.add_argument("--outputs", default=os.environ.get("OUTPUTS_DIR", "outputs"), help="Outputs directory root.")
    p.add_argument("--run-id", default=os.environ.get("RUN_ID", "local"), help="Run identifier.")
    p.add_argument("--blocked-reason", default=None, help="Original blocked reason (for evidence).")
    args = p.parse_args(argv)

    result = reattempt_blocked_survey(Path(args.outputs), args.run_id, blocked_reason=args.blocked_reason)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
