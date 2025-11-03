"""
ユーザーロール管理コマンド

Usage:
    # ロール一覧表示
    python manage.py manage_user_roles --list

    # 全ユーザーのロール確認
    python manage.py manage_user_roles --show-all

    # 特定ユーザーのロール確認
    python manage.py manage_user_roles --user admin --show

    # ロールを追加
    python manage.py manage_user_roles --user admin --add 役員
    python manage.py manage_user_roles --user tanaka --add 営業

    # ロールを削除
    python manage.py manage_user_roles --user admin --remove 経理

    # ロールをクリア（全削除）
    python manage.py manage_user_roles --user admin --clear
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from order_management.models import UserProfile
from order_management.user_roles import UserRole


class Command(BaseCommand):
    help = 'ユーザーロールの管理'

    def add_arguments(self, parser):
        parser.add_argument('--list', action='store_true', help='利用可能なロール一覧を表示')
        parser.add_argument('--show-all', action='store_true', help='全ユーザーのロールを表示')
        parser.add_argument('--user', type=str, help='対象ユーザー名')
        parser.add_argument('--show', action='store_true', help='ユーザーのロールを表示')
        parser.add_argument('--add', type=str, help='追加するロール')
        parser.add_argument('--remove', type=str, help='削除するロール')
        parser.add_argument('--clear', action='store_true', help='全ロールをクリア')

    def handle(self, *args, **options):
        # ロール一覧表示
        if options['list']:
            self.show_available_roles()
            return

        # 全ユーザーのロール表示
        if options['show_all']:
            self.show_all_users()
            return

        # ユーザー指定が必要な操作
        username = options.get('user')
        if not username:
            self.stdout.write(self.style.ERROR('エラー: --user でユーザー名を指定してください'))
            return

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'エラー: ユーザー "{username}" が見つかりません'))
            return

        # UserProfileを取得または作成
        profile, created = UserProfile.objects.get_or_create(user=user)
        if created:
            self.stdout.write(self.style.WARNING(f'UserProfileを新規作成しました: {username}'))

        # ロール表示
        if options['show']:
            self.show_user_roles(user, profile)
            return

        # ロール追加
        if options['add']:
            role = options['add']
            if role not in UserRole.ALL_ROLES:
                self.stdout.write(self.style.ERROR(f'エラー: "{role}" は有効なロールではありません'))
                self.show_available_roles()
                return

            if role in profile.roles:
                self.stdout.write(self.style.WARNING(f'"{role}" は既に割り当てられています'))
            else:
                profile.add_role(role)
                self.stdout.write(self.style.SUCCESS(f'✅ "{role}" を {username} に追加しました'))

            self.show_user_roles(user, profile)
            return

        # ロール削除
        if options['remove']:
            role = options['remove']
            if role in profile.roles:
                profile.remove_role(role)
                self.stdout.write(self.style.SUCCESS(f'✅ "{role}" を {username} から削除しました'))
            else:
                self.stdout.write(self.style.WARNING(f'"{role}" は割り当てられていません'))

            self.show_user_roles(user, profile)
            return

        # ロールクリア
        if options['clear']:
            old_roles = profile.roles.copy()
            profile.roles = []
            profile.save()
            self.stdout.write(self.style.SUCCESS(f'✅ {username} の全ロールをクリアしました'))
            self.stdout.write(f'   削除されたロール: {old_roles}')
            return

        # 何も指定されていない場合
        self.stdout.write(self.style.WARNING('オプションを指定してください。--help で使い方を確認できます。'))

    def show_available_roles(self):
        """利用可能なロール一覧を表示"""
        self.stdout.write('\n📋 利用可能なロール:')
        self.stdout.write('=' * 60)
        for role, description in UserRole.CHOICES:
            self.stdout.write(f'  • {role:12s} - {description}')
        self.stdout.write('=' * 60)

    def show_all_users(self):
        """全ユーザーのロールを表示"""
        self.stdout.write('\n👥 全ユーザーのロール一覧:')
        self.stdout.write('=' * 60)

        users = User.objects.all().order_by('username')
        for user in users:
            try:
                profile = user.userprofile
                roles_str = ', '.join(profile.roles) if profile.roles else '(なし)'
            except UserProfile.DoesNotExist:
                roles_str = '(UserProfileなし)'

            superuser_mark = ' 🔑' if user.is_superuser else ''
            staff_mark = ' 👔' if user.is_staff else ''

            self.stdout.write(f'  {user.username:20s} {superuser_mark}{staff_mark}')
            self.stdout.write(f'    ロール: {roles_str}')

        self.stdout.write('=' * 60)
        self.stdout.write('  🔑 = スーパーユーザー  👔 = スタッフ')

    def show_user_roles(self, user, profile):
        """ユーザーのロール情報を表示"""
        self.stdout.write(f'\n👤 ユーザー: {user.username}')
        self.stdout.write('=' * 60)
        self.stdout.write(f'  名前: {user.get_full_name() or "(未設定)"}')
        self.stdout.write(f'  メール: {user.email or "(未設定)"}')
        self.stdout.write(f'  スーパーユーザー: {"はい" if user.is_superuser else "いいえ"}')
        self.stdout.write(f'  スタッフ: {"はい" if user.is_staff else "いいえ"}')
        self.stdout.write(f'  アクティブ: {"はい" if user.is_active else "いいえ"}')
        self.stdout.write('')
        self.stdout.write(f'  割り当てられたロール:')
        if profile.roles:
            for role in profile.roles:
                self.stdout.write(f'    • {role}')
        else:
            self.stdout.write('    (なし)')
        self.stdout.write('=' * 60)
