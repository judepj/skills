"""
LaTeX Compiler

Compile LaTeX documents to PDF using pdflatex, xelatex, or lualatex.
Refactored from /tools/scientific_brainstorming/utils/report_generator.py
"""

from pathlib import Path
from typing import Optional, List
import subprocess
import logging

logger = logging.getLogger(__name__)


class CompilationError(Exception):
    """Raised when LaTeX compilation fails."""
    pass


class LatexCompiler:
    """Compile LaTeX documents to PDF."""

    def __init__(self, engine: str = 'pdflatex'):
        """
        Initialize LaTeX compiler.

        Args:
            engine: LaTeX engine to use ('pdflatex', 'xelatex', 'lualatex')
        """
        valid_engines = ['pdflatex', 'xelatex', 'lualatex']
        if engine not in valid_engines:
            raise ValueError(f"Engine must be one of {valid_engines}, got: {engine}")

        self.engine = engine

    def compile(
        self,
        tex_file: Path,
        cleanup: bool = True,
        runs: int = 2,
        timeout: int = 120
    ) -> Path:
        """
        Compile .tex file to .pdf.

        Args:
            tex_file: Path to .tex file
            cleanup: Remove auxiliary files (.aux, .log, .out) after compilation
            runs: Number of compilation passes (for references/TOC, typically 2)
            timeout: Timeout in seconds per compilation run

        Returns:
            Path to generated PDF

        Raises:
            CompilationError: If compilation fails
            FileNotFoundError: If LaTeX engine not found
        """
        if not tex_file.exists():
            raise FileNotFoundError(f"LaTeX file not found: {tex_file}")

        logger.info(f"Compiling {tex_file} with {self.engine} ({runs} run(s))")

        pdf_file = tex_file.with_suffix('.pdf')

        # Run compilation multiple times for references
        for run in range(1, runs + 1):
            logger.info(f"  Run {run}/{runs}...")

            try:
                result = subprocess.run(
                    [self.engine, '-interaction=nonstopmode', str(tex_file.name)],
                    capture_output=True,
                    text=True,
                    cwd=tex_file.parent,
                    timeout=timeout
                )

                # Check if PDF was created
                if not pdf_file.exists() and run == runs:
                    error_msg = self._parse_log_for_errors(tex_file.with_suffix('.log'))
                    raise CompilationError(
                        f"PDF generation failed. Check {tex_file.with_suffix('.log')}\n"
                        f"Error: {error_msg}"
                    )

            except subprocess.TimeoutExpired:
                raise CompilationError(
                    f"LaTeX compilation timed out after {timeout} seconds"
                )
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"{self.engine} not found. Install LaTeX distribution:\n"
                    f"  MacOS: brew install --cask mactex\n"
                    f"  Linux: sudo apt-get install texlive-full\n"
                    f"  Windows: https://miktex.org/"
                )

        if pdf_file.exists():
            logger.info(f"PDF generated successfully: {pdf_file}")

            # Cleanup auxiliary files
            if cleanup:
                self._cleanup_aux_files(tex_file)

            return pdf_file
        else:
            raise CompilationError(f"PDF file not created: {pdf_file}")

    def _cleanup_aux_files(self, tex_file: Path) -> None:
        """Remove auxiliary files created during compilation."""
        aux_extensions = ['.aux', '.log', '.out', '.toc', '.lof', '.lot', '.bbl', '.blg']

        for ext in aux_extensions:
            aux_file = tex_file.with_suffix(ext)
            if aux_file.exists():
                try:
                    aux_file.unlink()
                    logger.debug(f"Removed {aux_file.name}")
                except Exception as e:
                    logger.warning(f"Failed to remove {aux_file.name}: {e}")

    def _parse_log_for_errors(self, log_file: Path) -> str:
        """
        Parse LaTeX .log file for error messages.

        Args:
            log_file: Path to .log file

        Returns:
            Error message or "Unknown error" if not found
        """
        if not log_file.exists():
            return "Log file not found"

        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                log_content = f.read()

            # Look for common error patterns
            error_patterns = [
                "! LaTeX Error:",
                "! Undefined control sequence",
                "! Missing",
                "! Package",
                "! File",
            ]

            errors = []
            for line in log_content.split('\n'):
                for pattern in error_patterns:
                    if pattern in line:
                        errors.append(line.strip())
                        if len(errors) >= 5:  # Limit to first 5 errors
                            break
                if len(errors) >= 5:
                    break

            if errors:
                return '\n'.join(errors)
            else:
                return "Unknown compilation error (check .log file)"

        except Exception as e:
            return f"Could not parse log file: {e}"


def escape_latex(text: str) -> str:
    """
    Escape special LaTeX characters.

    Refactored from /tools/scientific_brainstorming/utils/report_generator.py

    Args:
        text: Text to escape

    Returns:
        LaTeX-safe text

    Example:
        >>> escape_latex("Price: $50 & up")
        'Price: \\$50 \\& up'
    """
    if not isinstance(text, str):
        return str(text)

    replacements = {
        '\\': r'\textbackslash{}',  # Must be first!
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\^{}',
    }

    # Process backslash first, then others
    text = text.replace('\\', replacements['\\'])
    for char, replacement in replacements.items():
        if char != '\\':  # Already processed
            text = text.replace(char, replacement)

    return text


def main():
    """Test compilation."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python compiler.py <file.tex>")
        sys.exit(1)

    tex_file = Path(sys.argv[1])

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )

    try:
        compiler = LatexCompiler()
        pdf_file = compiler.compile(tex_file, cleanup=True, runs=2)
        print(f"Success! PDF created: {pdf_file}")
    except (CompilationError, FileNotFoundError) as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
