"""Bounded failure types for report retrieval."""


class RetrievalError(Exception):
    """Base class for retrieval failures that must not look like success."""


class InvalidPdf(RetrievalError):
    pass


class PartialDownload(RetrievalError):
    pass


class BlockedAccess(RetrievalError):
    pass


class DisallowedRedirect(RetrievalError):
    pass


class UnsafeDestination(RetrievalError):
    pass


class DownloadFailed(RetrievalError):
    pass
