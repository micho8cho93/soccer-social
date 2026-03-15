from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from futbolapp.models import League, Season, Team, Player, Matchday, Match, LeagueStanding, Tournament, Group, Profile, PlayerStatistic, PickupGame, PickupGamePlayer
from datetime import date, datetime, timedelta
import pytz

@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
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
        self.tournament = Tournament.objects.create(name="Champions Cup")
        self.tournament_season = Season.objects.create(tournament=self.tournament, year=2024)
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
        self.assertContains(response, self.league.name)
        self.assertContains(response, f"Season {self.season.year}")
        self.assertContains(response, 'data-ui="competition-shell"')
        self.assertContains(response, 'data-nav="league"')
        self.assertContains(response, 'data-nav-item="teams"')
        self.assertContains(response, 'data-nav-item="matchdays"')

    def test_public_league_home_view_unauthenticated(self):
        """Test the public league home view for an unauthenticated user."""
        self.client.logout()
        response = self.client.get(reverse('public_league_home', args=[self.league.id, self.season.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.league.name)
        self.assertContains(response, f"Season {self.season.year}")
        self.assertContains(response, 'data-ui="competition-shell"')
        self.assertContains(response, 'data-nav="league"')
        self.assertNotContains(response, 'data-nav-item="teams"')
        self.assertNotContains(response, 'data-nav-item="matchdays"')

    def test_tournament_home_view_authenticated(self):
        """Authenticated tournament home view should render the competition shell and private nav items."""
        response = self.client.get(reverse('tournament_home', args=[self.tournament.id, self.tournament_season.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-ui="competition-shell"')
        self.assertContains(response, 'data-nav="tournament"')
        self.assertContains(response, 'data-nav-item="teams"')
        self.assertContains(response, 'data-nav-item="matchdays"')

    def test_public_tournament_home_view_unauthenticated(self):
        """Public tournament home view should hide private tournament nav items."""
        self.client.logout()
        response = self.client.get(reverse('public_tournament_home', args=[self.tournament.id, self.tournament_season.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-ui="competition-shell"')
        self.assertContains(response, 'data-nav="tournament"')
        self.assertNotContains(response, 'data-nav-item="teams"')
        self.assertNotContains(response, 'data-nav-item="matchdays"')

    def test_league_standings_view(self):
        """Test the league standings view."""
        LeagueStanding.recalculate_for_team(self.team1, self.season)
        LeagueStanding.update_positions_for_season(self.season)
        response = self.client.get(reverse('league_standings_view', args=[self.league.id, self.season.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.team1.name)
        self.assertContains(response, "3") # Points

    def test_tournament_standings_positions_start_at_one(self):
        """Tournament standings should assign 1-based positions even before matches are played."""
        tournament = Tournament.objects.create(name="Champions Cup")
        tournament_season = Season.objects.create(tournament=tournament, year=2024)
        group = Group.objects.create(name="A", tournament=tournament)
        tournament_team_1 = Team.objects.create(name="Tournament Team A", tournament=tournament)
        tournament_team_2 = Team.objects.create(name="Tournament Team B", tournament=tournament)
        group.teams.add(tournament_team_1, tournament_team_2)

        response = self.client.get(reverse('tournament_standings', args=[tournament.id, tournament_season.id]))

        self.assertEqual(response.status_code, 200)
        standings = list(response.context['group_standings_data'][0]['standings'])
        self.assertEqual([standing.position for standing in standings], [1, 2])

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

    def test_pickup_game_api_blocks_registration_when_full(self):
        """Pickup API should reject registrations once a game reaches max_players."""
        start_time = datetime.now().replace(tzinfo=self.utc)
        game = PickupGame.objects.create(
            location="Madrid",
            time=start_time,
            end_time=start_time + timedelta(hours=1),
            max_players=1,
        )
        PickupGamePlayer.objects.create(
            pickup_game=game,
            first_name="First",
            last_name="Player",
            email="first@example.com",
            phone_number="123456789",
            age=24,
        )

        response = self.client.post('/futbol/api/game-players/', {
            'pickup_game': game.id,
            'first_name': 'Second',
            'last_name': 'Player',
            'email': 'second@example.com',
            'phone_number': '987654321',
            'age': 26,
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['pickup_game'][0], 'This pickup game is full.')

        game.refresh_from_db()
        self.assertEqual(game.current_players, 1)

    def test_pickup_game_api_updates_count_on_join_and_cancel(self):
        """Pickup API should keep current_players in sync after join and cancel."""
        start_time = datetime.now().replace(tzinfo=self.utc)
        game = PickupGame.objects.create(
            location="Madrid",
            time=start_time,
            end_time=start_time + timedelta(hours=2),
            max_players=2,
        )

        join_response = self.client.post('/futbol/api/game-players/', {
            'pickup_game': game.id,
            'first_name': 'Join',
            'last_name': 'Tester',
            'email': 'joiner@example.com',
            'phone_number': '555555555',
            'age': 28,
        })

        self.assertEqual(join_response.status_code, 201)
        game.refresh_from_db()
        self.assertEqual(game.current_players, 1)

        games_response = self.client.get('/futbol/api/games/')
        self.assertEqual(games_response.status_code, 200)
        game_payload = next(item for item in games_response.json() if item['id'] == game.id)
        self.assertIn('end_time', game_payload)
        self.assertIsNotNone(game_payload['end_time'])
        self.assertEqual(game_payload['current_players'], 1)
        self.assertEqual(game_payload['spots_remaining'], 1)
        self.assertFalse(game_payload['is_full'])

        player_id = join_response.json()['id']
        cancel_response = self.client.delete(f'/futbol/api/game-players/{player_id}/')
        self.assertEqual(cancel_response.status_code, 204)

        game.refresh_from_db()
        self.assertEqual(game.current_players, 0)
