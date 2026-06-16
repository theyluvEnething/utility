#!/usr/bin/env python3
"""check-port — alias for show-port. See show-port.py for the implementation."""
import importlib.util
import os

_impl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "show-port.py")
_spec = importlib.util.spec_from_file_location("show_port", _impl_path)
_show_port = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_show_port)


if __name__ == "__main__":
    _show_port.main()
