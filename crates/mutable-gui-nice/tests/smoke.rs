//! Foundation smoke test of the adapter category: the adapter links the core it re-exports.

#[test]
fn adapter_reexports_the_core() {
    assert_eq!(mutable_gui_nice::mutable_gui::LIBRARY_VERSION, "0.1.0");
}
