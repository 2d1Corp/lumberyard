from django.core.management import BaseCommand

from lumberyard.models import Worker


class Command(BaseCommand):
    help = "create test user"
    def handle(self, *args, **options):
        user, created = Worker.objects.get_or_create(
            username="user",
            defaults={"phone_number": "+380501234567"},
        )
        user.set_password("user12345")
        user.save()
        self.stdout.write(
            self.style.SUCCESS(
                "Demo user 'user'" + ("created." if created else "password reset.")
            )
        )
