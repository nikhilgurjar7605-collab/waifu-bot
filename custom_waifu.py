"""
handlers/custom_waifu.py  –  Custom waifu generation logic
"""

import random
import database as db

# ── Name pools for auto-generated custom waifus ────────────────────────────
FIRST_NAMES = [
    "Yuki","Sakura","Hana","Rei","Ami","Nami","Kira","Luna","Sora","Hina",
    "Miku","Aoi","Rin","Yuna","Noa","Aria","Mia","Lena","Haru","Kana",
    "Shiori","Akane","Mizuki","Koharu","Tsuki","Hikari","Asahi","Natsuki",
]
LAST_NAMES = [
    "Miyamoto","Tanaka","Suzuki","Yamamoto","Nakamura","Ito","Watanabe",
    "Kobayashi","Saito","Kato","Yoshida","Yamada","Sasaki","Matsumoto",
    "Inoue","Kimura","Hayashi","Shimizu","Yamaguchi","Ogawa",
]
ANIME_WORLDS = [
    "Eternal Chronicles","Starlight Academy","Shadow Realm",
    "Crystal Nexus","Divine Blades","Moonlit Odyssey",
    "Azure Infinity","Celestial Throne","Phantom Horizon",
    "Radiant Ascension","Echo of the Void","Twilight Resonance",
]
TITLES = [
    "the Radiant","the Eternal","the Divine","the Boundless",
    "of the Stars","of the Void","the Unbroken","the Chosen",
    "the Luminous","the Transcendent","the Forgotten","the Reborn",
]


def generate_custom_waifu(owner_id: int, owner_name: str, reason: str) -> int | None:
    """
    Generate a custom waifu entry in the database.
    Returns the character ID, or None on failure.
    """
    first  = random.choice(FIRST_NAMES)
    last   = random.choice(LAST_NAMES)
    title  = random.choice(TITLES)
    anime  = random.choice(ANIME_WORLDS)

    # Personalise name with owner name initial or suffix
    initial = owner_name[0].upper() if owner_name else "X"
    name    = f"{first} {last} {title} [{initial}]"

    # Reason-based flavour
    if "leaderboard" in reason:
        anime = f"Champions of {anime}"
    elif "milestone" in reason:
        anime = f"Treasury of {anime}"

    # Always Legendary rarity for custom waifus
    rarity    = "🌠 Legendary"
    image_url = None   # Admin can update with /addimage later

    char_id = db.add_character(
        name=name,
        anime=anime,
        rarity=rarity,
        image_url=image_url,
        added_by=0,        # 0 = system
        is_custom=1,
        owner_id=owner_id
    )
    return char_id