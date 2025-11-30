# futbolapp/serializers.py
from rest_framework import serializers
from .models import PickupGame, PickupGamePlayer

class PickupGamePlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupGamePlayer
        fields = ['id', 'pickup_game', 'first_name', 'last_name', 'email', 'phone_number', 'age']

class PickupGameSerializer(serializers.ModelSerializer):
    players = PickupGamePlayerSerializer(many=True, read_only=True)
    
    class Meta:
        model = PickupGame
        fields = ['id', 'location', 'time', 'max_players', 'current_players', 'price', 'is_active', 'players']