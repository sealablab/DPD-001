---
publish: "true"
type: reference
created: 2025-11-25
modified: 2025-11-25
tags: [moku, api, reference, python]
---
# Moku Python API Reference

> [!info] About This Documentation
> This is a comprehensive reference for the **Moku Python API** (v4.0.3.1), used for programmatic control of Liquid Instruments Moku:Go and Moku:Pro devices. The documentation mirrors the structure of the installed pip package.

## Quick Start

```python
from moku.instruments import Oscilloscope, WaveformGenerator

# Connect to a Moku device
scope = Oscilloscope('192.168.1.100', force_connect=True)

# Configure and use the instrument
scope.set_timebase(-1e-3, 1e-3)  # ±1ms window
scope.set_trigger(type='Edge', source=1, level=0.5)

# Get data
data = scope.get_data()
```

## Documentation Structure

The complete API documentation is organized in the **[moku_md/](moku_md/)** directory:

### 📚 Core Documentation
- **[moku_md/README.md](moku_md/README.md)** - Start here! Complete overview, quick reference tables, and navigation guide

### 🔧 Core Modules
- [Moku Base Class](moku_md/init.md) - Device connection and ownership management
- [Device Discovery](moku_md/finder.md) - Find Moku devices on your network
- [Session Management](moku_md/session.md) - HTTP API communication
- [Exceptions](moku_md/exceptions.md) - Error handling hierarchy

### 🎛️ Instruments by Category

| Category | Instruments | Use Cases |
|----------|-------------|-----------|
| **Signal Generation** | [WaveformGenerator](moku_md/instruments/waveformgenerator.md), [AWG](moku_md/instruments/awg.md) | Test signals, stimulus generation |
| **Oscilloscopes** | [Oscilloscope](moku_md/instruments/oscilloscope.md) | Waveform capture, triggering |
| **Spectrum Analysis** | [SpectrumAnalyzer](moku_md/instruments/spectrumanalyzer.md), [Phasemeter](moku_md/instruments/phasemeter.md) | Frequency domain, phase measurements |
| **Signal Processing** | [DigitalFilterBox](moku_md/instruments/digitalfilterbox.md), [FIRFilterBox](moku_md/instruments/firfilter.md), [LockInAmp](moku_md/instruments/lockinamp.md) | Filtering, demodulation |
| **Control Systems** | [PIDController](moku_md/instruments/pidcontroller.md), [LaserLockBox](moku_md/instruments/laserlockbox.md) | Feedback control, laser stabilization |
| **Analysis** | [FrequencyResponseAnalyzer](moku_md/instruments/fra.md), [TimeFrequencyAnalyzer](moku_md/instruments/tfa.md) | System characterization |
| **Digital** | [LogicAnalyzer](moku_md/instruments/logicanalyzer.md) | Digital signal analysis, protocol decode |
| **Data Acquisition** | [Datalogger](moku_md/instruments/datalogger.md) | Long-term voltage logging |
| **Advanced** | [MultiInstrument](moku_md/instruments/_mim.md), [CloudCompile](moku_md/instruments/_cloudcompile.md), [NeuralNetwork](moku_md/instruments/nn.md) | Custom FPGA, ML inference |

## Project Context

This documentation is part of the **DPD-001** (Demo Probe Driver) project, which demonstrates:
- Custom FPGA bitstream development for Moku:Go
- Hardware/software co-design patterns
- Integration with the Moku Python API

## Installation

```bash
pip install moku
```

## See Also

- [Official Moku API Documentation](https://apis.liquidinstruments.com/starting.html)
- [Liquid Instruments](https://www.liquidinstruments.com/)
- [DPD-001 Project README](README.md)

---
**View this document:**
- 📖 [Obsidian Publish](https://publish.obsidian.md/dpd-001/MOKU_API)
- 💻 [GitHub](https://github.com/sealablab/DPD-001/blob/main/MOKU_API.md)
- ✏️ [Edit on GitHub](https://github.com/sealablab/DPD-001/edit/main/MOKU_API.md)
