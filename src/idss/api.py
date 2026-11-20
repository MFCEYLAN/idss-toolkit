"""One-call CSV scoring for notebooks and Python applications."""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from collections.abc import Mapping

from .core import Weights, PROFILES, rank, sensitivity


class IDSS:
    """Read validation measurements and calculate rankings immediately.

    IDSS('models.csv') uses equal weights. Supply either weights=(q,l,s),
    weights={'quality': q, 'latency': l, 'size': s}, or profile='quality_priority'.
    A four-column file describes one comparison; optional dataset, task,
    platform and workload_id columns separate multiple comparisons.
    """

    def __init__(self, csv_path, *, weights=None, profile=None, columns=None,
                 dataset="custom", task="custom", platform="custom",
                 workload_id="validation", metadata=None):
        from .cli import parse_measurements, GROUP
        if weights is not None and profile is not None:
            raise ValueError("Choose custom weights OR a named profile, not both.")
        if profile == "default":
            profile = "equal"
        if profile is not None:
            if profile not in PROFILES:
                raise ValueError("Unknown profile. Choose: " + ", ".join(PROFILES))
            self._weights = PROFILES[profile]
        elif weights is None:
            self._weights = Weights()
        elif isinstance(weights, Weights):
            self._weights = weights
        elif isinstance(weights, Mapping):
            if set(weights) != {"quality", "latency", "size"}:
                raise ValueError("Weight dictionary requires exactly quality, latency and size.")
            try:
                self._weights = Weights(**weights)
            except (TypeError, OverflowError) as e:
                raise ValueError("Weights must be finite numbers.") from e
        else:
            try:
                values = tuple(weights)
                if len(values) != 3:
                    raise ValueError("Supply three weights in quality, latency, size order.")
                self._weights = Weights(*values)
            except (TypeError, OverflowError) as e:
                raise ValueError("Supply a Weights object, dictionary or three numeric weights.") from e
        self.csv_path = Path(csv_path)
        self._input_bytes = self.csv_path.read_bytes()
        defaults = dict(zip(GROUP, (dataset, task, platform, workload_id)))
        self._groups, self._declarations = parse_measurements(
            self._input_bytes, strict=False, columns=columns, defaults=defaults)
        self._primary = {key: rank(models, self.weights) for key, models in self._groups.items()}
        self._metadata = deepcopy({} if metadata is None else metadata)
        if not isinstance(self._metadata, dict):
            raise ValueError("metadata must be a dictionary.")

    @staticmethod
    def profiles():
        """Return independent copies of the four manuscript weight profiles."""
        return {name: asdict(w) for name, w in PROFILES.items()}

    @property
    def weights(self):
        """Immutable weight setting used to calculate these stored results."""
        return self._weights

    @property
    def rankings(self):
        """List of ranked dictionaries, with comparison identifiers included."""
        from .cli import GROUP
        return [deepcopy({**dict(zip(GROUP, key)), **r})
                for key, rows in self._primary.items() for r in rows]

    @property
    def best(self):
        """All rank-one rows, preserving ties and separate comparison groups."""
        return [r for r in self.rankings if r["rank"] == 1]

    def calculate(self):
        """Return rankings; no fitting or re-reading of the input is performed."""
        return self.rankings

    def sensitivity(self):
        """Return flat ranked records for all four fixed manuscript profiles."""
        from .cli import GROUP
        return [{**dict(zip(GROUP, key)), "profile": profile, **r}
                for key, models in self._groups.items()
                for profile, rows in sensitivity(models).items() for r in rows]

    def to_dataframe(self):
        """Optional pandas view; pandas is never required for ordinary use."""
        try:
            import pandas as pd
        except ImportError as e:
            raise ImportError("DataFrame output requires pandas. Use .rankings for a dependency-free list.") from e
        return pd.DataFrame(self.rankings)

    def save(self, output_dir="idss_results"):
        """Export CSV/HTML/JSON using the input snapshot read at construction."""
        from .cli import export_results
        profiles = {key: sensitivity(models) for key, models in self._groups.items()}
        export_results(self.csv_path, output_dir, self._input_bytes, self._primary,
                       profiles, self.weights, self._metadata, self._declarations)
        return Path(output_dir)

    def __str__(self):
        lines = [f"IDSS weights: quality={self.weights.quality:g}, "
                 f"latency={self.weights.latency:g}, size={self.weights.size:g}"]
        for key, rows in self._primary.items():
            lines.append(" / ".join(key))
            for r in rows:
                lines.append(f"  {r['rank']}. {r['model']}: {r['idss']:.6f}")
        return "\n".join(lines)

    def __repr__(self):
        return f"IDSS(comparisons={len(self._groups)}, models={len(self.rankings)}, weights={self.weights!r})"
