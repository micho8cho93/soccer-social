from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from futbolapp.models import League, Season, Team, Player, Matchday, Match, LeagueStanding, Tournament, Group, Profile, PlayerStatistic, TournamentPlayerStatistic, TournamentMatch, GroupStanding, Referee, PickupGame, PickupGamePlayer
from datetime import date, datetime, timedelta
import pytz
import json
from django.conf import settings

@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage',
    SECRET_KEY=settings.SECRET_KEY if settings.SECRET_KEY else 'test-secret-key-for-testing-only'
)
class ViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')

        self.league = League.objects.create(name="Test League")
        self.season = Season.objects.create(league=self.league, year=2023, is_current=True)
        self.team1 = Team.objects.create(name="Team A", league=self.league)
        self.team2 = Team.objects.create(name="Team B", league=self.league)
        self.matchday = Matchday.objects.create(season=self.season, number=1, date=date.today())
        self.utc = pytz.UTC
        self.match_time = datetime.now().replace(tzinfo=self.utc)
        self.match = Match.objects.create(
            matchday=self.matchday,
            home_team=self.team1,
            away_team=self.team2,
            home_score=2,
            away_score=1,
            date=self.match_time
        )

    def test_league_selection_view(self):
        """Test the league selection view."""
        response = self.client.get(reverse('league_selection'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.league.name)

    def test_league_home_view_authenticated(self):
        """Test the league home view for an authenticated user."""
        response = self.client.get(reverse('league_home', args=[self.league.id, self.season.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"{self.league.name} - Season {self.season.year}")

    def test_public_league_home_view_unauthenticated(self):
        """Test the public league home view for an unauthenticated user."""
        self.client.logout()
        response = self.client.get(reverse('public_league_home', args=[self.league.id, self.season.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"{self.league.name} - Season {self.season.year}")

    def test_league_standings_view(self):
        """Test the league standings view."""
        LeagueStanding.recalculate_for_team(self.team1, self.season)
        LeagueStanding.update_positions_for_season(self.season)
        response = self.client.get(reverse('league_standings_view', args=[self.league.id, self.season.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.team1.name)
        self.assertContains(response, "3") # Points

    def test_leaderboard_view(self):
        """Test the leaderboard view."""
        player = Player.objects.create(name="Top Scorer", team=self.team1)
        PlayerStatistic.objects.create(player=player, match=self.match, goals=5)

        response = self.client.get(reverse('leaderboard_view', args=[self.league.id, self.season.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Top Scorer")
        self.assertContains(response, "5")

    def test_player_form_view_unauthorized(self):
        """Test that a user cannot edit a player from another team."""
        other_team = Team.objects.create(name="Other Team", league=self.league)
        player = Player.objects.create(name="Other Player", team=other_team)
        response = self.client.get(reverse('player_edit', args=[other_team.id, player.id]))
        self.assertEqual(response.status_code, 403) # Forbidden

    def test_update_roster_view_future_match(self):
        """Test updating a roster for a future match."""
        future_date = datetime.now().replace(tzinfo=self.utc) + timedelta(days=1)
        future_matchday = Matchday.objects.create(season=self.season, number=2, date=future_date.date())
        future_match = Match.objects.create(
            matchday=future_matchday,
            home_team=self.team1,
            away_team=self.team2,
            date=future_date
        )
        profile, created = Profile.objects.get_or_create(user=self.user, defaults={'team': self.team1})
        if not created:
            profile.team = self.team1
            profile.save()

        response = self.client.get(reverse('update_roster_view', args=[future_match.id]))
        self.assertEqual(response.status_code, 200)

    def test_update_roster_view_past_match(self):
        """Test that updating a roster for a past match is forbidden."""
        past_date = datetime.now().replace(tzinfo=self.utc) - timedelta(days=1)
        self.match.date = past_date
        self.match.save()

        response = self.client.get(reverse('update_roster_view', args=[self.match.id]))
        self.assertEqual(response.status_code, 403)

    def test_player_form_view_non_team_user_gets_403(self):
        """Test that a non-team user gets 403 when accessing player form."""
        other_team = Team.objects.create(name="Other Team", league=self.league)
        player = Player.objects.create(name="Other Player", team=other_team, field_position='field player', role='full-time')
        response = self.client.get(reverse('player_edit', args=[other_team.id, player.id]))
        self.assertEqual(response.status_code, 403)

    def test_player_form_view_team_member_can_get_post(self):
        """Test that team member can GET and POST player form."""
        # Assign user to team
        Profile.objects.create(user=self.user, team=self.team1)
        
        # Test GET
        response = self.client.get(reverse('player_add', args=[self.team1.id]))
        self.assertEqual(response.status_code, 200)
        
        # Test POST
        response = self.client.post(reverse('player_add', args=[self.team1.id]), {
            'name': 'New Player',
            'field_position': 'field player',
            'role': 'full-time'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(Player.objects.filter(name='New Player', team=self.team1).exists())

    def test_player_form_view_superuser_can_get_post(self):
        """Test that superuser can GET and POST player form for any team."""
        self.user.is_superuser = True
        self.user.save()
        
        # Test GET
        response = self.client.get(reverse('player_add', args=[self.team2.id]))
        self.assertEqual(response.status_code, 200)
        
        # Test POST
        response = self.client.post(reverse('player_add', args=[self.team2.id]), {
            'name': 'New Player 2',
            'field_position': 'goalkeeper',
            'role': 'ringer'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Player.objects.filter(name='New Player 2', team=self.team2).exists())

    def test_player_form_view_post_redirects_league_path(self):
        """Test that POST redirects correctly to league path."""
        Profile.objects.create(user=self.user, team=self.team1)
        
        response = self.client.post(reverse('player_add', args=[self.team1.id]), {
            'name': 'League Player',
            'field_position': 'field player',
            'role': 'full-time'
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('team', response.url)

    def test_player_form_view_post_redirects_tournament_path(self):
        """Test that POST redirects correctly to tournament path."""
        tournament = Tournament.objects.create(name="Test Tournament")
        season = Season.objects.create(tournament=tournament, year=2024)
        tournament_team = Team.objects.create(name="Tournament Team", tournament=tournament)
        Profile.objects.create(user=self.user, team=tournament_team)
        
        response = self.client.post(
            reverse('tournament_player_add', args=[tournament.id, season.id, tournament_team.id]), 
            {
                'name': 'Tournament Player',
                'field_position': 'field player',
                'role': 'full-time'
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('tournament', response.url)

    def test_update_roster_view_403_for_unauthorized_user(self):
        """Test that users not tied to either team get 403."""
        future_date = datetime.now().replace(tzinfo=pytz.UTC) + timedelta(days=1)
        future_matchday = Matchday.objects.create(season=self.season, number=2, date=future_date.date())
        future_match = Match.objects.create(
            matchday=future_matchday,
            home_team=self.team1,
            away_team=self.team2,
            date=future_date
        )
        
        # User has no team association
        response = self.client.get(reverse('update_roster_view', args=[future_match.id]))
        self.assertEqual(response.status_code, 403)

    def test_update_roster_view_200_for_authorized_user(self):
        """Test that authorized user gets 200 for future match."""
        future_date = datetime.now().replace(tzinfo=pytz.UTC) + timedelta(days=1)
        future_matchday = Matchday.objects.create(season=self.season, number=2, date=future_date.date())
        future_match = Match.objects.create(
            matchday=future_matchday,
            home_team=self.team1,
            away_team=self.team2,
            date=future_date
        )
        Profile.objects.create(user=self.user, team=self.team1)
        
        response = self.client.get(reverse('update_roster_view', args=[future_match.id]))
        self.assertEqual(response.status_code, 200)

    def test_match_roster_view_shows_only_present_players(self):
        """Test that match_roster_view shows only present=True players per side."""
        player1 = Player.objects.create(name="Player 1", team=self.team1, field_position='field player', role='full-time')
        player2 = Player.objects.create(name="Player 2", team=self.team1, field_position='field player', role='full-time')
        player3 = Player.objects.create(name="Player 3", team=self.team2, field_position='field player', role='full-time')
        
        # Create match and player statistics
        future_date = datetime.now().replace(tzinfo=pytz.UTC) + timedelta(days=1)
        matchday = Matchday.objects.create(season=self.season, number=3, date=future_date.date())
        match = Match.objects.create(
            matchday=matchday,
            home_team=self.team1,
            away_team=self.team2,
            date=future_date
        )
        
        # Set player1 and player3 as present
        stat1 = PlayerStatistic.objects.get(player=player1, match=match)
        stat1.present = True
        stat1.save()
        
        stat3 = PlayerStatistic.objects.get(player=player3, match=match)
        stat3.present = True
        stat3.save()
        
        response = self.client.get(reverse('match_roster_view', args=[match.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Player 1')
        self.assertNotContains(response, 'Player 2')
        self.assertContains(response, 'Player 3')

    def test_public_league_home_unauthenticated(self):
        """Test public_league_home renders 200 for unauthenticated users."""
        self.client.logout()
        response = self.client.get(reverse('public_league_home', args=[self.league.id, self.season.id]))
        self.assertEqual(response.status_code, 200)

    def test_public_league_standings_view_unauthenticated(self):
        """Test public_league_standings_view renders 200 for unauthenticated users."""
        self.client.logout()
        LeagueStanding.recalculate_for_team(self.team1, self.season)
        response = self.client.get(reverse('public_league_standings_view', args=[self.league.id, self.season.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.team1.name)

    def test_public_leaderboard_view_unauthenticated(self):
        """Test public_leaderboard_view renders 200 for unauthenticated users."""
        self.client.logout()
        player = Player.objects.create(name="Top Scorer", team=self.team1, field_position='field player', role='full-time')
        PlayerStatistic.objects.create(player=player, match=self.match, goals=5)
        
        response = self.client.get(reverse('public_leaderboard_view', args=[self.league.id, self.season.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Top Scorer")

    def test_public_tournament_home_unauthenticated(self):
        """Test public_tournament_home renders 200 for unauthenticated users."""
        self.client.logout()
        tournament = Tournament.objects.create(name="Test Tournament")
        season = Season.objects.create(tournament=tournament, year=2024)
        
        response = self.client.get(reverse('public_tournament_home', args=[tournament.id, season.id]))
        self.assertEqual(response.status_code, 200)

    def test_public_tournament_standings_unauthenticated(self):
        """Test public_tournament_standings renders 200 for unauthenticated users."""
        self.client.logout()
        tournament = Tournament.objects.create(name="Test Tournament")
        season = Season.objects.create(tournament=tournament, year=2024)
        
        response = self.client.get(reverse('public_tournament_standings', args=[tournament.id, season.id]))
        self.assertEqual(response.status_code, 200)

    def test_public_tournament_leaderboard_unauthenticated(self):
        """Test public_tournament_leaderboard renders 200 for unauthenticated users."""
        self.client.logout()
        tournament = Tournament.objects.create(name="Test Tournament")
        season = Season.objects.create(tournament=tournament, year=2024)
        
        response = self.client.get(reverse('public_tournament_leaderboard', args=[tournament.id, season.id]))
        self.assertEqual(response.status_code, 200)

    def test_leaderboard_view_aggregates_correctly(self):
        """Test leaderboard_view aggregates goals/assists/clean_sheets correctly."""
        player1 = Player.objects.create(name="Scorer", team=self.team1, field_position='field player', role='full-time')
        player2 = Player.objects.create(name="Assister", team=self.team1, field_position='field player', role='full-time')
        player3 = Player.objects.create(name="Keeper", team=self.team1, field_position='goalkeeper', role='full-time')
        
        # Create a separate matchday to avoid unique constraint
        matchday2 = Matchday.objects.create(season=self.season, number=2, date=date.today())
        
        # First match - use existing matchday
        match1_stats = PlayerStatistic.objects.get_or_create(player=player1, match=self.match)[0]
        match1_stats.goals = 3
        match1_stats.assists = 1
        match1_stats.save()
        
        # Second match - use new matchday
        match2 = Match.objects.create(
            matchday=matchday2,
            home_team=self.team1,
            away_team=self.team2,
            home_score=0,
            away_score=0,
            date=datetime.now().replace(tzinfo=pytz.UTC) + timedelta(hours=1)
        )
        
        # Add stats for match2
        match2_stat1 = PlayerStatistic.objects.get(player=player1, match=match2)
        match2_stat1.goals = 2
        match2_stat1.save()
        
        match_stat2 = PlayerStatistic.objects.get(player=player2, match=self.match)
        match_stat2.assists = 2
        match_stat2.save()
        
        match_stat3_1 = PlayerStatistic.objects.get(player=player3, match=self.match)
        match_stat3_1.clean_sheets = 1
        match_stat3_1.save()
        
        match_stat3_2 = PlayerStatistic.objects.get(player=player3, match=match2)
        match_stat3_2.clean_sheets = 1
        match_stat3_2.save()
        
        response = self.client.get(reverse('leaderboard_view', args=[self.league.id, self.season.id]))
        self.assertEqual(response.status_code, 200)
        
        # Verify goals leaderboard
        goals_leader = response.context['goals_leader']
        self.assertEqual(goals_leader[0]['player__name'], 'Scorer')
        self.assertEqual(goals_leader[0]['total_goals'], 5)
        
        # Verify clean sheets
        clean_sheets = response.context['clean_sheets_leader']
        self.assertEqual(clean_sheets[0]['player__name'], 'Keeper')
        self.assertEqual(clean_sheets[0]['total_clean_sheets'], 2)

    def test_tournament_leaderboard_aggregates_correctly(self):
        """Test tournament_leaderboard aggregates stats correctly from TournamentPlayerStatistic."""
        tournament = Tournament.objects.create(name="Test Tournament")
        season = Season.objects.create(tournament=tournament, year=2024)
        group = Group.objects.create(name="Group A", tournament=tournament)
        
        team1 = Team.objects.create(name="Team 1", tournament=tournament)
        team2 = Team.objects.create(name="Team 2", tournament=tournament)
        group.teams.add(team1, team2)
        
        player1 = Player.objects.create(name="Tournament Scorer", team=team1, field_position='field player', role='full-time')
        
        # Create tournament match
        match = TournamentMatch.objects.create(
            group=group,
            home_team=team1,
            away_team=team2,
            home_score=3,
            away_score=1,
            date=datetime.now().replace(tzinfo=pytz.UTC)
        )
        
        TournamentPlayerStatistic.objects.filter(player=player1, tournament_match=match).update(goals=3, assists=2)
        
        response = self.client.get(reverse('tournament_leaderboard', args=[tournament.id, season.id]))
        self.assertEqual(response.status_code, 200)
        
        goals_leader = response.context['goals_leader']
        self.assertEqual(goals_leader[0]['player__name'], 'Tournament Scorer')
        self.assertEqual(goals_leader[0]['total_goals'], 3)

    def test_league_standings_view_returns_200_with_standings(self):
        """Test league_standings_view returns 200 and includes standings."""
        response = self.client.get(reverse('league_standings_view', args=[self.league.id, self.season.id]))
        self.assertEqual(response.status_code, 200)
        self.assertIn('standings', response.context)
        self.assertTrue(len(response.context['standings']) > 0)

    def test_league_standings_view_respects_sorting(self):
        """Test league_standings_view respects sorting by position/points/gd/gf."""
        # Create a match to generate different standings using a different matchday
        matchday5 = Matchday.objects.create(season=self.season, number=5, date=date.today())
        Match.objects.create(
            matchday=matchday5,
            home_team=self.team1,
            away_team=self.team2,
            home_score=3,
            away_score=0,
            date=datetime.now().replace(tzinfo=pytz.UTC)
        )
        
        response = self.client.get(reverse('league_standings_view', args=[self.league.id, self.season.id]))
        standings = response.context['standings']
        
        # Verify team1 (3 points) is ahead of team2 (0 points)
        team1_standing = next(s for s in standings if s.team == self.team1)
        team2_standing = next(s for s in standings if s.team == self.team2)
        self.assertLess(team1_standing.position, team2_standing.position)

    def test_tournament_standings_returns_200_with_standings(self):
        """Test tournament_standings returns 200 and includes standings."""
        tournament = Tournament.objects.create(name="Test Tournament")
        season = Season.objects.create(tournament=tournament, year=2024)
        group = Group.objects.create(name="Group A", tournament=tournament)
        
        response = self.client.get(reverse('tournament_standings', args=[tournament.id, season.id]))
        self.assertEqual(response.status_code, 200)
        self.assertIn('group_standings_data', response.context)

    def test_referee_login_valid_username(self):
        """Test referee_login with valid username sets session & redirects."""
        referee = Referee.objects.create(name="Test Referee", username="ref123")
        
        response = self.client.post(reverse('referee_login'), {'username': 'ref123'})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('referee_portal'))
        self.assertEqual(self.client.session['referee_username'], 'ref123')

    def test_referee_login_invalid_username(self):
        """Test referee_login with invalid username shows error."""
        response = self.client.post(reverse('referee_login'), {'username': 'invalid'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username')

    def test_referee_match_update_pre_creates_player_statistics(self):
        """Test referee_match_update pre-creates PlayerStatistic for both teams."""
        player1 = Player.objects.create(name="Player 1", team=self.team1, field_position='field player', role='full-time')
        player2 = Player.objects.create(name="Player 2", team=self.team2, field_position='field player', role='full-time')
        
        # Use a different matchday to avoid unique constraint
        matchday3 = Matchday.objects.create(season=self.season, number=3, date=date.today())
        new_match = Match.objects.create(
            matchday=matchday3,
            home_team=self.team1,
            away_team=self.team2,
            date=datetime.now().replace(tzinfo=pytz.UTC)
        )
        
        # Verify PlayerStatistic entries exist after accessing the view
        response = self.client.get(reverse('referee_match_update', args=[new_match.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(PlayerStatistic.objects.filter(player=player1, match=new_match).exists())
        self.assertTrue(PlayerStatistic.objects.filter(player=player2, match=new_match).exists())

    def test_referee_match_update_valid_post_saves_and_redirects(self):
        """Test referee_match_update valid POST saves and redirects with success message."""
        Referee.objects.create(name="Test Referee", username="ref123")
        self.client.post(reverse('referee_login'), {'username': 'ref123'})
        
        player1 = Player.objects.create(name="Player 1", team=self.team1, field_position='field player', role='full-time')
        
        # Use a different matchday to avoid unique constraint
        matchday4 = Matchday.objects.create(season=self.season, number=4, date=date.today())
        new_match = Match.objects.create(
            matchday=matchday4,
            home_team=self.team1,
            away_team=self.team2,
            date=datetime.now().replace(tzinfo=pytz.UTC)
        )
        
        stat = PlayerStatistic.objects.get(player=player1, match=new_match)
        
        # Post with formset data
        response = self.client.post(reverse('referee_match_update', args=[new_match.id]), {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '1',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            f'form-0-id': stat.id,
            f'form-0-present': 'on',
            f'form-0-goals': '2',
            f'form-0-assists': '1',
            f'form-0-yellow_cards': '0',
            f'form-0-red_cards': '0',
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('referee_portal'))
        
        # Verify stats were saved
        stat.refresh_from_db()
        self.assertEqual(stat.goals, 2)
        self.assertEqual(stat.assists, 1)

    def test_pickup_game_viewset_list_returns_only_active_games(self):
        """Test PickupGameViewSet.list returns only active games ordered by time."""
        future_time = datetime.now().replace(tzinfo=pytz.UTC) + timedelta(days=1)
        past_time = datetime.now().replace(tzinfo=pytz.UTC) - timedelta(days=1)
        
        game1 = PickupGame.objects.create(location="Field 1", time=future_time, is_active=True, max_players=10)
        game2 = PickupGame.objects.create(location="Field 2", time=past_time, is_active=True, max_players=10)
        game3 = PickupGame.objects.create(location="Field 3", time=future_time, is_active=False, max_players=10)
        
        response = self.client.get('/futbol/api/games/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(len(data), 2)  # Only active games
        # Verify ordering by time (earliest first)
        self.assertEqual(data[0]['location'], 'Field 2')
        self.assertEqual(data[1]['location'], 'Field 1')

    def test_pickup_game_player_viewset_create_invalid_game_returns_400(self):
        """Test PickupGamePlayerViewSet.create with invalid/inactive game id returns 400."""
        response = self.client.post('/futbol/api/game-players/', {
            'pickup_game': 9999,
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'phone_number': '1234567890',
            'age': 25
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 400)

    def test_pickup_game_player_viewset_create_inactive_game_returns_400(self):
        """Test PickupGamePlayerViewSet.create with inactive game returns 400."""
        inactive_game = PickupGame.objects.create(
            location="Field", 
            time=datetime.now().replace(tzinfo=pytz.UTC), 
            is_active=False,
            max_players=10
        )
        
        response = self.client.post('/futbol/api/game-players/', {
            'pickup_game': inactive_game.id,
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'phone_number': '1234567890',
            'age': 25
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 400)

    def test_pickup_game_player_viewset_create_success_increments_current_players(self):
        """Test PickupGamePlayerViewSet.create success increments pickup_game.current_players."""
        active_game = PickupGame.objects.create(
            location="Field", 
            time=datetime.now().replace(tzinfo=pytz.UTC), 
            is_active=True,
            max_players=10
        )
        
        self.assertEqual(active_game.current_players, 0)
        
        response = self.client.post('/futbol/api/game-players/', {
            'pickup_game': active_game.id,
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'phone_number': '1234567890',
            'age': 25
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 201)
        
        active_game.refresh_from_db()
        self.assertEqual(active_game.current_players, 1)

    def test_pickup_game_player_viewset_perform_destroy_decrements_current_players(self):
        """Test PickupGamePlayerViewSet.perform_destroy decrements current_players after deletion."""
        active_game = PickupGame.objects.create(
            location="Field", 
            time=datetime.now().replace(tzinfo=pytz.UTC), 
            is_active=True,
            max_players=10
        )
        
        player = PickupGamePlayer.objects.create(
            pickup_game=active_game,
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            phone_number='1234567890',
            age=25
        )
        active_game.current_players = 1
        active_game.save()
        
        response = self.client.delete(f'/futbol/api/game-players/{player.id}/')
        self.assertEqual(response.status_code, 204)
        
        active_game.refresh_from_db()
        self.assertEqual(active_game.current_players, 0)
