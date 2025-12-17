"""
Figure Manager

Interactive figure selection via file-based editing (no stdin input()).
Implements smart auto-selection using scoring algorithm.
"""

from pathlib import Path
from typing import List, Dict, Optional, Any
import json
import time
from datetime import datetime
import logging
from PIL import Image

logger = logging.getLogger(__name__)


class Figure:
    """Represents a figure with metadata."""

    def __init__(
        self,
        source_path: Path,
        alt_text: str = '',
        url: str = '',
        score: float = 0.0
    ):
        self.source_path = Path(source_path)
        self.filename = self.source_path.name
        self.alt_text = alt_text
        self.url = url
        self.score = score

        # Get image dimensions and size
        self.width = 0
        self.height = 0
        self.size_bytes = 0

        try:
            self.size_bytes = self.source_path.stat().st_size

            # Try to get image dimensions
            with Image.open(self.source_path) as img:
                self.width, self.height = img.size
        except Exception as e:
            logger.warning(f"Could not read image metadata for {self.filename}: {e}")

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'source_path': str(self.source_path),
            'filename': self.filename,
            'alt_text': self.alt_text,
            'url': self.url,
            'width_px': self.width,
            'height_px': self.height,
            'size_bytes': self.size_bytes,
            'score': round(self.score, 2)
        }


