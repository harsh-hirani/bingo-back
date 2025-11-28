from django.contrib.auth import authenticate
from rest_framework import serializers
from core.models import User,Game,PlayerGame
#   creator
class CreatorRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = [
            "full_name", "company", "pan_number", "aadhaar_number",
            "address_line", "postal_code", "city", "state",
            "mobile_number", "email", "password"
        ]

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data['role'] = 'creator'  # Ensure role is set to creator
        creator = User.objects.create_user(password=password, **validated_data)
        return creator

class CreatorLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            raise serializers.ValidationError("Email and password are required.")

        user = authenticate(email=email, password=password)

        if not user:
            raise serializers.ValidationError("Invalid email or password.")

        if not user.is_active:
            raise serializers.ValidationError("Account is disabled.")
        if user.role != 'creator':
            raise serializers.ValidationError("User is not a creator.")

        data["user"] = user
        return data
    
#   player
class PlayerRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = [
            "full_name", "company", "pan_number", "aadhaar_number",
            "address_line", "postal_code", "city", "state",
            "mobile_number", "email", "password"
        ]

    def create(self, validated_data):
        password = validated_data.pop("password")
        player = User.objects.create_user(password=password, **validated_data)
        return player

class PlayerLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            raise serializers.ValidationError("Email and password are required.")

        user = authenticate(email=email, password=password)

        if not user:
            raise serializers.ValidationError("Invalid email or password.")

        if not user.is_active:
            raise serializers.ValidationError("Account is disabled.")
        if user.role != 'player':
            raise serializers.ValidationError("User is not a player.")

        data["user"] = user
        return data
    
    
# game creations
class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = [
            "id", "title", "description", "number_of_users",
            "total_prize_pool", "date_time",
            "prize_rounds",
            "creator"
        ]
        read_only_fields = ["creator"]

    def validate_prize_rounds(self, value):
        """
        Process rounds and patterns:
        - Assign round IDs (1,2,..)
        - Assign pattern IDs (<round>.<pattern>)
        - Add won=False and wonBy=None for each pattern
        - Add called_numbers=[] for each round
        - Validate no duplicate pattern names within a round
        """
        processed_rounds = []

        for round_index, round_data in enumerate(value, start=1):
            round_data["id"] = str(round_index)
            round_data["called_numbers"] = []  # initialize empty list for each round

            seen_patterns = set()
            new_patterns = []

            for pattern_index, pattern in enumerate(round_data.get("patterns", []), start=1):
                pattern_name = pattern.get("patternName")
                if pattern_name in seen_patterns:
                    raise serializers.ValidationError(
                        f"Duplicate pattern '{pattern_name}' found in round {round_index}."
                    )
                seen_patterns.add(pattern_name)

                pattern["id"] = f"{round_index}.{pattern_index}"
                pattern["won"] = pattern.get("won", False)
                pattern["wonBy"] = pattern.get("wonBy", None)

                new_patterns.append(pattern)

            round_data["patterns"] = new_patterns
            processed_rounds.append(round_data)

        return processed_rounds

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = user
        return super().create(validated_data)
    

class PlayerGameSerializer(serializers.ModelSerializer):
    player = serializers.ReadOnlyField(source='player.id')  # Auto-assign logged-in user

    class Meta:
        model = PlayerGame
        fields = ['id', 'game', 'player', 'won_amount']
        read_only_fields = ['player', 'won_amount']
