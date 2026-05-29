class AppError(Exception):
    pass


class RepositoryError(AppError):
    pass


class NotFoundError(AppError):
    pass


class OllamaError(AppError):
    pass
