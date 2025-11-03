from django.apps import AppConfig


class OrderManagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "order_management"

    def ready(self):
        """アプリ起動時の初期化処理"""
        import order_management.signals  # シグナルハンドラをインポート
