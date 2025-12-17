"""
LaTeX Report Generator Scripts

Core modules for generating professional LaTeX reports.
"""

__version__ = '1.0.0'

# Public API exports
from .compiler import LatexCompiler, CompilationError, escape_latex

__all__ = [
    'LatexCompiler',
    'CompilationError',
    'escape_latex',
]
