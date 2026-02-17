"""Custom exceptions for Scholar Tracker."""


class ScholarTrackerError(Exception):
    """Base exception for Scholar Tracker."""
    pass


class ConfigurationError(ScholarTrackerError):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class DataFetchError(ScholarTrackerError):
    """Raised when fetching data from Google Scholar fails."""

    def __init__(self, message: str, status_code: int = None, retryable: bool = True):
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        super().__init__(self.message)


class DataValidationError(ScholarTrackerError):
    """Raised when fetched data fails validation."""

    def __init__(self, message: str, field: str = None, value: any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(self.message)


class RateLimitError(DataFetchError):
    """Raised when rate limited by Google Scholar."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429, retryable=True)


class AuthorNotFoundError(DataFetchError):
    """Raised when author profile is not found."""

    def __init__(self, author_id: str = None, author_query: str = None):
        if author_id:
            message = f"Author not found with ID: {author_id}"
        elif author_query:
            message = f"Author not found with query: {author_query}"
        else:
            message = "Author not found"
        super().__init__(message, status_code=404, retryable=False)


class ScraperAPIError(DataFetchError):
    """Raised when ScraperAPI request fails."""

    def __init__(self, message: str, status_code: int = None):
        super().__init__(message, status_code=status_code, retryable=True)


class FileIOError(ScholarTrackerError):
    """Raised when file operations fail."""

    def __init__(self, message: str, filepath: str = None):
        self.message = message
        self.filepath = filepath
        super().__init__(self.message)
