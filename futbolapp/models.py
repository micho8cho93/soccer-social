from django.db import models, transaction
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError

class League(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.name

class Season(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE, null=True, blank=True)
    tournament = models.ForeignKey('Tournament', on_delete=models.CASCADE, null=True, blank=True) # New field
    year = models.IntegerField()
    is_current = models.BooleanField(default=False)

    def __str__(self):
        if self.league:
            return f"{self.league.name} - {self.year}"
        elif self.tournament:
            return f"{self.tournament.name} - {self.year}"
        return f"Season {self.year}"

    def clean(self):
        if self.league and self.tournament:
            raise ValidationError("A season cannot be associated with both a league and a tournament.")
        if not self.league and not self.tournament:
            raise ValidationError("A season must be associated with either a league or a tournament.")

    def save(self, *args, **kwargs):
        self.full_clean() # Call clean method before saving
        is_new = self.pk is None  # Check if this is a new season
        super().save(*args, **kwargs)  # Save the Season object first
        if is_new:
            if self.league:
                teams = Team.objects.filter(league=self.league)
                for team in teams:
                    LeagueStanding.objects.get_or_create(team=team, season=self)
            # No automatic GroupStanding creation here, as groups are defined within Tournament

class Team(models.Model):
    name = models.CharField(max_length=100)
    league = models.ForeignKey(League, on_delete=models.CASCADE, null=True, blank=True)
    tournament = models.ForeignKey('Tournament', on_delete=models.CASCADE, null=True, blank=True) # New field

    def clean(self):
        if self.league and self.tournament:
            raise ValidationError("A team cannot be associated with both a league and a tournament.")
        if not self.league and not self.tournament:
            raise ValidationError("A team must be associated with either a league or a tournament.")

    def __str__(self):
        return self.name

class Player(models.Model):
    name = models.CharField(max_length=100)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    field_position = models.CharField(max_length=20, choices=[('field player', 'Field Player'), ('goalkeeper', 'Goalkeeper')], default='field player')
    role = models.CharField(max_length=20, choices=[('full-time', 'Full-Time'), ('ringer', 'Ringer')])
    def __str__(self):
        return self.name

class Matchday(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    number = models.PositiveIntegerField()
    date = models.DateField()
    title = models.CharField(max_length=100, blank=True, null=True) # New field for title

    class Meta:
        ordering = ['season', 'number']
        unique_together = ('season', 'number')
    def __str__(self):
        return f"Season {self.season.year} - Match Day {self.number}"

class Match(models.Model):
    matchday = models.ForeignKey(Matchday, on_delete=models.CASCADE)
    home_team = models.ForeignKey(Team, related_name='home_matches', on_delete=models.CASCADE)
    away_team = models.ForeignKey(Team, related_name='away_matches', on_delete=models.CASCADE)
    home_score = models.PositiveIntegerField(null=True, blank=True)
    away_score = models.PositiveIntegerField(null=True, blank=True)
    date = models.DateTimeField()
    
    class Meta:
        unique_together = ('matchday', 'home_team', 'away_team')
        ordering = ['date']
        verbose_name_plural = "Matches"

    def __str__(self):
        return f"{self.home_team.name} vs {self.away_team.name} on {self.date.strftime('%Y-%m-%d')}"

    def save(self, *args, **kwargs):
        old_match = None
        if self.pk:
            old_match = Match.objects.get(pk=self.pk)

        super().save(*args, **kwargs)

        # Ensure PlayerStatistic entries exist for all players in both teams
        for team in [self.home_team, self.away_team]:
            for player in team.player_set.all():
                PlayerStatistic.objects.get_or_create(player=player, match=self)

        teams_to_update = {self.home_team, self.away_team}
        if old_match:
            teams_to_update.add(old_match.home_team)
            teams_to_update.add(old_match.away_team)
        
        for team in teams_to_update:
            LeagueStanding.recalculate_for_team(team, self.matchday.season)

        LeagueStanding.update_positions_for_season(self.matchday.season)

    def delete(self, *args, **kwargs):
        season = self.matchday.season
        home_team = self.home_team
        away_team = self.away_team
        
        super().delete(*args, **kwargs)

        LeagueStanding.recalculate_for_team(home_team, season)
        LeagueStanding.recalculate_for_team(away_team, season)
        LeagueStanding.update_positions_for_season(season)

class PlayerStatistic(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    goals = models.PositiveIntegerField(default=0)
    assists = models.PositiveIntegerField(default=0)
    clean_sheets = models.PositiveIntegerField(default=0)
    yellow_cards = models.PositiveIntegerField(default=0)
    red_cards = models.PositiveIntegerField(default=0)
    present = models.BooleanField(default=False) # New field for presence

    class Meta:
        unique_together = ('player', 'match')
    def __str__(self):
        return f"{self.player.name} - {self.match}"

class LeagueStanding(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    position = models.PositiveIntegerField(default=0)
    points = models.PositiveIntegerField(default=0)
    matches_played = models.PositiveIntegerField(default=0)
    wins = models.PositiveIntegerField(default=0)
    draws = models.PositiveIntegerField(default=0)
    losses = models.PositiveIntegerField(default=0)
    goals_for = models.PositiveIntegerField(default=0)
    goals_against = models.PositiveIntegerField(default=0)
    goal_difference = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = ('team', 'season')
    def __str__(self):
        return f"{self.team.name} - {self.season.year}"

    @classmethod
    def recalculate_for_team(cls, team, season):
        standing, _ = cls.objects.get_or_create(team=team, season=season)
        
        standing.matches_played = 0
        standing.wins = 0
        standing.draws = 0
        standing.losses = 0
        standing.points = 0
        standing.goals_for = 0
        standing.goals_against = 0

        home_matches = Match.objects.filter(home_team=team, matchday__season=season, home_score__isnull=False, away_score__isnull=False)
        away_matches = Match.objects.filter(away_team=team, matchday__season=season, home_score__isnull=False, away_score__isnull=False)

        for match in home_matches:
            standing.matches_played += 1
            standing.goals_for += match.home_score
            standing.goals_against += match.away_score
            if match.home_score > match.away_score:
                standing.wins += 1
                standing.points += 3
            elif match.home_score < match.away_score:
                standing.losses += 1
            else:
                standing.draws += 1
                standing.points += 1

        for match in away_matches:
            standing.matches_played += 1
            standing.goals_for += match.away_score
            standing.goals_against += match.home_score
            if match.away_score > match.home_score:
                standing.wins += 1
                standing.points += 3
            elif match.away_score < match.home_score:
                standing.losses += 1
            else:
                standing.draws += 1
                standing.points += 1
                
        standing.goal_difference = standing.goals_for - standing.goals_against
        standing.save()

    @classmethod
    def update_positions_for_season(cls, season):
        standings = cls.objects.filter(season=season).order_by('-points', '-goal_difference', '-goals_for', 'team__name')
        position = 1
        for standing in standings:
            cls.objects.filter(pk=standing.pk).update(position=position)
            position += 1

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s profile"


# Tournament Models
class Tournament(models.Model):
    name = models.CharField(max_length=100)
    # Removed season field from here
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name # Changed to just name, as season is now on Season model

class Group(models.Model):
    name = models.CharField(max_length=100)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    teams = models.ManyToManyField(Team)

    class Meta:
        unique_together = ('name', 'tournament')

    def __str__(self):
        return f"{self.tournament.name} - Group {self.name}"

class TournamentMatch(models.Model):
    MATCH_TYPE_CHOICES = [
        ('group_stage', 'Group Stage'),
        ('quarter_final', 'Quarter-Final'),
        ('semi_final', 'Semi-Final'),
        ('final', 'Final'),
        ('third_place', '3rd Place Match'),
    ]
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True, blank=True)
    home_team = models.ForeignKey(Team, related_name='tournament_home_matches', on_delete=models.CASCADE)
    away_team = models.ForeignKey(Team, related_name='tournament_away_matches', on_delete=models.CASCADE)
    home_score = models.PositiveIntegerField(null=True, blank=True)
    away_score = models.PositiveIntegerField(null=True, blank=True)
    date = models.DateTimeField()
    title = models.CharField(max_length=100, blank=True, null=True)
    match_type = models.CharField(max_length=20, choices=MATCH_TYPE_CHOICES, default='group_stage')

    class Meta:
        ordering = ['date']
        verbose_name_plural = "Tournament Matches"

    def __str__(self):
        if self.group:
            return f"{self.home_team.name} vs {self.away_team.name} in {self.group.name}"
        else:
            return f"{self.home_team.name} vs {self.away_team.name} ({self.get_match_type_display()})"

    def save(self, *args, **kwargs):
        old_match = None
        if self.pk:
            old_match = TournamentMatch.objects.get(pk=self.pk)

        super().save(*args, **kwargs)

        # Ensure TournamentPlayerStatistic entries exist for all players in both teams
        for team in [self.home_team, self.away_team]:
            for player in team.player_set.all():
                TournamentPlayerStatistic.objects.get_or_create(player=player, tournament_match=self)

        if self.group: # Only update group standings if it's a group match
            teams_to_update = {self.home_team, self.away_team}
            if old_match and old_match.group: # Also consider old group if it existed
                teams_to_update.add(old_match.home_team)
                teams_to_update.add(old_match.away_team)
            
            for team in teams_to_update:
                GroupStanding.recalculate_for_team(team, self.group)

            GroupStanding.update_positions_for_group(self.group)

    def delete(self, *args, **kwargs):
        group = self.group
        home_team = self.home_team
        away_team = self.away_team
        
        super().delete(*args, **kwargs)

        if group: # Only recalculate group standings if it was a group match
            GroupStanding.recalculate_for_team(home_team, group)
            GroupStanding.recalculate_for_team(away_team, group)
            GroupStanding.update_positions_for_group(group)

class TournamentPlayerStatistic(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    tournament_match = models.ForeignKey(TournamentMatch, on_delete=models.CASCADE)
    goals = models.PositiveIntegerField(default=0)
    assists = models.PositiveIntegerField(default=0)
    clean_sheets = models.PositiveIntegerField(default=0)
    yellow_cards = models.PositiveIntegerField(default=0)
    red_cards = models.PositiveIntegerField(default=0)
    present = models.BooleanField(default=False)

    class Meta:
        unique_together = ('player', 'tournament_match')

    def __str__(self):
        return f"{self.player.name} - {self.tournament_match}"

class GroupStanding(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    position = models.PositiveIntegerField(default=0)
    points = models.PositiveIntegerField(default=0)
    matches_played = models.PositiveIntegerField(default=0)
    wins = models.PositiveIntegerField(default=0)
    draws = models.PositiveIntegerField(default=0)
    losses = models.PositiveIntegerField(default=0)
    goals_for = models.PositiveIntegerField(default=0)
    goals_against = models.PositiveIntegerField(default=0)
    goal_difference = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('group', 'team')

    def __str__(self):
        return f"{self.team.name} - {self.group.name}"

    @classmethod
    def recalculate_for_team(cls, team, group):
        standing, _ = cls.objects.get_or_create(team=team, group=group)
        
        standing.matches_played = 0
        standing.wins = 0
        standing.draws = 0
        standing.losses = 0
        standing.points = 0
        standing.goals_for = 0
        standing.goals_against = 0

        home_matches = TournamentMatch.objects.filter(home_team=team, group=group, home_score__isnull=False, away_score__isnull=False)
        away_matches = TournamentMatch.objects.filter(away_team=team, group=group, home_score__isnull=False, away_score__isnull=False)

        for match in home_matches:
            standing.matches_played += 1
            standing.goals_for += match.home_score
            standing.goals_against += match.away_score
            if match.home_score > match.away_score:
                standing.wins += 1
                standing.points += 3
            elif match.home_score < match.away_score:
                standing.losses += 1
            else:
                standing.draws += 1
                standing.points += 1

        for match in away_matches:
            standing.matches_played += 1
            standing.goals_for += match.away_score
            standing.goals_against += match.home_score
            if match.away_score > match.home_score:
                standing.wins += 1
                standing.points += 3
            elif match.away_score < match.home_score:
                standing.losses += 1
            else:
                standing.draws += 1
                standing.points += 1
                
        standing.goal_difference = standing.goals_for - standing.goals_against
        standing.save()

    @classmethod
    def update_positions_for_group(cls, group):
        standings = cls.objects.filter(group=group).order_by('-points', '-goal_difference', '-goals_for', 'team__name')
        position = 1
        for standing in standings:
            cls.objects.filter(pk=standing.pk).update(position=position)
            position += 1

class Referee(models.Model):
    name = models.CharField(max_length=100)
    username = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

# Pickup games
class PickupGame(models.Model):
    location = models.CharField(max_length=100)
    time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    max_players = models.IntegerField(default=10)
    current_players = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    price = models.FloatField(default=4.5)

    def clean(self):
        errors = {}

        if self.max_players < 1:
            errors['max_players'] = 'Maximum players must be at least 1.'

        if self.end_time and self.end_time <= self.time:
            errors['end_time'] = 'End time must be after the start time.'

        existing_players = self.players.count() if self.pk else self.current_players
        if self.max_players < existing_players:
            errors['max_players'] = 'Maximum players cannot be lower than the number of registered players.'

        if errors:
            raise ValidationError(errors)

    def sync_current_players(self, save=True):
        current_count = self.players.count() if self.pk else 0
        self.current_players = current_count
        if save and self.pk:
            PickupGame.objects.filter(pk=self.pk).update(current_players=current_count)
        return current_count

    @property
    def spots_remaining(self):
        return max(self.max_players - self.current_players, 0)

    @property
    def is_full(self):
        return self.current_players >= self.max_players

    def __str__(self):
        return f"Game at {self.location} on {self.time.date()}"

class PickupGamePlayer(models.Model):
    pickup_game = models.ForeignKey(PickupGame, on_delete=models.CASCADE, related_name='players')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    age = models.PositiveIntegerField()

    def clean(self):
        errors = {}

        if not self.pickup_game_id:
            errors['pickup_game'] = 'A pickup game is required.'
        else:
            available_slots = self.pickup_game.players.exclude(pk=self.pk).count()
            if not self.pickup_game.is_active:
                errors['pickup_game'] = 'Cannot register for an inactive pickup game.'
            elif available_slots >= self.pickup_game.max_players:
                errors['pickup_game'] = 'This pickup game is full.'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        old_pickup_game_id = None
        if self.pk:
            old_pickup_game_id = type(self).objects.filter(pk=self.pk).values_list('pickup_game_id', flat=True).first()

        with transaction.atomic():
            self.pickup_game = PickupGame.objects.select_for_update().get(pk=self.pickup_game_id)
            self.full_clean()
            super().save(*args, **kwargs)

            affected_game_ids = {self.pickup_game_id}
            if old_pickup_game_id and old_pickup_game_id != self.pickup_game_id:
                affected_game_ids.add(old_pickup_game_id)

            for game in PickupGame.objects.select_for_update().filter(pk__in=affected_game_ids):
                game.sync_current_players()

    def delete(self, *args, **kwargs):
        pickup_game_id = self.pickup_game_id

        with transaction.atomic():
            pickup_game = PickupGame.objects.select_for_update().get(pk=pickup_game_id)
            super().delete(*args, **kwargs)
            pickup_game.sync_current_players()

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.pickup_game}"
