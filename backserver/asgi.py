"""
ASGI config for backserver project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

# import os

# from django.core.asgi import get_asgi_application

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backserver.settings')

# application = get_asgi_application()
import os
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
from core.middleware.jwt_auth_middleware import JWTAuthMiddleware
import wsapp.routing  # your WebSocket routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backserver.settings")

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket":  JWTAuthMiddleware(
        AuthMiddlewareStack(
            URLRouter(
                wsapp.routing.websocket_urlpatterns
            )
        )
    ),
})
