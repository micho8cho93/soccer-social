from django.shortcuts import render, get_object_or_404
from .models import Matchday, Match, Team, Player, PlayerStatistic, LeagueStanding, Season
from django.db.models import Sum

# Create your views here.

def matchday_list(request):
    """
    View for listing all match days, ordered by season and number.
    """
    matchdays = Matchday.objects.all()
    return render(request, 'futbolapp/matchday_list.html', {'matchdays': matchdays})

def matchday_detail(request, matchday_id):
    """
    View for a single match day schedule, showing all matches for that day.
    Each match day has its own page.
    """
    matchday = get_object_or_404(Matchday, pk=matchday_id)
    matches = Match.objects.filter(matchday=matchday)
    return render(request, 'futbolapp/matchday_detail.html', {'matchday': matchday, 'matches': matches})

def team_detail(request, team_id):
    """
    View for a single team, showing all their players and individual statistics.
    """
    team = get_object_or_404(Team, pk=team_id)
    players = Player.objects.filter(team=team)
    for player in players:
        stats = PlayerStatistic.objects.filter(player=player).aggregate(
            total_goals=Sum('goals'),
            total_assists=Sum('assists'),
            total_clean_sheets=Sum('clean_sheets'),
            total_yellow_cards=Sum('yellow_cards'),
            total_red_cards=Sum('red_cards')
        )
        # Replace None values with 0 for players with no stats yet
        player.stats = {k: v if v is not None else 0 for k, v in stats.items()}
    return render(request, 'futbolapp/team_detail.html', {'team': team, 'players': players})

def league_standings(request, season_id):
    """
    View for the league standings for a given season.
    The goal difference is calculated as goals_for - goals_against and stored in the database.
    """
    season = get_object_or_404(Season, pk=season_id)
    teams = Team.objects.filter(league=season.league)
    standings = []
    for team in teams:
        standing, created = LeagueStanding.objects.get_or_create(
            team=team, 
            season=season,
            defaults={
                'position': 0,
                'points': 0,
                'matches_played': 0,
                'wins': 0,
                'draws': 0,
                'losses': 0,
                'goals_for': 0,
                'goals_against': 0,
                'goal_difference': 0,
            }
        )
        standings.append(standing)

    # Sort by position, then points, goal difference, and goals for
    standings.sort(key=lambda x: (x.position, -x.points, -x.goal_difference, -x.goals_for))

    return render(request, 'futbolapp/league_standings.html', {'season': season, 'standings': standings})