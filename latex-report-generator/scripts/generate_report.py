#!/usr/bin/env python3
"""
Simple report generator for testing.

Generates a draft report from web-scraper output.
"""

from pathlib import Path
import argparse
import logging
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from source_integrators import WebScraperIntegrator
from figure_manager import FigureManager
from content_processor import ContentProcessor
from template_engine import TemplateEngine
from compiler import LatexCompiler, escape_latex


def main():
    parser = argparse.ArgumentParser(description='Generate LaTeX report from web-scraper output')
    parser.add_argument('input', type=Path, help='Path to scrape_results.json')
    parser.add_argument('--output', type=Path, required=True, help='Output directory')
    parser.add_argument('--title', type=str, help='Report title (default: from scraped data)')
    parser.add_argument('--author', type=str, default='Research Team', help='Author name')
    parser.add_argument('--max-figures', type=int, default=5, help='Maximum figures to auto-select')
    parser.add_argument('--use-manifest', action='store_true', help='Use existing figure_manifest.json')
    parser.add_argument('--finalize', action='store_true', help='Generate final report (use with --use-manifest)')
    parser.add_argument('--no-compile', action='store_true', help='Skip PDF compilation')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format='%(levelname)s: %(message)s'
    )

    logger = logging.getLogger(__name__)

    try:
        print("="*60)
        if args.use_manifest and args.finalize:
            print("LaTeX Report Generator - Final Mode")
        elif args.use_manifest:
            print("LaTeX Report Generator - Using Manifest")
        else:
            print("LaTeX Report Generator - Draft Mode")
        print("="*60)

        # 1. Parse web-scraper output
        print(f"\n[1/6] Parsing web-scraper output: {args.input}")
        integrator = WebScraperIntegrator()
        content = integrator.parse(args.input)

        title = args.title or content['title']
        print(f"      Title: {title}")

        # 2. Scan for images
        print(f"\n[2/6] Scanning for images...")
        fm = FigureManager(output_dir=args.output)

        images_dirs = []
        if content['images_dir']:
            images_dirs.append(content['images_dir'])

        # 3. Handle figures
        if args.use_manifest:
            # Use existing manifest
            print(f"\n[3/6] Loading figure manifest...")
            try:
                manifest = fm.load_manifest()
                print(f"      Loaded {len(manifest['figures'])} figures from manifest")

                # Copy only figures marked as include=True
                selected = fm.get_selected_figures()
                print(f"      {len(selected)} figures marked for inclusion")
                fm.copy_figures_to_output(selected)
            except FileNotFoundError as e:
                print(f"      Error: {e}")
                print(f"      Run without --use-manifest first to generate manifest")
                sys.exit(1)
        else:
            # Auto-select figures
            print(f"\n[3/6] Auto-selecting figures (max: {args.max_figures})...")
            if images_dirs:
                figures = fm.scan_images(images_dirs)
                print(f"      Found {len(figures)} images")
            else:
                print("      No images directory found")
                figures = []

            if figures:
                selected_figures = fm.auto_select_figures(figures, max_figures=args.max_figures)
                print(f"      Selected {len(selected_figures)} figures")

                # Generate manifest
                manifest_file = fm.generate_manifest(
                    selected_figures,
                    source_type='web-scraper',
                    source_file=str(args.input)
                )
                print(f"      Manifest: {manifest_file}")

                # Copy figures
                manifest = fm.load_manifest()
                fm.copy_figures_to_output(manifest['figures'])
            else:
                selected_figures = []
                manifest = {'figures': []}

        # 4. Process content (bullets to paragraphs)
        print(f"\n[4/6] Processing content...")
        processor = ContentProcessor()
        for section in content['sections']:
            section['content'] = processor.bullets_to_paragraphs(
                section['content'],
                section_name=section['title']
            )
        print(f"      Processed {len(content['sections'])} sections")

        # 5. Render LaTeX template
        print(f"\n[5/6] Rendering LaTeX template...")
        engine = TemplateEngine()

        # Prepare template context
        context = {
            'title': escape_latex(title),
            'author': escape_latex(args.author),
            'date': datetime.now().strftime("%B %d, %Y"),
            'abstract': escape_latex(content.get('description', '')),
            'sections': [
                {
                    'title': escape_latex(s['title']),
                    'content': escape_latex(s['content']),
                    'figures': []  # TODO: Associate figures with sections
                }
                for s in content['sections']
            ],
            'standalone_figures': manifest.get('figures', []),
            'url': content.get('url', ''),
            'references': []  # TODO: Extract references
        }

        latex_content = engine.render_template(
            'report_types/web_scraping.tex',
            **context
        )

        # Write LaTeX file
        if args.finalize:
            tex_file = args.output / 'final_report.tex'
        else:
            tex_file = args.output / 'draft_report.tex'
        tex_file.write_text(latex_content)
        print(f"      LaTeX file: {tex_file}")

        # 6. Compile to PDF
        if not args.no_compile:
            print(f"\n[6/6] Compiling to PDF...")
            compiler = LatexCompiler()
            try:
                pdf_file = compiler.compile(tex_file, cleanup=True, runs=2)
                print(f"      PDF file: {pdf_file}")
                if args.finalize:
                    print(f"\n✓ Success! Final report generated: {pdf_file}")
                else:
                    print(f"\n✓ Success! Draft report generated: {pdf_file}")
            except Exception as e:
                print(f"      Compilation failed: {e}")
                print(f"      LaTeX file saved for manual compilation: {tex_file}")
        else:
            print(f"\n✓ LaTeX file generated: {tex_file}")
            print("   (Skipped PDF compilation)")

        # Summary
        print("\n" + "="*60)
        if args.finalize:
            print("Report Generation Complete!")
            print(f"Final PDF: {args.output}/final_report.pdf")
        else:
            print("Next Steps:")
            if args.use_manifest:
                print(f"1. Review PDF: {args.output}/draft_report.pdf")
                print(f"2. If satisfied, re-run with --finalize for final report")
            else:
                print(f"1. Review draft PDF: {args.output}/draft_report.pdf")
                print(f"2. Edit figure manifest: {args.output}/figure_manifest.json")
                print(f"   - Set include: false for unwanted figures")
                print(f"   - Write descriptive captions")
                print(f"3. Re-run with --use-manifest --finalize for final report")
        print("="*60)

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=args.verbose)
        print(f"\n✗ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
