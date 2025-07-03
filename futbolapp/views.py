from django.shortcuts import render, get_object_or_404, redirect
from .models import Matchday, Match, Team, Player, PlayerStatistic, LeagueStanding, Season, League
from django.db.models import Sum, F
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from .forms import PlayerForm

# Create your views here.

@login_required
def league_selection(request):
    """
    View for selecting a league and season.
    """
    leagues = League.objects.all()
    return render(request, 'futbolapp/league_selection.html', {'leagues': leagues})

@login_required
def get_seasons_for_league(request, league_id):
    """
    AJAX view to get seasons for a selected league.
    """
    seasons = Season.objects.filter(league_id=league_id).order_by('-year').values('id', 'year')
    return JsonResponse(list(seasons), safe=False)

@login_required
def league_home(request, league_id, season_id):
    """
    Home page for a specific league and season, with navigation options.
    """
    league = get_object_or_404(League, pk=league_id)
    season = get_object_or_404(Season, pk=season_id)
    return render(request, 'futbolapp/league_home.html', {'league': league, 'season': season, 'active_tab': 'home'})

@login_required
def team_list(request, league_id, season_id):
    """
    View for listing all teams in a specific league and season.
    """
    league = get_object_or_404(League, pk=league_id)
    season = get_object_or_404(Season, pk=season_id)
    teams = Team.objects.filter(league=league)
    return render(request, 'futbolapp/team_list.html', {'league': league, 'season': season, 'teams': teams, 'active_tab': 'teams'})

@login_required
def player_detail(request, player_id):
    """
    View for a single player, showing their individual statistics.
    This view is now primarily for displaying stats, not editing.
    """
    player = get_object_or_404(Player, pk=player_id)
    stats = PlayerStatistic.objects.filter(player=player).aggregate(
            total_goals=Sum('goals'),
            total_assists=Sum('assists'),
            total_clean_sheets=Sum('clean_sheets'),
            total_yellow_cards=Sum('yellow_cards'),
            total_red_cards=Sum('red_cards')
        )
    player.stats = {k: v if v is not None else 0 for k, v in stats.items()}
    return render(request, 'futbolapp/player_detail.html', {'player': player})

@login_required
def player_form_view(request, team_id, player_id=None):
    """
    View for adding a new player or updating an existing player.
    Users can only add/update players for their associated team.
    """
    team = get_object_or_404(Team, pk=team_id)

    # Authorization check
    user_team = None
    if hasattr(request.user, 'profile') and request.user.profile.team:
        user_team = request.user.profile.team

    if not request.user.is_superuser and user_team != team:
        return HttpResponseForbidden("You are not authorized to modify players for this team.")

    player = None
    if player_id:
        player = get_object_or_404(Player, pk=player_id, team=team)

    if request.method == 'POST':
        form = PlayerForm(request.POST, instance=player)
        if form.is_valid():
            new_player = form.save(commit=False)
            new_player.team = team
            new_player.save()
            return redirect('team_detail', team_id=team.id)
    else:
        form = PlayerForm(instance=player)

    return render(request, 'futbolapp/player_form.html', {'form': form, 'team': team, 'player': player})

@login_required
def league_matchday_list(request, league_id, season_id):
    """
    View for listing all match days for a specific league and season, ordered by season and number.
    """
    league = get_object_or_404(League, pk=league_id)
    season = get_object_or_404(Season, pk=season_id)
    matchdays = Matchday.objects.filter(season=season).order_by('number')
    return render(request, 'futbolapp/matchday_list.html', {'league': league, 'season': season, 'matchdays': matchdays, 'active_tab': 'matchdays'})

@login_required
def matchday_detail(request, matchday_id):
    """
    View for a single match day schedule, showing all matches for that day.
    Each match day has its own page.
    """
    matchday = get_object_or_404(Matchday, pk=matchday_id)
    matches = Match.objects.filter(matchday=matchday)
    return render(request, 'futbolapp/matchday_detail.html', {'matchday': matchday, 'matches': matches})

