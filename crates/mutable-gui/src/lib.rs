//! mutable-gui: an audio plugin interface that the user can rearrange, restyle and save while
//! the plugin runs. This crate is the toolkit-level core; it holds no plugin-framework code.
#![forbid(unsafe_code)]

/// The version of this library, equal to the `mutable-gui` package version.
pub const LIBRARY_VERSION: &str = env!("CARGO_PKG_VERSION");
