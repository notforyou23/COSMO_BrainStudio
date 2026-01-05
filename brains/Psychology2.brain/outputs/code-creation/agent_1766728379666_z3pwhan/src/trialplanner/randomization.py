"""Randomization utilities for multi-wave intervention trials.

Supports individual/cluster assignment, stratification, re-randomization, and
reproducible allocation tables for experimental arms and ZPD variants.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import hashlib
import random


def _stable_int_seed(*parts: Any) -> int:
    s = "|".join("" if p is None else str(p) for p in parts)
    h = hashlib.sha256(s.encode("utf-8")).hexdigest()
    return int(h[:16], 16)


def _weighted_cycle(labels: Sequence[str], weights: Optional[Sequence[float]]) -> List[str]:
    if not labels:
        raise ValueError("labels must be non-empty")
    if weights is None:
        return list(labels)
    if len(weights) != len(labels) or any(w < 0 for w in weights) or sum(weights) <= 0:
        raise ValueError("weights must align with labels and sum to > 0")
    m = min(w for w in weights if w > 0)
    counts = [max(1, int(round(w / m))) if w > 0 else 0 for w in weights]
    seq: List[str] = []
    for lab, c in zip(labels, counts):
        seq.extend([lab] * c)
    return seq


def _assign_balanced(rng: random.Random, ids: List[str], labels: Sequence[str],
                     weights: Optional[Sequence[float]] = None) -> Dict[str, str]:
    seq = _weighted_cycle(labels, weights)
    rng.shuffle(ids)
    rng.shuffle(seq)
    out: Dict[str, str] = {}
    for i, pid in enumerate(ids):
        out[pid] = seq[i % len(seq)]
    return out


@dataclass(frozen=True)
class RandomizationSpec:
    seed: int
    waves: Sequence[str]
    arms: Sequence[str]
    zpd_variants: Sequence[str] = ()
    arm_weights: Optional[Sequence[float]] = None
    zpd_weights: Optional[Sequence[float]] = None
    unit: str = "individual"  # "individual" or "cluster"
    id_col: str = "participant_id"
    cluster_col: str = "cluster_id"
    strata_cols: Tuple[str, ...] = ()
    rerandomize_waves: Tuple[str, ...] = ()  # if provided, only these waves rerandomize
    carryover: bool = True  # if True and not rerandomizing, keep prior wave assignments


class MultiWaveRandomizer:
    def __init__(self, spec: RandomizationSpec):
        if spec.unit not in ("individual", "cluster"):
            raise ValueError("unit must be 'individual' or 'cluster'")
        self.spec = spec

    def _rng_for(self, wave: str, *extra: Any) -> random.Random:
        return random.Random(_stable_int_seed(self.spec.seed, wave, *extra))

    def _key_for_strata(self, row: Mapping[str, Any]) -> Tuple[Any, ...]:
        return tuple(row.get(c) for c in self.spec.strata_cols)

    def _units(self, rows: Sequence[Mapping[str, Any]]) -> Tuple[List[str], Dict[str, List[str]]]:
        if self.spec.unit == "individual":
            ids = [str(r[self.spec.id_col]) for r in rows]
            return ids, {pid: [pid] for pid in ids}
        # cluster: map cluster -> participants
        by_cluster: Dict[str, List[str]] = {}
        for r in rows:
            cid = str(r[self.spec.cluster_col])
            pid = str(r[self.spec.id_col])
            by_cluster.setdefault(cid, []).append(pid)
        return sorted(by_cluster.keys()), by_cluster

    def allocate(self, rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        # rows must include id_col, and cluster_col if unit='cluster', plus strata_cols if used
        by_wave: Dict[str, List[Mapping[str, Any]]] = {w: [] for w in self.spec.waves}
        for r in rows:
            w = str(r.get("wave", self.spec.waves[0]))
            if w in by_wave:
                by_wave[w].append(r)

        prior_arm: Dict[str, str] = {}
        prior_zpd: Dict[str, str] = {}
        out: List[Dict[str, Any]] = []

        for wave in self.spec.waves:
            wave_rows = by_wave.get(wave, [])
            rerand = (wave in self.spec.rerandomize_waves) if self.spec.rerandomize_waves else True
            rng = self._rng_for(wave, "root")
            # group units by strata
            strata_to_units: Dict[Tuple[Any, ...], List[str]] = {}
            unit_ids, unit_to_pids = self._units(wave_rows)
            # build representative row per unit for strata lookup (first member)
            rep_for_unit: Dict[str, Mapping[str, Any]] = {}
            if self.spec.unit == "individual":
                rep_for_unit = {str(r[self.spec.id_col]): r for r in wave_rows}
            else:
                for r in wave_rows:
                    cid = str(r[self.spec.cluster_col])
                    rep_for_unit.setdefault(cid, r)
            for uid in unit_ids:
                key = self._key_for_strata(rep_for_unit.get(uid, {}))
                strata_to_units.setdefault(key, []).append(uid)

            arm_assign_unit: Dict[str, str] = {}
            zpd_assign_unit: Dict[str, str] = {}
            for skey, uids in strata_to_units.items():
                rng_s = self._rng_for(wave, "strata", skey)
                need_ids = []
                for uid in uids:
                    # carryover check at participant-level; for cluster, require all members same prior
                    if self.spec.carryover and not rerand:
                        pids = unit_to_pids[uid]
                        pa = prior_arm.get(pids[0])
                        pz = prior_zpd.get(pids[0])
                        if pa is not None and all(prior_arm.get(p) == pa for p in pids):
                            arm_assign_unit[uid] = pa
                        if self.spec.zpd_variants and pz is not None and all(prior_zpd.get(p) == pz for p in pids):
                            zpd_assign_unit[uid] = pz
                    if uid not in arm_assign_unit:
                        need_ids.append(uid)
                if need_ids:
                    arm_assign_unit.update(_assign_balanced(rng_s, need_ids, list(self.spec.arms), self.spec.arm_weights))
                if self.spec.zpd_variants:
                    need_z = [uid for uid in uids if uid not in zpd_assign_unit]
                    if need_z:
                        zpd_assign_unit.update(_assign_balanced(rng_s, need_z, list(self.spec.zpd_variants), self.spec.zpd_weights))

            # expand to participant-level output
            for uid, pids in unit_to_pids.items():
                for pid in pids:
                    arm = arm_assign_unit[uid]
                    zpd = zpd_assign_unit.get(uid) if self.spec.zpd_variants else None
                    out.append({
                        "wave": wave,
                        self.spec.id_col: pid,
                        (self.spec.cluster_col if self.spec.unit == "cluster" else "unit_id"): uid,
                        "arm": arm,
                        "zpd_variant": zpd,
                        "rerandomized": bool(rerand),
                    })
                    prior_arm[pid] = arm
                    if zpd is not None:
                        prior_zpd[pid] = zpd
        return out


def allocation_table(rows: Sequence[Mapping[str, Any]], spec: RandomizationSpec) -> List[Dict[str, Any]]:
    """Convenience wrapper returning participant-level allocation rows."""
    return MultiWaveRandomizer(spec).allocate(rows)
