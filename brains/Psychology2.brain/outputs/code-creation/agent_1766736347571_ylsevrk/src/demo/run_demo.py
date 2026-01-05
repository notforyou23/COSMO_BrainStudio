from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_demo_dataset(root: Path) -> dict[str, Path]:
    root.mkdir(parents=True, exist_ok=True)

    # Canonical convention assumed by the project:
    # StudyID:  STU-YYYY-NNNN  (e.g., STU-2025-0001)
    # EffectID: EFF-YYYY-NNNN-NNN (e.g., EFF-2025-0001-001)
    #
    # This demo intentionally creates a mismatch:
    # CSV uses EffectID=EFF-2025-0001-001 while JSONL uses EffectID=EFF-2025-0001-002
    csv_path = root / "effects.csv"
    jsonl_path = root / "effects.jsonl"
    prereg_path = root / "prereg_template.txt"

    csv_text = (
        "StudyID,EffectID,Outcome,Estimate\n"
        "STU-2025-0001,EFF-2025-0001-001,test_score,0.25\n"
    )
    csv_path.write_text(csv_text, encoding="utf-8")

    jsonl_records = [
        {
            "StudyID": "STU-2025-0001",
            "EffectID": "EFF-2025-0001-002",  # INTENTIONAL MISMATCH vs CSV
            "Outcome": "test_score",
            "Estimate": 0.25,
        }
    ]
    jsonl_path.write_text("\n".join(json.dumps(r) for r in jsonl_records) + "\n", encoding="utf-8")

    prereg_text = (
        "Preregistration Template\n"
        "StudyID: STU-2025-0001\n"
        "EffectID: EFF-2025-0001-001\n"
        "Notes: This prereg matches the CSV; JSONL is intentionally mismatched.\n"
    )
    prereg_path.write_text(prereg_text, encoding="utf-8")

    return {"csv": csv_path, "jsonl": jsonl_path, "prereg": prereg_path}


def _run_checker_via_import(paths: dict[str, Path]) -> int | None:
    try:
        from src.ids import checker as checker_mod  # type: ignore
    except Exception:
        return None

    argv = [
        "--csv",
        str(paths["csv"]),
        "--jsonl",
        str(paths["jsonl"]),
        "--prereg",
        str(paths["prereg"]),
    ]

    main = getattr(checker_mod, "main", None)
    if callable(main):
        try:
            rc = main(argv)  # may return int or None or raise SystemExit
            return 0 if (rc is None or rc == 0) else int(rc)
        except SystemExit as e:
            return int(e.code or 0)

    check_fns = [getattr(checker_mod, n, None) for n in ("check", "run_check", "check_ids", "run")]
    check_fn = next((f for f in check_fns if callable(f)), None)
    if check_fn is None:
        return None

    try:
        res = check_fn(str(paths["csv"]), str(paths["jsonl"]), str(paths["prereg"]))
    except TypeError:
        try:
            res = check_fn(paths)
        except Exception:
            return None

    if isinstance(res, dict):
        ok = bool(res.get("ok", res.get("success", False)))
        return 0 if ok else 2
    if hasattr(res, "ok"):
        return 0 if bool(getattr(res, "ok")) else 2
    if isinstance(res, bool):
        return 0 if res else 2
    if isinstance(res, int):
        return res
    return 0


def _run_checker_via_subprocess(paths: dict[str, Path]) -> int:
    cmd = [
        sys.executable,
        "-m",
        "src.ids.checker",
        "--csv",
        str(paths["csv"]),
        "--jsonl",
        str(paths["jsonl"]),
        "--prereg",
        str(paths["prereg"]),
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = (p.stdout or "").strip()
    err = (p.stderr or "").strip()
    if out:
        print(out)
    if err:
        print(err, file=sys.stderr)
    return int(p.returncode)


def main() -> int:
    here = Path(__file__).resolve().parent
    demo_root = here / "demo_dataset_intentional_mismatch"
    paths = _write_demo_dataset(demo_root)

    print("DEMO: Running ID checker on an intentionally mismatched dataset")
    print(f"DEMO: CSV={paths['csv'].as_posix()}")
    print(f"DEMO: JSONL={paths['jsonl'].as_posix()}")
    print(f"DEMO: PREREG={paths['prereg'].as_posix()}")
    print("DEMO: Expected behavior: checker reports an ID mismatch (EffectID differs across files) and exits non-zero.")

    rc = _run_checker_via_import(paths)
    if rc is None:
        rc = _run_checker_via_subprocess(paths)

    if rc == 0:
        print("UNEXPECTED: checker exited 0 despite intentional mismatch")
        return 3

    print(f"EXPECTED_FAILURE: checker exited non-zero (rc={rc}) due to intentional ID mismatch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
