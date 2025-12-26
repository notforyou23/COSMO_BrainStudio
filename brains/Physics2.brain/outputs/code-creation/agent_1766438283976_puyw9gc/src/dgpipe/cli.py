"""dgpipe CLI.

Small, dependency-light command line interface that operates on dgpipe's core
models (PipelineSpec, StageSpec, RunConfig). It supports creating, validating,
and inspecting pipeline specs stored as JSON.

Typical usage:
  dgpipe new pipeline.json
  dgpipe validate pipeline.json
  dgpipe show pipeline.json
  dgpipe plan pipeline.json
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Sequence

from . import __version__
from .models import PipelineSpec, StageSpec, stages_in_order
from .utils import ValidationError, DgpipeError, format_exception, json_dumps, read_json, write_json
def _load_spec(path: str | Path) -> PipelineSpec:
    d = read_json(path)
    if not isinstance(d, dict):
        raise ValidationError(f"Pipeline spec must be a JSON object: {path}")
    spec = PipelineSpec.from_dict(d)
    spec.validate()
    return spec


def _cmd_new(args: argparse.Namespace) -> int:
    spec = PipelineSpec(
        name=args.name,
        stages=[StageSpec(name="stage1", kind="python", config={"note": "edit me"})],
        metadata={"dgpipe_version": __version__},
    )
    if args.output:
        write_json(args.output, spec.to_dict())
    else:
        sys.stdout.write(json_dumps(spec.to_dict()) + "\n")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    _load_spec(args.spec)
    if not args.quiet:
        sys.stdout.write("OK\n")
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    spec = _load_spec(args.spec)
    sys.stdout.write(json_dumps(spec.to_dict()) + "\n")
    return 0


def _cmd_plan(args: argparse.Namespace) -> int:
    spec = _load_spec(args.spec)
    if args.stages:
        stage_specs = stages_in_order(spec, args.stages)
        missing = [n for n in args.stages if n not in {s.name for s in stage_specs}]
        if missing:
            raise ValidationError(f"Unknown stage(s): {missing}")
    else:
        stage_specs = list(spec.stages)
    for s in stage_specs:
        req = f" requires={s.requires}" if s.requires else ""
        sys.stdout.write(f"{s.name} kind={s.kind}{req}\n")
    return 0
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dgpipe",
        description="Work with dgpipe pipeline specs (JSON).",
    )
    p.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")

    sub = p.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser("new", help="Create a minimal pipeline spec JSON.")
    p_new.add_argument("output", nargs="?", help="Output path (default: stdout).")
    p_new.add_argument("--name", default="pipeline", help="Pipeline name.")
    p_new.set_defaults(func=_cmd_new)

    p_val = sub.add_parser("validate", help="Validate a pipeline spec JSON file.")
    p_val.add_argument("spec", help="Path to pipeline spec JSON.")
    p_val.add_argument("-q", "--quiet", action="store_true", help="Suppress OK output.")
    p_val.set_defaults(func=_cmd_validate)

    p_show = sub.add_parser("show", help="Print a normalized pipeline spec JSON.")
    p_show.add_argument("spec", help="Path to pipeline spec JSON.")
    p_show.set_defaults(func=_cmd_show)

    p_plan = sub.add_parser("plan", help="Print a stage execution plan (in order).")
    p_plan.add_argument("spec", help="Path to pipeline spec JSON.")
    p_plan.add_argument(
        "stages",
        nargs="*",
        help="Optional stage names to filter the plan (still in pipeline order).",
    )
    p_plan.set_defaults(func=_cmd_plan)

    return p


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    p = build_parser()
    try:
        args = p.parse_args(argv)
        return int(args.func(args))
    except (ValidationError, DgpipeError, ValueError) as e:
        sys.stderr.write(format_exception(e) + "\n")
        return 2
    except KeyboardInterrupt:
        sys.stderr.write("Interrupted\n")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