class FigureManager:
    """Manage figure selection and captions via file editing."""

    def __init__(self, output_dir: Path):
        """
        Initialize figure manager.

        Args:
            output_dir: Directory for output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_file = self.output_dir / 'figure_manifest.json'

    def scan_images(self, source_dirs: List[Path]) -> List[Figure]:
        """
        Find all images in source directories.

        Args:
            source_dirs: List of directories to scan

        Returns:
            List of Figure objects

        Supported formats: .png, .jpg, .jpeg, .pdf
        """
        image_extensions = {'.png', '.jpg', '.jpeg', '.pdf'}
        figures = []

        for source_dir in source_dirs:
            source_dir = Path(source_dir)

            if not source_dir.exists():
                logger.warning(f"Source directory not found: {source_dir}")
                continue

            for ext in image_extensions:
                for img_file in source_dir.glob(f'*{ext}'):
                    if img_file.is_file():
                        fig = Figure(source_path=img_file)
                        figures.append(fig)

        logger.info(f"Found {len(figures)} images in {len(source_dirs)} director(ies)")
        return figures

    def score_image(self, figure: Figure) -> float:
        """
        Score an image for automatic selection (0-100 scale).

        Scoring criteria:
        - Size: 25 points (prefer 200KB-2MB)
        - Dimensions: 25 points (prefer ≥1200px width)
        - Alt text: 20 points (prefer descriptive text)
        - Filename: 15 points (prefer descriptive names)
        - Aspect ratio: 10 points (prefer landscape/square)
        - Format: 5 points (prefer PNG/PDF)

        Args:
            figure: Figure to score

        Returns:
            Score from 0-100
        """
        score = 0.0

        # 1. Size score (0-25 points)
        size_kb = figure.size_bytes / 1024
        if 200 <= size_kb <= 2000:
            score += 25
        elif 100 <= size_kb < 200:
            score += 20
        elif size_kb < 100:
            score += 10  # Too small
        elif 2000 < size_kb <= 5000:
            score += 15
        else:
            score += 5  # Too large

        # 2. Dimension score (0-25 points)
        if figure.width >= 1200 and figure.height >= 800:
            score += 25
        elif figure.width >= 800 and figure.height >= 600:
            score += 20
        elif figure.width >= 600:
            score += 10
        else:
            score += 5

        # 3. Alt text quality (0-20 points)
        alt_len = len(figure.alt_text)
        if alt_len > 50:
            score += 20
        elif alt_len > 20:
            score += 15
        elif alt_len > 0:
            score += 10
        else:
            score += 0

        # 4. Filename quality (0-15 points)
        descriptive_words = ['diagram', 'graph', 'chart', 'figure', 'plot',
                              'architecture', 'brain', 'electrode', 'neural']
        filename_lower = figure.filename.lower()

        if any(word in filename_lower for word in descriptive_words):
            score += 15
        elif any(char.isdigit() for char in figure.filename):
            score += 5  # Has numbers (likely hash)
        else:
            score += 10

        # 5. Aspect ratio (0-10 points)
        if figure.width > 0 and figure.height > 0:
            aspect = figure.width / figure.height
            if 1.2 <= aspect <= 2.0:  # Landscape
                score += 10
            elif 0.8 <= aspect < 1.2:  # Square-ish
                score += 8
            else:
                score += 5

        # 6. Format preference (0-5 points)
        ext = Path(figure.filename).suffix.lower()
        if ext in ['.png', '.pdf']:
            score += 5
        elif ext in ['.jpg', '.jpeg']:
            score += 4
        else:
            score += 2

        return min(score, 100.0)

    def auto_select_figures(
        self,
        figures: List[Figure],
        max_figures: int = 5
    ) -> List[Figure]:
        """
        Automatically select best figures from available images.

        Args:
            figures: List of all available figures
            max_figures: Maximum number to select

        Returns:
            List of selected figures (sorted by score, descending)
        """
        # Score all figures
        for fig in figures:
            fig.score = self.score_image(fig)

        # Sort by score (descending)
        figures.sort(key=lambda f: f.score, reverse=True)

        # Select top N
        selected = figures[:max_figures]

        logger.info(f"Auto-selected {len(selected)} figures (max: {max_figures})")
        for i, fig in enumerate(selected, 1):
            logger.info(f"  {i}. {fig.filename} (score: {fig.score:.1f})")

        return selected

    def generate_manifest(
        self,
        figures: List[Figure],
        source_type: str = 'web-scraper',
        source_file: str = ''
    ) -> Path:
        """
        Generate figure_manifest.json for user editing.

        Args:
            figures: List of figures to include
            source_type: Type of source ('web-scraper', 'manual', etc.)
            source_file: Path to source data file

        Returns:
            Path to manifest file
        """
        manifest = {
            'version': '1.0',
            'auto_selected': True,
            'figures': [],
            'metadata': {
                'created_date': datetime.now().isoformat(),
                'source_type': source_type,
                'source_file': source_file
            }
        }

        for i, fig in enumerate(figures, 1):
            manifest['figures'].append({
                'id': f'fig{i}',
                'source_path': str(fig.source_path),
                'filename': fig.filename,
                'caption': f'[TODO: Add caption for {fig.filename}]',
                'short_caption': f'Figure {i}',
                'label': f'fig:{fig.filename.split(".")[0][:20]}',
                'width': 0.8,
                'placement': 'htbp',
                'include': True,
                'alt_text': fig.alt_text,
                'url': fig.url,
                'score': round(fig.score, 2),
                'notes': ''
            })

        # Write manifest
        with open(self.manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Figure manifest created: {self.manifest_file}")
        return self.manifest_file

    def load_manifest(self) -> Dict:
        """
        Load figure manifest from JSON file.

        Returns:
            Manifest dictionary

        Raises:
            FileNotFoundError: If manifest doesn't exist
        """
        if not self.manifest_file.exists():
            raise FileNotFoundError(
                f"Figure manifest not found: {self.manifest_file}\n"
                "Generate manifest first with generate_manifest()"
            )

        with open(self.manifest_file, 'r') as f:
            manifest = json.load(f)

        logger.info(f"Loaded manifest with {len(manifest['figures'])} figures")
        return manifest

    def get_selected_figures(self) -> List[Dict]:
        """
        Get figures marked as include=True from manifest.

        Returns:
            List of selected figure dictionaries
        """
        manifest = self.load_manifest()
        selected = [fig for fig in manifest['figures'] if fig.get('include', True)]

        logger.info(f"Selected {len(selected)} figures from manifest")
        return selected

    def copy_figures_to_output(self, figures: List[Dict]) -> None:
        """
        Copy figure files to output directory.

        Args:
            figures: List of figure dictionaries from manifest
        """
        figures_dir = self.output_dir / 'figures'
        figures_dir.mkdir(exist_ok=True)

        for fig in figures:
            source = Path(fig['source_path'])

            if not source.exists():
                logger.warning(f"Source figure not found: {source}")
                continue

            dest = figures_dir / fig['filename']

            try:
                import shutil
                shutil.copy2(source, dest)
                logger.info(f"Copied: {fig['filename']}")
            except Exception as e:
                logger.error(f"Failed to copy {fig['filename']}: {e}")


def main():
    """Test figure manager."""
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )

    if len(sys.argv) < 2:
        print("Usage: python figure_manager.py <images_directory>")
        sys.exit(1)

    images_dir = Path(sys.argv[1])

    fm = FigureManager(output_dir=Path('./test_output'))

    # Scan images
    figures = fm.scan_images([images_dir])

    if not figures:
        print(f"No images found in {images_dir}")
        sys.exit(1)

    # Auto-select
    selected = fm.auto_select_figures(figures, max_figures=5)

    # Generate manifest
    manifest_file = fm.generate_manifest(
        selected,
        source_type='manual',
        source_file=str(images_dir)
    )

    print(f"\nManifest created: {manifest_file}")
    print("Edit the manifest to select figures and add captions.")


if __name__ == '__main__':
    main()
