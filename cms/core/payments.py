from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional


class PaymentInterface(ABC):
    @abstractmethod
    def token_is_required_as_payment_input(
        self, gateway: str, channel_slug: str
    ) -> bool:
        pass

    @abstractmethod
    def get_client_token(
        self, gateway: str, token_config: "TokenConfig", channel_slug: str
    ) -> str:
        pass

    @abstractmethod
    def list_payment_sources(
        self, gateway: str, customer_id: str, channel_slug: str
    ) -> List["CustomerSource"]:
        pass
