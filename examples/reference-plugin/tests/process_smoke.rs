//! Foundation smoke test of the reference plugin's process call: audio passes through unchanged.

use mutable_gui_reference::RefFx;
use nice_plug::context::process::SendEventError;
use nice_plug::midi::PluginNoteEvent;
use nice_plug::prelude::*;

/// A process context with a stopped transport and no events.
struct SilentContext {
    transport: Transport,
}

impl ProcessContext<RefFx> for SilentContext {
    fn plugin_api(&self) -> PluginApi {
        PluginApi::Clap
    }

    fn execute_background(&self, (): ()) {}

    fn execute_gui(&self, (): ()) {}

    fn transport(&self) -> &Transport {
        &self.transport
    }

    fn next_event(&mut self) -> Option<PluginNoteEvent<RefFx>> {
        None
    }

    fn try_send_event(
        &mut self,
        event: PluginNoteEvent<RefFx>,
    ) -> Result<(), (PluginNoteEvent<RefFx>, SendEventError)> {
        Err((event, SendEventError::NoOutputBuffer))
    }

    fn set_latency_samples(&self, _samples: u32) {}

    fn request_restart(&self) {}

    fn set_current_voice_capacity(&self, _capacity: u32) {}
}

#[test]
fn process_passes_a_ramp_through() {
    const FRAMES: usize = 64;
    #[allow(clippy::cast_precision_loss)] // indices below 64 are exact in f32
    let ramp: Vec<f32> = (0..FRAMES).map(|i| i as f32 / FRAMES as f32).collect();
    let mut left = ramp.clone();
    let mut right: Vec<f32> = ramp.iter().map(|s| -s).collect();

    let mut buffer = Buffer::default();
    // SAFETY: both slices hold FRAMES samples and outlive every use of `buffer` below.
    unsafe {
        buffer.set_slices(FRAMES, |slices| {
            *slices = vec![left.as_mut_slice(), right.as_mut_slice()];
        });
    }
    let mut aux = AuxiliaryBuffers {
        inputs: &mut [],
        outputs: &mut [],
    };
    let mut context = SilentContext {
        transport: Transport::new(48_000.0),
    };

    let mut plugin = RefFx::default();
    let status = plugin.process(&mut buffer, &mut aux, &mut context);
    drop(buffer);

    assert!(matches!(status, ProcessStatus::Normal));
    assert_eq!(left, ramp);
    assert_eq!(right, ramp.iter().map(|s| -s).collect::<Vec<f32>>());
}
