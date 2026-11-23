//! Foundation smoke benchmark: the same sum as `perf_smoke_timer`. A report, not a gate.

use std::hint::black_box;

use criterion::{Criterion, criterion_group, criterion_main};

fn sum_of_a_million(c: &mut Criterion) {
    let values: Vec<u64> = (0..1_000_000).collect();
    c.bench_function("sum_1m_u64", |b| {
        b.iter(|| black_box(&values).iter().sum::<u64>());
    });
}

criterion_group!(benches, sum_of_a_million);
criterion_main!(benches);
