---
created: 2025-12-02
status: RESEARCH NOTE
author: Claude (research session)
---
# Mosh Transport Feasibility Analysis

Research into whether the oscilloscope widget rendering pipeline can leverage [mosh](https://mosh.org) (mobile shell) as a transport layer for efficient compression and rendering.

## Executive Summary

**Feasibility: Indirect — Design for mosh-friendliness, not mosh-as-library**

Mosh's State Synchronization Protocol (SSP) is **not exposed as a reusable library or API**. However, we can design our widget to be **mosh-friendly** by adopting rendering patterns that work well with mosh's differential update mechanism.

The good news: `prompt_toolkit` already implements differential screen updates similar to mosh's approach, so our widget will automatically benefit when run over mosh.

## Mosh Architecture Overview

### State Synchronization Protocol (SSP)

From the [mosh paper](https://web.mit.edu/keithw/www/Winstein-Balakrishnan-Mosh.pdf):

> SSP runs over UDP, synchronizing the state of any object from one host to another. The server and client both maintain a snapshot of the current screen state. Each datagram represents an idempotent operation—a "diff" between a numbered source and target state.

Key characteristics:
- **Object-level synchronization**: Syncs terminal screen state, not byte streams
- **Frame-rate adaptive**: Adjusts update rate based on network conditions
- **Idempotent diffs**: Can skip intermediate states without loss
- **Encrypted**: AES-128 in OCB3 mode

### How Mosh Generates Diffs

From [GitHub issue #817](https://github.com/mobile-shell/mosh/issues/817):

> Mosh currently generates display updates with ad-hoc code in `Terminal::Display::new_frame()` and `Terminal::Display::put_row()`. This code generates strings to update a terminal by comparing individual cells, with some lookahead down the row, and there's also some optimization for scrolling rows.

The diff is **not** LCS-based (like traditional diff). A maintainer noted:

> For a terminal where symbols can only really be modified in place, a straightforward linear scan looking for modified symbols works much more simply.

### SSP as a Library: Not Feasible

From [GitHub issue #1087](https://github.com/mobile-shell/mosh/issues/1087):

> "SSP is not at all extensible, and it is strongly tied to the Mosh codebase."
> "Proper documentation for State Synchronization Protocol other than a reference implementation would be much appreciated."

**Conclusion**: We cannot use SSP as a transport library. It's deeply integrated into mosh's terminal emulator.

## prompt_toolkit's Rendering Pipeline

The [prompt_toolkit documentation](https://python-prompt-toolkit.readthedocs.io/en/stable/pages/advanced_topics/rendering_pipeline.html) describes a similar approach:

> The rendering needs to be very efficient, because it's something that happens on every single key stroke. The approach is to output as little as possible on stdout in order to reduce latency on slow network connections and older terminals.

> When the screen has been painted, it needs to be rendered to stdout. This is done by **taking the difference of the previously rendered screen and the new one**. The algorithm is heavily optimized to compute this difference as quickly as possible.

This is conceptually identical to mosh's approach:
1. Maintain previous and current screen state
2. Compute minimal diff
3. Output only changed characters

## Design Recommendations

### 1. Leverage Existing Differential Rendering

Both mosh and prompt_toolkit already implement differential updates. Our widget benefits automatically by:

- Using `prompt_toolkit`'s `UIControl` interface correctly
- Letting the framework handle screen diffing
- Not bypassing the rendering pipeline with raw terminal writes

### 2. Minimize Visual Entropy

Mosh's diff algorithm performs best when changes are localized. Design principles:

| Pattern | Mosh-Friendly | Mosh-Unfriendly |
|---------|---------------|-----------------|
| Update specific cells | ✓ | |
| Full screen clear + redraw | | ✗ |
| Stable border/frame | ✓ | |
| Animated border | | ✗ |
| Vertical waveform (changes in column) | ✓ | |
| Horizontal scroll | | ✗ |

**Our widget design** (vertical bars that change height) is inherently mosh-friendly:
- Each column is a single character that may change
- Border/label areas are static
- No horizontal scrolling
- Changes are spatially localized

### 3. Fixed Refresh Rate

Mosh adapts its frame rate to network conditions. From mosh.org:

> Mosh adjusts its frame rate so as not to fill up network queues on slow links.

Our 20Hz target is reasonable because:
- Mosh will automatically drop frames if network is slow
- The client-side model means we're not blocking on hardware
- 20Hz provides smooth visual updates on good connections

### 4. Avoid Expensive Terminal Operations

Some terminal operations are more expensive over mosh:

| Operation | Cost | Notes |
|-----------|------|-------|
| Character write | Low | Single cell update |
| Cursor move | Low | Relative moves preferred |
| Color change | Low | Attributes cached |
| Clear line | Medium | Affects multiple cells |
| Clear screen | High | Full redraw required |
| Scroll region | Medium | Mosh has scroll optimization |
| Alt screen buffer | High | Full state switch |

**Recommendation**: Use incremental updates, avoid `clear()`, use stable layouts.

### 5. Unicode Block Characters

Our widget uses Unicode block characters (`▁▂▃▄▅▆▇█`). These are:

- ✓ Single-codepoint characters (no combining marks)
- ✓ Fixed-width in monospace fonts
- ✓ UTF-8 compatible (mosh requires UTF-8)
- ✓ 1-3 bytes each (efficient encoding)

Mosh handles these well because it was designed for UTF-8 from the start.

## Alternative Approaches Considered

### A. Custom SSP Implementation

**Rejected**: SSP is undocumented and tightly coupled to mosh internals. The [paper](https://mosh.org/mosh-paper-draft.pdf) provides design rationale but not protocol specification.

### B. Mosh as Subprocess

**Not applicable**: Mosh is a shell replacement, not a transport library. The user runs `mosh user@host` instead of `ssh user@host`.

### C. Direct UDP with Custom Protocol

**Overkill**: For our use case (oscilloscope widget), the terminal's existing update mechanism is sufficient. Building a custom UDP protocol would add complexity without clear benefit.

### D. WebSocket Transport (Future)

If we later need direct widget-to-widget communication bypassing the terminal, WebSocket would be more appropriate than UDP/SSP. But this is out of scope for the current design.

## Integration with Current Design

### No Changes Required

The oscilloscope widget spec already follows mosh-friendly patterns:

1. **`TextRenderer.render()`**: Returns list of strings, not raw terminal escapes
2. **`OscilloWidget`**: Uses `prompt_toolkit`'s `UIControl` interface
3. **Fixed dimensions**: 32-40 × 8-16 is a stable region
4. **Vertical bar rendering**: Changes are column-local

### Optional Enhancements

If we observe performance issues over mosh:

1. **Dirty-region tracking**: Only update columns where waveform changed
   ```python
   def update(self):
       new_data = self.store.get_waveform(...)
       if np.array_equal(new_data, self._last_data):
           return  # No change, skip render
       self._last_data = new_data.copy()
       # ... render
   ```

2. **Temporal dithering**: Reduce effective update rate on slow connections
   ```python
   def should_update(self) -> bool:
       # Skip every other frame if updates are slow
       if self._network_slow:
           self._frame_counter += 1
           return self._frame_counter % 2 == 0
       return True
   ```

3. **Low-fidelity mode**: Reduce vertical resolution (4 rows instead of 8) over slow links

## Conclusion

**Design our widget to be mosh-friendly, not mosh-dependent.**

The current oscilloscope widget design is already well-suited for mosh because:
1. It uses `prompt_toolkit`'s differential rendering
2. It has localized, predictable visual changes
3. It uses simple Unicode characters
4. It has fixed dimensions and stable layout

No special mosh integration is needed. When run over mosh, the widget will automatically benefit from:
- UDP transport with packet loss resilience
- Adaptive frame rate
- Local echo for input
- Roaming support

## References

- [Mosh: the mobile shell](https://mosh.org)
- [Mosh Paper (MIT)](https://web.mit.edu/keithw/www/Winstein-Balakrishnan-Mosh.pdf)
- [SSP Documentation Request (GitHub #1087)](https://github.com/mobile-shell/mosh/issues/1087)
- [Terminal Diff Algorithm Discussion (GitHub #817)](https://github.com/mobile-shell/mosh/issues/817)
- [prompt_toolkit Rendering Pipeline](https://python-prompt-toolkit.readthedocs.io/en/stable/pages/advanced_topics/rendering_pipeline.html)
- [ncurses Screen Optimization](https://invisible-island.net/ncurses/ncurses-intro.html)
- [Wikipedia: Mosh](https://en.wikipedia.org/wiki/Mosh_(software))
