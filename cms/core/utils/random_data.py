import datetime
import itertools
import json
import os
import random
import unicodedata
import uuid
from collections import defaultdict
from functools import lru_cache

from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.core.files import File
from django.db import connection
from django.utils import timezone
from django.utils.text import slugify
from faker import Factory

from ...account.models import Address, User
from ...account.search import (
    generate_address_search_document_value,
    generate_user_fields_search_document_value,
)
from ...account.utils import store_user_address
from ...channel.models import Channel
from ...core.permissions import (
    AccountPermissions,   
    get_permissions,
)

from ...menu.models import Menu, MenuItem
from ...page.models import Page, PageType
from ...plugins.manager import get_plugins_manager
from ...post.models import Post, PostType, PostMedia

from ..postgres import FlatConcatSearchVector

fake = Factory.create()
fake.seed(0)

PRODUCTS_LIST_DIR = "products-list/"

DUMMY_STAFF_PASSWORD = "password"

DEFAULT_CURRENCY = os.environ.get("DEFAULT_CURRENCY", "USD")

IMAGES_MAPPING = {
    126: ["cms-headless-omnichannel-book.png"],
    127: [
        "cms-white-plimsolls-1.png",
        "cms-white-plimsolls-2.png",
        "cms-white-plimsolls-3.png",
        "cms-white-plimsolls-4.png",
    ],
    128: [
        "cms-blue-plimsolls-1.png",
        "cms-blue-plimsolls-2.png",
        "cms-blue-plimsolls-3.png",
        "cms-blue-plimsolls-4.png",
    ],
    129: ["cms-dash-force-1.png", "cms-dash-force-2.png"],
    130: ["cms-pauls-blanace-420-1.png", "cms-pauls-blanace-420-2.png"],
    131: ["cms-grey-hoodie.png"],
    132: ["cms-blue-hoodie.png"],
    133: ["cms-white-hoodie.png"],
    134: ["cms-ascii-shirt-front.png", "cms-ascii-shirt-back.png"],
    135: ["cms-team-tee-front.png", "cms-team-tee-front.png"],
    136: ["cms-polo-shirt-front.png", "cms-polo-shirt-back.png"],
    137: ["cms-blue-polygon-tee-front.png", "cms-blue-polygon-tee-back.png"],
    138: ["cms-dark-polygon-tee-front.png", "cms-dark-polygon-tee-back.png"],
    141: ["cms-beanie-1.png", "cms-beanie-2.png"],
    143: ["cms-neck-warmer.png"],
    144: ["cms-sunnies.png"],
    145: ["cms-battle-tested-book.png"],
    146: ["cms-enterprise-cloud-book.png"],
    147: ["cms-own-your-stack-and-data-book.png"],
    150: ["cms-mighty-mug.png"],
    151: ["cms-cushion-blue.png"],
    152: ["cms-apple-drink.png"],
    153: ["cms-bean-drink.png"],
    154: ["cms-banana-drink.png"],
    155: ["cms-carrot-drink.png"],
    156: ["cms-sunnies-dark.png"],
    157: [
        "cms-monospace-white-tee-front.png",
        "cms-monospace-white-tee-back.png",
    ],
    160: ["cms-gift-100.png"],
    161: ["cms-white-cubes-tee-front.png", "cms-white-cubes-tee-back.png"],
    162: ["cms-white-parrot-cushion.png"],
    163: ["cms-gift-500.png"],
    164: ["cms-gift-50.png"],
}

CATEGORY_IMAGES = {
    7: "accessories.jpg",
    8: "groceries.jpg",
    9: "apparel.jpg",
}

COLLECTION_IMAGES = {1: "summer.jpg", 2: "clothing.jpg", 3: "clothing.jpg"}


