import getpass
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from pilot.models import Venue, Membership, Table


class Command(BaseCommand):
    help = "Create a venue or add a new named operator to an existing venue."

    def add_arguments(self, p):
        p.add_argument("venue")
        p.add_argument("username")
        p.add_argument("--role", choices=["owner", "manager", "staff"], default="staff")
        p.add_argument("--tables", type=int, default=8)

    @transaction.atomic
    def handle(self, venue, username, role, tables, **kwargs):
        if (
            not 1 <= tables <= 100
            or get_user_model().objects.filter(username=username).exists()
        ):
            raise CommandError("Choose a new username and between 1 and 100 tables.")
        password = getpass.getpass("New operator password (12+ characters): ")
        if len(password) < 12:
            raise CommandError("Use at least 12 characters.")
        v, _ = Venue.objects.get_or_create(name=venue)
        for i in range(1, tables + 1):
            Table.objects.get_or_create(venue=v, label=f"Table {i:02}")
        u = get_user_model().objects.create_user(username, password=password)
        Membership.objects.create(user=u, role=role, venue=v)
        self.stdout.write("Venue, operator and tables are ready.")
