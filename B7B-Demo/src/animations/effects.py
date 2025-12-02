"""Animation effect generators.

Each effect returns a generator that yields (samples, height) tuples.
The animations are designed for 80x25 terminal viewing.
"""

from typing import Generator, Tuple
import numpy as np

from wavetables import generate_sine, generate_cosine, generate_linear, generate_triangle


def scroll_animation(
    samples: np.ndarray,
    height: int = 4,
    frames: int = 64,
    step: int = 1
) -> Generator[Tuple[np.ndarray, int], None, None]:
    """Scroll waveform left through the view.

    Creates the effect of data streaming in from the right.

    Args:
        samples: Source waveform data
        height: Vertical blocks
        frames: Number of animation frames
        step: Samples to shift per frame

    Yields:
        (samples, height) tuples for each frame
    """
    n = len(samples)
    for frame in range(frames):
        offset = (frame * step) % n
        # Roll the array to create scrolling effect
        shifted = np.roll(samples, -offset)
        yield (shifted, height)


def phase_animation(
    length: int = 78,
    height: int = 4,
    frames: int = 64,
    wave_type: str = "sine"
) -> Generator[Tuple[np.ndarray, int], None, None]:
    """Animate waveform phase shifting.

    Regenerates the waveform at different phase offsets.

    Args:
        length: Number of samples
        height: Vertical blocks
        frames: Number of animation frames
        wave_type: "sine", "cosine", or "triangle"

    Yields:
        (samples, height) tuples for each frame
    """
    for frame in range(frames):
        phase = 2 * np.pi * frame / frames
        t = np.linspace(phase, phase + 2 * np.pi, length, endpoint=False)

        if wave_type == "cosine":
            wave = 63.5 + 63.5 * np.cos(t)
        elif wave_type == "triangle":
            # Triangle from sawtooth
            wave = 63.5 + 63.5 * (2 * np.abs(2 * (t / (2 * np.pi) - np.floor(t / (2 * np.pi) + 0.5))) - 1)
        else:  # sine
            wave = 63.5 + 63.5 * np.sin(t)

        samples = np.round(wave).astype(np.uint8)
        yield (samples, height)


def amplitude_animation(
    length: int = 78,
    height: int = 4,
    frames: int = 64,
    min_amp: float = 0.2,
    max_amp: float = 1.0
) -> Generator[Tuple[np.ndarray, int], None, None]:
    """Animate waveform amplitude modulation.

    Creates a "breathing" effect as amplitude oscillates.

    Args:
        length: Number of samples
        height: Vertical blocks
        frames: Number of animation frames
        min_amp: Minimum amplitude (0-1)
        max_amp: Maximum amplitude (0-1)

    Yields:
        (samples, height) tuples for each frame
    """
    t = np.linspace(0, 2 * np.pi, length, endpoint=False)
    base_wave = np.sin(t)

    for frame in range(frames):
        # Amplitude oscillates sinusoidally
        amp_phase = 2 * np.pi * frame / frames
        amplitude = min_amp + (max_amp - min_amp) * (0.5 + 0.5 * np.sin(amp_phase))

        wave = 63.5 + 63.5 * amplitude * base_wave
        samples = np.round(wave).astype(np.uint8)
        yield (samples, height)


def morph_animation(
    length: int = 78,
    height: int = 4,
    frames: int = 64,
    from_wave: str = "sine",
    to_wave: str = "triangle"
) -> Generator[Tuple[np.ndarray, int], None, None]:
    """Morph between two waveform types.

    Linear interpolation between source and target waveforms.

    Args:
        length: Number of samples
        height: Vertical blocks
        frames: Number of animation frames
        from_wave: Starting waveform type
        to_wave: Ending waveform type

    Yields:
        (samples, height) tuples for each frame
    """
    generators = {
        "sine": generate_sine,
        "cosine": generate_cosine,
        "linear": generate_linear,
        "triangle": generate_triangle,
    }

    wave_a = generators[from_wave](length).astype(np.float64)
    wave_b = generators[to_wave](length).astype(np.float64)

    for frame in range(frames):
        # Use sine easing for smooth morph
        t = frame / (frames - 1) if frames > 1 else 0
        eased_t = 0.5 - 0.5 * np.cos(np.pi * t)

        # Interpolate between waveforms
        wave = wave_a * (1 - eased_t) + wave_b * eased_t
        samples = np.round(wave).astype(np.uint8)
        yield (samples, height)


def resolution_animation(
    samples: np.ndarray | None = None,
    frames_per_level: int = 8,
    direction: str = "up"
) -> Generator[Tuple[np.ndarray, int], None, None]:
    """Cycle through resolution levels.

    Shows the same waveform at different bit depths.

    Args:
        samples: Waveform data (default: sine)
        frames_per_level: Frames to hold at each level
        direction: "up" (3->7), "down" (7->3), or "bounce"

    Yields:
        (samples, height) tuples for each frame
    """
    if samples is None:
        samples = generate_sine(78)

    heights = [1, 2, 4, 8, 16]  # 3, 4, 5, 6, 7 bits

    if direction == "down":
        heights = heights[::-1]
    elif direction == "bounce":
        heights = heights + heights[-2:0:-1]  # 1,2,4,8,16,8,4,2

    for height in heights:
        for _ in range(frames_per_level):
            yield (samples, height)


def composite_animation(
    length: int = 78,
    height: int = 4,
    frames: int = 128
) -> Generator[Tuple[np.ndarray, int], None, None]:
    """Composite animation combining multiple effects.

    Combines phase shift with subtle amplitude modulation.

    Args:
        length: Number of samples
        height: Vertical blocks
        frames: Number of animation frames

    Yields:
        (samples, height) tuples for each frame
    """
    for frame in range(frames):
        # Phase shifts through one complete cycle
        phase = 2 * np.pi * frame / frames
        t = np.linspace(phase, phase + 2 * np.pi, length, endpoint=False)

        # Amplitude modulation (subtle breathing)
        amp_phase = 4 * np.pi * frame / frames  # 2 breath cycles
        amplitude = 0.85 + 0.15 * np.sin(amp_phase)

        wave = 63.5 + 63.5 * amplitude * np.sin(t)
        samples = np.round(wave).astype(np.uint8)
        yield (samples, height)
