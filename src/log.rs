use crate::error::Result;
use hdrhistogram::Histogram;
use std::time::Duration;

#[allow(clippy::too_many_arguments)]
pub fn log_stats(
    csv: &mut impl std::io::Write,
    duration_s: f64,
    progress: f64,
    txns: u64,
    throughput: f64,
    p50_ms: f64,
    p90_ms: f64,
    p99_ms: f64,
    max: f64,
    cache_hits: u64,
    cache_misses: u64,
    cache_hit_rate: f64,
) -> Result<()> {
    println!(
        "{:<8} {:>5.1}%  {:>7}  {:>6.0}/s  {:>6.1}ms  {:>6.1}ms  {:>6.1}ms  {:>6.1}ms  {:>7}  {:>7}  {:>5.1}%",
        format!("{:.1}s", duration_s),
        progress,
        txns,
        throughput,
        p50_ms,
        p90_ms,
        p99_ms,
        max,
        cache_hits,
        cache_misses,
        cache_hit_rate * 100.0,
    );
    writeln!(
        csv,
        "{:.3},{:.3},{},{:.3},{:.6},{:.6},{:.6},{:.6},{},{},{:.6}",
        duration_s,
        progress,
        txns,
        throughput,
        p50_ms,
        p90_ms,
        p99_ms,
        max,
        cache_hits,
        cache_misses,
        cache_hit_rate,
    )?;
    csv.flush()?;
    Ok(())
}

pub fn latency_stats(hist: &Histogram<u32>) -> (f64, f64, f64, f64) {
    let p50_ms = Duration::from_nanos(hist.value_at_quantile(0.5)).as_secs_f64() * 1000.0;
    let p90_ms = Duration::from_nanos(hist.value_at_quantile(0.9)).as_secs_f64() * 1000.0;
    let p99_ms = Duration::from_nanos(hist.value_at_quantile(0.99)).as_secs_f64() * 1000.0;
    let max = Duration::from_nanos(hist.max()).as_secs_f64() * 1000.0;
    (p50_ms, p90_ms, p99_ms, max)
}
