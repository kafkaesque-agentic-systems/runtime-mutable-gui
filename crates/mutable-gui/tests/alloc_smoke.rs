//! Foundation smoke test of the allocation category. The checker is active in debug builds only.
#![cfg(debug_assertions)]

use nice_assert_no_alloc::{AllocDisabler, assert_no_alloc, violation_count};

#[global_allocator]
static A: AllocDisabler = AllocDisabler;

#[test]
fn checker_counts_allocations() {
    let two = assert_no_alloc(|| std::hint::black_box(1) + 1);
    assert_eq!(two, 2);
    assert_eq!(violation_count(), 0);

    assert_no_alloc(|| drop(Vec::<u8>::with_capacity(8)));
    assert!(
        violation_count() > 0,
        "an allocation inside assert_no_alloc was not counted"
    );
}
