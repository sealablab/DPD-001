---
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/nn/_linn.py
title: _linn
---

# Overview

This module provides the `LinnModel` class and utilities for creating, training, and converting neural networks for deployment on the Moku Neural Network Instrument. It handles model construction with quantization-aware constraints, data scaling/transformation, training with early stopping, and conversion to the `.linn` format required by Moku hardware.

> [!info] Key Dependencies
> - **tensorflow/keras** - Neural network construction and training
> - **numpy** - Data manipulation and array operations
> - **json** - Serialization of models to .linn format
> - **typing** - Type hints for function signatures

# Classes

## WeightClip

A Keras constraint that clips all weights and biases to the range [-1, 1] to facilitate quantization for hardware deployment.

**Key Methods:**
- `__init__(clip_value: float = 1.0)` - Initialize with symmetric clip bounds
- `__call__(w: Any) -> Tensor` - Apply clipping to weight tensor
- `get_config() -> dict` - Return configuration dictionary

```python
class WeightClip(keras.constraints.Constraint):
    def __init__(self, clip_value: float = 1.0) -> None:
        """Clips weights/biases to [-1, 1] range"""
```

> [!note] Implementation Notes
> Applied to both kernel and bias constraints in Dense layers to ensure all parameters stay within quantization bounds.

## OutputClipLayer

A Keras layer that clips layer outputs to the range [-1, 1] to ensure proper quantization throughout the network.

**Key Methods:**
- `__init__(clip_value: float = 1.0)` - Initialize with symmetric clip bounds
- `call(inputs, *args, **kwargs) -> Tensor` - Clip inputs to symmetric bounds

```python
class OutputClipLayer(keras.layers.Layer):
    def __init__(self, clip_value: float = 1.0):
        """Ensures outputs are clipped to [-1, 1] for quantization"""
```

> [!note] Implementation Notes
> Applied after each Dense layer in the network to maintain bounded activations throughout forward pass.

## LinnModel

Main class for creating and managing neural networks compatible with the Moku Neural Network Instrument. Handles data scaling, model construction, training, and prediction.

**Key Methods:**
- `__init__()` - Initialize empty model
- `set_training_data(training_inputs, training_outputs, scale=True, input_data_boundary=None, output_data_boundary=None)` - Set and optionally scale training data
- `construct_model(layer_definition, show_summary=False, optimizer='adam', loss='mse', metrics=())` - Build the neural network from layer definitions
- `fit_model(epochs, es_config=None, validation_split=0.0, validation_data=None, **keras_kwargs)` - Train the model with optional early stopping
- `predict(inputs, scale=None, unscale_output=None, **keras_kwargs)` - Generate predictions with automatic scaling/unscaling

**Internal Methods:**
- `_transform(data_array, is_input)` - Transform data to [-1, 1] domain
- `_inverse_transform(data_array, is_input)` - Undo scaling transformation
- `_check_model_definition()` - Validate layer definitions against data dimensions
- `_check_data_model_dim(inputs, outputs, data_name)` - Verify data matches model shape

```python
class LinnModel:
    def __init__(self):
        self.model = None
        self.training_inputs = None
        self.training_outputs = None
        self._input_transform_args = None
        self._output_transform_args = None
        self.model_definition = None
```

> [!note] Usage Pattern
> Typical workflow:
> 1. Create LinnModel instance
> 2. Call `set_training_data()` with input/output arrays
> 3. Call `construct_model()` with layer definitions
> 4. Call `fit_model()` to train
> 5. Call `predict()` for inference

> [!warning] Data Scaling
> By default, `set_training_data()` scales inputs and outputs to [-1, 1] range. This scaling is automatically applied/reversed in `predict()`. Custom boundaries can be specified via `input_data_boundary` and `output_data_boundary` parameters.

> [!info] Layer Definition Format
> Layer definitions are lists of tuples: `[(width, activation), ...]`
> - Supported activations: relu, tanh, sigmoid, softsign, linear
> - Each layer automatically includes WeightClip and OutputClipLayer constraints
> - Input/output dimensions are automatically validated against training data

# Functions

## list_activations

```python
def list_activations():
    """List the available activation functions"""
```

Returns the list of supported activation functions for use in layer definitions.

**Returns:** List of strings: ["relu", "tanh", "sigmoid", "softsign", "linear"]

## get_linn

```python
def get_linn(
    model: keras.models.Model,
    input_channels: int,
    output_channels: int,
    **kwargs
) -> dict:
    """Converts a LinnModel into .linn format for Moku Neural Network Instrument"""
```

Converts a trained LinnModel or compatible Keras model to the .linn dictionary format required for hardware deployment.

**Parameters:**
- `model` - LinnModel instance or compatible Keras model
- `input_channels` - Number of instrument inputs to connect (determines serial/parallel processing)
- `output_channels` - Number of instrument outputs to connect (determines serial/parallel processing)

**Keyword Args:**
- `output_mapping` (list) - Optional list of integers selecting which output neurons to use

**Returns:** Dictionary containing the .linn JSON structure with version, channels, and layer data

> [!warning] Hardware Constraints
> - Maximum 5 dense layers allowed
> - Maximum 100 inputs and 100 outputs per layer
> - Total weights + biases must not exceed 1024 (sum of all layer widths + 3*num_layers)
> - Network latency is approximately equal to this total

## save_linn

```python
def save_linn(
    model: keras.models.Model,
    input_channels: int,
    output_channels: int,
    file_name: str,
    **kwargs
):
    """Converts and saves a Keras model to .linn file format"""
```

Converts a LinnModel to .linn format and saves it to a file for loading into the Neural Network instrument.

**Parameters:**
- `model` - LinnModel instance or compatible Keras model
- `input_channels` - Number of instrument inputs to connect
- `output_channels` - Number of instrument outputs to connect
- `file_name` - Output filename (must have .linn extension)

**Keyword Args:**
- `output_mapping` (list) - Optional list of integers selecting which output neurons to use

**Returns:** None (writes to file)

> [!note] File Format
> The .linn format is a JSON document containing network version, channel counts, and layer specifications (weights, biases, activations).

## convert_keras_to_linn

```python
def convert_keras_to_linn(
    model: keras.models.Model,
    input_channels: int,
    output_channels: int,
    **kwargs
):
    """Internal conversion function from Keras to .linn format"""
```

Internal implementation that performs the actual conversion from Keras model to .linn dictionary structure. Called by both `get_linn()` and `save_linn()`.

**Parameters:**
- `model` - Keras Sequential, Model, or LinnModel instance
- `input_channels` - Number of hardware input channels
- `output_channels` - Number of hardware output channels

**Keyword Args:**
- `output_mapping` (list) - Optional output neuron selection

**Returns:** Dictionary with .linn format structure

> [!warning] Validation
> Performs extensive validation of model structure:
> - Only Dense layers supported (InputLayer, WeightClip, OutputClipLayer are skipped)
> - Enforces hardware constraints on layer counts and sizes
> - Validates input/output channel mappings
> - Ensures memory budget is not exceeded

# See Also

- Related module: `moku.instruments` - For loading and deploying .linn models on hardware
- TensorFlow/Keras documentation for base layer and model classes
