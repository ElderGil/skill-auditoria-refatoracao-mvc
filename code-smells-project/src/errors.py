"""Erros de aplicação. Não dependem do Flask: models e controllers lançam, o middleware traduz."""


class AppError(Exception):
    status = 400

    def __init__(self, mensagem, status=None):
        super().__init__(mensagem)
        self.mensagem = mensagem
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
