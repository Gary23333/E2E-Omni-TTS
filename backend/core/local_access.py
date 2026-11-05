"""Local-development access boundary, not a substitute for authentication."""

import ipaddress
from urllib.parse import urlsplit

from starlette.responses import JSONResponse

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
LOCAL_ORIGINS = {
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:8900", "http://127.0.0.1:8900",
}
MAX_REQUEST_BYTES = 12 * 1024 * 1024


class LocalOnlyMiddleware:
    """Reject non-loopback peers, rebinding hosts and foreign browser origins.

    Native local clients may omit Origin. Browser clients must use an explicit
    local origin. Keep this app off reverse proxies/tunnels: local processes are
    trusted and there is no account authentication or authorization layer.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in {"http", "websocket"}:
            return await self.app(scope, receive, send)

        client = scope.get("client")
        try:
            address = ipaddress.ip_address(client[0] if client else "")
            address = getattr(address, "ipv4_mapped", None) or address
            loopback = address.is_loopback
        except ValueError:
            loopback = False

        headers = scope.get("headers", [])
        hosts = [v.decode("latin1") for k, v in headers if k.lower() == b"host"]
        origins = [v.decode("latin1") for k, v in headers if k.lower() == b"origin"]
        valid_host = False
        if len(hosts) == 1:
            try:
                host = urlsplit("//" + hosts[0])
                valid_host = (host.hostname in LOCAL_HOSTS and not host.username
                              and not host.password and not host.path
                              and not host.query and not host.fragment)
                _ = host.port  # Reject malformed ports.
            except ValueError:
                valid_host = False

        if not loopback or not valid_host or len(origins) > 1 or (origins and origins[0] not in LOCAL_ORIGINS):
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008})
            else:
                await JSONResponse({"detail": "Local access only"}, status_code=403)(scope, receive, send)
            return

        if scope["type"] == "http" and scope.get("method") in {"POST", "PUT", "PATCH"}:
            lengths = [v for k, v in headers if k.lower() == b"content-length"]
            try:
                oversized = len(lengths) > 1 or (lengths and (int(lengths[0]) < 0 or int(lengths[0]) > MAX_REQUEST_BYTES))
            except ValueError:
                oversized = True
            if oversized:
                await JSONResponse({"detail": "Request body too large"}, status_code=413)(scope, receive, send)
                return
            # Bound chunked bodies before multipart parsing can spool to disk.
            body = bytearray()
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                if len(body) + len(chunk) > MAX_REQUEST_BYTES:
                    await JSONResponse({"detail": "Request body too large"}, status_code=413)(scope, receive, send)
                    return
                body.extend(chunk)
                if not message.get("more_body", False):
                    break
            delivered = False

            async def bounded_receive():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            return await self.app(scope, bounded_receive, send)

        return await self.app(scope, receive, send)
