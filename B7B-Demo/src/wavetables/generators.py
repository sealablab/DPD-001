"""Waveform generators for B7B-Demo.

All generators return numpy arrays with dtype uint8, values 0-127 (7-bit).
"""

import numpy as np


def generate_linear(length: int = 128) -> np.ndarray:
    """Generate linear ramp from 0 to 127.

    Args:
        length: Number of samples

    Returns:
        Array of uint8 values ramping from 0 to 127
    """
    return np.linspace(0, 127, length, dtype=np.uint8)


def generate_sine(length: int = 128) -> np.ndarray:
    """Generate one period of sine wave, scaled 0-127.

    Zero-crossing at index 0, peak at index length/4.

    Args:
        length: Number of samples

    Returns:
        Array of uint8 values representing sine wave
    """
    t = np.linspace(0, 2 * np.pi, length, endpoint=False)
    # Sine starts at 0, peaks at π/2
    wave = 63.5 + 63.5 * np.sin(t)
    return np.round(wave).astype(np.uint8)


def generate_cosine(length: int = 128) -> np.ndarray:
    """Generate one period of cosine wave, scaled 0-127.

    Peak at index 0, zero-crossing at index length/4.

    Args:
        length: Number of samples

    Returns:
        Array of uint8 values representing cosine wave
    """
    t = np.linspace(0, 2 * np.pi, length, endpoint=False)
    # Cosine starts at peak
    wave = 63.5 + 63.5 * np.cos(t)
    return np.round(wave).astype(np.uint8)


def generate_triangle(length: int = 128) -> np.ndarray:
    """Generate one period of triangle wave, scaled 0-127.

    Starts at 0, peaks at length/2.

    Args:
        length: Number of samples

    Returns:
        Array of uint8 values representing triangle wave
    """
    half = length // 2
    up = np.linspace(0, 127, half, dtype=np.uint8)
    down = np.linspace(127, 0, length - half, dtype=np.uint8)
    return np.concatenate([up, down])
