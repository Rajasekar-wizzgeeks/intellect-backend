from fastapi import Request
from fastapi.responses import JSONResponse

from Utils.authentication import Authentication
from Utils.apiException import ApiException



class AuthMiddleware:

    def __init__(self, app):
        self.app = app
        self.auth = Authentication()
        self.exclude_routes = [             
            "/api/user/login",
            "/api/user/create"
        ]

    async def __call__(self, scope, receive, send):

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        path = request.url.path

        if path in self.exclude_routes:
            await self.app(scope, receive, send)
            return

        token = request.headers.get("authorization")

        if not token:
            response = JSONResponse(
                status_code=401,
                content={
                    "message": "Authorization token missing"
                }
            )

            await response(
                scope,
                receive,
                send
            )

            return



        try:
            payload = self.auth.decode_token(token)
            scope["user"] = payload


        except Exception as e:

            response = JSONResponse(
                status_code=401,
                content={
                    "message": "Invalid or expired token"
                }
            )

            await response(
                scope,
                receive,
                send
            )

            return

        await self.app(scope, receive, send)