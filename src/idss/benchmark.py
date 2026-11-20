"""Optional in-process timing helper, independent of model libraries."""
from time import perf_counter
from statistics import mean, stdev


def benchmark(predict, X, *, warmups=5, repeats=30, synchronize=None):
    """Time repeated predict(X) calls on pre-extracted features.

    Pass pipeline.predict_proba to include preprocessing. No model loading or
    fitting is performed. For asynchronous devices provide a synchronize()
    callback. Device synchronization is included in the measured interval.
    Return raw repetitions and within-session sample SD, NOT a confidence interval.
    """
    if isinstance(warmups, bool) or not isinstance(warmups, int) or warmups < 0:
        raise ValueError("warmups must be a nonnegative integer.")
    if isinstance(repeats, bool) or not isinstance(repeats, int) or repeats < 2:
        raise ValueError("At least two measured repetitions are required for sample SD.")
    n = len(X)
    if n == 0:
        raise ValueError("The workload must contain records.")
    for _ in range(warmups):
        predict(X)
        if synchronize is not None:
            synchronize()
    durations = []
    for _ in range(repeats):
        if synchronize is not None:
            synchronize()
        start = perf_counter()
        predict(X)
        if synchronize is not None:
            synchronize()
        durations.append(perf_counter() - start)
    if min(durations) <= 0:
        raise ValueError("Nonpositive duration; use a larger workload.")
    ms = [1000 * t / n for t in durations]
    return {"records": n, "warmups": warmups, "repeats": repeats,
            "seconds": durations, "latency_ms_per_record_mean": mean(ms),
            "latency_ms_per_record_sample_sd": stdev(ms)}