@login_required
def match_statistics(request, match_id):
    """
    View for displaying detailed player statistics for a specific match.
    """
    match = get_object_or_404(Match, pk=match_id)
    player_stats = PlayerStatistic.objects.filter(match=match)
    return render(request, 'futbolapp/match_statistics.html', {'match': match, 'player_stats': player_stats})

@login_required
def match_roster_view(request, match_id):
    """
    View for displaying the roster (player presence) for a specific match.
    """
    match = get_object_or_404(Match, pk=match_id)
    home_team_players = PlayerStatistic.objects.filter(match=match, player__team=match.home_team).order_by('player__name')
    away_team_players = PlayerStatistic.objects.filter(match=match, player__team=match.away_team).order_by('player__name')
    return render(request, 'futbolapp/match_roster.html', {
        'match': match,
        'home_team_players': home_team_players,
        'away_team_players': away_team_players
    })

@login_required
def team_detail(request, team_id):
    """
    View for a single team, showing all their players and individual statistics.
    """
    team = get_object_or_404(Team, pk=team_id)
    league = team.league # Get the league from the team
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
    
    user_can_edit = False
    if request.user.is_superuser:
        user_can_edit = True
    elif hasattr(request.user, 'profile') and request.user.profile.team == team:
        user_can_edit = True

    return render(request, 'futbolapp/team_detail.html', {'team': team, 'players': players, 'league': league, 'active_tab': 'teams', 'user_can_edit': user_can_edit})

@login_required
def league_standings_view(request, league_id, season_id):
    """
    View for the league standings for a given league and season.
    """
    league = get_object_or_404(League, pk=league_id)
    season = get_object_or_404(Season, pk=season_id)

    teams = Team.objects.filter(league=league)
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

    return render(request, 'futbolapp/league_standings.html', {'league': league, 'season': season, 'standings': standings, 'active_tab': 'standings'})

@login_required
def leaderboard_view(request, league_id, season_id):
    """
    View for displaying various leaderboards for a given league and season.
    """
    league = get_object_or_404(League, pk=league_id)
    season = get_object_or_404(Season, pk=season_id)

    # Filter player statistics for the current season and league
    player_stats_in_season = PlayerStatistic.objects.filter(
        match__matchday__season=season,
        player__team__league=league
    )

    # Goals Leader
    goals_leader = player_stats_in_season.values('player__name', 'player__team__name') \
        .annotate(total_goals=Sum('goals')) \
        .order_by('-total_goals')[:10]

    # Assists Leader
    assists_leader = player_stats_in_season.values('player__name', 'player__team__name') \
        .annotate(total_assists=Sum('assists')) \
        .order_by('-total_assists')[:10]

    # Goal Contributions Leader (Goals + Assists)
    goal_contributions_leader = player_stats_in_season.values('player__name', 'player__team__name') \
        .annotate(total_contributions=Sum(F('goals') + F('assists'))) \
        .order_by('-total_contributions')[:10]

    # Clean Sheets Leader (only goalkeepers)
    clean_sheets_leader = player_stats_in_season.filter(player__field_position='goalkeeper') \
        .values('player__name', 'player__team__name') \
        .annotate(total_clean_sheets=Sum('clean_sheets')) \
        .order_by('-total_clean_sheets')[:10]

    # Yellow Cards Leader
    yellow_cards_leader = player_stats_in_season.values('player__name', 'player__team__name') \
        .annotate(total_yellow_cards=Sum('yellow_cards')) \
        .order_by('-total_yellow_cards')[:10]

    # Red Cards Leader
    red_cards_leader = player_stats_in_season.values('player__name', 'player__team__name') \
        .annotate(total_red_cards=Sum('red_cards')) \
        .order_by('-total_red_cards')[:10]

    context = {
        'league': league,
        'season': season,
        'active_tab': 'leaderboard',
        'goals_leader': goals_leader,
        'assists_leader': assists_leader,
        'goal_contributions_leader': goal_contributions_leader,
        'clean_sheets_leader': clean_sheets_leader,
        'yellow_cards_leader': yellow_cards_leader,
        'red_cards_leader': red_cards_leader,
    }
    return render(request, 'futbolapp/leaderboard.html', context)
