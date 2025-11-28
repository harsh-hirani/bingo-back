from django.urls import path

from .views import (
    CreatorRegisterView, 
    CreatorLoginView, 
    PlayerRegisterView, 
    PlayerLoginView, 
    GameCreateView, 
    PlayerGameAssignView, 
    LatestGamesView, 
    PlayerRoundView,
    GetRegisteredPlayersView,
    CreatorGamesView,
    GameLobbyView,
    GameDetailView,
    GameUpdateView,
    GameStatusUpdateView,  
    CreatorRoundView,
    PlayerGameDetailView,
    PlayerDashboardView,
    GamesListView,
    CreatorGamesListView,
    PlayerHistoryView,
)

urlpatterns = [
    path('creator/register/', CreatorRegisterView.as_view(), name='creator-register'),
    path('creator/login/', CreatorLoginView.as_view(), name='creator-login'),
    path('player/register/', PlayerRegisterView.as_view(), name='player-register'),
    path('player/login/', PlayerLoginView.as_view(), name='player-login'),
    path('creator/games/create/', GameCreateView.as_view(), name='create-games'),  
    path('player/games/assign/', PlayerGameAssignView.as_view(), name='assign-games'),
    path('games/listlatest/', LatestGamesView.as_view(), name='list-latest-games'),
    path("game/<int:game_id>/round/<int:round_id>/", PlayerRoundView.as_view(), name="player-round-view"),
    path('creator/actions/getregisteredplayers/', GetRegisteredPlayersView.as_view(), name='get-registered-players'),
    path('creator/games/', CreatorGamesView.as_view(), name='creator-games'),
    path('game/<int:game_id>/lobby/', GameLobbyView.as_view(), name='game-lobby'),
    path('creator/game/<int:game_id>/detail/', GameDetailView.as_view(), name='game-detail'),
    path('creator/game/<int:game_id>/update/', GameUpdateView.as_view(), name='game-update'),
    
    # ✅ Add this
    path('creator/game/<int:game_id>/status/', GameStatusUpdateView.as_view(), name='game-status-update'),
    path('creator/game/<int:game_id>/round/<int:round_id>/', CreatorRoundView.as_view(), name='creator-round-view'),
    path('player/game/<int:game_id>/detail/', PlayerGameDetailView.as_view(), name='player-game-detail'),
    path('player/dashboard/', PlayerDashboardView.as_view(), name='player-dashboard'),
    path('user/games/list/', GamesListView.as_view(), name='games-list'),
    path('creator/games/list/', CreatorGamesListView.as_view(), name='creator-games-list'),
    path('player/history/', PlayerHistoryView.as_view(), name='player-history'),
]