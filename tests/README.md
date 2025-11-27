# [README](tests/README.md)

  # Verbose output (DEBUG level)
  python run.py --verbose
  python run.py -v

  # Moku debug logging (hw only)
  python run.py --backend hw --debug                    # Output to stderr
  python run.py --backend hw --debug moku_debug.log    # Output to file

  Ready to Test Hardware

  Once your bitstream is re-synthesized, try:

  cd /Users/johnycsh/DPD/DPD-001/tests

  # Normal run
  uv run python run.py --backend hw --device 192.168.31.41 --bitstream ../dpd-bits.tar

  # Verbose (shows DEBUG messages from plumbing.py)
  uv run python run.py --backend hw --device 192.168.31.41 --bitstream ../dpd-bits.tar -v

  # With Moku API debug logging
  uv run python run.py --backend hw --device 192.168.31.41 --bitstream ../dpd-bits.tar --debug
