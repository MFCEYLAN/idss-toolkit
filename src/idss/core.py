"""Manuscript equations (12)-(17), with explicit input validation."""
from dataclasses import dataclass, asdict
from math import isfinite, isclose, exp, log


@dataclass(frozen=True)
class Weights:
    quality: float = 1 / 3
    latency: float = 1 / 3
    size: float = 1 / 3

    def __post_init__(self):
        values = (self.quality, self.latency, self.size)
        if any(not isfinite(v) or v < 0 for v in values):
            raise ValueError("Weights must be finite and nonnegative.")
        if not isclose(sum(values), 1.0, rel_tol=0, abs_tol=1e-12):
            raise ValueError("Weights must sum to one; weights are not silently rescaled.")


@dataclass(frozen=True)
class Candidate:
    model: str
    validation_macro_f1: float
    latency_ms_per_record: float
    size_bytes: int

    def __post_init__(self):
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("A nonempty model identifier is required.")
        if not isfinite(self.validation_macro_f1) or not 0 <= self.validation_macro_f1 <= 1:
            raise ValueError("Validation Macro-F1 must be finite and in [0, 1].")
        if not isfinite(self.latency_ms_per_record) or self.latency_ms_per_record <= 0:
            raise ValueError("Latency must be finite and strictly positive.")
        if isinstance(self.size_bytes, bool) or not isinstance(self.size_bytes, int) or self.size_bytes <= 0:
            raise ValueError("Serialized pipeline size must be a positive integer byte count.")


PROFILES = {
    "equal": Weights(),
    "quality_priority": Weights(0.50, 0.30, 0.20),
    "latency_priority": Weights(0.40, 0.40, 0.20),
    "footprint_priority": Weights(0.40, 0.20, 0.40),
}


def rank(candidates, weights=Weights()):
    """Rank ONE fixed dataset/task/platform/workload candidate set.

    Ties receive competition ranks (1, 1, 3). Model name determines display
    order within ties, not the winning model. Exact score ties are retained.
    Zero-F1 candidates score zero when quality has positive weight. If quality
    is inactive it contributes a factor of one. All-zero F1 groups are rejected
    when quality is active because their normalization is undefined.
    """
    candidates = list(candidates)
    if not candidates:
        raise ValueError("At least one candidate is required.")
    if len({c.model for c in candidates}) != len(candidates):
        raise ValueError("Duplicate model identifiers within a comparison.")
    fmax = max(c.validation_macro_f1 for c in candidates)
    if fmax == 0 and weights.quality > 0:
        raise ValueError("Quality normalization is undefined when all Macro-F1 values are zero.")
    lmin = min(c.latency_ms_per_record for c in candidates)
    smin = min(c.size_bytes for c in candidates)
    results = []
    for c in candidates:
        components = (
            c.validation_macro_f1 / fmax if fmax else 0.0,
            lmin / c.latency_ms_per_record,
            smin / c.size_bytes,
        )
        active = [(x, w) for x, w in zip(components, (weights.quality, weights.latency, weights.size)) if w > 0]
        score = 0.0 if any(x == 0 for x, _ in active) else exp(sum(w * log(x) for x, w in active))
        results.append({**asdict(c), "quality_component": components[0],
                        "latency_component": components[1], "size_component": components[2],
                        "idss": score})
    results.sort(key=lambda r: (-r["idss"], r["model"]))
    last_score, last_rank = None, None
    for pos, row in enumerate(results, 1):
        if row["idss"] != last_score:
            last_rank = pos
        row["rank"] = last_rank
        last_score = row["idss"]
    return results


def sensitivity(candidates, profiles=None):
    """Recombine fixed measurements; no fitting, test use or remeasurement."""
    candidates = list(candidates)
    return {name: rank(candidates, w) for name, w in (PROFILES if profiles is None else profiles).items()}
