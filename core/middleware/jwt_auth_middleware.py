from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import get_user_model

User = get_user_model()


@database_sync_to_async
def get_user(validated_token):
    """
    Return user from a validated JWT token.
    """
    try:
        user_id = validated_token.get("user_id")
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()


class JWTAuthMiddleware:
    """
    Custom middleware for JWT authentication in WebSockets.
    Token should be provided as:
        ws://localhost:8000/ws/game/1/round/1/?token=<JWT>
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)
        token = query_params.get("token", [None])[0]

        if token:
            try:
                validated_token = UntypedToken(token)
                jwt_auth = JWTAuthentication()
                user = await get_user(validated_token)
                scope["user"] = user
            except (InvalidToken, TokenError):
                scope["user"] = AnonymousUser()
        else:
            scope["user"] = AnonymousUser()

        return await self.inner(scope, receive, send)
