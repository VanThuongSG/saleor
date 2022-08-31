import json

from django.contrib.sites.models import Site


def get_organization():
    site = Site.objects.get_current()
    return {"@type": "Organization", "name": site.name}
