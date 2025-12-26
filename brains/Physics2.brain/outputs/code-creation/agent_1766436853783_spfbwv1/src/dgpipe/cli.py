from __future__ import annotations
import argparse, json, math, os, platform, random, sys, hashlib, datetime, subprocess
from pathlib import Path
def _utcnow() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def _maybe_git_rev(cwd: Path) -> str | None:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(cwd), stderr=subprocess.DEVNULL)
        return out.decode().strip()
    except Exception:
        return None

def _provenance(argv: list[str], outdir: Path) -> dict:
    return {
        "timestamp_utc": _utcnow(),
        "argv": argv,
        "python": sys.version.split()[0],
        "platform": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
        "git_rev": _maybe_git_rev(Path.cwd()),
        "outdir": str(outdir),
    }

def _write_json(path: Path, obj: dict) -> None:
    data = json.dumps(obj, indent=2, sort_keys=True).encode("utf-8")
    path.write_bytes(data)
def generate_protocols() -> dict:
    # Prioritized protocols for correlators + entanglement diagnostics across analogue/astro probes.
    return {
        "version": 1,
        "parameters": {
            "ell": "discreteness length scale (effective) controlling dispersive corrections",
            "rho": "sprinkling density / microstructure density proxy",
            "alpha": "dimensionless dispersion strength",
        },
        "protocols": [
            {
                "priority": 1,
                "name": "Equal-time two-point correlator C(x) in analogue QFT",
                "platforms": ["BEC phonons", "optical waveguides", "superconducting circuits"],
                "observable": "C(x)=<phi(0)phi(x)> or density-density correlator",
                "measurement": "homodyne/Bragg imaging; extract C(x) and Fourier spectrum S(k)",
                "signature": "UV roll-off and oscillatory residuals consistent with discrete spectrum / modified dispersion",
                "systematics": ["finite-size", "trap inhomogeneity", "detector resolution", "thermal background"],
            },
            {
                "priority": 2,
                "name": "Unequal-time correlator C(t) and retarded Green's function",
                "platforms": ["optomechanical arrays", "cold-atom simulators"],
                "observable": "C(t)=<phi(0)phi(t)>, G_R(t)",
                "measurement": "pump-probe; quench then read out temporal correlations",
                "signature": "phase slip / beating from discrete modes; dispersive group-delay shifts",
                "systematics": ["dispersion calibration", "sampling jitter", "bath coupling"],
            },
            {
                "priority": 3,
                "name": "Entanglement diagnostics via mutual information / negativity proxy",
                "platforms": ["continuous-variable photonics", "cQED", "ion chains"],
                "observable": "I(A:B) from covariance matrix; logarithmic negativity if accessible",
                "measurement": "Gaussian tomography / quadrature readout; build covariance blocks",
                "signature": "scale-dependent suppression/enhancement across partitions tracking ell, rho",
                "systematics": ["loss", "mode mismatch", "finite squeezing", "classical correlations"],
            },
            {
                "priority": 4,
                "name": "Astrophysical time-of-flight dispersion constraints",
                "platforms": ["GRB/FRB timing", "GW multi-messenger"],
                "observable": "energy-dependent arrival delays",
                "measurement": "cross-band timing; hierarchical population model",
                "signature": "Δt ∝ alpha*ell^2*E^2*D (toy), bounded by non-detection",
                "systematics": ["intrinsic source lags", "plasma dispersion", "selection biases"],
            },
        ],
    }
