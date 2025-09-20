from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum
from .models import PlayerStatistic, Match, Player, Team

@receiver(post_save, sender=PlayerStatistic)
def update_match_score(sender, instance, **kwargs):
    # Get the match associated with the player statistic
    match = instance.match
    
    # Get all player statistics for this match
    player_stats_in_match = PlayerStatistic.objects.filter(match=match)
    
    # Calculate total goals for home team
    home_team_goals = player_stats_in_match.filter(
        player__team=match.home_team
    ).aggregate(total_goals=Sum('goals'))['total_goals'] or 0
    
    # Calculate total goals for away team
    away_team_goals = player_stats_in_match.filter(
        player__team=match.away_team
    ).aggregate(total_goals=Sum('goals'))['total_goals'] or 0
    
    # Update match scores if they have changed
    if match.home_score != home_team_goals or match.away_score != away_team_goals:
        match.home_score = home_team_goals
        match.away_score = away_team_goals
        match.save()
