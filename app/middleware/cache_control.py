"""ASGI middleware that sets Cache-Control: no-cache on HTML responses.

Hermes browser verification mandates that every HTML document carries a real
HTTP ``Cache-Control: no-cache`` response header — ``<meta>`` tags are not
sufficient.  This middleware applies the header to all ``text/html`` responses.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class CacheControlMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        return response
