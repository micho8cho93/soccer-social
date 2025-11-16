# futbolapp/serializers.py
from rest_framework import serializers
from .models import PickupGame

class PickupGameSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupGame
        fields = ['id', 'location', 'time', 'max_players', 'current_players', 'price', 'is_active']