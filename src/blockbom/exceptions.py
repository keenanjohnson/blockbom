"""Custom exceptions for blockbom."""

from typing import Optional


class BlockBomError(Exception):
    """Base exception for blockbom."""

    pass


class ParseError(BlockBomError):
    """Error during Mermaid parsing."""

    def __init__(self, message: str, line_number: Optional[int] = None):
        self.line_number = line_number
        if line_number is not None:
            super().__init__(f"Line {line_number}: {message}")
        else:
            super().__init__(message)


class InvalidDiagramError(ParseError):
    """Diagram is not a valid flowchart."""

    pass


class MetadataError(BlockBomError):
    """Error loading or parsing metadata."""

    pass
