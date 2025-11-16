from django.contrib import admin
from django import forms
from datetime import datetime
from .models import League, Season, Team, Player, Matchday, Match, PlayerStatistic, LeagueStanding, Profile, Tournament, Group, TournamentMatch, TournamentPlayerStatistic, GroupStanding, PickupGame
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

class TeamInline(admin.TabularInline):
    model = Team
    extra = 1

@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    inlines = [TeamInline]

class SeasonAdminForm(forms.ModelForm):
    class Meta:
        model = Season
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        league = cleaned_data.get('league')
        tournament = cleaned_data.get('tournament')

        if league and tournament:
            raise forms.ValidationError("A season cannot be associated with both a league and a tournament.")
        if not league and not tournament:
            raise forms.ValidationError("A season must be associated with either a league or a tournament.")
        return cleaned_data

@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    form = SeasonAdminForm
    list_display = ('year', 'league', 'tournament', 'is_current')
    list_filter = ('league', 'tournament',)

# New PlayerInline class
class PlayerInline(admin.TabularInline):
    model = Player
    extra = 1
    fields = ('name', 'field_position', 'role')

class TeamAdminForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        league = cleaned_data.get('league')
        tournament = cleaned_data.get('tournament')

        if league and tournament:
            raise forms.ValidationError("A team cannot be associated with both a league and a tournament.")
        if not league and not tournament:
            raise forms.ValidationError("A team must be associated with either a league or a tournament.")
        return cleaned_data

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    form = TeamAdminForm
    list_display = ('name', 'league', 'tournament') # Added tournament
    list_filter = ('league', 'tournament',)
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

class TournamentMatchdayInline(admin.TabularInline):
    model = TournamentMatch
    extra = 1
    fk_name = 'group'
    fields = ('home_team', 'away_team', 'home_score', 'away_score', 'date', 'title')

@admin.register(Matchday)
class MatchdayAdmin(admin.ModelAdmin):
    list_display = ('number', 'season', 'date', 'title') # Added title
    list_filter = ('season',)
    inlines = [MatchInline]
    fieldsets = (
        (None, {
            'fields': ('season', 'number', 'date', 'title'), # Added title
        }),
    )

    

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


# Tournament Admin
class GroupInline(admin.TabularInline):
    model = Group
    extra = 1
    fields = ('name', 'teams')
    filter_horizontal = ('teams',)

class TournamentMatchInline(admin.TabularInline):
    model = TournamentMatch
    extra = 1
    fk_name = 'group'
    fields = ('home_team', 'away_team', 'home_score', 'away_score', 'date', 'title') # Added title

# Removed @admin.register(Group)
# class GroupAdmin(admin.ModelAdmin):
#     list_display = ('name', 'tournament')
#     list_filter = ('tournament',)
#     inlines = [TournamentMatchInline]
#     exclude = ('teams',)

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ('name', ) # Removed season from list_display
    list_filter = ('season',)
    inlines = [GroupInline]

class TournamentMatchAdminForm(forms.ModelForm):
    class Meta:
        model = TournamentMatch
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        match_type = cleaned_data.get('match_type')
        group = cleaned_data.get('group')

        if match_type == 'group_stage':
            if not group:
                self.add_error('group', "Group must be provided for group stage matches.")
        else: # Knockout matches
            if group:
                self.add_error('group', "Group must be empty for knockout matches.")
        return cleaned_data

@admin.register(TournamentMatch)
class TournamentMatchAdmin(admin.ModelAdmin):
    form = TournamentMatchAdminForm
    list_display = ('home_team', 'away_team', 'home_score', 'away_score', 'group', 'match_type', 'date', 'title')
    list_filter = ('group__tournament', 'group', 'match_type')
    search_fields = ('home_team__name', 'away_team__name')
    fieldsets = (
        (None, {
            'fields': ('group', 'match_type', 'home_team', 'away_team', 'home_score', 'away_score', 'date', 'title'),
        }),
    )

class TournamentPlayerStatisticInline(admin.TabularInline):
    model = TournamentPlayerStatistic
    extra = 1
    fields = ('player', 'goals', 'assists', 'clean_sheets', 'yellow_cards', 'red_cards', 'present')

@admin.register(TournamentPlayerStatistic)
class TournamentPlayerStatisticAdmin(admin.ModelAdmin):
    list_display = ('player', 'tournament_match', 'present', 'goals', 'assists', 'clean_sheets')
    list_filter = ('player__team', 'tournament_match__group__tournament__season')
    search_fields = ('player__name',)

@admin.register(GroupStanding)
class GroupStandingAdmin(admin.ModelAdmin):
    list_display = ('position', 'team', 'group', 'points', 'matches_played', 'wins', 'draws', 'losses', 'goals_for', 'goals_against', 'goal_difference')
    list_filter = ('group__tournament', 'group')
    readonly_fields = ('goal_difference',)
    ordering = ('group', 'position')

from .models import Referee

@admin.register(Referee)
class RefereeAdmin(admin.ModelAdmin):
    list_display = ('name', 'username')
    search_fields = ('name', 'username')

# ====================
# PICKUP GAMES ADMIN
# ====================

@admin.register(PickupGame)
class PickupGameAdmin(admin.ModelAdmin):
    list_display = ('get_game_title', 'get_formatted_time', 'location', 'current_players', 'max_players', 'price', 'is_active')
    list_filter = ('is_active', 'location')
    search_fields = ('location',)
    date_hierarchy = 'time'
    
    fieldsets = (
        ('Game Information', {
            'fields': ('location', 'time', 'price')
        }),
        ('Players', {
            'fields': ('max_players', 'current_players')
        }),
        ('Settings', {
            'fields': ('is_active',)
        }),
    )
    
    readonly_fields = ('current_players',)
    
    def get_game_title(self, obj):
        """Generate a title for the game based on location and date"""
        return f"Pickup Game - {obj.location}"
    get_game_title.short_description = 'Game'
    get_game_title.admin_order_field = 'location'
    
    def get_formatted_time(self, obj):
        """Display formatted date and time"""
        return obj.time.strftime('%A, %B %d, %Y at %I:%M %p')
    get_formatted_time.short_description = 'Date & Time'
    get_formatted_time.admin_order_field = 'time'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.order_by('-time')
    
    actions = ['activate_games', 'deactivate_games']
    
    def activate_games(self, request, queryset):
        """Bulk activate selected games"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} game(s) successfully activated.')
    activate_games.short_description = 'Activate selected games'
    
    def deactivate_games(self, request, queryset):
        """Bulk deactivate selected games"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} game(s) successfully deactivated.')
    deactivate_games.short_description = 'Deactivate selected games'
