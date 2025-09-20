from django.apps import AppConfig


class FutbolappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'futbolapp'

    def ready(self):
        import futbolapp.signals  # noqa
