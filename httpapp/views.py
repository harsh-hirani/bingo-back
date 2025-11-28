

# Create your views here.
from django.db.models import Sum
from django.utils.timezone import now
# Create your views here.
from django.db import transaction,models
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, permissions
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import CreatorRegistrationSerializer, CreatorLoginSerializer, PlayerRegistrationSerializer, PlayerLoginSerializer,GameSerializer, PlayerGameSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from core.models import PlayerGame, Game, Tickets, PlayerTicket,RoundWise


#  creator
class CreatorRegisterView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = CreatorRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            creator = serializer.save()
            refresh = RefreshToken.for_user(creator)
            return Response({
                "message": "Creator registered successfully",
                "email": creator.email,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "userName": creator.full_name,
                "userId": creator.id
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class CreatorLoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = CreatorLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            refresh = RefreshToken.for_user(user)
            return Response({
                "message": "Login successful",
                "email": user.email,
                "role": user.role,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "userName": user.full_name,
                "userId": user.id
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
# player
class PlayerRegisterView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = PlayerRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            player = serializer.save()
            refresh = RefreshToken.for_user(player)
            return Response({
                "message": "Player registered successfully",
                "email": player.email,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "userName": player.full_name,
                "userId": player.id
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class PlayerLoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = PlayerLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            refresh = RefreshToken.for_user(user)
            return Response({
                "message": "Login successful",
                "email": user.email,
                "role": user.role,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "userName": user.full_name,
                "userId": user.id
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
# game creation
    
class GameCreateView(APIView):
    permission_classes = [IsAuthenticated]  # Only logged-in creators can create
    # Only creators can access this

    def post(self, request):
        if getattr(request.user, 'role', None) != 'creator':
            return Response(
                {'error': 'Only creators can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = GameSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            game = serializer.save()
            return Response({
                "message": "Game created successfully",
                "game_id": game.id,
                "title": game.title,
                "prize_rounds": game.prize_rounds,
                "totalPrizePool": game.total_prize_pool
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# player assignment 
class PlayerGameAssignView(generics.CreateAPIView):
    serializer_class = PlayerGameSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        user = request.user

        # Only players can join
        if getattr(user, 'role', None) != 'player':
            return Response({'error': 'Only players can join games'}, status=status.HTTP_403_FORBIDDEN)

        game_id = request.data.get('game')
        if not game_id:
            return Response({'error': 'game id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            game = Game.objects.get(id=game_id)
        except Game.DoesNotExist:
            return Response({'error': 'Invalid game id'}, status=status.HTTP_404_NOT_FOUND)

        # Prevent duplicate join
        if PlayerGame.objects.filter(game=game, player=user).exists():
            return Response({'error': 'You have already joined this game'}, status=status.HTTP_400_BAD_REQUEST)

        # Create PlayerGame entry
        player_game = PlayerGame.objects.create(game=game, player=user)

        # Get number of rounds from game
        num_rounds = len(game.prize_rounds)

        assigned_tickets = []

        for round_number in range(1, num_rounds + 1):
            # Pick one unused ticket
            ticket = Tickets.objects.filter(used=False).first()
            if not ticket:
                return Response({'error': 'Not enough tickets available for all rounds'}, status=status.HTTP_400_BAD_REQUEST)

            # Mark ticket as used
            ticket.used = True
            ticket.save()

            # Create PlayerTicket for this round
            player_ticket = PlayerTicket.objects.create(
                player=user,
                game=game,
                round_id=round_number,
                ticket_data=ticket.ticket_data
            )
            assigned_tickets.append({
                'round_id': round_number,
                'ticket_data': player_ticket.ticket_data
            })

        # Serialize player game
        serializer = self.get_serializer(player_game)
        response_data = serializer.data
        response_data['assigned_tickets'] = assigned_tickets

        return Response(response_data, status=status.HTTP_201_CREATED)




class LatestGamesView(APIView):
    """
    Returns the latest created games with summarized info.
    """
    def get(self, request):
        # Get games ordered by creation date
        games = Game.objects.order_by('-created_at')[:10]  # latest 10 games

        data = []
        for g in games:
            # Use the state field if available, otherwise calculate
            if hasattr(g, 'state') and g.state:
                status_label = g.state
            else:
                # Fallback calculation
                if g.date_time > now():
                    status_label = "upcoming"
                else:
                    status_label = "completed"

            # Count rounds
            rounds_count = len(g.prize_rounds or [])

            # Get actual player count from PlayerGame relation
            players_count = PlayerGame.objects.filter(game=g).count()

            data.append({
                "id": g.id,
                "title": g.title,
                "dateTime": g.date_time.isoformat(),  # Format datetime properly
                "status": status_label,
                "players": players_count,
                "maxPlayers": g.number_of_users,
                "totalPrize": str(g.total_prize_pool),
                "rounds": rounds_count,
                "organizer": getattr(g.creator, "full_name", "Unknown Organizer"),
                "description": g.description or "",
            })

        return Response(data, status=status.HTTP_200_OK)
class CreatorGamesView(APIView):
    """
    Returns games created by the authenticated creator.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Only creators can access this
        if getattr(user, 'role', None) != 'creator':
            return Response(
                {'error': 'Only creators can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get all games created by this user
        games = Game.objects.filter(creator=user).order_by('-created_at')

        data = []
        for g in games:
            # Use the state field
            status_label = g.state if hasattr(g, 'state') else 'upcoming'

            # Count rounds
            rounds_count = len(g.prize_rounds or [])

            # Get actual player count
            players_count = PlayerGame.objects.filter(game=g).count()

            data.append({
                "id": g.id,
                "title": g.title,
                "dateTime": g.date_time.isoformat(),
                "status": status_label,
                "players": players_count,
                "maxPlayers": g.number_of_users,
                "totalPrize": str(g.total_prize_pool),
                "rounds": rounds_count,
                "organizer": user.full_name,
                "description": g.description or "",
            })

        # Calculate stats
        total_games = len(data)
        total_players = sum(game['players'] for game in data)
        upcoming_games = len([g for g in data if g['status'] == 'upcoming'])
        
        # Calculate total prizes distributed (you might want to track this separately)
        total_prizes = sum(float(game['totalPrize']) for game in data if game['status'] == 'completed')

        return Response({
            "games": data,
            "stats": {
                "totalGames": total_games,
                "totalPlayers": total_players,
                "prizesDistributed": str(total_prizes),
                "upcomingGames": upcoming_games,
            }
        }, status=status.HTTP_200_OK)


class PlayerRoundView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, game_id, round_id):
        user = request.user

        # ✅ 1. Get the player’s ticket
        try:
            ticket = PlayerTicket.objects.get(game_id=game_id, player=user, round_id=round_id)
        except PlayerTicket.DoesNotExist:
            return Response(
                {"error": "Ticket not found for this game."},
                status=status.HTTP_404_NOT_FOUND
            )

        # ✅ 2. Get the game and round details
        try:
            game = Game.objects.get(id=game_id)
        except Game.DoesNotExist:
            return Response({"error": "Game not found."}, status=status.HTTP_404_NOT_FOUND)

        prize_rounds = game.prize_rounds
        round_data = next((r for r in prize_rounds if str(r.get("id")) == str(round_id)), None)

        if not round_data:
            return Response({"error": "Round not found."}, status=status.HTTP_404_NOT_FOUND)

        # ✅ 3. Process pattern details
        patterns_response = []
        for pattern in round_data.get("patterns", []):
            pattern_id = pattern.get("id")
            pattern_name = pattern.get("patternName")
            prize_amount = pattern.get("prizeAmount")
            prize_description = pattern.get("prizeDescription", "")

            # Find winner info in RoundWise
            rw = RoundWise.objects.filter(game_id=game_id, round_id=round_id, pattern_id=pattern_id).first()

            if not rw or rw.won_by.count() == 0:
                status_text = "pending"
                winner_name = None
            else:
                if user in rw.won_by.all():
                    status_text = "won_by_you"
                    winner_name = None
                else:
                    status_text = "won_by_other"
                    winner_name = rw.won_by.first().full_name

            pattern_entry = {
                "id": pattern_id,
                "name": pattern_name,
                "description": prize_description,
                "amount": str(prize_amount),
                "status": status_text,
            }

            if winner_name:
                pattern_entry["winner"] = winner_name

            patterns_response.append(pattern_entry)

        # ✅ 4. Build response
        response_data = {
            "ticketNumbers": ticket.ticket_data,
            "patterns": patterns_response,
            "gameTitle": game.title,
            
        }

        return Response(response_data, status=status.HTTP_200_OK)
    


class GetRegisteredPlayersView(APIView):
    """
    Get all registered players for a specific game.
    Only accessible by creators.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Only creators can access this
        if getattr(user, 'role', None) != 'creator':
            return Response(
                {'error': 'Only creators can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get game_id from query params
        game_id = request.query_params.get('game_id')
        
        if not game_id:
            return Response(
                {'error': 'game_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Check if game exists and belongs to creator
            game = Game.objects.get(id=game_id, creator=user)
        except Game.DoesNotExist:
            return Response(
                {'error': 'Game not found or you do not have permission'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get all players registered for this game
        player_games = PlayerGame.objects.filter(game=game).select_related('player')
        
        # Build response data
        players_data = []
        for pg in player_games:
            player = pg.player
            players_data.append({
                'id': player.id,
                'full_name': player.full_name,
                'email': player.email,
                'mobile_number': player.mobile_number,
                'joined_at': pg.joined_at,
                'won_amount': str(pg.won_amount),
            })
        
        return Response({
            'game_id': game.id,
            'game_title': game.title,
            'total_players': len(players_data),
            'max_players': game.number_of_users,
            'players': players_data
        }, status=status.HTTP_200_OK)    

class GameLobbyView(APIView):
    """
    Get game lobby information including rounds and leaderboard.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, game_id):
        user = request.user
        
        try:
            # Get the game
            game = Game.objects.get(id=game_id)
        except Game.DoesNotExist:
            return Response(
                {'error': 'Game not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if user has access (creator or registered player)
        is_creator = game.creator == user
        is_player = PlayerGame.objects.filter(game=game, player=user).exists()
        
        if not is_creator and not is_player:
            return Response(
                {'error': 'You do not have access to this game'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Game basic info
        game_data = {
            "id": game.id,
            "title": game.title,
            "description": game.description or "",
            "dateTime": game.date_time.isoformat(),
            "organizer": game.creator.full_name,
            "totalPrizePool": str(game.total_prize_pool),
            "totalRounds": len(game.prize_rounds or []),
            "status": game.state if hasattr(game, 'state') else 'upcoming',
            "maxPlayers": game.number_of_users,
            "registeredPlayers": PlayerGame.objects.filter(game=game).count(),
            "isCreator": is_creator,
        }
        
        # Build rounds data from prize_rounds JSON (round summary only)
        rounds_data = []
        prize_rounds = game.prize_rounds or []
        
        for round_data in prize_rounds:
            round_id = round_data.get('id')
            patterns = round_data.get('patterns', [])
            called_numbers = round_data.get('called_numbers', [])
            
            # Calculate total prize for this round
            total_prize = sum(float(p.get('prizeAmount', 0)) for p in patterns)
            
            # Count winners for this round
            winners_count = RoundWise.objects.filter(
                game=game,
                round_id=round_id
            ).aggregate(
                total_winners=models.Count('won_by', distinct=True)
            )['total_winners'] or 0
            
            rounds_data.append({
                "id": round_id,
                "number": round_id,
                "totalPatterns": len(patterns),
                "totalPrize": str(total_prize),
                "calledNumbers": len(called_numbers),
                "winnersCount": winners_count,
            })
        
        # Build leaderboard from RoundWise
        leaderboard_data = []
        round_wise_entries = RoundWise.objects.filter(game=game).prefetch_related('won_by')
        
        for rw in round_wise_entries:
            if rw.won_by.exists():
                for winner in rw.won_by.all():
                    leaderboard_data.append({
                        "id": f"{rw.id}-{winner.id}",
                        "name": winner.full_name,
                        "email": winner.email,
                        "prize": str(rw.prize_amount),
                        "round": f"Round {rw.round_id} - {rw.patternName}",
                        "roundId": rw.round_id,
                        "patternName": rw.patternName,
                    })
        
        # Sort leaderboard by prize amount (highest first)
        leaderboard_data.sort(key=lambda x: float(x['prize']), reverse=True)
        
        return Response({
            "game": game_data,
            "rounds": rounds_data,
            "leaderboard": leaderboard_data,
        }, status=status.HTTP_200_OK)

class GameDetailView(APIView):
    """
    Get game details for editing.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, game_id):
        user = request.user
        
        # Only creators can access this
        if getattr(user, 'role', None) != 'creator':
            return Response(
                {'error': 'Only creators can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Check if game exists and belongs to creator
            game = Game.objects.get(id=game_id, creator=user)
        except Game.DoesNotExist:
            return Response(
                {'error': 'Game not found or you do not have permission'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Return game data
        return Response({
            'id': game.id,
            'title': game.title,
            'description': game.description or '',
            'numberOfUsers': game.number_of_users,
            'dateTime': game.date_time.strftime('%Y-%m-%dT%H:%M'),  # Format for datetime-local input
            'totalPrizePool': str(game.total_prize_pool),
            'prizeRounds': game.prize_rounds or [],
        }, status=status.HTTP_200_OK)


class GameUpdateView(APIView):
    """
    Update game details.
    """
    permission_classes = [IsAuthenticated]

    def put(self, request, game_id):
        user = request.user
        
        # Only creators can update
        if getattr(user, 'role', None) != 'creator':
            return Response(
                {'error': 'Only creators can update games'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        
        try:
            # Check if game exists and belongs to creator
            game = Game.objects.get(id=game_id, creator=user)
        except Game.DoesNotExist:
            return Response(
                {'error': 'Game not found or you do not have permission'},
                status=status.HTTP_404_NOT_FOUND
            )
        if game.state != "upcoming":
            return Response(
                {'error':"Game can not be edited after it is started..."},
                status=status.HTTP_403_FORBIDDEN
            )
        # Get data from request
        title = request.data.get('title')
        description = request.data.get('description', '')
        number_of_users = request.data.get('number_of_users')
        total_prize_pool = request.data.get('total_prize_pool')
        date_time = request.data.get('date_time')
        prize_rounds = request.data.get('prize_rounds', [])
        
        # Validate required fields
        if not title:
            return Response({'error': 'Title is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not number_of_users:
            return Response({'error': 'Number of users is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not date_time:
            return Response({'error': 'Date and time is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update game
        game.title = title
        game.description = description
        game.number_of_users = int(number_of_users)
        game.total_prize_pool = float(total_prize_pool)
        game.date_time = date_time
        game.prize_rounds = prize_rounds
        game.save()
        
        return Response({
            'message': 'Game updated successfully',
            'game_id': game.id,
            'title': game.title,
        }, status=status.HTTP_200_OK)

class GameStatusUpdateView(APIView):
    """
    Update game status (start, pause, complete).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, game_id):
        user = request.user
        
        # Only creators can update game status
        if getattr(user, 'role', None) != 'creator':
            return Response(
                {'error': 'Only creators can update game status'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Check if game exists and belongs to creator
            game = Game.objects.get(id=game_id, creator=user)
        except Game.DoesNotExist:
            return Response(
                {'error': 'Game not found or you do not have permission'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get new status from request
        new_status = request.data.get('status')
        
        # Validate status
        valid_statuses = ['upcoming', 'ongoing', 'paused', 'completed']
        if new_status not in valid_statuses:
            return Response(
                {'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update game status
        old_status = game.state
        game.state = new_status
        game.save()
        
        return Response({
            'message': 'Game status updated successfully',
            'game_id': game.id,
            'old_status': old_status,
            'new_status': new_status,
        }, status=status.HTTP_200_OK)

class CreatorRoundView(APIView):
    """
    Get round details for creator with pattern winners.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, game_id, round_id):
        user = request.user
        
        # Only creators can access this
        if getattr(user, 'role', None) != 'creator':
            return Response(
                {'error': 'Only creators can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Check if game exists and belongs to creator
            game = Game.objects.get(id=game_id, creator=user)
        except Game.DoesNotExist:
            return Response(
                {'error': 'Game not found or you do not have permission'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        prize_rounds = game.prize_rounds or []
        round_data = next((r for r in prize_rounds if str(r.get("id")) == str(round_id)), None)

        if not round_data:
            return Response({"error": "Round not found."}, status=status.HTTP_404_NOT_FOUND)

        # Get called numbers from round data
        called_numbers = round_data.get("called_numbers", [])
        
        # Get patterns for this round
        patterns = round_data.get("patterns", [])
        
        # Build patterns with winners
        patterns_response = []
        for pattern in patterns:
            pattern_id = pattern.get('id')
            pattern_name = pattern.get('patternName')
            prize_amount = pattern.get('prizeAmount')
            prize_description = pattern.get('prizeDescription', '')
            
            # Find winners for this pattern
            round_wise = RoundWise.objects.filter(
                game=game,
                round_id=round_id,
                pattern_id=pattern_id
            ).prefetch_related('won_by').first()
            
            winners = []
            if round_wise and round_wise.won_by.exists():
                for winner in round_wise.won_by.all():
                    winners.append({
                        'id': winner.id,
                        'name': winner.full_name,
                        'email': winner.email,
                    })
            
            patterns_response.append({
                'id': pattern_id,
                'name': pattern_name,
                'description': prize_description,
                'amount': str(prize_amount),
                'winners': winners,
                'hasWinners': len(winners) > 0,
            })
        
        return Response({
            'roundId': round_id,
            'roundNumber': round_id,
            'gameTitle': game.title,
            'calledNumbers': called_numbers,
            'currentNumber': called_numbers[-1] if called_numbers else None,
            'patterns': patterns_response,
        }, status=status.HTTP_200_OK)
        
        
class PlayerGameDetailView(APIView):
    """
    Get game details for players (public game info).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, game_id):
        user = request.user
        
        # Only players can access this
        if getattr(user, 'role', None) != 'player':
            return Response(
                {'error': 'Only players can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            game = Game.objects.get(id=game_id)
        except Game.DoesNotExist:
            return Response(
                {'error': 'Game not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if player already joined
        has_joined = PlayerGame.objects.filter(game=game, player=user).exists()
        
        # Get registered players count
        registered_players = PlayerGame.objects.filter(game=game).count()
        
        # Build rounds info
        rounds_info = []
        prize_rounds = game.prize_rounds or []
        for round_data in prize_rounds:
            patterns = round_data.get('patterns', [])
            total_prize = sum(float(p.get('prizeAmount', 0)) for p in patterns)
            
            rounds_info.append({
                'id': round_data.get('id'),
                'number': round_data.get('id'),
                'totalPatterns': len(patterns),
                'totalPrize': str(total_prize),
                'patterns': [
                    {
                        'name': p.get('patternName'),
                        'description': p.get('prizeDescription', ''),
                        'amount': str(p.get('prizeAmount', 0)),
                    }
                    for p in patterns
                ]
            })
        
        return Response({
            'id': game.id,
            'title': game.title,
            'description': game.description or '',
            'dateTime': game.date_time.isoformat(),
            'organizer': game.creator.full_name,
            'status': game.state if hasattr(game, 'state') else 'upcoming',
            'totalPrizePool': str(game.total_prize_pool),
            'maxPlayers': game.number_of_users,
            'registeredPlayers': registered_players,
            'totalRounds': len(prize_rounds),
            'rounds': rounds_info,
            'hasJoined': has_joined,
            'canJoin': not has_joined and registered_players < game.number_of_users,
        }, status=status.HTTP_200_OK)
        
class PlayerDashboardView(APIView):
    """
    Get player dashboard statistics and games.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Only players can access this
        if getattr(user, 'role', None) != 'player':
            return Response(
                {'error': 'Only players can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get all games player has joined
        player_games = PlayerGame.objects.filter(player=user).select_related('game')
        
        # Calculate stats
        total_games_played = player_games.count()
        total_winnings = player_games.aggregate(
            total=Sum('won_amount')
        )['total'] or 0
        
        # Get games won (where won_amount > 0)
        games_won = player_games.filter(won_amount__gt=0).count()
        win_rate = (games_won / total_games_played * 100) if total_games_played > 0 else 0
        
        # Get upcoming games (games joined but not completed)
        upcoming_games = Game.objects.filter(
            player_games__player=user,
            state='upcoming'
        ).count()
        
        # Get next game datetime
        next_game = Game.objects.filter(
            player_games__player=user,
            state='upcoming',
            date_time__gt=now()
        ).order_by('date_time').first()
        
        # Get player's games list
        games_list = []
        for pg in player_games.select_related('game').order_by('-joined_at')[:10]:
            game = pg.game
            games_list.append({
                'id': game.id,
                'title': game.title,
                'dateTime': game.date_time.isoformat(),
                'status': game.state if hasattr(game, 'state') else 'upcoming',
                'players': PlayerGame.objects.filter(game=game).count(),
                'maxPlayers': game.number_of_users,
                'totalPrize': str(game.total_prize_pool),
                'rounds': len(game.prize_rounds or []),
                'organizer': game.creator.full_name,
                'wonAmount': str(pg.won_amount),
                'hasJoined': True,
            })
        
        return Response({
            'stats': {
                'gamesPlayed': total_games_played,
                'totalWinnings': str(total_winnings),
                'winRate': round(win_rate, 1),
                'upcomingGames': upcoming_games,
                'nextGameTime': next_game.date_time.isoformat() if next_game else None,
            },
            'games': games_list,
        }, status=status.HTTP_200_OK)
        
        
        
        
        
        
        
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q

class GamesListView(APIView):
    """
    Get all games with pagination and search.
    """
    permission_classes = [AllowAny]  # Public endpoint

    def get(self, request):
        # Get query parameters
        page = request.GET.get('page', 1)
        search = request.GET.get('search', '')
        status_filter = request.GET.get('status', '')  # Filter by status
        
        # Base queryset
        games = Game.objects.all().select_related('creator').order_by('-created_at')
        
        # Apply search filter
        if search:
            games = games.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(creator__full_name__icontains=search)
            )
        
        # Apply status filter
        if status_filter and hasattr(Game, 'state'):  # ✅ Fixed condition
            games = games.filter(state=status_filter)
        
        # Paginate (10 per page)
        paginator = Paginator(games, 10)
        
        try:
            paginated_games = paginator.page(page)
        except EmptyPage:
            paginated_games = paginator.page(paginator.num_pages)
        
        # Build response data
        games_data = []
        for game in paginated_games:
            # Get player count
            players_count = PlayerGame.objects.filter(game=game).count()
            
            # Count rounds
            rounds_count = len(game.prize_rounds or [])
            
            games_data.append({
                'id': game.id,
                'title': game.title,
                'description': game.description or '',
                'dateTime': game.date_time.isoformat(),
                'organizer': game.creator.full_name,
                'organizerEmail': game.creator.email,
                'status': game.state if hasattr(game, 'state') else 'upcoming',
                'players': players_count,
                'maxPlayers': game.number_of_users,
                'totalPrize': str(game.total_prize_pool),
                'rounds': rounds_count,
            })
        
        return Response({
            'games': games_data,
            'pagination': {
                'currentPage': paginated_games.number,
                'totalPages': paginator.num_pages,
                'totalGames': paginator.count,
                'hasNext': paginated_games.has_next(),
                'hasPrevious': paginated_games.has_previous(),
            }
        }, status=status.HTTP_200_OK)
        
        
        

class CreatorGamesListView(APIView):
    """
    creator - Get all games with pagination and search.
    """
    permission_classes = [IsAuthenticated]  # Only authenticated users can access this

    def get(self, request):
        # Get query parameters
        # Only creators can access this
        if getattr(request.user, 'role', None) != 'creator':
            return Response(
                {'error': 'Only creators can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        page = request.GET.get('page', 1)
        search = request.GET.get('search', '')
        status_filter = request.GET.get('status', '')  # Filter by status
        
        # Base queryset
        games = Game.objects.filter(creator=request.user).select_related('creator').order_by('-created_at')
        
        # Apply search filter
        if search:
            games = games.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(creator__full_name__icontains=search)
            )
        
        # Apply status filter
        if status_filter and hasattr(Game, 'state'):  # ✅ Fixed condition
            games = games.filter(state=status_filter)
        
        # Paginate (10 per page)
        paginator = Paginator(games, 10)
        
        try:
            paginated_games = paginator.page(page)
        except EmptyPage:
            paginated_games = paginator.page(paginator.num_pages)
        
        # Build response data
        games_data = []
        for game in paginated_games:
            # Get player count
            players_count = PlayerGame.objects.filter(game=game).count()
            
            # Count rounds
            rounds_count = len(game.prize_rounds or [])
            
            games_data.append({
                'id': game.id,
                'title': game.title,
                'description': game.description or '',
                'dateTime': game.date_time.isoformat(),
                'organizer': game.creator.full_name,
                'organizerEmail': game.creator.email,
                'status': game.state if hasattr(game, 'state') else 'upcoming',
                'players': players_count,
                'maxPlayers': game.number_of_users,
                'totalPrize': str(game.total_prize_pool),
                'rounds': rounds_count,
            })
        
        return Response({
            'games': games_data,
            'pagination': {
                'currentPage': paginated_games.number,
                'totalPages': paginator.num_pages,
                'totalGames': paginator.count,
                'hasNext': paginated_games.has_next(),
                'hasPrevious': paginated_games.has_previous(),
            }
        }, status=status.HTTP_200_OK)
        
        
        


class PlayerHistoryView(APIView):
    """
    Get player's game history with pagination and search.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Only players can access this
        if getattr(user, 'role', None) != 'player':
            return Response(
                {'error': 'Only players can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get query parameters
        page = request.GET.get('page', 1)
        search = request.GET.get('search', '')
        status_filter = request.GET.get('status', '')
        
        # Get all games player has joined
        player_games = PlayerGame.objects.filter(
            player=user
        ).select_related('game', 'game__creator').order_by('-joined_at')
        
        # Apply search filter
        if search:
            player_games = player_games.filter(
                Q(game__title__icontains=search) |
                Q(game__creator__full_name__icontains=search)
            )
        
        # Apply status filter
        if status_filter:
            player_games = player_games.filter(game__state=status_filter)
        
        # Paginate (10 per page)
        paginator = Paginator(player_games, 10)
        
        try:
            paginated_games = paginator.page(page)
        except EmptyPage:
            paginated_games = paginator.page(paginator.num_pages)
        
        # Build response data
        games_data = []
        for pg in paginated_games:
            game = pg.game
            
            games_data.append({
                'id': game.id,
                'title': game.title,
                'organizer': game.creator.full_name,
                'dateTime': game.date_time.isoformat(),
                'status': game.state if hasattr(game, 'state') else 'upcoming',
                'prizeWon': str(pg.won_amount),
                'totalPrize': str(game.total_prize_pool),
                'joinedAt': pg.joined_at.isoformat(),
                'rounds': len(game.prize_rounds or []),
            })
        
        return Response({
            'games': games_data,
            'pagination': {
                'currentPage': paginated_games.number,
                'totalPages': paginator.num_pages,
                'totalGames': paginator.count,
                'hasNext': paginated_games.has_next(),
                'hasPrevious': paginated_games.has_previous(),
            }
        }, status=status.HTTP_200_OK)
        
        
        
        
        