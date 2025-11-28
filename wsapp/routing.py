from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(
        r'ws/game/(?P<game_id>\d+)/round/(?P<round_id>\d+)/$',
        consumers.GameConsumer.as_asgi()
    ),
]

# Example URL: ws://<host>/ws/game/1/2/ for game_id=1 and round_id=2

# new ws://localhost:8000/ws/game/1/round/1/?token=<JWT>