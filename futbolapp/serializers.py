# futbolapp/serializers.py
from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import PickupGame, PickupGamePlayer

class PickupGamePlayerSerializer(serializers.ModelSerializer):
    def validate_pickup_game(self, pickup_game):
        if not pickup_game.is_active:
            raise serializers.ValidationError('Invalid or inactive game ID.')
        return pickup_game

    def create(self, validated_data):
        player = PickupGamePlayer(**validated_data)
        try:
            player.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict)
        return player

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        try:
            instance.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict)
        return instance

    class Meta:
        model = PickupGamePlayer
        fields = ['id', 'pickup_game', 'first_name', 'last_name', 'email', 'phone_number', 'player_level']

class PickupGameSerializer(serializers.ModelSerializer):
    players = PickupGamePlayerSerializer(many=True, read_only=True)
    spots_remaining = serializers.IntegerField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        game = instance or PickupGame()

        for attr, value in attrs.items():
            setattr(game, attr, value)

        try:
            game.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict)

        return attrs
    
    class Meta:
        model = PickupGame
        fields = ['id', 'location', 'time', 'end_time', 'max_players', 'current_players', 'spots_remaining', 'is_full', 'price', 'is_active', 'players']
        read_only_fields = ['current_players', 'spots_remaining', 'is_full', 'players']
