from django.urls import path
from . import views

urlpatterns = [
    path('matchdays/', views.matchday_list, name='matchday_list'),
    path('matchday/<int:matchday_id>/', views.matchday_detail, name='matchday_detail'),
    path('team/<int:team_id>/', views.team_detail, name='team_detail'),
    path('standings/<int:season_id>/', views.league_standings, name='league_standings'),
]
