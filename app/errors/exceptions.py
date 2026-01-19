class AppError(Exception):
    """Base application exception."""

    def __init__(self, message: str, code: str = "APP_ERROR"):
        super().__init__(message)
        self.code = code
