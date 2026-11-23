//! Foundation smoke tests of the interaction and snapshot categories.

use std::cell::Cell;

use mutable_gui_testkit::egui_kittest::kittest::Queryable;
use mutable_gui_testkit::{snapshot_on_macos, ui_harness};

#[test]
fn click_counts() {
    let count = Cell::new(0_u32);
    let mut harness = ui_harness(egui::vec2(160.0, 64.0), |ui| {
        if ui.button("Press").clicked() {
            count.set(count.get() + 1);
        }
    });
    harness.get_by_label("Press").click();
    harness.run();
    assert_eq!(count.get(), 1);
}

#[test]
fn smoke_picture() {
    let mut harness = ui_harness(egui::vec2(96.0, 96.0), |ui| {
        let rect =
            egui::Rect::from_center_size(ui.ctx().content_rect().center(), egui::vec2(64.0, 64.0));
        ui.painter()
            .rect_filled(rect, 0.0, egui::Color32::from_rgb(0x5A, 0xAB, 0xFF));
    });
    harness.run();
    snapshot_on_macos(&mut harness, "foundation-smoke");
}
