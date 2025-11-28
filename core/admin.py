from django.contrib import admin

# Register your models here.
from .models import Game, PlayerGame, PlayerTicket, RoundWise, Tickets

admin.site.register(Game)
admin.site.register(PlayerGame)
admin.site.register(PlayerTicket)
admin.site.register(RoundWise)
admin.site.register(Tickets)