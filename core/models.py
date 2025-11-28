from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.conf import settings

class CreatorManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email must be provided')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'creator')  # superuser default role
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('player', 'Player'),
        ('creator', 'Creator'),
    )

    full_name = models.CharField(max_length=255)
    company = models.CharField(max_length=255, blank=True, null=True)
    pan_number = models.CharField(max_length=10, blank=True, null=True)
    aadhaar_number = models.CharField(max_length=12, blank=True, null=True)
    address_line = models.TextField(blank=True, null=True)
    postal_code = models.CharField(max_length=10, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    mobile_number = models.CharField(max_length=15)

    email = models.EmailField(unique=True)
    date_joined = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='player')

    # override PermissionsMixin defaults to avoid conflicts
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='creator_set',
        blank=True,
        help_text='The groups this user belongs to.',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='creator_permissions_set',
        blank=True,
        help_text='Specific permissions for this user.',
    )

    objects = CreatorManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'mobile_number']

    def __str__(self):
        return f"{self.email} ({self.role})"

class Game(models.Model):
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('ongoing', 'Ongoing'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
    ]
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='games'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    number_of_users = models.PositiveIntegerField()
    total_prize_pool = models.DecimalField(max_digits=10, decimal_places=2)
    date_time = models.DateTimeField()
    state = models.CharField(max_length=50, choices=STATUS_CHOICES, default='upcoming')
    # Store all rounds and patterns
    prize_rounds = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} (by {self.creator.email})"

# relations
class PlayerGame(models.Model):
    player = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='player_games'
    )
    game = models.ForeignKey(
        'Game',
        on_delete=models.CASCADE,
        related_name='player_games'
    )
    won_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('player', 'game')  # prevents duplicate entries per player-game pair

    def __str__(self):
        return f"{self.player.email} in {self.game.title} - Won: {self.won_amount}"
# with pattern entries for winners



class RoundWise(models.Model):
    game = models.ForeignKey(
        'Game',
        on_delete=models.CASCADE,
        related_name='rounds_wise'
    )
    round_id = models.PositiveIntegerField()
    pattern_id = models.CharField(max_length=100)
    patternName = models.CharField(max_length=100)  # ✅ new field
    prize_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # ✅ new field

    won_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='won_rounds',
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('game', 'round_id', 'pattern_id')
        ordering = ['game', 'round_id']

    def __str__(self):
        winners = ", ".join([user.email for user in self.won_by.all()]) or "No winners yet"
        return (
            f"Game: {self.game.title} | Round: {self.round_id} | "
            f"Pattern: {self.patternName} | Prize: {self.prize_amount} | Winners: {winners}"
        )


# with tickets round id binding on Game model
class PlayerTicket(models.Model):
    """
    Stores a single player's ticket for a specific game and round.
    """
    player = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tickets'
    )
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name='tickets'
    )
    round_id = models.PositiveIntegerField()  # round number (1, 2, 3, etc.)
    ticket_data = models.JSONField(default=list)  # e.g. a 3x9 matrix of numbers
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('player', 'game', 'round_id')
        ordering = ['game', 'round_id']

    def __str__(self):
        return f"Ticket for {self.player.email} (Game {self.game.id}, Round {self.round_id})"






#extrats

class Tickets(models.Model):
    """
    Standalone plain 3x9 tickets.
    """
    ticket_data = models.JSONField(default=list)  # Example: [[0, 12, 0, 23, ...], [...], [...]]
    used = models.BooleanField(default=False)     # True if assigned to some user
   

    def __str__(self):
        return f"Ticket {'assigned' if self.used else 'unassigned'} - ID {self.id}"