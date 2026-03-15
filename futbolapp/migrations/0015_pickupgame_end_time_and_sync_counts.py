from django.db import migrations, models


def sync_pickup_game_counts(apps, schema_editor):
    PickupGame = apps.get_model('futbolapp', 'PickupGame')

    for game in PickupGame.objects.all():
        game.current_players = game.players.count()
        game.save(update_fields=['current_players'])


class Migration(migrations.Migration):

    dependencies = [
        ('futbolapp', '0014_alter_pickupgame_price_pickupgameplayer'),
    ]

    operations = [
        migrations.AddField(
            model_name='pickupgame',
            name='end_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(sync_pickup_game_counts, migrations.RunPython.noop),
    ]