@lru_cache()
def get_sample_data():
    path = os.path.join(
        settings.PROJECT_ROOT, "cms", "static", "populatedb_data.json"
    )
    with open(path, encoding="utf8") as f:
        db_items = json.load(f)
    types = defaultdict(list)
    # Sort db objects by its model
    for item in db_items:
        model = item.pop("model")
        types[model].append(item)
    return types


def get_email(first_name, last_name):
    _first = unicodedata.normalize("NFD", first_name).encode("ascii", "ignore")
    _last = unicodedata.normalize("NFD", last_name).encode("ascii", "ignore")
    return "%s.%s@example.com" % (
        _first.lower().decode("utf-8"),
        _last.lower().decode("utf-8"),
    )


def create_post_image(post, placeholder_dir, image_name):
    image = get_image(placeholder_dir, image_name)
    # We don't want to create duplicated post images
    if post.media.count() >= len(IMAGES_MAPPING.get(post.pk, [])):
        return None
    post_image = PostMedia(post=post, image=image)
    post_image.save()
    return post_image


def create_address(save=True, **kwargs):
    address = Address(
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        street_address_1=fake.street_address(),
        city=fake.city(),
        country=settings.DEFAULT_COUNTRY,
        **kwargs,
    )

    if address.country == "US":
        state = fake.state_abbr()
        address.country_area = state
        address.postal_code = fake.postalcode_in_state(state)
    else:
        address.postal_code = fake.postalcode()

    if save:
        address.save()
    return address


def create_fake_user(user_password, save=True):
    address = create_address(save=save)
    email = get_email(address.first_name, address.last_name)

    # Skip the email if it already exists
    try:
        return User.objects.get(email=email)
    except User.DoesNotExist:
        pass

    _, max_user_id = connection.ops.integer_field_range(
        User.id.field.get_internal_type()
    )
    user = User(
        id=fake.random_int(min=1, max=max_user_id),
        first_name=address.first_name,
        last_name=address.last_name,
        email=email,
        is_active=True,
        note=fake.paragraph(),
        date_joined=fake.date_time(tzinfo=timezone.get_current_timezone()),
    )
    user.search_document = _prepare_search_document_value(user, address)

    if save:
        user.set_password(user_password)
        user.save()
        user.addresses.add(address)
    return user


def create_users(user_password, how_many=10):
    for _ in range(how_many):
        user = create_fake_user(user_password)
        yield "User: %s" % (user.email,)


def create_permission_groups(staff_password):
    super_users = User.objects.filter(is_superuser=True)
    if not super_users:
        super_users = create_staff_users(staff_password, 1, True)
    group = create_group("Full Access", get_permissions(), super_users)
    yield f"Group: {group}"

    staff_users = create_staff_users(staff_password)
    customer_support_codenames = [ ]
    customer_support_codenames.append(AccountPermissions.MANAGE_USERS.codename)
    customer_support_permissions = Permission.objects.filter(
        codename__in=customer_support_codenames
    )
    group = create_group("Customer Support", customer_support_permissions, staff_users)
    yield f"Group: {group}"


def create_staffs(staff_password):
    for permission in get_permissions():
        base_name = permission.codename.split("_")[1:]

        group_name = " ".join(base_name)
        group_name += " management"
        group_name = group_name.capitalize()

        email_base_name = [name[:-1] if name[-1] == "s" else name for name in base_name]
        user_email = ".".join(email_base_name)
        user_email += ".manager@example.com"

        user = _create_staff_user(staff_password, email=user_email)
        group = create_group(group_name, [permission], [user])

        yield f"Group: {group}"
        yield f"User: {user}"


def create_group(name, permissions, users):
    group, _ = Group.objects.get_or_create(name=name)
    group.permissions.add(*permissions)
    group.user_set.add(*users)
    return group


def _create_staff_user(staff_password, email=None, superuser=False):
    address = create_address()
    first_name = address.first_name
    last_name = address.last_name
    if not email:
        email = get_email(first_name, last_name)

    staff_user = User.objects.filter(email=email).first()
    if staff_user:
        return staff_user

    staff_user = User.objects.create_user(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=staff_password,
        is_staff=True,
        is_active=True,
        is_superuser=superuser,
        search_document=_prepare_search_document_value(
            User(email=email, first_name=first_name, last_name=last_name), address
        ),
    )
    return staff_user


