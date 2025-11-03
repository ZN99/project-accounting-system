"""
Django management command to reset user password
Usage: python manage.py reset_password <username> <new_password>
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Reset user password'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to reset password for')
        parser.add_argument('password', type=str, help='New password')

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']

        try:
            user = User.objects.get(username=username)
            user.set_password(password)
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'✅ Password successfully changed for user: {username}')
            )
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ User "{username}" not found')
            )
            self.stdout.write('\nAvailable users:')
            for u in User.objects.all():
                self.stdout.write(f'  - {u.username} ({u.get_full_name() or "No name"})')
