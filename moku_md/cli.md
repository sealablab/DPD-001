---
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/cli.py
title: cli
created: 2025-11-19
modified: 2025-11-29 17:20:01
accessed: 2025-11-29 17:20:01
---

# Overview

This module provides a deprecated command-line interface that has been replaced by the `mokucli` utility. The module now serves as a redirect, informing users to download the new full-featured Moku Command Line Utility.

> [!info] Key Dependencies
> - `argparse.ArgumentParser` - Imported but not used in current implementation

> [!warning] Deprecation Notice
> This CLI has been deprecated and replaced with `mokucli`. The module only prints a message directing users to download the new utility from https://liquidinstruments.com/software/utilities/

# Classes

None

# Functions

## main

```python
def main():
    """Prints deprecation message directing users to mokucli"""
```

Displays a message informing users that this command-line interface has been replaced by the `mokucli` utility and provides a download link.

**Parameters:** None

**Returns:** None (prints to stdout)

> [!note] Implementation Notes
> - The function does not parse any arguments despite importing `ArgumentParser`
> - Simply prints a deprecation message
> - Can be invoked directly via script execution or as a distutils binary entry point

# See Also

- The replacement utility is available at: https://liquidinstruments.com/software/utilities/
