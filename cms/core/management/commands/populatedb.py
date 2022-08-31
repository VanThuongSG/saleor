from io import StringIO

from django.apps import apps
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection

from ....account.utils import create_superuser
from ...utils.random_data import (
    add_address_to_admin,
    create_channels,
    create_menus,
    create_page_type,
    create_pages,
    create_permission_groups,
    create_post_type,
    create_posts,
    create_staffs,
    create_users,
)


class Command(BaseCommand):
    help = "Populate database with test objects"
    placeholders_dir = "cms/static/placeholders/"

    def add_arguments(self, parser):
        parser.add_argument(
            "--createsuperuser",
            action="store_true",
            dest="createsuperuser",
            default=False,
            help="Create admin account",
        )
        parser.add_argument("--user_password", type=str, default="password")
        parser.add_argument("--staff_password", type=str, default="password")
        parser.add_argument("--superuser_password", type=str, default="admin")
        parser.add_argument(
            "--withoutimages",
            action="store_true",
            dest="withoutimages",
            default=False,
            help="Don't create product images",
        )
        parser.add_argument(
            "--skipsequencereset",
            action="store_true",
            dest="skipsequencereset",
            default=False,
            help="Don't reset SQL sequences that are out of sync.",
        )

    def sequence_reset(self):
        """Run a SQL sequence reset on all cms.* apps.

        When a value is manually assigned to an auto-incrementing field
        it doesn't update the field's sequence, which might cause a conflict
        later on.
        """
        commands = StringIO()
        for app in apps.get_app_configs():
            if "cms" in app.name:
                call_command(
                    "sqlsequencereset", app.label, stdout=commands, no_color=True
                )
        with connection.cursor() as cursor:
            cursor.execute(commands.getvalue())

    def handle(self, *args, **options):
        # set only our custom plugin to not call external API when preparing
        # example database
        user_password = options["user_password"]
        staff_password = options["staff_password"]
        superuser_password = options["superuser_password"]
        
        for msg in create_channels():
            self.stdout.write(msg)
        
        self.stdout.write("Created warehouses")
        for msg in create_page_type():
            self.stdout.write(msg)
        for msg in create_pages():
            self.stdout.write(msg)
        for msg in create_post_type():
            self.stdout.write(msg)
        for msg in create_posts():
            self.stdout.write(msg)
        for msg in create_users(user_password, 20):
            self.stdout.write(msg)        
            self.stdout.write(msg)
        for msg in create_menus():
            self.stdout.write(msg)
        
        if options["createsuperuser"]:
            credentials = {
                "email": "admin@example.com",
                "password": superuser_password,
            }
            msg = create_superuser(credentials)
            self.stdout.write(msg)
            add_address_to_admin(credentials["email"])
        if not options["skipsequencereset"]:
            self.sequence_reset()

        for msg in create_permission_groups(staff_password):
            self.stdout.write(msg)
        for msg in create_staffs(staff_password):
            self.stdout.write(msg)
