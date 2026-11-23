//! Build helper of the mutable-gui workspace, run as `cargo xtask <command>`.
//!
//! `bundle` and `bundle-universal` build plugin bundles through nice-plug-xtask.

use std::io;

fn main() -> nice_plug_xtask::Result<()> {
    match std::env::args().nth(1).as_deref() {
        Some("bundle" | "bundle-universal") => nice_plug_xtask::main(),
        Some(other) => Err(io::Error::other(format!(
            "unknown command `{other}`; the commands are: bundle, bundle-universal"
        ))
        .into()),
        None => Err(io::Error::other(
            "missing command; the commands are: bundle, bundle-universal",
        )
        .into()),
    }
}