def simulate(outdir: Path, n: int, dt: float, xi: float, omega: float, ell: float, alpha: float,
             rho: float, L: float, noise: float, seed: int) -> dict:
    random.seed(seed)
    # Toy model: correlator with dispersive correction and finite-size mode discretization.
    k0 = math.pi / max(L, 1e-9)  # IR mode spacing
    omega_eff = omega * (1.0 + alpha * (ell * k0) ** 2)
    times = [i * dt for i in range(n)]
    C = []
    for t in times:
        base = math.exp(-t / max(xi, 1e-9)) * math.cos(omega_eff * t)
        # Microstructure density proxy: small-amplitude ripple scaling with rho.
        ripple = 0.02 * math.tanh(rho) * math.cos(3.0 * omega_eff * t)
        y = base + ripple + random.gauss(0.0, noise)
        C.append(y)
    # Gaussian-state proxy: mutual information from an effective correlation coefficient r(t0).
    t0 = times[min(n - 1, max(1, n // 10))]
    r = max(-0.999, min(0.999, math.exp(-t0 / max(xi, 1e-9)) * (1.0 - 0.5 * alpha * (ell * k0) ** 2)))
    mutual_info = float(-0.5 * math.log(1.0 - r * r))
    return {
        "model": "toy_discrete_dispersion_v1",
        "inputs": {"n": n, "dt": dt, "xi": xi, "omega": omega, "ell": ell, "alpha": alpha, "rho": rho, "L": L, "noise": noise, "seed": seed},
        "data": {"t": times, "C": C, "mutual_info": mutual_info},
        "summary": {"C0": C[0], "C_rms": float(math.sqrt(sum(x*x for x in C)/len(C)))},
    }
def infer(data_path: Path, outdir: Path, ell_min: float, ell_max: float, m: int, alpha: float, L: float) -> dict:
    obj = json.loads(data_path.read_text(encoding="utf-8"))
    t = obj["data"]["t"]; Cobs = obj["data"]["C"]
    xi = float(obj["inputs"]["xi"]); omega = float(obj["inputs"]["omega"]); dt = float(obj["inputs"]["dt"])
    noise = float(obj["inputs"]["noise"])
    k0 = math.pi / max(L, 1e-9)
    sig2 = max(noise * noise, 1e-12)
    grid = []
    for j in range(m):
        ell = ell_min + (ell_max - ell_min) * (j / max(1, m - 1))
        omega_eff = omega * (1.0 + alpha * (ell * k0) ** 2)
        chi2 = 0.0
        for ti, yi in zip(t, Cobs):
            mu = math.exp(-ti / max(xi, 1e-9)) * math.cos(omega_eff * ti)
            chi2 += (yi - mu) ** 2 / sig2
        logL = -0.5 * chi2
        grid.append({"ell": ell, "logL": float(logL)})
    # Normalize to a discrete posterior with flat prior over ell.
    mx = max(g["logL"] for g in grid)
    w = [math.exp(g["logL"] - mx) for g in grid]
    Z = sum(w) or 1.0
    for gi, wi in zip(grid, w):
        gi["posterior"] = float(wi / Z)
    ell_map = max(grid, key=lambda g: g["posterior"])["ell"]
    mean = sum(g["ell"] * g["posterior"] for g in grid)
    cdf = []
    s = 0.0
    for g in sorted(grid, key=lambda z: z["ell"]):
        s += g["posterior"]; cdf.append((g["ell"], s))
    def q(p: float) -> float:
        for e, cp in cdf:
            if cp >= p: return float(e)
        return float(cdf[-1][0])
    return {"data_ref": str(data_path), "alpha": alpha, "L": L, "ell_grid": grid,
            "point_estimates": {"ell_map": float(ell_map), "ell_mean": float(mean), "ell_q16": q(0.16), "ell_q84": q(0.84)}}
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dgpipe", description="Discrete-gravity pipeline CLI: protocols, simulation, inference.")
    p.add_argument("--outdir", type=Path, default=Path("dgpipe_out"), help="Output directory (created if missing).")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("protocols", help="Write a prioritized measurement-protocol specification (JSON).")

    ss = sub.add_parser("simulate", help="Run a controlled toy simulation with finite-size and dispersive systematics.")
    ss.add_argument("--n", type=int, default=512); ss.add_argument("--dt", type=float, default=0.01)
    ss.add_argument("--xi", type=float, default=1.0); ss.add_argument("--omega", type=float, default=6.0)
    ss.add_argument("--ell", type=float, default=0.1); ss.add_argument("--alpha", type=float, default=1.0)
    ss.add_argument("--rho", type=float, default=1.0); ss.add_argument("--L", type=float, default=10.0)
    ss.add_argument("--noise", type=float, default=0.02); ss.add_argument("--seed", type=int, default=0)

    si = sub.add_parser("infer", help="Infer discreteness scale ell from a saved simulation/measurement JSON.")
    si.add_argument("data", type=Path, help="Path to JSON produced by simulate (or compatible measurement file).")
    si.add_argument("--ell-min", type=float, default=0.0); si.add_argument("--ell-max", type=float, default=0.5)
    si.add_argument("--m", type=int, default=101); si.add_argument("--alpha", type=float, default=1.0)
    si.add_argument("--L", type=float, default=10.0)
    return p

def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(argv)
    outdir: Path = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)
    prov = _provenance(["dgpipe"] + argv, outdir)

    if args.cmd == "protocols":
        payload = {"provenance": prov, "protocol_spec": generate_protocols()}
        path = outdir / "protocols.json"
        _write_json(path, payload)
        print(str(path))
        return 0

    if args.cmd == "simulate":
        sim = simulate(outdir, args.n, args.dt, args.xi, args.omega, args.ell, args.alpha, args.rho, args.L, args.noise, args.seed)
        payload = {"provenance": prov, **sim}
        path = outdir / "simulation.json"
        _write_json(path, payload)
        (outdir / "simulation.sha256").write_text(_sha256_bytes(path.read_bytes()) + "\n", encoding="utf-8")
        print(str(path))
        return 0

    if args.cmd == "infer":
        inf = infer(args.data, outdir, args.ell_min, args.ell_max, args.m, args.alpha, args.L)
        payload = {"provenance": prov, **inf}
        path = outdir / "inference.json"
        _write_json(path, payload)
        (outdir / "inference.sha256").write_text(_sha256_bytes(path.read_bytes()) + "\n", encoding="utf-8")
        print(str(path))
        return 0

    raise SystemExit("Unknown command")

if __name__ == "__main__":
    raise SystemExit(main())
