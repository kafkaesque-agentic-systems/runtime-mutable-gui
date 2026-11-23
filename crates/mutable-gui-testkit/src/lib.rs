//! Fakes and harness helpers shared by the mutable-gui tests. Used only as a dev-dependency.

/// Re-exported so tests reach the harness queries (`egui_kittest::kittest::Queryable`) through
/// this one dev-dependency.
pub use egui_kittest;

/// A headless egui harness of `size` logical points at `pixels_per_point` 1.0 running `app`.
#[must_use]
pub fn ui_harness<'a>(
    size: egui::Vec2,
    app: impl FnMut(&mut egui::Ui) + 'a,
) -> egui_kittest::Harness<'a> {
    egui_kittest::Harness::builder()
        .with_size(size)
        .with_pixels_per_point(1.0)
        .build_ui(app)
}

/// Compares the harness picture with `tests/snapshots/<name>.png` on macOS; elsewhere it returns
/// without rendering (D-46: pictures are recorded and compared on the macOS gate platform only).
///
/// A mismatch is recorded in the harness, which panics when it is dropped.
pub fn snapshot_on_macos(harness: &mut egui_kittest::Harness<'_, impl Sized>, name: &str) {
    if cfg!(target_os = "macos") {
        harness.snapshot(name);
    }
}
