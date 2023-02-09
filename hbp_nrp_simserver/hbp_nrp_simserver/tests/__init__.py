"""
This package contains tests for the commons project
"""

__author__ = 'NRP software team, Georg Hinkel'

from hbp_nrp_cleserver import python_version_major

builtins_str = "__builtin__" if python_version_major < 3 else "builtins"
