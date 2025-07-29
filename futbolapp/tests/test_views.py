from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from futbolapp.models import League, Season, Team, Player, Matchday, Match, LeagueStanding, Tournament, Group, Profile, PlayerStatistic
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
