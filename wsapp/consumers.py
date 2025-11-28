import json
import random
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from core.models import Game, RoundWise
from core.ops import GameWinnerHandler

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Join game+round specific room"""
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.round_id = self.scope['url_route']['kwargs']['round_id']
        self.room_group_name = f'game_{self.game_id}_round_{self.round_id}'

        # Only accept if user is authenticated
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Optional: send welcome
        await self.send(text_data=json.dumps({
            "message": f"Connected to Game {self.game_id}, Round {self.round_id}",
            "role": getattr(user, "role", "unknown")
        }))

    async def disconnect(self, close_code):
        """Leave the game+round group"""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Handle actions from WebSocket client"""
        try:
            text_data_json = json.loads(text_data)
            action = text_data_json.get("action")

            user = self.scope["user"]

            if action == "generate_number":
                # 🔒 Only creator can generate numbers
                if getattr(user, "role", None) != "creator":
                    await self.send(json.dumps({"error": "Only creator can generate numbers"}))
                    return

                result = await self.generate_number()
                if result['r']:
                    # Broadcast new number to all players in the same room
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            "type": "number_generated",
                            "number": result["number"],
                            "called_numbers": result["called_numbers"],
                        },
                    )
                    
                    # ✅ Check winners right after number generation
                    handler = GameWinnerHandler()
                    winner_result = await handler.check_and_assign_winners(self.game_id, self.round_id)
                    
                    # ✅ If someone won, broadcast to all players
                    if "winners" in winner_result and winner_result["winners"]:
                        # 🔥 AWAIT the coroutine here!
                        broadcast_payload = await self._prepare_winner_payload(winner_result)
                        await self.channel_layer.group_send(
                            self.room_group_name,
                            {
                                "type": "winner_announced",
                                "winners": broadcast_payload
                            }
                        )
                else:
                    if result['number'] == -1:
                        await self.send(json.dumps({"error": "Game is not ongoing"}))
                    elif result['number'] == -2:
                        await self.send(json.dumps({"error": "All numbers already called"}))
                    elif result['number'] == -3:
                        await self.send(json.dumps({"error": "Invalid round"}))

            elif action == "get_called_numbers":
                # Player or creator can request current state
                called_numbers = await self.get_called_numbers()
                await self.send(json.dumps({
                    "called_numbers": called_numbers
                }))

            elif action == "check_winners":
                """
                Return all winners of the current game across all rounds.
                """
                # Fetch all RoundWise entries for this game
                all_rounds = await database_sync_to_async(
                    lambda: list(RoundWise.objects.filter(game_id=self.game_id).prefetch_related('won_by'))
                )()

                all_winners_payload = []

                for round_entry in all_rounds:
                    winners_list = []
                    for user in round_entry.won_by.all():
                        user_name = await database_sync_to_async(lambda: getattr(user, "full_name", str(user)))()
                        winners_list.append({
                            "player_id": user.id,
                            "player_name": user_name
                        })

                    all_winners_payload.append({
                        "round_id": round_entry.round_id,
                        "pattern_id": round_entry.pattern_id,
                        "pattern_name": getattr(round_entry, "patternName", ""),
                        "prize_amount": str(getattr(round_entry, "prize_amount", "0.00")),
                        "winners": winners_list
                    })

                # Send all winners to requesting client
                await self.send(text_data=json.dumps({
                    "message": "All winners fetched",
                    "all_winners": all_winners_payload
                }))

        except json.JSONDecodeError:
            await self.send(json.dumps({"error": "Invalid JSON"}))
        except Exception as e:
            await self.send(json.dumps({"error": str(e)}))

    async def number_generated(self, event):
        """Send updated number and list to all group members"""
        await self.send(text_data=json.dumps({
            "number": event["number"],
            "called_numbers": event["called_numbers"],
        }))

    async def winner_announced(self, event):
        """Broadcast winner announcement to all players"""
        await self.send(text_data=json.dumps({
            "winners": event["winners"]
        }))

    # -----------------------
    # Utility functions
    # -----------------------

    @database_sync_to_async
    def get_game(self):
        try:
            return Game.objects.get(id=self.game_id)
        except Game.DoesNotExist:
            return None

    async def generate_number(self):
        """Generate a random number 1–90 that is not already called"""
        game = await self.get_game()
        if not game:
            return {'r':False,"number": -1 }  # Game not found
        if game.state != 'ongoing':
            return {'r':False,"number": -2 }  # Game not ongoing

        prize_rounds = game.prize_rounds
        round_index = int(self.round_id) - 1
        if round_index < 0 or round_index >= len(prize_rounds):
            return {'r':False,"number": -3 }  # Invalid round

        round_data = prize_rounds[round_index]
        called_numbers = round_data.get("called_numbers", [])

        available_numbers = [n for n in range(1, 91) if n not in called_numbers]
        if not available_numbers:
            return None

        number = random.choice(available_numbers)
        called_numbers.append(number)
        round_data["called_numbers"] = called_numbers
        prize_rounds[round_index] = round_data

        # Save to DB
        game.prize_rounds = prize_rounds
        await database_sync_to_async(game.save)()

        return {'r':True,"number": number, "called_numbers": called_numbers}

    async def get_called_numbers(self):
        """Fetch existing called numbers without generating new one"""
        game = await self.get_game()
        if not game:
            return []

        prize_rounds = game.prize_rounds
        round_index = int(self.round_id) - 1
        if round_index < 0 or round_index >= len(prize_rounds):
            return []

        return prize_rounds[round_index].get("called_numbers", [])

    async def _prepare_winner_payload(self, winner_result):
        """
        Convert backend winner data into clean frontend payload.
        Fully async-safe.
        """
        winners_payload = []

        for pattern_id, winlist in winner_result["winners"].items():
            if not winlist:
                continue

            pattern_name = winlist[0]["pattern"]["patternName"]

            winners_data = []
            for entry in winlist:
                player_obj = entry["player"]

                # Async-safe access to player name
                player_name = await database_sync_to_async(
                    lambda: getattr(player_obj, "full_name", str(player_obj))
                )()

                winners_data.append({
                    "player_id": player_obj.id,
                    "player_name": player_name,
                    "amount": str(entry["amount"])
                })

            winners_payload.append({
                "pattern_id": pattern_id,
                "pattern_name": pattern_name,
                "winners": winners_data
            })

        return winners_payload