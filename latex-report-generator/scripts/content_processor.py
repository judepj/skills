"""
Content Processor

Convert bullet-point content to flowing academic paragraphs.
"""

from typing import List, Dict
import re
import logging

logger = logging.getLogger(__name__)


# Transition word database
TRANSITIONS = {
    'addition': ['Moreover', 'Furthermore', 'Additionally', 'In addition'],
    'contrast': ['However', 'In contrast', 'Conversely', 'Nevertheless'],
    'example': ['For instance', 'For example', 'Specifically'],
    'sequence': ['Subsequently', 'Following this', 'Next'],
    'conclusion': ['Therefore', 'Thus', 'Consequently']
}


class ContentProcessor:
    """Convert structured content to academic prose."""

    def __init__(self, max_bullets_per_paragraph: int = 4):
        """
        Initialize content processor.

        Args:
            max_bullets_per_paragraph: Maximum bullets to combine into one paragraph
        """
        self.max_bullets = max_bullets_per_paragraph

    def bullets_to_paragraphs(
        self,
        content: str,
        section_name: str = ''
    ) -> str:
        """
        Convert bullet points to flowing paragraphs.

        Args:
            content: Content with bullet points
            section_name: Section name for context

        Returns:
            Content with paragraphs instead of bullets

        Example:
            Input:
                - CRISPR delivery investigated
                - AAV vectors: 65-85% efficiency
                - LNPs: 40-60% efficiency

            Output:
                Multiple delivery approaches have been investigated. Viral
                vectors (AAV) demonstrated efficiency of 65-85%. In contrast,
                lipid nanoparticles showed 40-60% efficiency.
        """
        # Simple implementation: detect bullet lists and convert
        lines = content.split('\n')

        result = []
        current_bullets = []

        for line in lines:
            line = line.strip()

            # Check if line is a bullet
            if line.startswith(('-', '*', '•')):
                # Remove bullet marker
                bullet_text = re.sub(r'^[-*•]\s+', '', line)
                current_bullets.append(bullet_text)

            elif current_bullets and line:
                # End of bullet list, convert to paragraph
                paragraph = self._bullets_to_paragraph(current_bullets)
                result.append(paragraph)
                current_bullets = []
                result.append(line)  # Add non-bullet line

            elif line:
                result.append(line)

        # Handle remaining bullets
        if current_bullets:
            paragraph = self._bullets_to_paragraph(current_bullets)
            result.append(paragraph)

        return '\n\n'.join(result)

    def _bullets_to_paragraph(self, bullets: List[str]) -> str:
        """
        Convert list of bullet points to a single paragraph.

        Args:
            bullets: List of bullet point texts

        Returns:
            Flowing paragraph
        """
        if not bullets:
            return ''

        if len(bullets) == 1:
            # Single bullet becomes single sentence
            return self._ensure_sentence(bullets[0])

        # Multiple bullets: combine with transitions
        sentences = []

        for i, bullet in enumerate(bullets):
            sentence = self._ensure_sentence(bullet)

            # Add transition word occasionally (not every sentence)
            if i > 0 and i % 2 == 0 and len(bullets) > 2:
                transition = self._get_transition(i, len(bullets))
                sentence = f"{transition}, {sentence[0].lower()}{sentence[1:]}"

            sentences.append(sentence)

        return ' '.join(sentences)

    def _ensure_sentence(self, text: str) -> str:
        """
        Ensure text is a complete sentence.

        Args:
            text: Text to check

        Returns:
            Complete sentence with capital first letter and period
        """
        text = text.strip()

        if not text:
            return text

        # Capitalize first letter
        text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()

        # Add period if missing
        if not text.endswith(('.', '!', '?', ':')):
            text += '.'

        return text

    def _get_transition(self, index: int, total: int) -> str:
        """
        Get appropriate transition word.

        Args:
            index: Current sentence index
            total: Total number of sentences

        Returns:
            Transition word
        """
        import random

        # Choose transition type based on position
        if index < total - 1:
            if random.random() < 0.5:
                return random.choice(TRANSITIONS['addition'])
            else:
                return random.choice(TRANSITIONS['contrast'])
        else:
            return random.choice(TRANSITIONS['conclusion'])

    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text.

        Args:
            text: Text to clean

        Returns:
            Cleaned text
        """
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove multiple line breaks
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()


def main():
    """Test content processor."""
    processor = ContentProcessor()

    # Test input
    test_content = """
Introduction

The following findings were observed:
- CRISPR delivery methods were investigated
- AAV vectors showed 65-85% efficiency
- Lipid nanoparticles demonstrated 40-60% efficiency with better safety
- Immunogenicity concerns arose with viral vectors

These results are significant.
    """

    print("Input:")
    print("=" * 60)
    print(test_content)

    result = processor.bullets_to_paragraphs(test_content)

    print("\n\nOutput:")
    print("=" * 60)
    print(result)


if __name__ == '__main__':
    main()
