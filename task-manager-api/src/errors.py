class AppError(Exception):
    """Erro de aplicação: vira {"error": message} com o status da classe."""

    status = 400

    def __init__(self, message, status=None):
        super().__init__(message)
        self.message = message
        if status:
            self.status = status


class ValidationError(AppError):
    status = 400


class UnauthorizedError(AppError):
    status = 401


class ForbiddenError(AppError):
    status = 403


class NotFoundError(AppError):
    status = 404


class ConflictError(AppError):
    status = 409
