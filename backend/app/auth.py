import time

import jwt

from .errors import Unauthorized


def create_token(user_id, secret, expires_in):
    now = int(time.time())
    return jwt.encode({"sub": str(user_id), "iat": now, "exp": now + expires_in}, secret, algorithm="HS256")


def decode_token(token, secret):
    try:
        return int(jwt.decode(token, secret, algorithms=["HS256"])["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise Unauthorized("Token inválido o expirado")
