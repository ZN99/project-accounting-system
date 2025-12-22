from django.apps import AppConfig


class SubcontractManagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "subcontract_management"

    def ready(self):
        """アプリケーション起動時にシグナルを登録"""
        import subcontract_management.signals  # noqa: F401
