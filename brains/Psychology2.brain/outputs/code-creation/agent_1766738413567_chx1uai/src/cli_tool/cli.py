from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any, Dict, Optional

import typer

app = typer.Typer(add_completion=False, no_args_is_help=True, help="Canonical cli_tool entrypoint.")

DEFAULT_THRESHOLDS: Dict[str, float] = {
    "overall": 0.50,
    "high": 0.70,
    "critical": 0.90,
}


def _coerce_thresholds(
    overall: float,
    high: float,
    critical: float,
    thresholds_json: Optional[str],
) -> Dict[str, float]:
    thresholds: Dict[str, float] = dict(DEFAULT_THRESHOLDS)
    thresholds.update({"overall": float(overall), "high": float(high), "critical": float(critical)})
    if thresholds_json:
        try:
            overrides = json.loads(thresholds_json)
        except Exception as e:  # pragma: no cover
            raise typer.BadParameter(f"--risk-thresholds-json must be valid JSON: {e}") from e
        if not isinstance(overrides, dict):
            raise typer.BadParameter("--risk-thresholds-json must decode to an object/dict.")
        for k, v in overrides.items():
            try:
                thresholds[str(k)] = float(v)
            except Exception as e:
                raise typer.BadParameter(f"Invalid threshold for key '{k}': {e}") from e
    for k, v in thresholds.items():
        if not (0.0 <= float(v) <= 1.0):
            raise typer.BadParameter(f"Risk threshold '{k}' must be in [0, 1], got {v}.")
    return thresholds


def _dispatch_run(run_kwargs: Dict[str, Any]) -> Any:
    from . import runner as runner_mod

    run_fn = getattr(runner_mod, "run", None)
    if run_fn is None:
        raise RuntimeError("cli_tool.runner.run not found.")

    try:
        sig = inspect.signature(run_fn)
    except Exception:  # pragma: no cover
        return run_fn(run_kwargs)

    params = sig.parameters
    if len(params) == 1:
        only = next(iter(params.values()))
        if only.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
            return run_fn(run_kwargs)

    filtered = {k: v for k, v in run_kwargs.items() if k in params}
    return run_fn(**filtered)


@app.command()
def run(
    goal: str = typer.Option("default", "--goal", help="Goal name for sweep orchestration (e.g., goal_10, goal_12)."),
    config: Optional[Path] = typer.Option(None, "--config", exists=False, dir_okay=False, help="Optional config file path."),
    prompt: Optional[str] = typer.Option(None, "--prompt", help="Optional prompt/input string for the run."),
    decompose_claims: bool = typer.Option(
        True,
        "--decompose-claims/--no-decompose-claims",
        help="Toggle claim decomposition to support goal_10/goal_12 sweeps.",
    ),
    risk_threshold: float = typer.Option(0.50, "--risk-threshold", min=0.0, max=1.0, help="Overall risk threshold in [0,1]."),
    risk_threshold_high: float = typer.Option(0.70, "--risk-threshold-high", min=0.0, max=1.0, help="High risk threshold in [0,1]."),
    risk_threshold_critical: float = typer.Option(
        0.90, "--risk-threshold-critical", min=0.0, max=1.0, help="Critical risk threshold in [0,1]."
    ),
    risk_thresholds_json: Optional[str] = typer.Option(
        None,
        "--risk-thresholds-json",
        help="Optional JSON object to override/add thresholds (e.g. '{"overall":0.4,"custom":0.2}').",
    ),
    seed: Optional[int] = typer.Option(None, "--seed", help="Optional seed forwarded to the runner/determinism layer."),
    dry_run: bool = typer.Option(False, "--dry-run", help="If set, runner may perform preflight without executing the full pipeline."),
) -> None:
    thresholds = _coerce_thresholds(risk_threshold, risk_threshold_high, risk_threshold_critical, risk_thresholds_json)
    run_kwargs: Dict[str, Any] = {
        "goal": goal,
        "config_path": str(config) if config else None,
        "config": str(config) if config else None,
        "prompt": prompt,
        "decompose_claims": decompose_claims,
        "claim_decomposition": decompose_claims,
        "risk_thresholds": thresholds,
        "risk_threshold": thresholds.get("overall"),
        "seed": seed,
        "dry_run": dry_run,
    }
    result = _dispatch_run(run_kwargs)
    if result is not None:
        try:
            typer.echo(json.dumps(result, ensure_ascii=False, sort_keys=True, default=str))
        except Exception:
            typer.echo(str(result))


def main() -> None:
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
