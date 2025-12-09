from django.test import TestCase
from django.contrib.auth.models import User
from futbolapp.models import League, Season, Team, Player, Matchday, Match, LeagueStanding, Tournament, Group, TournamentMatch, GroupStanding, PlayerStatistic, TournamentPlayerStatistic
from django.core.exceptions import ValidationError
from datetime import date, datetime
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

    def test_season_neither_league_nor_tournament(self):
        """Test that a season must be associated with either a league or a tournament."""
        with self.assertRaises(ValidationError):
            season = Season(year=2024)
            season.full_clean()
            season.save()

    def test_team_neither_league_nor_tournament(self):
        """Test that a team must be associated with either a league or a tournament."""
        with self.assertRaises(ValidationError):
            team = Team(name="Invalid Team")
            team.full_clean()
            team.save()

    def test_season_save_auto_creates_league_standings(self):
        """Test that Season.save auto-creates LeagueStanding for all teams in the league on first save."""
        # Create a new league with teams but no season yet
        new_league = League.objects.create(name="New League")
        new_team1 = Team.objects.create(name="New Team 1", league=new_league)
        new_team2 = Team.objects.create(name="New Team 2", league=new_league)
        
        # Verify no standings exist yet
        self.assertEqual(LeagueStanding.objects.filter(team__league=new_league).count(), 0)
        
        # Create a new season - this should auto-create standings
        new_season = Season.objects.create(league=new_league, year=2024)
        
        # Verify standings were created for both teams
        self.assertEqual(LeagueStanding.objects.filter(season=new_season).count(), 2)
        self.assertTrue(LeagueStanding.objects.filter(team=new_team1, season=new_season).exists())
        self.assertTrue(LeagueStanding.objects.filter(team=new_team2, season=new_season).exists())

    def test_match_save_creates_player_statistics(self):
        """Test that Match.save creates PlayerStatistic entries for all players on both teams."""
        player1 = Player.objects.create(name="Player 1", team=self.team1, field_position='field player', role='full-time')
        player2 = Player.objects.create(name="Player 2", team=self.team1, field_position='goalkeeper', role='full-time')
        player3 = Player.objects.create(name="Player 3", team=self.team2, field_position='field player', role='ringer')
        
        match_time = datetime.now().replace(tzinfo=self.utc)
        match = Match.objects.create(
            matchday=self.matchday,
            home_team=self.team1,
            away_team=self.team2,
            home_score=2,
            away_score=1,
            date=match_time
        )
        
        # Verify PlayerStatistic entries were created
        self.assertEqual(PlayerStatistic.objects.filter(match=match).count(), 3)
        self.assertTrue(PlayerStatistic.objects.filter(player=player1, match=match).exists())
        self.assertTrue(PlayerStatistic.objects.filter(player=player2, match=match).exists())
        self.assertTrue(PlayerStatistic.objects.filter(player=player3, match=match).exists())

    def test_match_save_recalculates_standings_and_positions(self):
        """Test that Match.save recalculates LeagueStanding and updates positions."""
        match_time = datetime.now().replace(tzinfo=self.utc)
        match = Match.objects.create(
            matchday=self.matchday,
            home_team=self.team1,
            away_team=self.team2,
            home_score=3,
            away_score=0,
            date=match_time
        )
        
        # Verify standings were recalculated
        standing1 = LeagueStanding.objects.get(team=self.team1, season=self.season)
        standing2 = LeagueStanding.objects.get(team=self.team2, season=self.season)
        
        self.assertEqual(standing1.points, 3)
        self.assertEqual(standing1.wins, 1)
        self.assertEqual(standing2.points, 0)
        self.assertEqual(standing2.losses, 1)
        
        # Verify positions were updated
        self.assertEqual(standing1.position, 1)
        self.assertGreater(standing2.position, standing1.position)

    def test_tournament_match_save_creates_tournament_player_statistics(self):
        """Test that TournamentMatch.save creates TournamentPlayerStatistic entries for all players."""
        tournament = Tournament.objects.create(name="Test Tournament")
        group = Group.objects.create(name="Group A", tournament=tournament)
        
        player1 = Player.objects.create(name="Player 1", team=self.team1, field_position='field player', role='full-time')
        player2 = Player.objects.create(name="Player 2", team=self.team2, field_position='field player', role='full-time')
        
        match_time = datetime.now().replace(tzinfo=self.utc)
        tournament_match = TournamentMatch.objects.create(
            group=group,
            home_team=self.team1,
            away_team=self.team2,
            home_score=2,
            away_score=1,
            date=match_time
        )
        
        # Verify TournamentPlayerStatistic entries were created
        self.assertEqual(TournamentPlayerStatistic.objects.filter(tournament_match=tournament_match).count(), 2)
        self.assertTrue(TournamentPlayerStatistic.objects.filter(player=player1, tournament_match=tournament_match).exists())
        self.assertTrue(TournamentPlayerStatistic.objects.filter(player=player2, tournament_match=tournament_match).exists())

    def test_tournament_match_save_with_group_recalculates_standings(self):
        """Test that TournamentMatch.save with group set recalculates GroupStanding and positions."""
        tournament = Tournament.objects.create(name="Test Tournament")
        group = Group.objects.create(name="Group A", tournament=tournament)
        group.teams.add(self.team1, self.team2)
        
        match_time = datetime.now().replace(tzinfo=self.utc)
        tournament_match = TournamentMatch.objects.create(
            group=group,
            home_team=self.team1,
            away_team=self.team2,
            home_score=3,
            away_score=1,
            date=match_time
        )
        
        # Verify standings were recalculated
        standing1 = GroupStanding.objects.get(team=self.team1, group=group)
        standing2 = GroupStanding.objects.get(team=self.team2, group=group)
        
        self.assertEqual(standing1.points, 3)
        self.assertEqual(standing1.wins, 1)
        self.assertEqual(standing2.points, 0)
        self.assertEqual(standing2.losses, 1)
        
        # Verify positions were updated
        self.assertEqual(standing1.position, 1)
        self.assertEqual(standing2.position, 2)

    def test_tournament_match_save_without_group_no_standings_recalc(self):
        """Test that TournamentMatch.save with group=None does not recalculate standings."""
        tournament = Tournament.objects.create(name="Test Tournament")
        
        match_time = datetime.now().replace(tzinfo=self.utc)
        tournament_match = TournamentMatch.objects.create(
            group=None,
            home_team=self.team1,
            away_team=self.team2,
            home_score=2,
            away_score=1,
            date=match_time,
            match_type='final'
        )
        
        # Verify no GroupStanding entries exist for these teams
        self.assertEqual(GroupStanding.objects.filter(team=self.team1).count(), 0)
        self.assertEqual(GroupStanding.objects.filter(team=self.team2).count(), 0)

    def test_tournament_match_delete_with_group_recalculates_standings(self):
        """Test that TournamentMatch.delete with group set recalculates GroupStanding and positions."""
        tournament = Tournament.objects.create(name="Test Tournament")
        group = Group.objects.create(name="Group A", tournament=tournament)
        group.teams.add(self.team1, self.team2)
        
        match_time = datetime.now().replace(tzinfo=self.utc)
        tournament_match = TournamentMatch.objects.create(
            group=group,
            home_team=self.team1,
            away_team=self.team2,
            home_score=2,
            away_score=0,
            date=match_time
        )
        
        # Verify initial standings
        standing1 = GroupStanding.objects.get(team=self.team1, group=group)
        self.assertEqual(standing1.points, 3)
        
        # Delete the match
        tournament_match.delete()
        
        # Verify standings were recalculated (should be 0 now)
        standing1.refresh_from_db()
        self.assertEqual(standing1.points, 0)
        self.assertEqual(standing1.wins, 0)

    def test_league_standing_update_positions_tiebreak_order(self):
        """Test LeagueStanding.update_positions_for_season tie-break order: points, goal_diff, goals_for, team__name."""
        # Create teams with alphabetically sortable names
        team_alpha = Team.objects.create(name="Alpha Team", league=self.league)
        team_beta = Team.objects.create(name="Beta Team", league=self.league)
        team_gamma = Team.objects.create(name="Gamma Team", league=self.league)
        
        # Create standings with tie-break scenarios
        LeagueStanding.objects.create(team=team_alpha, season=self.season, points=3, goal_difference=2, goals_for=3)
        LeagueStanding.objects.create(team=team_beta, season=self.season, points=3, goal_difference=2, goals_for=3)
        LeagueStanding.objects.create(team=team_gamma, season=self.season, points=3, goal_difference=2, goals_for=4)
        
        LeagueStanding.update_positions_for_season(self.season)
        
        # Verify positions based on tie-break: gamma has more goals_for, then beta/alpha by name
        standing_alpha = LeagueStanding.objects.get(team=team_alpha, season=self.season)
        standing_beta = LeagueStanding.objects.get(team=team_beta, season=self.season)
        standing_gamma = LeagueStanding.objects.get(team=team_gamma, season=self.season)
        
        self.assertEqual(standing_gamma.position, 1)  # Higher goals_for
        self.assertEqual(standing_alpha.position, 2)  # Alphabetically first
        self.assertEqual(standing_beta.position, 3)   # Alphabetically second

    def test_group_standing_update_positions_tiebreak_order(self):
        """Test GroupStanding.update_positions_for_group tie-break order: points, goal_diff, goals_for, team__name."""
        tournament = Tournament.objects.create(name="Test Tournament")
        group = Group.objects.create(name="Group A", tournament=tournament)
        
        # Create teams with alphabetically sortable names
        team_alpha = Team.objects.create(name="Alpha Team", tournament=tournament)
        team_beta = Team.objects.create(name="Beta Team", tournament=tournament)
        team_gamma = Team.objects.create(name="Gamma Team", tournament=tournament)
        group.teams.add(team_alpha, team_beta, team_gamma)
        
        # Create standings with tie-break scenarios
        # team_beta and team_gamma have same points, goal_diff, and goals_for - will be sorted by name
        # team_alpha has lower goal_difference, so it should be third
        GroupStanding.objects.create(group=group, team=team_alpha, points=6, goal_difference=3, goals_for=5)
        GroupStanding.objects.create(group=group, team=team_beta, points=6, goal_difference=4, goals_for=6)
        GroupStanding.objects.create(group=group, team=team_gamma, points=6, goal_difference=4, goals_for=6)
        
        GroupStanding.update_positions_for_group(group)
        
        # Verify positions: team_beta and team_gamma tie on stats, sorted alphabetically
        standing_alpha = GroupStanding.objects.get(team=team_alpha, group=group)
        standing_beta = GroupStanding.objects.get(team=team_beta, group=group)
        standing_gamma = GroupStanding.objects.get(team=team_gamma, group=group)
        
        self.assertEqual(standing_beta.position, 1)   # Higher goal_difference
        self.assertEqual(standing_gamma.position, 2)  # Same goal_diff & goals_for as beta, alphabetically second
        self.assertEqual(standing_alpha.position, 3)  # Lower goal_difference

    def test_player_statistic_post_save_signal_updates_match_scores(self):
        """Test that PlayerStatistic post-save signal updates parent Match home_score/away_score."""
        player1 = Player.objects.create(name="Player 1", team=self.team1, field_position='field player', role='full-time')
        player2 = Player.objects.create(name="Player 2", team=self.team2, field_position='field player', role='full-time')
        
        match_time = datetime.now().replace(tzinfo=self.utc)
        match = Match.objects.create(
            matchday=self.matchday,
            home_team=self.team1,
            away_team=self.team2,
            date=match_time
        )
        
        # Initially, scores should be None or 0 (from signal)
        match.refresh_from_db()
        self.assertEqual(match.home_score, 0)
        self.assertEqual(match.away_score, 0)
        
        # Update player statistics
        stat1 = PlayerStatistic.objects.get(player=player1, match=match)
        stat1.goals = 2
        stat1.save()
        
        # Verify match score updated
        match.refresh_from_db()
        self.assertEqual(match.home_score, 2)
        self.assertEqual(match.away_score, 0)
        
        # Update away team player
        stat2 = PlayerStatistic.objects.get(player=player2, match=match)
        stat2.goals = 1
        stat2.save()
        
        match.refresh_from_db()
        self.assertEqual(match.home_score, 2)
        self.assertEqual(match.away_score, 1)
