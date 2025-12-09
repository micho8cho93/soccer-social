from django.test import TestCase
from django.contrib.auth.models import User
from futbolapp.models import League, Season, Team, Player, Match, Matchday, Profile, PlayerStatistic
from futbolapp.forms import RosterUpdateForm, PlayerForm
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

    def test_player_form_valid(self):
        """Test PlayerForm is valid with required fields."""
        form_data = {
            'name': 'Test Player',
            'field_position': 'field player',
            'role': 'full-time'
        }
        form = PlayerForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_player_form_invalid_missing_name(self):
        """Test PlayerForm is invalid when name is missing."""
        form_data = {
            'field_position': 'field player',
            'role': 'full-time'
        }
        form = PlayerForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_player_form_invalid_choices(self):
        """Test PlayerForm is invalid when choices are invalid."""
        form_data = {
            'name': 'Test Player',
            'field_position': 'invalid_position',
            'role': 'invalid_role'
        }
        form = PlayerForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('field_position', form.errors)
        self.assertIn('role', form.errors)

    def test_roster_update_form_init_sets_fields_and_initial(self):
        """Test RosterUpdateForm.__init__ sets fields for both teams and initial selections from PlayerStatistic.present."""
        # Create additional players before match is saved to ensure PlayerStatistic entries exist
        player3 = Player.objects.create(name="Player 3", team=self.team1, field_position='field player', role='full-time')
        player4 = Player.objects.create(name="Player 4", team=self.team2, field_position='field player', role='full-time')
        
        # Re-save the match to create PlayerStatistic entries for new players
        self.match.save()
        
        # Set some players as present
        stat1 = PlayerStatistic.objects.get(player=self.player1, match=self.match)
        stat1.present = True
        stat1.save()
        
        stat4 = PlayerStatistic.objects.get(player=player4, match=self.match)
        stat4.present = True
        stat4.save()
        
        # Initialize form
        form = RosterUpdateForm(match=self.match, user=self.user)
        
        # Verify fields exist
        self.assertIn('home_team_players', form.fields)
        self.assertIn('away_team_players', form.fields)
        
        # Verify queryset counts
        self.assertEqual(form.fields['home_team_players'].queryset.count(), 2)  # player1, player3
        self.assertEqual(form.fields['away_team_players'].queryset.count(), 2)  # player2, player4
        
        # Verify initial values
        self.assertIn(self.player1, form.initial['home_team_players'])
        self.assertIn(player4, form.initial['away_team_players'])
        self.assertNotIn(player3, form.initial['home_team_players'])

    def test_roster_update_form_authorization_non_superuser_home_team(self):
        """Test RosterUpdateForm authorization: non-superuser tied to home team can't change away players."""
        player3 = Player.objects.create(name="Player 3", team=self.team2, field_position='field player', role='full-time')
        
        # Re-save the match to create PlayerStatistic entries for new players
        self.match.save()
        
        form_data = {
            'home_team_players': [self.player1.id],
            'away_team_players': [self.player2.id, player3.id]
        }
        form = RosterUpdateForm(data=form_data, match=self.match, user=self.user)
        self.assertTrue(form.is_valid())
        form.update_roster_data()
        
        # Home team player should be updated
        stat1 = PlayerStatistic.objects.get(player=self.player1, match=self.match)
        self.assertTrue(stat1.present)
        
        # Away team players should NOT be updated (user is not authorized)
        stat2 = PlayerStatistic.objects.get(player=self.player2, match=self.match)
        stat3 = PlayerStatistic.objects.get(player=player3, match=self.match)
        self.assertFalse(stat2.present)
        self.assertFalse(stat3.present)

    def test_roster_update_form_authorization_superuser_can_change_both(self):
        """Test RosterUpdateForm authorization: superuser can change both teams."""
        self.user.is_superuser = True
        self.user.save()
        
        form_data = {
            'home_team_players': [self.player1.id],
            'away_team_players': [self.player2.id]
        }
        form = RosterUpdateForm(data=form_data, match=self.match, user=self.user)
        self.assertTrue(form.is_valid())
        form.update_roster_data()
        
        # Both teams should be updated
        stat1 = PlayerStatistic.objects.get(player=self.player1, match=self.match)
        stat2 = PlayerStatistic.objects.get(player=self.player2, match=self.match)
        self.assertTrue(stat1.present)
        self.assertTrue(stat2.present)

    def test_roster_update_form_preserves_other_team_flags(self):
        """Test RosterUpdateForm.update_roster_data preserves other team's present flags."""
        # Set away team player as present
        stat2 = PlayerStatistic.objects.get(player=self.player2, match=self.match)
        stat2.present = True
        stat2.save()
        
        # Non-superuser from home team updates only home team
        form_data = {
            'home_team_players': [self.player1.id],
            'away_team_players': []  # Try to clear away team
        }
        form = RosterUpdateForm(data=form_data, match=self.match, user=self.user)
        self.assertTrue(form.is_valid())
        form.update_roster_data()
        
        # Away team player should still be present (not changed)
        stat2.refresh_from_db()
        self.assertTrue(stat2.present)
