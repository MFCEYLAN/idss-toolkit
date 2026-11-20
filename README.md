# IDSS Toolkit

Compare intrusion detection models with **one Python call**, using validation Macro-F1, inference latency and serialized pipeline size.

```python
from idss import IDSS

result = IDSS("models.csv")
print(result)
```

Equal weights are automatic. Python 3.10+; no third-party runtime dependencies for scoring or reports. No fitting or model loading is required.

## Install

Install once, then import `IDSS` in your Python code. Python 3.10 or newer is required.

### Directly from GitHub

Once this project is published at `https://github.com/MFCEYLAN/idss-toolkit`, install it without manually downloading files:

```bash
python -m pip install git+https://github.com/MFCEYLAN/idss-toolkit.git
```

This route requires Git on your computer and access to the published repository. The command above is conditional on publication; this source archive does not itself create a GitHub repository.

For a Colab or Jupyter notebook, use the notebook's pip command:

```python
%pip install git+https://github.com/MFCEYLAN/idss-toolkit.git
```

After installation:

```python
from idss import IDSS

result = IDSS("models.csv")
print(result)
```

`models.csv` must be your local measurement file. Upload it to the notebook session if you use Colab. Importing this package does not download datasets or your CSV.

### From a downloaded ZIP

Extract the archive and open a terminal in the directory containing `pyproject.toml`:

```bash
python -m pip install .
```

For development, use `python -m pip install -e .`. This project has not been published to PyPI; `pip install idss` is not its installation command.

## Prepare a CSV

For one dataset, task, device and validation workload, only four columns are needed:

```csv
model,validation_macro_f1,latency_ms_per_record,size_bytes
ModelA,0.95,0.001,1000000
ModelB,0.94,0.002,500000
ModelC,0.90,0.0005,200000
```

These values are synthetic examples. Use **validation** Macro-F1 as a fraction, latency in **milliseconds per record**, and pipeline size in **bytes**. All candidates in a comparison must use the same validation workload and timing scope. Do not use test scores for model selection.

## Default weights

```python
from idss import IDSS

result = IDSS("models.csv")      # quality=1/3, latency=1/3, size=1/3
print(result)                     # Human-readable ranking
print(result.rankings)            # List of dictionaries
print(result.best)                # All first-ranked models, including ties
```

Try the bundled example with `IDSS("examples/models.csv")`.

## Custom weights

Pass weights in **quality, latency, size** order:

```python
result = IDSS("models.csv", weights=(0.50, 0.30, 0.20))
```

Or name each weight explicitly:

```python
result = IDSS("models.csv", weights={
    "quality": 0.50,
    "latency": 0.30,
    "size": 0.20,
})
```

Weights must be nonnegative and sum to one. They are never silently rescaled.

## Standard profiles

```python
result = IDSS("models.csv", profile="equal")
result = IDSS("models.csv", profile="quality_priority")
result = IDSS("models.csv", profile="latency_priority")
result = IDSS("models.csv", profile="footprint_priority")

print(IDSS.profiles())
```

| Profile | Quality | Latency | Size |
|---|---:|---:|---:|
| `equal` (default) | 1/3 | 1/3 | 1/3 |
| `quality_priority` | 0.50 | 0.30 | 0.20 |
| `latency_priority` | 0.40 | 0.40 | 0.20 |
| `footprint_priority` | 0.40 | 0.20 | 0.40 |

`profile="default"` is an alias for `equal`. Choose either custom weights or a profile. The latency-priority profile follows the manuscript and gives equal weight to quality and latency.

## Reports and sensitivity

```python
result.save("my_results")
sensitivity_rows = result.sensitivity()
```

Open `my_results/report.html` in a browser. The folder also contains `rankings.csv`, `sensitivity.csv`, `manifest.json` and the exact original input CSV. Export uses the snapshot read by the constructor, even if the source file later changes. Existing output files are replaced; choose a new folder for each retained experiment.

If pandas is already installed, an optional DataFrame view is available:

```python
df = result.to_dataframe()
```

## Custom column names

```python
result = IDSS("my_results.csv", columns={
    "model": "algorithm",
    "validation_macro_f1": "val_f1",
    "latency_ms_per_record": "latency_ms",
    "size_bytes": "pipeline_bytes",
}, weights=(0.5, 0.3, 0.2))
```

Mappings rename fields, not units. Convert seconds to milliseconds and MiB to bytes before scoring.

## Multiple datasets and devices

Add the optional columns `dataset`, `task`, `platform` and `workload_id` to your CSV. Each distinct combination is normalized separately. See [the multi-platform example](examples/measurements.csv).

For a four-column CSV these identifiers default to `custom/custom/custom/validation`. Set them explicitly if desired:

```python
result = IDSS("models.csv", dataset="MyDataset", task="binary",
              platform="Raspberry Pi 5", workload_id="validation-v1")
```

CSV group labels take precedence over these defaults. An optional `selection_split` column must contain `validation`; other values are rejected. If absent, validation use is assumed and recorded in the export manifest. The software cannot audit the provenance of metrics or detect undeclared mixtures of workloads.

## Formula

Within one comparison:

```text
Q_i = F_i / max(F)
L_i = min(latency) / latency_i
S_i = min(size) / size_i
IDSS_i = Q_i**wQ * L_i**wL * S_i**wS
```

Higher scores indicate a more favorable trade-off within that candidate set. Scores are relative and not directly comparable between platforms. Storage size is not runtime memory. Apply mandatory application requirements separately.

See [advanced usage](docs/advanced_usage.md) for exact tie rules, zero-quality handling, the lower-level API and timing helper. See [measurement protocol](docs/measurement_protocol.md) and [publication guidance](docs/publication.md) for research use.

## Examples and tests

- [Quickstart notebook](examples/quickstart.ipynb)
- [Runnable Python example](examples/quickstart.py)
- [Minimal CSV](examples/models.csv)
- [Multi-platform CSV](examples/measurements.csv)

```bash
python -m unittest discover -s tests -v
```

The strict CLI remains available and requires explicit grouping and split columns:

```bash
idss examples/measurements.csv --output idss_results
```

## Research context

Authors: Mustafa Furkan Ceylan and Gökhan Dalkılıç.

Accompanying manuscript: *Explainable and Edge-Deployable Machine Learning for Fine-Grained DoS/DDoS Detection in IoT Networks*.

Version 0.2.0 contains synthetic examples, not the complete manuscript experiments or unrounded Table 7 inputs. No datasets or trained pipelines are redistributed. No public repository URL, manuscript acceptance status or DOI is asserted. Review the included MIT license and author details before publishing. Software citation metadata is in [CITATION.cff](CITATION.cff).
