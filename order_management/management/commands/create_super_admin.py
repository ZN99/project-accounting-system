"""
Django management command to create a superuser
Usage: python manage.py create_super_admin <username> <email> <password>
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Create a superuser account'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username for the superuser')
        parser.add_argument('email', type=str, help='Email for the superuser')
        parser.add_argument('password', type=str, help='Password for the superuser')
        parser.add_argument(
            '--first-name',
            type=str,
            default='',
            help='First name (optional)'
        )
        parser.add_argument(
            '--last-name',
            type=str,
            default='',
            help='Last name (optional)'
        )

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']
        first_name = options.get('first_name', '')
        last_name = options.get('last_name', '')

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            existing_user = User.objects.get(username=username)
            self.stdout.write(
                self.style.WARNING(f'⚠️  User "{username}" already exists!')
            )

            # Ask if we should update to superuser
            self.stdout.write(f'Current status:')
            self.stdout.write(f'  - Superuser: {existing_user.is_superuser}')
            self.stdout.write(f'  - Staff: {existing_user.is_staff}')
            self.stdout.write(f'  - Active: {existing_user.is_active}')

            # Update to superuser
            existing_user.is_superuser = True
            existing_user.is_staff = True
            existing_user.is_active = True
            existing_user.email = email
            if first_name:
                existing_user.first_name = first_name
            if last_name:
                existing_user.last_name = last_name
            existing_user.set_password(password)
            existing_user.save()

            self.stdout.write(
                self.style.SUCCESS(f'✅ Updated "{username}" to superuser with new password')
            )
            return

        # Create new superuser
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        self.stdout.write(
            self.style.SUCCESS(f'✅ Superuser "{username}" created successfully!')
        )
        self.stdout.write(f'\nLogin credentials:')
        self.stdout.write(f'  Username: {username}')
        self.stdout.write(f'  Email: {email}')
        self.stdout.write(f'  Password: {password}')
        self.stdout.write(f'\nPermissions:')
        self.stdout.write(f'  - Superuser: Yes')
        self.stdout.write(f'  - Staff: Yes')
        self.stdout.write(f'  - Can access Django admin: Yes')
        self.stdout.write(f'  - Can access all systems: Yes')
