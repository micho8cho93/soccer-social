from django import forms
from .models import Player, PlayerStatistic, Match

class PlayerForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ['name', 'field_position', 'role']

class PlayerStatisticForm(forms.ModelForm):
    class Meta:
        model = PlayerStatistic
        fields = ['present', 'goals', 'assists', 'yellow_cards', 'red_cards']

class PlayerStatisticForm(forms.ModelForm):
    class Meta:
        model = PlayerStatistic
        fields = ['present', 'goals', 'assists', 'yellow_cards', 'red_cards']

class PlayerStatisticForm(forms.ModelForm):
    class Meta:
        model = PlayerStatistic
        fields = ['present', 'goals', 'assists', 'yellow_cards', 'red_cards']

class RosterUpdateForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.match = kwargs.pop('match')
        self.user = kwargs.pop('user') # Get the user from kwargs
        super().__init__(*args, **kwargs)

        home_players_queryset = Player.objects.filter(team=self.match.home_team)
        away_players_queryset = Player.objects.filter(team=self.match.away_team)

        self.fields['home_team_players'] = forms.ModelMultipleChoiceField(
            queryset=home_players_queryset,
            widget=forms.CheckboxSelectMultiple,
            required=False,
            label=f'{self.match.home_team.name} Players'
        )
        self.fields['away_team_players'] = forms.ModelMultipleChoiceField(
            queryset=away_players_queryset,
            widget=forms.CheckboxSelectMultiple,
            required=False,
            label=f'{self.match.away_team.name} Players'
        )

        # Set initial values based on existing PlayerStatistic.present
        initial_home_players = [ps.player for ps in PlayerStatistic.objects.filter(match=self.match, player__in=home_players_queryset, present=True)]
        initial_away_players = [ps.player for ps in PlayerStatistic.objects.filter(match=self.match, player__in=away_players_queryset, present=True)]
        self.initial['home_team_players'] = initial_home_players
        self.initial['away_team_players'] = initial_away_players

    def update_roster_data(self):
        present_home_players = self.cleaned_data['home_team_players']
        present_away_players = self.cleaned_data['away_team_players']

        user_team = None
        if hasattr(self.user, 'profile') and self.user.profile.team:
            user_team = self.user.profile.team

        # Only update players for the user's associated team, or if superuser
        if self.user.is_superuser or user_team == self.match.home_team:
            for player in Player.objects.filter(team=self.match.home_team):
                player_stat, created = PlayerStatistic.objects.get_or_create(player=player, match=self.match)
                player_stat.present = player in present_home_players
                player_stat.save()

        if self.user.is_superuser or user_team == self.match.away_team:
            for player in Player.objects.filter(team=self.match.away_team):
                player_stat, created = PlayerStatistic.objects.get_or_create(player=player, match=self.match)
                player_stat.present = player in present_away_players
                player_stat.save()

