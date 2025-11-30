# RTL Experiments

Minimal VHDL designs for investigating Moku CloudCompile behavior.

## clock_probe.vhd

**Purpose**: Measure the actual FPGA fabric clock frequency by observing pulse width.

**Method**: Outputs a SQR_04_128 waveform (4 samples high, 124 samples low) at one sample per clock cycle. The pulse width directly reveals the clock period.

**Expected Results**:

| Platform | If ADC Clock | If MCC Fabric Clock |
|----------|--------------|---------------------|
| Moku:Go | 4 × 8ns = **32ns** | 4 × 32ns = **128ns** |
| Moku:Lab | 4 × 2ns = **8ns** | 4 × 8ns = **32ns** |

**Usage**:
1. Compile for target platform using Moku Cloud Compile
2. Deploy with `py_tools/experiments/clock_probe_test.py`
3. Measure pulse width on OutputA

**Documentation**: See [docs/mcc-fabric-clock.md](../../docs/mcc-fabric-clock.md)

## Compilation

These designs use the standard `CustomWrapper` entity interface and can be compiled via:
- Moku Cloud Compile web interface
- Moku Cloud Compile CLI tools

No external dependencies required - all ROMs are inline.
