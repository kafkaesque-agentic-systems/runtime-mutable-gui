//! Reference FX: the example CLAP plugin that exercises mutable-gui.
//!
//! Phase 0 skeleton: one stereo input and output, the bypass and input gain parameters, no editor,
//! and audio passed through unchanged.

use std::num::NonZeroU32;
use std::sync::Arc;

use nice_plug::prelude::*;

/// The parameters of Reference FX.
#[derive(Params)]
pub struct RefParams {
    /// Bypass, the host's bypass switch.
    #[id = "bypass"]
    pub bypass: BoolParam,
    /// Input Gain, −24 to +24 dB. Declared in Phase 0 so that clap-validator's parameter tests
    /// have a value to change besides the two-state bypass; the processing applies it from
    /// Step 1.25 on.
    #[id = "input_gain"]
    pub input_gain: FloatParam,
}

impl Default for RefParams {
    fn default() -> Self {
        Self {
            bypass: BoolParam::new("Bypass", false).make_bypass(),
            input_gain: FloatParam::new(
                "Input Gain",
                0.0,
                FloatRange::Linear {
                    min: -24.0,
                    max: 24.0,
                },
            )
            .with_unit(" dB"),
        }
    }
}

/// The Reference FX plugin.
#[derive(Default)]
pub struct RefFx {
    params: Arc<RefParams>,
}

impl Plugin for RefFx {
    const NAME: &'static str = "Reference FX";
    const VENDOR: &'static str = "mutable-gui";
    const URL: &'static str = "";
    const EMAIL: &'static str = "";
    const VERSION: &'static str = env!("CARGO_PKG_VERSION");

    const AUDIO_IO_LAYOUTS: &'static [AudioIOLayout] = &[AudioIOLayout {
        main_input_channels: NonZeroU32::new(2),
        main_output_channels: NonZeroU32::new(2),
        ..AudioIOLayout::const_default()
    }];

    type Editor = ();
    type SysExMessage = ();
    type BackgroundTask = ();

    fn params(&self) -> Arc<dyn Params> {
        self.params.clone()
    }

    fn process(
        &mut self,
        _buffer: &mut Buffer,
        _aux: &mut AuxiliaryBuffers,
        _context: &mut impl ProcessContext<Self>,
    ) -> ProcessStatus {
        // The host has already copied the input into the output buffer, so passing audio through
        // unchanged means leaving the buffer as it is.
        ProcessStatus::Normal
    }
}

impl ClapPlugin for RefFx {
    const CLAP_ID: &'static str = "org.mutable-gui.reference";
    const CLAP_DESCRIPTION: Option<&'static str> =
        Some("Reference plugin of the mutable-gui library");
    const CLAP_MANUAL_URL: Option<&'static str> = None;
    const CLAP_SUPPORT_URL: Option<&'static str> = None;
    const CLAP_FEATURES: &'static [ClapFeature] = &[ClapFeature::AudioEffect, ClapFeature::Stereo];
}

nice_export_clap!(RefFx);
