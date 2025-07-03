from django.contrib import admin
from django import forms
from datetime import datetime
from .models import League, Season, Team, Player, Matchday, Match, PlayerStatistic, LeagueStanding, Profile
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

class TeamInline(admin.TabularInline):
    model = Team
    extra = 1

@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    inlines = [TeamInline]

@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ('year', 'league', 'is_current')
    list_filter = ('league',)

# New PlayerInline class
class PlayerInline(admin.TabularInline):
    model = Player
    extra = 1
    fields = ('name', 'field_position', 'role')

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'league')
    list_filter = ('league',)
    search_fields = ('name',)
    inlines = [PlayerInline] # Add PlayerInline here

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'team', 'field_position', 'role')
    list_filter = ('team', 'field_position', 'role')
    search_fields = ('name',)

class MatchInlineForm(forms.ModelForm):
    match_time = forms.TimeField(label='Time', widget=admin.widgets.AdminTimeWidget(format='%H:%M'), required=False)

    class Meta:
        model = Match
        fields = ('home_team', 'away_team', 'match_time', 'home_score', 'away_score')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.date:
            self.fields['match_time'].initial = self.instance.date.time()

    def save(self, commit=True):
        match_time = self.cleaned_data.get('match_time')
        if self.instance.matchday and match_time:
            self.instance.date = datetime.combine(
                self.instance.matchday.date,
                match_time
            )
        return super().save(commit=commit)

class MatchInline(admin.TabularInline):
    model = Match
    form = MatchInlineForm
    extra = 1
    fk_name = 'matchday'

@admin.register(Matchday)
class MatchdayAdmin(admin.ModelAdmin):
    list_display = ('number', 'season', 'date')
    list_filter = ('season',)
    inlines = [MatchInline]

# Custom form for Match Admin to handle rosters
class MatchAdminForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            match = self.instance
            home_players = Player.objects.filter(team=match.home_team)
            away_players = Player.objects.filter(team=match.away_team)

            # Add dynamic fields for home team players
            for player in home_players:
                field_name = f'home_player_{player.id}_present'
                initial_value = PlayerStatistic.objects.filter(player=player, match=match, present=True).exists()
                self.fields[field_name] = forms.BooleanField(
                    label=f'{player.name}',
                    required=False,
                    initial=initial_value
                )
            
            # Add dynamic fields for away team players
            for player in away_players:
                field_name = f'away_player_{player.id}_present'
                initial_value = PlayerStatistic.objects.filter(player=player, match=match, present=True).exists()
                self.fields[field_name] = forms.BooleanField(
                    label=f'{player.name}',
                    required=False,
                    initial=initial_value
                )

class PlayerStatisticInline(admin.TabularInline):
    model = PlayerStatistic
    extra = 1
    fields = ('player', 'goals', 'assists', 'clean_sheets', 'yellow_cards', 'red_cards') # Removed 'present' here
    readonly_fields = ('player',)

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    form = MatchAdminForm # Use the custom form
    list_display = ('home_team', 'away_team', 'home_score', 'away_score', 'matchday', 'date')
    list_filter = ('matchday', 'matchday__season')
    search_fields = ('home_team__name', 'away_team__name')
    change_form_template = "admin/futbolapp/match/change_form.html" # Custom template
    inlines = [PlayerStatisticInline] # Re-added PlayerStatisticInline

    fieldsets = (
        (None, {
            'fields': ('matchday', 'home_team', 'away_team', 'home_score', 'away_score', 'date'),
        }),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        # Process dynamic roster fields
        home_players = Player.objects.filter(team=obj.home_team)
        away_players = Player.objects.filter(team=obj.away_team)

        for player in home_players:
            field_name = f'home_player_{player.id}_present'
            is_present = form.cleaned_data.get(field_name, False)
            player_stat, created = PlayerStatistic.objects.get_or_create(player=player, match=obj)
            player_stat.present = is_present
            player_stat.save()
        
        for player in away_players:
            field_name = f'away_player_{player.id}_present'
            is_present = form.cleaned_data.get(field_name, False)
            player_stat, created = PlayerStatistic.objects.get_or_create(player=player, match=obj)
            player_stat.present = is_present
            player_stat.save()


@admin.register(PlayerStatistic)
class PlayerStatisticAdmin(admin.ModelAdmin):
    list_display = ('player', 'match', 'present', 'goals', 'assists', 'clean_sheets')
    list_filter = ('player__team', 'match__matchday__season')
    search_fields = ('player__name',)

@admin.register(LeagueStanding)
class LeagueStandingAdmin(admin.ModelAdmin):
    list_display = ('position', 'team', 'season', 'points', 'matches_played', 'wins', 'draws', 'losses', 'goals_for', 'goals_against', 'goal_difference')
    list_filter = ('season',)
    readonly_fields = ('goal_difference',)
    ordering = ('season', 'position')

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'profile'

class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)

admin.site.unregister(User)
admin.site.register(User, UserAdmin)