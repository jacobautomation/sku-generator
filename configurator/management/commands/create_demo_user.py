from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create/reset a demo login. Usage: python manage.py create_demo_user [username] [password]"

    def add_arguments(self, parser):
        parser.add_argument("username", nargs="?", default="david")
        parser.add_argument("password", nargs="?", default="12345")

    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"]

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"is_staff": True, "is_superuser": True},
        )
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(
            f"{action} user '{username}' with password '{password}' (staff + admin access)."
        ))