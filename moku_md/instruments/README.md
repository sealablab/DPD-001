---
publish: "true"
type: reference
created: 2025-11-25
modified: 2025-11-25
tags: [moku, api, instruments, reference]
---
# Moku Instruments

This directory contains documentation for all Moku instrument classes. Each instrument provides specialized measurement, generation, or signal processing capabilities.

> [!NOTE] Naming Convention
> Files with the `_` prefix have not been reviewed yet. Files without the prefix (like `cloudcompile.md` and `mim.md`) have been reviewed and enhanced.

## Reviewed Instruments

### [CloudCompile](cloudcompile.md)
**Module:** `moku.instruments.CloudCompile` ([source](https://github.com/sealablab/DPD-001/blob/main/moku_md/instruments/cloudcompile.md))

Custom user-defined instruments created through Moku's cloud compilation service. Load custom FPGA bitstreams for specialized applications.

**Key Features:**
- Custom bitstream deployment (tar/tar.gz packages)
- Generic control register interface
- Multi-instrument mode support
- Settings save/load

### [MultiInstrument (MIM)](mim.md)
**Module:** `moku.instruments.MultiInstrument` ([source](https://github.com/sealablab/DPD-001/blob/main/moku_md/instruments/mim.md))

Multi-Instrument Mode controller for running multiple instruments simultaneously on a single Moku platform.

**Key Features:**
- Slot-based instrument management
- Signal routing between instruments
- Frontend/output configuration per slot
- Digital I/O management
- Platform-level configuration

## Instrument Categories

### Signal Generators
- [_waveformgenerator.md](_waveformgenerator.md) - Basic waveform generation (Sine, Square, Ramp, Pulse, Noise, DC)
- [_awg.md](_awg.md) - Arbitrary Waveform Generator with custom waveforms

### Analyzers & Measurement
- [_oscilloscope.md](_oscilloscope.md) - Oscilloscope with triggering and data acquisition
- [_spectrumanalyzer.md](_spectrumanalyzer.md) - Frequency-domain analysis (0Hz-30MHz)
- [_phasemeter.md](_phasemeter.md) - Phase and amplitude measurement (2-200MHz)
- [_logicanalyzer.md](_logicanalyzer.md) - Digital signal analysis with protocol decoders
- [_tfa.md](_tfa.md) - Time-Frequency Analyzer with sub-nanosecond precision
- [_fra.md](_fra.md) - Frequency Response Analyzer

### Signal Processing
- [_digitalfilterbox.md](_digitalfilterbox.md) - IIR digital filtering
- [_firfilter.md](_firfilter.md) - FIR digital filtering
- [_lockinamp.md](_lockinamp.md) - Lock-In Amplifier with dual-phase demodulation

### Control & Feedback
- [_pidcontroller.md](_pidcontroller.md) - PID Controller with comprehensive control loops
- [_laserlockbox.md](_laserlockbox.md) - Laser frequency stabilization

### Data Acquisition
- [_datalogger.md](_datalogger.md) - Voltage logging and waveform generation

### Infrastructure
- [_stream.md](_stream.md) - Streaming infrastructure base class
- [_nn.md](_nn.md) - Neural Network inference engine
- [__init__.md](__init__.md) - Instrument package initialization and exports

## See Also

- [Moku API Documentation](../README.md) - Main API documentation index
- [Official Moku Instruments Documentation](https://apis.liquidinstruments.com/instruments.html)
- [Moku Python Package](https://pypi.org/project/moku/)

---
**View this document:**
- 📖 [Obsidian Publish](https://publish.obsidian.md/dpd-001/moku_md/instruments/README)
- 💻 [GitHub](https://github.com/sealablab/DPD-001/blob/main/moku_md/instruments/README.md)
- ✏️ [Edit on GitHub](https://github.com/sealablab/DPD-001/edit/main/moku_md/instruments/README.md)
