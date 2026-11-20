# Measurement protocol

## Comparison unit

Declare a dataset, task, validation partition, feature schema, platform and prediction workload before measuring candidates. Use one candidate representative per declared model/configuration. Select representatives without using test performance. Compute normalized components separately on each platform, even when the same model artifacts are transferred.

## Quality

Calculate Macro-F1 using a declared, fixed label set and consistent handling of undefined class metrics. Use actual validation labels and predictions. The toolkit consumes the resulting number; it does not check label mappings or score definitions.

## Latency

Load a fitted pipeline and the full validation features before timing. Use five warm-up calls followed by 30 measured `predict_proba` calls, matching the manuscript's full-validation timing convention. Divide each duration by the number of validation records and convert seconds to milliseconds. Supply the mean, retaining raw durations and sample SD with the experiment records. Loading, feature extraction and fitting are outside this interval. Inference-time preprocessing inside the supplied pipeline is included.

For a batch experiment, give every batch size a distinct workload identifier and declare calls, number of records, warm-ups and repetitions. Amortized per-record latency is not single-request latency. Keep separate the full-validation and batch benchmarks. Neither establishes end-to-end packet processing capacity.

Record the CPU and RAM, OS, package versions, active threads, power supply, frequency/governor settings, cooling, temperature and any relevant throttling observations. Avoid running competing workloads during measurement. For asynchronous inference, use an appropriate synchronization callback before and after the measured call. These declarations improve interpretability but do not eliminate all hardware variability.

## Size

Serialize the same pipeline whose predictions were measured and count its exact bytes. Declare whether preprocessing is included. Use a single serialization policy across candidates. Compression and omitted preprocessing can change this criterion independently of classifier structure.

## Scoring

Use the primary weights fixed for the application before examining winners. Run sensitivity on those same measurements. Report component values and original measurements alongside scores. Do not report only the winning model or interpret an IDSS ratio as a speedup.

## Evidence boundary

This starter release provides a reusable scorer and a timing utility. It does not contain the manuscript's complete data preparation, HPO, training, Pi orchestration or artifact audit. Reproducing Table 7 requires its original validation measurements and byte counts; the synthetic example is solely a functional demonstration.
