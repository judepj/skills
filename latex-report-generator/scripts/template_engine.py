"""
LaTeX Template Engine

Render LaTeX documents from Jinja2 templates with LaTeX-safe delimiters.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import jinja2
import logging

try:
    from .compiler import escape_latex
except ImportError:
    from compiler import escape_latex

logger = logging.getLogger(__name__)


class TemplateEngine:
    """Render LaTeX templates with Jinja2."""

    def __init__(self, template_dir: Optional[Path] = None):
        """
        Initialize template engine.

        Args:
            template_dir: Directory containing templates (defaults to ../templates)
        """
        if template_dir is None:
            # Default to ../templates relative to this file
            template_dir = Path(__file__).parent.parent / 'templates'

        if not template_dir.exists():
            raise FileNotFoundError(f"Template directory not found: {template_dir}")

        self.template_dir = template_dir

        # Create Jinja2 environment with LaTeX-safe delimiters
        # Using custom delimiters to avoid conflicts with LaTeX's {} syntax
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(template_dir)),
            block_start_string='\\BLOCK{',
            block_end_string='}',
            variable_start_string='\\VAR{',
            variable_end_string='}',
            comment_start_string='\\#{',
            comment_end_string='}',
            line_statement_prefix='%%',
            line_comment_prefix='%#',
            trim_blocks=True,
            autoescape=False,  # Don't auto-escape, we'll do it manually
            keep_trailing_newline=True,
        )

        # Add custom filters
        self.env.filters['latex_escape'] = escape_latex
        self.env.filters['latex'] = escape_latex  # Alias

        logger.info(f"Template engine initialized with directory: {template_dir}")

    def render_template(
        self,
        template_name: str,
        **context: Any
    ) -> str:
        """
        Render a template with context variables.

        Args:
            template_name: Name of template file (e.g., 'report_types/web_scraping.tex')
            **context: Template context variables

        Returns:
            Rendered LaTeX content

        Raises:
            jinja2.TemplateNotFound: If template doesn't exist
            jinja2.TemplateSyntaxError: If template has syntax errors

        Example:
            >>> engine = TemplateEngine()
            >>> latex = engine.render_template(
            ...     'report_types/web_scraping.tex',
            ...     title='My Report',
            ...     author='John Doe',
            ...     sections=[{'title': 'Intro', 'content': 'Text...'}]
            ... )
        """
        try:
            template = self.env.get_template(template_name)
            rendered = template.render(**context)
            logger.info(f"Rendered template: {template_name}")
            return rendered

        except jinja2.TemplateNotFound:
            available = self.list_templates()
            raise jinja2.TemplateNotFound(
                f"Template not found: {template_name}\n"
                f"Available templates: {available}"
            )
        except jinja2.TemplateSyntaxError as e:
            raise jinja2.TemplateSyntaxError(
                f"Syntax error in template {template_name} at line {e.lineno}: {e.message}",
                lineno=e.lineno,
                name=e.name,
                filename=e.filename
            )

    def list_templates(self) -> list:
        """
        List all available templates.

        Returns:
            List of template filenames relative to template_dir
        """
        templates = []
        for path in self.template_dir.rglob('*.tex'):
            rel_path = path.relative_to(self.template_dir)
            templates.append(str(rel_path))

        return sorted(templates)

    def template_exists(self, template_name: str) -> bool:
        """
        Check if a template exists.

        Args:
            template_name: Name of template file

        Returns:
            True if template exists, False otherwise
        """
        template_path = self.template_dir / template_name
        return template_path.exists()

    def get_template_path(self, template_name: str) -> Path:
        """
        Get absolute path to template file.

        Args:
            template_name: Name of template file

        Returns:
            Absolute path to template

        Raises:
            FileNotFoundError: If template doesn't exist
        """
        template_path = self.template_dir / template_name

        if not template_path.exists():
            raise FileNotFoundError(
                f"Template not found: {template_name}\n"
                f"Expected path: {template_path}"
            )

        return template_path


def main():
    """Test template rendering."""
    import sys

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )

    engine = TemplateEngine()

    print("Available templates:")
    for template in engine.list_templates():
        print(f"  - {template}")

    # Test rendering if template name provided
    if len(sys.argv) > 1:
        template_name = sys.argv[1]

        try:
            latex = engine.render_template(
                template_name,
                title='Test Report',
                author='Test Author',
                date='\\today',
                sections=[
                    {
                        'title': 'Introduction',
                        'content': 'This is a test section with special characters: $100 & 50\\%'
                    }
                ]
            )

            print(f"\nRendered template '{template_name}':")
            print("=" * 60)
            print(latex)

        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)


if __name__ == '__main__':
    main()
