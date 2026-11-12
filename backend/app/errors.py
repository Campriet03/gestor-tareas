class AppError(Exception):
    status = 400
    code = "bad_request"

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class ValidationError(AppError):
    status, code = 400, "validation_error"


class Unauthorized(AppError):
    status, code = 401, "unauthorized"


class Forbidden(AppError):
    status, code = 403, "forbidden"


class NotFound(AppError):
    status, code = 404, "not_found"


class Conflict(AppError):
    status, code = 409, "conflict"
