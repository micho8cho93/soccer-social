from django.test import TestCase
from django.contrib.auth.models import User
from futbolapp.models import League, Season, Team, Player, Matchday, Match, LeagueStanding, Tournament, Group, TournamentMatch, GroupStanding, PickupGame, PickupGamePlayer
from django.core.exceptions import ValidationError
from datetime import date, datetime, timedelta
import pytz

class ModelTests(TestCase):

    def setUp(self):
        # Common setup for all tests
        self.league = League.objects.create(name="Test League")
        self.season = Season.objects.create(league=self.league, year=2023, is_current=True)
        self.team1 = Team.objects.create(name="Team A", league=self.league)
        self.team2 = Team.objects.create(name="Team B", league=self.league)
        self.team3 = Team.objects.create(name="Team C", league=self.league)

        # Manually create LeagueStanding objects for each team
        LeagueStanding.objects.create(team=self.team1, season=self.season)
        LeagueStanding.objects.create(team=self.team2, season=self.season)
        LeagueStanding.objects.create(team=self.team3, season=self.season)

        self.matchday = Matchday.objects.create(season=self.season, number=1, date=date.today())
        self.utc = pytz.UTC

    def test_season_validation(self):
        """Test that a season cannot be associated with both a league and a tournament."""
        tournament = Tournament.objects.create(name="Test Tournament")
        with self.assertRaises(ValidationError):
            season = Season(league=self.league, tournament=tournament, year=2024)
            season.full_clean()
            season.save()


    def test_team_validation(self):
        """Test that a team cannot be associated with both a league and a tournament."""
        tournament = Tournament.objects.create(name="Test Tournament")
        with self.assertRaises(ValidationError):
            team = Team(name="Invalid Team", league=self.league, tournament=tournament)
            team.full_clean()
            team.save()

    def test_league_standing_recalculation(self):
        """Test the recalculation of league standings after a match."""
        standing1 = LeagueStanding.objects.get(team=self.team1, season=self.season)
        self.assertEqual(standing1.points, 0)

        match_time = datetime.now().replace(tzinfo=self.utc)
        match = Match.objects.create(
            matchday=self.matchday,
            home_team=self.team1,
            away_team=self.team2,
            home_score=3,
            away_score=1,
            date=match_time
        )

        LeagueStanding.recalculate_for_team(self.team1, self.season)
        LeagueStanding.recalculate_for_team(self.team2, self.season)

        standing1.refresh_from_db()
        standing2 = LeagueStanding.objects.get(team=self.team2, season=self.season)

        self.assertEqual(standing1.matches_played, 1)
        self.assertEqual(standing1.wins, 1)
        self.assertEqual(standing1.points, 3)
        self.assertEqual(standing1.goals_for, 3)
        self.assertEqual(standing1.goals_against, 1)
        self.assertEqual(standing1.goal_difference, 2)

        self.assertEqual(standing2.matches_played, 1)
        self.assertEqual(standing2.losses, 1)
        self.assertEqual(standing2.points, 0)

    def test_league_position_update(self):
        """Test the update of league positions based on standings."""
        match_time = datetime.now().replace(tzinfo=self.utc)
        Match.objects.create(matchday=self.matchday, home_team=self.team1, away_team=self.team2, home_score=2, away_score=0, date=match_time)
        Match.objects.create(matchday=self.matchday, home_team=self.team3, away_team=self.team2, home_score=4, away_score=0, date=match_time)

        LeagueStanding.update_positions_for_season(self.season)

        standing1 = LeagueStanding.objects.get(team=self.team1, season=self.season)
        standing3 = LeagueStanding.objects.get(team=self.team3, season=self.season)

        self.assertEqual(standing3.position, 1)
        self.assertEqual(standing1.position, 2)

    def test_match_save_and_delete_hooks(self):
        """Test that match save and delete hooks trigger standing recalculations."""
        match_time = datetime.now().replace(tzinfo=self.utc)
        match = Match(matchday=self.matchday, home_team=self.team1, away_team=self.team2, home_score=1, away_score=1, date=match_time)
        match.save()

        standing1 = LeagueStanding.objects.get(team=self.team1, season=self.season)
        self.assertEqual(standing1.points, 1)

        match.delete()
        standing1.refresh_from_db()
        self.assertEqual(standing1.points, 0)

    def test_group_standing_recalculation(self):
        """Test the recalculation of group standings."""
        tournament = Tournament.objects.create(name="Tournament")
        group = Group.objects.create(name="Group A", tournament=tournament)
        group.teams.add(self.team1, self.team2)

        GroupStanding.objects.create(group=group, team=self.team1)
        GroupStanding.objects.create(group=group, team=self.team2)

        match_time = datetime.now().replace(tzinfo=self.utc)
        tournament_match = TournamentMatch.objects.create(
            group=group,
            home_team=self.team1,
            away_team=self.team2,
            home_score=2,
            away_score=2,
            date=match_time
        )

        GroupStanding.recalculate_for_team(self.team1, group)
        GroupStanding.recalculate_for_team(self.team2, group)

        standing1 = GroupStanding.objects.get(team=self.team1, group=group)
        standing2 = GroupStanding.objects.get(team=self.team2, group=group)

        self.assertEqual(standing1.points, 1)
        self.assertEqual(standing1.draws, 1)
        self.assertEqual(standing2.points, 1)

    def test_group_position_update(self):
        """Test the update of group positions."""
        tournament = Tournament.objects.create(name="Tournament")
        group = Group.objects.create(name="Group A", tournament=tournament)
        team4 = Team.objects.create(name="Team D", tournament=tournament)
        group.teams.add(self.team1, self.team2, team4)

        GroupStanding.objects.create(group=group, team=self.team1)
        GroupStanding.objects.create(group=group, team=self.team2)
        GroupStanding.objects.create(group=group, team=team4)

        match_time = datetime.now().replace(tzinfo=self.utc)
        TournamentMatch.objects.create(group=group, home_team=self.team1, away_team=self.team2, home_score=3, away_score=0, date=match_time)
        TournamentMatch.objects.create(group=group, home_team=team4, away_team=self.team2, home_score=5, away_score=0, date=match_time)

        GroupStanding.update_positions_for_group(group)

        standing1 = GroupStanding.objects.get(team=self.team1, group=group)
        standing4 = GroupStanding.objects.get(team=team4, group=group)

        self.assertEqual(standing4.position, 1)
        self.assertEqual(standing1.position, 2)

    def test_pickup_game_player_limit_enforced(self):
        """Pickup games should reject registrations past max_players."""
        start_time = datetime.now().replace(tzinfo=self.utc)
        game = PickupGame.objects.create(location="Madrid", time=start_time, end_time=start_time + timedelta(hours=1), max_players=1)
        PickupGamePlayer.objects.create(
            pickup_game=game,
            first_name="Alex",
            last_name="One",
            email="alex1@example.com",
            phone_number="123456789",
            age=25,
        )

        with self.assertRaises(ValidationError):
            PickupGamePlayer.objects.create(
                pickup_game=game,
                first_name="Alex",
                last_name="Two",
                email="alex2@example.com",
                phone_number="987654321",
                age=27,
            )

        game.refresh_from_db()
        self.assertEqual(game.current_players, 1)

    def test_pickup_game_player_count_updates_on_create_and_delete(self):
        """Pickup game counts should increment on join and decrement on cancel."""
        start_time = datetime.now().replace(tzinfo=self.utc)
        game = PickupGame.objects.create(location="Madrid", time=start_time, end_time=start_time + timedelta(hours=1), max_players=2)

        player = PickupGamePlayer.objects.create(
            pickup_game=game,
            first_name="Taylor",
            last_name="Joiner",
            email="taylor@example.com",
            phone_number="123123123",
            age=29,
        )
        game.refresh_from_db()
        self.assertEqual(game.current_players, 1)

        player.delete()
        game.refresh_from_db()
        self.assertEqual(game.current_players, 0)

    def test_pickup_game_end_time_must_be_after_start_time(self):
        """Pickup games should require an end time after the start time."""
        start_time = datetime.now().replace(tzinfo=self.utc)
        game = PickupGame(
            location="Madrid",
            time=start_time,
            end_time=start_time,
            max_players=10,
        )

        with self.assertRaises(ValidationError):
            game.full_clean()
