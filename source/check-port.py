#!/usr/bin/env python3
"""check-port — alias for show-port. See show-port.py for the implementation."""
import importlib.util
import os
import sys

_impl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "show-port.py")
if not os.path.isfile(_impl_path):
    sys.stderr.write(f"check-port: implementation not found at {_impl_path}\n")
    sys.exit(1)

_spec = importlib.util.spec_from_file_location("show_port", _impl_path)
_show_port = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_show_port)


if __name__ == "__main__":
    _show_port.main()
