from django.urls import path
from . import views

urlpatterns = [
    path('', views.league_selection, name='league_selection'),
    path('get_seasons/<int:league_id>/', views.get_seasons_for_league, name='get_seasons_for_league'),
    path('league/<int:league_id>/<int:season_id>/', views.league_home, name='league_home'),
    path('league/<int:league_id>/<int:season_id>/teams/', views.team_list, name='team_list'),
    path('league/<int:league_id>/<int:season_id>/matchdays/', views.league_matchday_list, name='league_matchday_list'),
    path('league/<int:league_id>/<int:season_id>/standings/', views.league_standings_view, name='league_standings_view'),
    path('league/<int:league_id>/<int:season_id>/leaderboard/', views.leaderboard_view, name='leaderboard_view'),
    path('matchday/<int:matchday_id>/', views.matchday_detail, name='matchday_detail'),
    path('match/<int:match_id>/stats/', views.match_statistics, name='match_statistics'),
    path('team/<int:team_id>/', views.team_detail, name='team_detail'),
    path('player/<int:player_id>/', views.player_detail, name='player_detail'),
]