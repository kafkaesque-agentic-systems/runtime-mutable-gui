//! Foundation smoke test of the timing category. Timing bounds hold in release builds only.

use std::hint::black_box;
use std::time::{Duration, Instant};

#[test]
#[cfg_attr(debug_assertions, ignore = "timing bound; run with --release")]
fn perf_smoke_timer() {
    let values: Vec<u64> = (0..1_000_000).collect();
    let start = Instant::now();
    let sum: u64 = black_box(&values).iter().sum();
    let elapsed = start.elapsed();
    assert_eq!(black_box(sum), 499_999_500_000);
    assert!(
        elapsed < Duration::from_millis(50),
        "summing took {elapsed:?}"
    );
}
