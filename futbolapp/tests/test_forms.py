from django.test import TestCase
from django.contrib.auth.models import User
from futbolapp.models import League, Season, Team, Player, Match, Matchday, Profile
from futbolapp.forms import RosterUpdateForm
from datetime import datetime, date
import pytz

class FormTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.league = League.objects.create(name="Test League")
        self.season = Season.objects.create(league=self.league, year=2023)
        self.team1 = Team.objects.create(name="Team A", league=self.league)
        self.team2 = Team.objects.create(name="Team B", league=self.league)
        self.player1 = Player.objects.create(name="Player 1", team=self.team1)
        self.player2 = Player.objects.create(name="Player 2", team=self.team2)
        self.matchday = Matchday.objects.create(season=self.season, number=1, date=date.today())
        self.utc = pytz.UTC
        self.match = Match.objects.create(
            matchday=self.matchday,
            home_team=self.team1,
            away_team=self.team2,
            date=datetime.now().replace(tzinfo=self.utc)
        )
        # Associate user with a team
        Profile.objects.create(user=self.user, team=self.team1)


    def test_roster_update_form_init(self):
        """Test that the RosterUpdateForm initializes correctly."""
        form = RosterUpdateForm(match=self.match, user=self.user)
        self.assertIn('home_team_players', form.fields)
        self.assertIn('away_team_players', form.fields)
        self.assertEqual(form.fields['home_team_players'].queryset.count(), 1)
        self.assertEqual(form.fields['away_team_players'].queryset.count(), 1)

    def test_roster_update_form_valid(self):
        """Test a valid RosterUpdateForm submission."""
        form_data = {
            'home_team_players': [self.player1.id],
            'away_team_players': []
        }
        form = RosterUpdateForm(data=form_data, match=self.match, user=self.user)
        self.assertTrue(form.is_valid())

    def test_roster_update_form_update_roster(self):
        """Test the update_roster_data method of the form."""
        form_data = {
            'home_team_players': [self.player1.id],
            'away_team_players': [self.player2.id]
        }
        form = RosterUpdateForm(data=form_data, match=self.match, user=self.user)
        self.assertTrue(form.is_valid())
        form.update_roster_data()

        # Verify that the player statistics were updated
        stat1 = self.match.playerstatistic_set.get(player=self.player1)
        stat2 = self.match.playerstatistic_set.get(player=self.player2)
        self.assertTrue(stat1.present)
        # The user is only on team1, so they can't update team2's roster
        self.assertFalse(stat2.present)

        # Now test with a superuser
        self.user.is_superuser = True
        self.user.save()
        form = RosterUpdateForm(data=form_data, match=self.match, user=self.user)
        self.assertTrue(form.is_valid())
        form.update_roster_data()
        stat2.refresh_from_db()
        self.assertTrue(stat2.present)
