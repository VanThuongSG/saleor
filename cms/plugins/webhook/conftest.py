import pytest

from ..manager import get_plugins_manager


@pytest.fixture
def webhook_plugin(settings):
    def factory():
        settings.PLUGINS = ["cms.plugins.webhook.plugin.WebhookPlugin"]
        manager = get_plugins_manager()
        return manager.global_plugins[0]

    return factory
