# IDSS Toolkit

A reusable Python implementation of the **IDS Deployment Suitability Score** for comparing candidate intrusion detection pipelines using validation Macro-F1, measured inference latency and serialized pipeline size.

The package implements the scoring and weight-sensitivity method in the accompanying manuscript by Mustafa Furkan Ceylan and Gökhan Dalkılıç. Version 0.2.0 is a software starter release. The bundled values are **synthetic demonstrations**, not the paper's experimental results. Raw datasets and trained pipelines are not distributed here.

## Install and run

Requires Python 3.10 or newer. The scoring package has no third-party runtime dependencies. From this directory:

```bash
python -m pip install -e .
idss examples/measurements.csv --output idss_results --metadata examples/measurement_metadata.json
```

An installation-free route is also available from the repository root:

```bash
PYTHONPATH=src python -m idss examples/measurements.csv --output idss_results
```

On Windows, use the installation route or set `PYTHONPATH` using your shell's syntax. Open `idss_results/report.html` in a browser. No server or network connection is required to view the report.

The output directory contains:

- `rankings.csv`: primary scores, component values, original measurements and ranks.
- `sensitivity.csv`: all four manuscript weight profiles.
- `report.html`: standalone report with expandable sensitivity tables.
- `manifest.json`: package version, input SHA-256, weights and supplied measurement conditions.
- `input_measurements.csv`: the exact input used for the run.

An existing output directory is overwritten by filename; use a new directory for every retained experiment.

## Formula

Within **one dataset, task, platform and inference-workload comparison**, let `F_i` be validation Macro-F1, `lambda_i` mean inference latency per record and `M_i` serialized pipeline size in bytes:

```text
Q_i = F_i / max_j(F_j)
L_i = min_j(lambda_j) / lambda_i
S_i = min_j(M_j) / M_i
IDSS_i = Q_i**wQ * L_i**wL * S_i**wS
wQ + wL + wS = 1, with all weights >= 0
```

The default weights are `(1/3, 1/3, 1/3)`. Higher scores indicate a more favorable trade-off **within that comparison**. Scores cannot be interpreted as absolute deployment readiness or directly compared across platforms/candidate sets. Adding or removing candidates changes normalizers and absolute scores. With fixed weights and unchanged criterion values, the relative ordering of retained candidates is unchanged; a newly added candidate can of course become the winner.

All active, positive components are aggregated in log space for numerical stability. Zero quality produces zero score when quality has positive weight. An all-zero quality group is rejected when quality is active. Zero-weight criteria contribute a factor of one. Latency and size must always be strictly positive. Exact ties receive competition ranks, e.g. `1, 1, 3`; alphabetical ordering within ties is only for display. Nearly equal floating-point scores are not automatically tied. This explicit zero-quality policy extends the manuscript's positive-component setting without inserting an arbitrary epsilon.

## Your measurements

Required CSV columns:

| Column | Meaning |
|---|---|
| `dataset` | Dataset or evaluation population identifier |
| `task` | E.g. binary or multiclass |
| `platform` | Hardware/software measurement environment identifier |
| `workload_id` | Same validation rows, feature representation, prediction method and batch protocol |
| `model` | Unique pipeline representative identifier within a comparison |
| `validation_macro_f1` | Macro-F1 as a fraction in `[0, 1]`, not a percentage |
| `latency_ms_per_record` | Positive mean amortized latency, in milliseconds per record |
| `size_bytes` | Positive integer serialized pipeline byte count |
| `selection_split` | Must be `validation` |

Each unique `(dataset, task, platform, workload_id)` is normalized separately. Use different workload identifiers for batch sizes or different validation inputs. Each candidate should identify one declared pipeline representative; do not accidentally pool seed-level runs as independent model families. Extra CSV fields are retained in the copied input but do not affect scoring.

```bash
idss my_measurements.csv --weights 0.5 0.3 0.2 --output quality_priority_results
```

Custom weights affect the primary ranking; sensitivity always reports the four manuscript profiles:

| Profile | Quality | Latency | Size |
|---|---:|---:|---:|
| Equal | 1/3 | 1/3 | 1/3 |
| Quality priority | 0.50 | 0.30 | 0.20 |
| Latency priority | 0.40 | 0.40 | 0.20 |
| Footprint priority | 0.40 | 0.20 | 0.40 |

The latency-priority profile assigns equal weight to quality and latency, as in the manuscript.

## Python API

```python
from idss import Candidate, Weights, rank, sensitivity

# Illustrative measurements, not reported experimental values.
candidates = [
    Candidate('ModelA', 0.95, 0.001, 1_000_000),
    Candidate('ModelB', 0.94, 0.002, 500_000),
]
ranking = rank(candidates, Weights(0.5, 0.3, 0.2))
profiles = sensitivity(candidates)
```

The Python API accepts one comparison at a time. It does not infer datasets, devices or splits. The CSV interface provides explicit grouping.

## Optional timing helper

```python
from pathlib import Path
from idss import benchmark

# pipeline and X_val must already be loaded by your own experiment code.
timing = benchmark(pipeline.predict_proba, X_val, warmups=5, repeats=30)
latency = timing['latency_ms_per_record_mean']
size_bytes = Path('pipeline.joblib').stat().st_size
```

This function does not load models, calculate Macro-F1 or fit anything. Passing a fitted pipeline method includes its inference-time preprocessing. Record hardware, software versions, thread count, cooling, power settings, seed, artifact hash and workload identity in a metadata JSON. For asynchronous accelerators provide a suitable `synchronize` callback. The returned sample SD measures within-session variation, not a confidence interval. The helper measures calls in one process; it is not a standardized cross-device benchmark harness.

## Measurement and interpretation

- Select configurations and IDSS winners using validation data. Reserve test data for final evaluation.
- Use the same validation workload and comparable timing scope for every candidate in a group.
- Serialized storage size is not peak RAM, energy use or a proof of hardware feasibility.
- Apply mandatory application requirements separately. A high relative score can still belong to an unusable detector.
- The software validates declared input values and split labels. It cannot certify partition independence, comparable hardware conditions or the provenance of supplied metrics.
- Prefer original byte counts and unrounded measurements. Manuscript table rounding may prevent exact reproduction.
- The package does not automatically fit, retune, load or transmit models and data.

See [the measurement protocol](measurement_protocol.md), [publication guidance](publication.md), and the [demo notebook](../examples/quickstart.ipynb).

## Tests

```bash
python -m unittest discover -s tests -v
```

## License and citation

The starter package includes an MIT license. Review the license and author details before publishing the repository. The accompanying manuscript is **Explainable and Edge-Deployable Machine Learning for Fine-Grained DoS/DDoS Detection in IoT Networks**, Mustafa Furkan Ceylan and Gökhan Dalkılıç. Publication year, DOI, journal status and repository URL are not asserted here. Fill in the final bibliographic details after they are available. No GitHub repository or archival DOI has been created by this package.
