from django.apps import AppConfig


class MembresConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'membres'

from django.apps import AppConfig

class MembresConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'membres'

    def ready(self):
        import membres.signals  # Charge les signaux