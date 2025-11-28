class Checker:
    def get_non_empty_numbers(self, ticket):
        return [num for row in ticket for num in row if num not in (0, '', None)]


    def check_full_housie(self, ticket, called):
        nums = self.get_non_empty_numbers(ticket)
        return all(num in called for num in nums)


    def check_any_one_line(self, ticket, called):
        for row in ticket:
            nums = [num for num in row if num not in (0, '', None)]
            if len(nums) > 0 and all(num in called for num in nums):
                return True
        return False


    def check_two_lines(self, ticket, called):
        count = 0
        for row in ticket:
            nums = [num for num in row if num not in (0, '', None)]
            if len(nums) > 0 and all(num in called for num in nums):
                count += 1
        return count >= 2


    def check_early_five(self, ticket, called):
        nums = self.get_non_empty_numbers(ticket)
        matched = [n for n in nums if n in called]
        return len(matched) >= 5


    def check_four_corners(self, ticket, called):
        corners = [ticket[0][0], ticket[0][-1], ticket[-1][0], ticket[-1][-1]]
        corners = [num for num in corners if num not in (0, '', None)]
        return len(corners) == 4 and all(num in called for num in corners)


    def check_t_shape(self, ticket, called):
        col = 4 # 4th column, 0-based
        col_nums = [ticket[i][col] for i in range(3) if ticket[i][col] not in (0, '', None)]
        if len(col_nums) < 2:
            return False
        if ticket[0][4]==0:
            return False
        top_row = [num for num in ticket[0] if num not in (0, '', None)]
        shape_nums = list(set(top_row + col_nums))
        return all(num in called for num in shape_nums)


    def check_cross_plus(self, ticket, called):
        col = 4
        col_nums = [ticket[i][col] for i in range(3) if ticket[i][col] not in (0, '', None)]
        if len(col_nums) < 2 or ticket[1][4]!=0:
            return False
        mid_row = [num for num in ticket[1] if num not in (0, '', None)]
        shape_nums = list(set(mid_row + col_nums))
        return all(num in called for num in shape_nums)


    def check_l_shape(self,ticket, called):
        col = 0
        col_nums = [ticket[i][col] for i in range(3) if ticket[i][col] not in (0, '', None)]
        if len(col_nums) < 2 or ticket[2][0]==0:
            return False
        bottom_row = [num for num in ticket[2] if num not in (0, '', None)]
        shape_nums = list(set(col_nums + bottom_row))
        return all(num in called for num in shape_nums)


    def check_border_shape(self,ticket, called):
        first_col = [ticket[i][0] for i in range(3) if ticket[i][0] not in (0, '', None)]
        last_col = [ticket[i][-1] for i in range(3) if ticket[i][-1] not in (0, '', None)]
        if ticket[1][0]==0 and ticket[1][-1]==0: 
            return False
        top_row = [num for num in ticket[0] if num not in (0, '', None)]
        bottom_row = [num for num in ticket[2] if num not in (0, '', None)]
        shape_nums = list(set(first_col + last_col + top_row + bottom_row))
        return all(num in called for num in shape_nums)


    def check_four_corner_middle(self,ticket, called):
        corners = [ticket[0][0], ticket[0][-1], ticket[-1][0], ticket[-1][-1]]
        corners = [num for num in corners if num not in (0, '', None)]
        middle = ticket[1][4]
        if middle in (0, '', None) or len(corners) < 4:
            return False
        shape_nums = corners + [middle]
        return all(num in called for num in shape_nums)
    def check_patterns(self, ticket, called_numbers, pattern_list):
        results = {}
        pattern_map = {
            "full-housie": self.check_full_housie,
            "any-one-line": self.check_any_one_line,
            "two-lines": self.check_two_lines,
            "early-five": self.check_early_five,
            "four-corners": self.check_four_corners,
            "t-shape": self.check_t_shape,
            "cross-plus": self.check_cross_plus,
            "l-shape": self.check_l_shape,
            "border-shape": self.check_border_shape,
            "four-corner-middle": self.check_four_corner_middle
        }

        for pattern in pattern_list:
            results[pattern] = pattern_map.get(pattern, lambda t, c: False)(ticket, called_numbers)

        return results


   


# Example usage
# Example usage
# ticket = [
#     [5, 9, 72, 22, 32, 40, 56, 70, 88],
#     [2, 12, 19, 28, 38, 48, 59, 72, 1],
#     [3, 10, 18, 25, 37, 45, 60, 80, 90]
# ]

# called_numbers = [5, 9, 72, 22, 32, 40, 56, 70, 88, 3, 10, 18, 25, 37, 45, 60, 80, 90, 1, 2]
# patterns = ["border-shape"]

# checker = Checker()
# result = checker.check_patterns(ticket, called_numbers, patterns)
# print(result)


from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from asgiref.sync import sync_to_async
from core.models import Game, PlayerGame, PlayerTicket, RoundWise

from django.contrib.auth import get_user_model
User = get_user_model()
class GameWinnerHandler:
    def __init__(self):
        self.checker = Checker()

    @sync_to_async
    @transaction.atomic
    def check_and_assign_winners(self, game_id, round_id):
        try:
            game = Game.objects.get(id=game_id)
        except Game.DoesNotExist:
            return {"error": "Game not found"}

        # Extract round data
        prize_rounds = game.prize_rounds
        round_index = int(round_id) - 1
        if round_index >= len(prize_rounds):
            return {"error": "Invalid round"}

        round_data = prize_rounds[round_index]
        called_numbers = round_data.get("called_numbers", [])
        available_patterns = [
            p for p in round_data["patterns"] if not p.get("won", False)
        ]

        # No patterns left
        if not available_patterns:
            return {"message": "No available patterns left"}

        # Players and their tickets
        players = PlayerGame.objects.filter(game_id=game_id)
        player_tickets = PlayerTicket.objects.filter(game_id=game_id, round_id=round_id)

        winners = {}

        # Check each player's tickets
        for player in players:
            player_tix = [
                pt.ticket_data for pt in player_tickets if pt.player_id == player.player_id
            ]

            for pattern in available_patterns:
                pattern_name = pattern["patternName"]
                prize_amount = Decimal(pattern["prizeAmount"])

                for tix in player_tix:
                    result = self.checker.check_patterns(tix, called_numbers, [pattern_name])
                    if result.get(pattern_name):
                        winners.setdefault(pattern["id"], []).append({
                            "player": player.full_name,
                            "pattern": pattern,
                            "amount": prize_amount
                        })

        # Assign winners and update RoundWise
        for pattern_id, winlist in winners.items():
            if not winlist:
                continue

            prize_amount = winlist[0]["amount"]
            per_player = (prize_amount / len(winlist)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            player_objs = []

            for entry in winlist:
                player = entry["player"]
                player.won_amount = player.won_amount + per_player
                player.save()
                player_objs.append(User.objects.get(id=player.player_id))

            # Update Game JSON
            for pat in round_data["patterns"]:
                if pat["id"] == pattern_id:
                    pat["won"] = True
                    pat["wonBy"] = [p.id for p in player_objs]

            # Prevent duplicate round records
            round_entry, created = RoundWise.objects.get_or_create(
                game=game,
                round_id=round_id,
                pattern_id=pattern_id,
                defaults={
                    "patternName": winlist[0]["pattern"]["patternName"],
                    "prize_amount": prize_amount,
                },
            )

            # Add winners (append if already exists)
            round_entry.won_by.add(*player_objs)
            round_entry.save()

        # Save updated JSON
        game.prize_rounds[round_index] = round_data
        game.save()
        print("Winners assigned:", winners)

        return {"message": "Winners updated", "winners": winners}