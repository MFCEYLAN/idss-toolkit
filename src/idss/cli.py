"""CSV interface with separate normalization for every comparison group."""
import argparse
import csv
import io
import hashlib
import json
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from . import __version__
from .core import Candidate, Weights, rank, sensitivity

GROUP = ("dataset", "task", "platform", "workload_id")
METRICS = ("model", "validation_macro_f1", "latency_ms_per_record", "size_bytes")
REQUIRED = GROUP + METRICS + ("selection_split",)


def read_measurements(path):
    groups, _ = parse_measurements(Path(path).read_bytes())
    return groups


def parse_measurements(raw, *, strict=True, columns=None, defaults=None):
    """Parse one immutable CSV snapshot. Strict mode preserves the CLI schema."""
    columns = {} if columns is None else dict(columns)
    if set(columns) - set(REQUIRED):
        raise ValueError("Unknown canonical column name in column mapping.")
    mapping = {k: columns.get(k, k) for k in REQUIRED}
    if any(not isinstance(v, str) or not v.strip() for v in mapping.values()):
        raise ValueError("Column mapping values must be nonempty strings.")
    if len(set(mapping.values())) != len(mapping):
        raise ValueError("Column mappings must identify distinct columns.")
    defaults = {} if defaults is None else defaults
    groups = defaultdict(list)
    with io.StringIO(raw.decode("utf-8-sig"), newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("Missing or duplicate CSV header fields.")
        required = REQUIRED if strict else METRICS
        missing = {mapping[k] for k in set(required) | set(columns)} - set(reader.fieldnames)
        if missing:
            raise ValueError("Missing columns: " + ", ".join(sorted(missing)))
        absent = [k for k in REQUIRED if mapping[k] not in reader.fieldnames]
        for k in GROUP:
            if k in absent and (not isinstance(defaults.get(k), str) or not defaults[k].strip()):
                raise ValueError(f"A nonempty {k} identifier is required.")
        declarations = {"assumed_validation_split": "selection_split" in absent,
                        "defaulted_group_identifiers": {k: defaults[k] for k in GROUP if k in absent},
                        "column_mapping": columns}
        for n, row in enumerate(reader, 2):
            try:
                if None in row or any(v is None for v in row.values()):
                    raise ValueError("Wrong number of CSV fields.")
                row = {k: row[mapping[k]] if mapping[k] in row else
                       ("validation" if k == "selection_split" else defaults[k]) for k in REQUIRED}
                if any(not row[k].strip() for k in REQUIRED):
                    raise ValueError("Required fields cannot be empty.")
                if row["selection_split"].strip().lower() != "validation":
                    raise ValueError("IDSS selection requires validation measurements.")
                candidate = Candidate(row["model"].strip(), float(row["validation_macro_f1"]),
                                      float(row["latency_ms_per_record"]), int(row["size_bytes"]))
                key = tuple(row[k].strip() for k in GROUP)
                groups[key].append(candidate)
            except (ValueError, TypeError, OverflowError) as e:
                raise ValueError(f"CSV row {n}: {e}") from e
    if not groups:
        raise ValueError("CSV contains no measurements.")
    return dict(groups), declarations


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def html_report(primary, profiles, weights=None):
    parts = ['<!doctype html><html lang="en"><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width,initial-scale=1">',
             '<title>IDSS comparison report</title><style>',
             'body{font:16px/1.5 system-ui;margin:2rem auto;max-width:1100px;padding:0 1rem;color:#17212b}',
             'table{border-collapse:collapse;width:100%;margin:1rem 0 2rem;font-variant-numeric:tabular-nums}',
             'td,th{padding:.6rem;border:1px solid #cbd5df;text-align:left}th{background:#edf2f7}',
             '.scroll{overflow-x:auto}svg{min-width:65px}h2{margin-top:2rem}</style>',
             '<h1>IDSS comparison report</h1>',
             '<p>Validation measurements; scores are relative to each candidate set and platform. ',
             'Exact ties share ranks. Serialized size represents storage, not runtime memory.</p>']
    if weights is not None:
        parts.append(f'<p>Primary weights: quality={weights.quality:.8g}, '
                     f'latency={weights.latency:.8g}, size={weights.size:.8g}.</p>')
    def table(rows):
        out = ['<div class="scroll"><table><thead><tr><th>Rank</th><th>Model</th><th>Validation Macro-F1</th>',
               '<th>Latency (ms/record)</th><th>Size (bytes)</th><th>IDSS</th></tr></thead><tbody>']
        for r in rows:
            out.append(f'<tr><td>{r["rank"]}</td><td>{escape(r["model"])}</td>'
                       f'<td>{r["validation_macro_f1"]:.6f}</td><td>{r["latency_ms_per_record"]:.8g}</td>'
                       f'<td>{r["size_bytes"]:,}</td><td>{r["idss"]:.6f} '
                       f'<svg width="100" height="12" role="img" aria-label="IDSS {r["idss"]:.6f}">'
                       f'<rect width="{100*r["idss"]:.4f}" height="12" fill="#2368a0"/></svg></td></tr>')
        return ''.join(out) + '</tbody></table></div>'
    for key, rows in primary.items():
        title = ' / '.join(key)
        parts += [f'<h2>{escape(title)}</h2><h3>Primary weights</h3>', table(rows),
                  '<details><summary>Weight sensitivity</summary>']
        for name, ranked in profiles[key].items():
            parts += [f'<h3>{escape(name)}</h3>', table(ranked)]
        parts.append('</details>')
    return ''.join(parts) + '</html>'


def run(input_path, output_dir, weights, metadata_path=None):
    input_path, output_dir = Path(input_path), Path(output_dir)
    raw = input_path.read_bytes()
    groups, declarations = parse_measurements(raw)
    # Validate every group before writing any output.
    primary = {k: rank(v, weights) for k, v in groups.items()}
    profiles = {k: sensitivity(v) for k, v in groups.items()}
    metadata = json.loads(Path(metadata_path).read_text(encoding="utf-8")) if metadata_path else {}
    if not isinstance(metadata, dict):
        raise ValueError("Measurement metadata must be a JSON object.")
    export_results(input_path, output_dir, raw, primary, profiles, weights, metadata, declarations)
    return primary


def export_results(input_path, output_dir, raw, primary, profiles, weights, metadata, declarations):
    input_path, output_dir = Path(input_path), Path(output_dir)
    if input_path.resolve().is_relative_to(output_dir.resolve()):
        raise ValueError("Keep input measurements outside the output directory.")
    ranked_rows, sensitivity_rows = [], []
    for key, rows in primary.items():
        base = dict(zip(GROUP, key))
        ranked_rows.extend({**base, **r} for r in rows)
        for profile, values in profiles[key].items():
            sensitivity_rows.extend({**base, "profile": profile, **r} for r in values)
    manifest = {"idss_version": __version__, "created_utc": datetime.now(timezone.utc).isoformat(),
                "input_sha256": hashlib.sha256(raw).hexdigest(),
                "primary_weights": asdict(weights), "selection_split": "validation",
                "input_declarations": declarations,
                "group_fields": GROUP, "measurement_metadata": metadata,
                "normalization": "F/max(F); min(latency)/latency; min(bytes)/bytes",
                "notes": ["Input split labels are declarations, not a leakage audit.",
                          "Hardware/workload comparability must be established by the researcher.",
                          "Sensitivity uses the manuscript's four fixed profiles."]}
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "rankings.csv", ranked_rows)
    write_csv(output_dir / "sensitivity.csv", sensitivity_rows)
    (output_dir / "report.html").write_text(html_report(primary, profiles, weights), encoding="utf-8")
    (output_dir / "manifest.json").write_text(manifest_text + "\n", encoding="utf-8")
    (output_dir / "input_measurements.csv").write_bytes(raw)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Rank IDS models using validation-based IDSS.")
    parser.add_argument("input", type=Path, help="CSV of measurements")
    parser.add_argument("--output", type=Path, default=Path("idss_results"))
    parser.add_argument("--weights", type=float, nargs=3, metavar=("QUALITY", "LATENCY", "SIZE"), default=(1/3,)*3)
    parser.add_argument("--metadata", type=Path, help="Optional measurement conditions JSON")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)
    try:
        groups = run(args.input, args.output, Weights(*args.weights), args.metadata)
    except (ValueError, TypeError, OverflowError, OSError) as e:
        parser.exit(2, f"idss: {e}\n")
    for key, rows in groups.items():
        winners = ', '.join(r["model"] for r in rows if r["rank"] == 1)
        print(' / '.join(key) + ': ' + winners)
    print(f"Reports saved to {args.output.resolve()}")
    return 0
