"""Shim: this module has moved to kolay_cli.proxy.cache.
All imports from this path continue to work unchanged (including private names).
"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module('kolay_cli.proxy.cache')
_sys.modules[__name__] = _real
