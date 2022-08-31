from collections import defaultdict

from ...page.models import Page, PageType
from ..core.dataloaders import DataLoader


class PageByIdLoader(DataLoader):
    context_key = "page_by_id"

    def batch_load(self, keys):
        pages = Page.objects.using(self.database_connection_name).in_bulk(keys)
        return [pages.get(page_id) for page_id in keys]


class PageTypeByIdLoader(DataLoader):
    context_key = "page_type_by_id"

    def batch_load(self, keys):
        page_types = PageType.objects.using(self.database_connection_name).in_bulk(keys)
        return [page_types.get(page_type_id) for page_type_id in keys]


class PagesByPageTypeIdLoader(DataLoader):
    """Loads pages by pages type ID."""

    context_key = "pages_by_pagetype"

    def batch_load(self, keys):
        pages = Page.objects.using(self.database_connection_name).filter(
            page_type_id__in=keys
        )

        pagetype_to_pages = defaultdict(list)
        for page in pages:
            pagetype_to_pages[page.page_type_id].append(page)

        return [pagetype_to_pages[key] for key in keys]