def _prepare_search_document_value(user, address):
    search_document_value = generate_user_fields_search_document_value(user)
    search_document_value += generate_address_search_document_value(address)
    return search_document_value


def create_staff_users(staff_password, how_many=2, superuser=False):
    users = []
    for _ in range(how_many):
        staff_user = _create_staff_user(staff_password, superuser=superuser)
        users.append(staff_user)
    return users


def create_channel(channel_name, slug=None):
    if not slug:
        slug = slugify(channel_name)
    channel, _ = Channel.objects.get_or_create(
        slug=slug,
        defaults={
            "name": channel_name,
            "is_active": True,
        },
    )
    return f"Channel: {channel}"


def create_channels():
    yield create_channel(
        channel_name="vn",
        slug=settings.DEFAULT_CHANNEL_SLUG,
    )
    yield create_channel(
        channel_name="en",
        slug="en",
    )


def add_address_to_admin(email):
    address = create_address()
    user = User.objects.get(email=email)
    manager = get_plugins_manager()
    store_user_address(user, address, manager)
    store_user_address(user, address, manager)


def create_page_type():
    types = get_sample_data()

    data = types["page.pagetype"]

    for page_type_data in data:
        pk = page_type_data.pop("pk")
        defaults = dict(page_type_data["fields"])
        page_type, _ = PageType.objects.update_or_create(pk=pk, defaults=defaults)
        yield "Page type %s created" % page_type.slug


def create_post_type():
    types = get_sample_data()

    data = types["post.posttype"]

    for post_type_data in data:
        pk = post_type_data.pop("pk")
        defaults = dict(post_type_data["fields"])
        post_type, _ = PostType.objects.update_or_create(pk=pk, defaults=defaults)
        yield "Post type %s created" % post_type.slug


def create_pages():
    types = get_sample_data()

    data_pages = types["page.page"]

    for page_data in data_pages:
        pk = page_data["pk"]
        defaults = dict(page_data["fields"])
        defaults["page_type_id"] = defaults.pop("page_type")
        page, _ = Page.objects.update_or_create(pk=pk, defaults=defaults)
        yield "Page %s created" % page.slug


def create_posts():
    types = get_sample_data()

    data_pages = types["post.post"]

    for post_data in data_pages:
        pk = post_data["pk"]
        defaults = dict(post_data["fields"])
        defaults["post_type_id"] = defaults.pop("post_type")
        post, _ = Post.objects.update_or_create(pk=pk, defaults=defaults)
        yield "Post %s created" % post.slug


def create_menus():
    types = get_sample_data()

    menu_data = types["menu.menu"]
    menu_item_data = types["menu.menuitem"]
    for menu in menu_data:
        pk = menu["pk"]
        defaults = menu["fields"]
        menu, _ = Menu.objects.update_or_create(pk=pk, defaults=defaults)
        yield "Menu %s created" % menu.name
    for menu_item in menu_item_data:
        pk = menu_item["pk"]
        defaults = dict(menu_item["fields"])
        defaults["menu_id"] = defaults.pop("menu")
        defaults["page_id"] = defaults.pop("page")
        defaults.pop("parent")
        menu_item, _ = MenuItem.objects.update_or_create(pk=pk, defaults=defaults)
        yield "MenuItem %s created" % menu_item.name
    for menu_item in menu_item_data:
        pk = menu_item["pk"]
        defaults = dict(menu_item["fields"])
        MenuItem.objects.filter(pk=pk).update(parent_id=defaults["parent"])



def get_image(image_dir, image_name):
    img_path = os.path.join(image_dir, image_name)
    return File(open(img_path, "rb"), name=image_name)
