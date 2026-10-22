"""Exception hierarchy of the package."""


class LookbookError(Exception):
    """Base class for every error the CLI reports without a traceback."""


class ContentError(LookbookError):
    """The content files are missing, malformed or reference missing assets."""


class LayoutError(LookbookError):
    """The content does not fit the page it is assigned to."""
