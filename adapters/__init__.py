# adapters/__init__.py
from .EmailAdapter import GmailEmailAdapter
from .TelegramAdapter import TelegramAdapter
# from .DiscordAdapter import DiscordAdapter

__all__ = ["ADAPTERS"]

ADAPTERS = {
    "email": GmailEmailAdapter(),
    "telegram": TelegramAdapter(),
    # "discord": DiscordAdapter(),
}