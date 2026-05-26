class DomainError(Exception):
    """Base exception for domain-level failures."""


class InvalidTextRegionError(DomainError):
    """Raised when a text region is invalid for capture."""


class EmptyExtractedTextError(DomainError):
    """Raised when extracted text is unexpectedly empty."""


class TranslationFailedError(DomainError):
    """Raised when translation cannot be produced."""


class CacheMissError(DomainError):
    """Raised when required cache entry is not found."""


class GameProfileNotFoundError(DomainError):
    """Raised when a requested game profile does not exist."""
