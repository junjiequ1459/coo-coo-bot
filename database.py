"""Compatibility facade for the bot's PostgreSQL data access layer."""

from data.schema import init_db

# Schema migrations must complete before the card cache is loaded.
init_db()

from data.cards import (  # noqa: E402
    delete_card_from_inventory, generate_card_code, get_card_by_code_and_owner,
    get_cards_from_db_pool, get_next_mint, get_user_inventory, load_cards_cache,
    roll_card_quality, sample_rarity, save_card_to_inventory,
    transfer_cards_between_users, update_card_quality, update_card_tag,
)
from data.users import (  # noqa: E402
    add_user_drop_tickets, add_user_dust, add_user_gems, add_user_grab_tickets,
    add_user_premium, get_effective_cooldowns, get_user_cooldowns,
    get_user_drop_tickets, get_user_dust, get_user_gems, get_user_grab_tickets,
    get_user_premium_until, is_user_premium, set_user_cooldown, transfer_gems,
)

__all__ = [
    "add_user_drop_tickets",
    "add_user_dust",
    "add_user_gems",
    "add_user_grab_tickets",
    "add_user_premium",
    "delete_card_from_inventory",
    "generate_card_code",
    "get_card_by_code_and_owner",
    "get_cards_from_db_pool",
    "get_effective_cooldowns",
    "get_next_mint",
    "get_user_cooldowns",
    "get_user_drop_tickets",
    "get_user_dust",
    "get_user_gems",
    "get_user_grab_tickets",
    "get_user_inventory",
    "get_user_premium_until",
    "init_db",
    "is_user_premium",
    "load_cards_cache",
    "roll_card_quality",
    "sample_rarity",
    "save_card_to_inventory",
    "set_user_cooldown",
    "transfer_cards_between_users",
    "transfer_gems",
    "update_card_quality",
    "update_card_tag",
]
