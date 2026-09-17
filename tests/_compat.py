"""Test helpers for optional runtime dependencies.

These helpers keep the unit tests runnable in environments that do not have
the full production dependency set installed.
"""

from __future__ import annotations

import sys
import types
from importlib.machinery import ModuleSpec


def _install_module(name: str) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__spec__ = ModuleSpec(name, loader=None)
    sys.modules[name] = module
    return module


def ensure_fastapi() -> None:
    if "fastapi" in sys.modules:
        return

    fastapi = _install_module("fastapi")

    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str, headers: dict[str, str] | None = None) -> None:
            self.status_code = status_code
            self.detail = detail
            self.headers = headers

    class FastAPI:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            self.state = types.SimpleNamespace()

        @staticmethod
        def _route(*_args: object, **_kwargs: object):
            return lambda function: function

        on_event = _route
        get = _route
        post = _route
        middleware = _route

    class JSONResponse:
        def __init__(self, status_code: int, content: dict[str, object]) -> None:
            self.status_code = status_code
            self.content = content
            self.headers: dict[str, str] = {}

    class StreamingResponse:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            self.headers: dict[str, str] = {}

    fastapi.FastAPI = FastAPI
    fastapi.HTTPException = HTTPException
    fastapi.Depends = lambda dependency=None: dependency
    fastapi.Request = object
    fastapi.BackgroundTasks = object
    fastapi.status = types.SimpleNamespace(
        HTTP_401_UNAUTHORIZED=401,
        HTTP_403_FORBIDDEN=403,
        HTTP_404_NOT_FOUND=404,
        HTTP_422_UNPROCESSABLE_ENTITY=422,
        HTTP_503_SERVICE_UNAVAILABLE=503,
    )

    responses = _install_module("fastapi.responses")
    responses.JSONResponse = JSONResponse
    responses.StreamingResponse = StreamingResponse

    security = _install_module("fastapi.security")

    class HTTPAuthorizationCredentials:
        def __init__(self, scheme: str, credentials: str) -> None:
            self.scheme = scheme
            self.credentials = credentials

    class HTTPBearer:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

    security.HTTPAuthorizationCredentials = HTTPAuthorizationCredentials
    security.HTTPBearer = HTTPBearer


def ensure_jwt() -> None:
    if "jwt" in sys.modules:
        return

    jwt = _install_module("jwt")
    jwt.InvalidTokenError = ValueError
    jwt.decode = lambda *_args, **_kwargs: {}


def ensure_dotenv() -> None:
    if "dotenv" in sys.modules:
        return

    dotenv = _install_module("dotenv")
    dotenv.load_dotenv = lambda *_args, **_kwargs: False


def ensure_asyncpg() -> None:
    if "asyncpg" in sys.modules:
        return

    asyncpg = _install_module("asyncpg")
    asyncpg.Pool = object
    asyncpg.PostgresError = Exception


def ensure_ollama() -> None:
    if "ollama" in sys.modules:
        return

    ollama = _install_module("ollama")
    ollama.AsyncClient = object
