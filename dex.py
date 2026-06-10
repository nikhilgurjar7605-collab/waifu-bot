#!/usr/bin/env python3
"""
🐉 HTTYD DRAGON DATABASE
How to Train Your Dragon - Complete Dragon Pokedex
Single file database for Telegram Bot integration

Run: python dex.py
"""

# ============================================================================
# COMPLETE HTTYD DRAGON DATABASE (17 Dragons)
# ============================================================================

DRAGONS = {
    # ========================================================================
    # LEGENDARY DRAGONS
    # ========================================================================
    
    1: {
        "id": 1,
        "name": "Toothless",
        "movie_name": "Night Fury",
        "emoji": "⚫🐉",
        "type_primary": "Storm",
        "type_secondary": "Astral",
        "rarity": "Legendary",
        "catch_rate": 3,
        "base_stats": {
            "hp": 85,
            "atk": 24,
            "def": 16,
            "spa": 22,
            "spd": 16,
            "spe": 25
        },
        "abilities": {
            "primary": "Plasma Strike",
            "hidden": "Alpha Dragon"
        },
        "evolution": {
            "evolves_to": None,
            "level": None,
            "item": "Dragon Eye Crystal"
        },
        "lore": "The last of the Night Furies. Lightning-fast and incredibly intelligent. Bonds for life with its rider.",
        "movie": "How to Train Your Dragon",
        "rider": "Hiccup",
        "height": 1.8,
        "weight": 68.5,
        "starter_moves": ["plasma_blast", "dive_bomb", "tail_fin_slam"]
    },
    
    2: {
        "id": 2,
        "name": "Light Fury",
        "movie_name": "Light Fury",
        "emoji": "⚪✨",
        "type_primary": "Storm",
        "type_secondary": "Astral",
        "rarity": "Legendary",
        "catch_rate": 5,
        "base_stats": {
            "hp": 80,
            "atk": 22,
            "def": 15,
            "spa": 21,
            "spd": 15,
            "spe": 26
        },
        "abilities": {
            "primary": "Cloaking",
            "hidden": "Plasma Stealth"
        },
        "evolution": {"evolves_to": None, "level": None, "item": None},
        "lore": "A rare female Night Fury variant. Can turn invisible and shoot precise plasma blasts. Toothless's mate.",
        "movie": "How to Train Your Dragon: The Hidden World",
        "rider": "Wild",
        "height": 1.7,
        "weight": 64.2,
        "starter_moves": ["plasma_blast", "invisibility", "lightning_strike"]
    },
    
    3: {
        "id": 3,
        "name": "Bewilderbeast",
        "movie_name": "Bewilderbeast",
        "emoji": "⚪👑",
        "type_primary": "Glacial",
        "type_secondary": "Astral",
        "rarity": "Legendary",
        "catch_rate": 3,
        "base_stats": {
            "hp": 130,
            "atk": 20,
            "def": 22,
            "spa": 18,
            "spd": 22,
            "spe": 12
        },
        "abilities": {
            "primary": "Alpha Command",
            "hidden": "Ice Fortress"
        },
        "evolution": {"evolves_to": None, "level": None, "item": None},
        "lore": "A massive Alpha dragon that can control other dragons with its will. Shoots ice beams and creates glaciers.",
        "movie": "How to Train Your Dragon 2",
        "rider": "Berk's Alpha",
        "height": 8.5,
        "weight": 456.8,
        "starter_moves": ["ice_beam", "alpha_roar", "glacier_create"]
    },
    
    # ========================================================================
    # EPIC DRAGONS
    # ========================================================================
    
    4: {
        "id": 4,
        "name": "Cloudjumper",
        "movie_name": "Stormcutter",
        "emoji": "🟣🌀",
        "type_primary": "Storm",
        "type_secondary": "Glacial",
        "rarity": "Epic",
        "catch_rate": 60,
        "base_stats": {
            "hp": 85,
            "atk": 17,
            "def": 15,
            "spa": 18,
            "spd": 15,
            "spe": 20
        },
        "abilities": {
            "primary": "Four Wings",
            "hidden": "Storm Caller"
        },
        "evolution": {"evolves_to": None, "level": None, "item": None},
        "lore": "A majestic Stormcutter with four wings. Can create massive tornadoes and control storms.",
        "movie": "How to Train Your Dragon 2",
        "rider": "Valka",
        "height": 3.5,
        "weight": 112.3,
        "starter_moves": ["tornado", "ice_blast", "aerial_dive"]
    },
    
    5: {
        "id": 5,
        "name": "Shattermaster",
        "movie_name": "Screaming Death",
        "emoji": "⚪",
        "type_primary": "Terra",
        "type_secondary": "Ember",
        "rarity": "Epic",
        "catch_rate": 50,
        "base_stats": {
            "hp": 100,
            "atk": 20,
            "def": 16,
            "spa": 15,
            "spd": 16,
            "spe": 11
        },
        "abilities": {
            "primary": "Tunnel Master",
            "hidden": "Ringed Fury"
        },
        "evolution": {"evolves_to": None, "level": None, "item": None},
        "lore": "A massive albino Screaming Death. Can tunnel through earth and shoot devastating fireballs.",
        "movie": "Dragons: Riders of Berk",
        "rider": "Dagur",
        "height": 4.2,
        "weight": 198.5,
        "starter_moves": ["fire_burst", "tunnel_strike", "tail_whip"]
    },
    
    6: {
        "id": 6,
        "name": "Fireworm Queen",
        "movie_name": "Fireworm Queen",
        "emoji": "🔴👑",
        "type_primary": "Ember",
        "type_secondary": None,
        "rarity": "Epic",
        "catch_rate": 55,
        "base_stats": {
            "hp": 90,
            "atk": 19,
            "def": 16,
            "spa": 20,
            "spd": 16,
            "spe": 15
        },
        "abilities": {
            "primary": "Fire Immunity",
            "hidden": "Queen's Command"
        },
        "evolution": {"evolves_to": None, "level": None, "item": None},
        "lore": "The massive alpha of all Fireworms. Can control smaller Fireworms and breathe intense flames.",
        "movie": "Dragons: Riders of Berk",
        "rider": "None",
        "height": 3.8,
        "weight": 156.9,
        "starter_moves": ["inferno", "fireworm_summon", "flame_breath"]
    },
    
    # ========================================================================
    # RARE DRAGONS
    # ========================================================================
    
    7: {
        "id": 7,
        "name": "Stormfly",
        "movie_name": "Deadly Nadder",
        "emoji": "🔵⚡",
        "type_primary": "Storm",
        "type_secondary": "Ember",
        "rarity": "Rare",
        "catch_rate": 75,
        "base_stats": {
            "hp": 70,
            "atk": 18,
            "def": 12,
            "spa": 16,
            "spd": 12,
            "spe": 19
        },
        "abilities": {
            "primary": "Spitfire",
            "hidden": "Magnesium Blast"
        },
        "evolution": {"evolves_to": None, "level": None, "item": None},
        "lore": "A fierce and beautiful Deadly Nadder. Shoots magnesium blasts and deadly tail spines. Very competitive.",
        "movie": "How to Train Your Dragon",
        "rider": "Astrid",
        "height": 2.1,
        "weight": 45.3,
        "starter_moves": ["tail_spine", "fire_breath", "wing_slash"]
    },
    
    8: {
        "id": 8,
        "name": "Skullcrusher",
        "movie_name": "Rumblehorn",
        "emoji": "🟤🦏",
        "type_primary": "Terra",
        "type_secondary": None,
        "rarity": "Rare",
        "catch_rate": 85,
        "base_stats": {
            "hp": 95,
            "atk": 18,
            "def": 17,
            "spa": 10,
            "spd": 15,
            "spe": 9
        },
        "abilities": {
            "primary": "Thick Skull",
            "hidden": "Earth Shaker"
        },
        "evolution": {"evolves_to": None, "level": None, "item": None},
        "lore": "A massive Rumblehorn with incredible tracking abilities. Can sense vibrations through the earth.",
        "movie": "How to Train Your Dragon 2",
        "rider": "Stoick",
        "height": 2.6,
        "weight": 145.7,
        "starter_moves": ["horn_charge", "earthquake", "stomp"]
    },
    
    9: {
        "id": 9,
        "name": "Thornado",
        "movie_name": "Thunderdrum",
        "emoji": "🔵🔊",
        "type_primary": "Storm",
        "type_secondary": None,
        "rarity": "Rare",
        "catch_rate": 90,
        "base_stats": {
            "hp": 85,
            "atk": 17,
            "def": 14,
            "spa": 15,
            "spd": 14,
            "spe": 13
        },
        "abilities": {
            "primary": "Sonic Boom",
            "hidden": "Thunderous Roar"
        },
        "evolution": {"evolves_to": None, "level": None, "item": None},
        "lore": "A massive Thunderdrum that creates sonic booms. Once wild, later bonded with Stoick.",
        "movie": "Dragons: Riders of Berk",
        "rider": "Stoick",
        "height": 2.9,
        "weight": 134.2,
        "starter_moves": ["sonic_boom", "thunder_clap", "roar"]
    },
    
    10: {
        "id": 10,
        "name": "Scauldron",
        "movie_name": "Scauldron",
        "emoji": "🌊🐉",
        "type_primary": "Glacial",
        "type_secondary": "Ember",
        "rarity": "Rare",
        "catch_rate": 85,
        "base_stats": {
            "hp": 95,
            "atk": 17,
            "def": 16,
            "spa": 18,
            "spd": 16,
            "spe": 10
        },
        "abilities": {
            "primary": "Boiling Water",
            "hidden": "Aquatic"
        },
        "evolution": {"evolves_to": None, "level": None, "item": None},
        "lore": "A massive aquatic dragon that boils water in its body and shoots scalding blasts.",
        "movie": "Dragons: Defenders of Berk",
        "rider": "None",
        "height": 4.5,
        "weight": 212.4,
        "starter_moves": ["scalding_blast", "water_spout", "dive"]
    },
    
    # ========================================================================
    # UNCOMMON DRAGONS
    # ========================================================================
    
    11: {
        "id": 11,
        "name": "Barf & Belch",
        "movie_name": "Hideous Zippleback",
        "emoji": "🟢🐉",
        "type_primary": "Storm",
        "type_secondary": "Ember",
        "rarity": "Uncommon",
        "catch_rate": 120,
        "base_stats": {
            "hp": 80,
            "atk": 16,
            "def": 14,
            "spa": 15,
            "spd": 14,
            "spe": 12
        },
        "abilities": {
            "primary": "Gas & Spark",
            "hidden": "Two Heads"
        },
        "evolution": {"evolves_to": None, "level": None, "item": None},
        "lore": "A two-headed Zippleback. One head breathes gas, the other creates sparks. Chaotic but powerful.",
        "movie": "How to Train Your Dragon",
        "rider": "Tuffnut & Ruffnut",
        "height": 2.8,
        "weight": 98.4,
        "starter_moves": ["gas_blast", "spark_ignition", "dual_bite"]
    },
    
    12: {
        "id": 12,
        "name": "Hookfang",
        "movie_name": "Monstrous Nightmare",
        "emoji": "🔴",
        "type_primary": "Ember",
        "type_secondary": None,
        "rarity": "Uncommon",
        "catch_rate": 110,
        "base_stats": {
            "hp": 75,
            "atk": 19,
            "def": 13,
            "spa": 14,
            "spd": 13,
            "spe": 14
        },
        "abilities": {
            "primary": "Fire Immunity",
            "hidden": "Flame Body"
        },
        "evolution": {"evolves_to": None, "level": None, "item": None},
        "lore": "A prideful Monstrous Nightmare that sets itself on fire. Very temperamental but fiercely loyal.",
        "movie": "How to Train Your Dragon",
        "rider": "Snotlout",
        "height": 2.3,
        "weight": 87.6,
        "starter_moves": ["flame_whirl", "fire_immersion", "headbutt"]
    },
    
    13: {
        "id": 13,
        "name": "Slitherwing",
        "movie_name": "Slitherwing",
        "emoji": "🟢🐍",
        "type_primary": "Terra",
        "type_secondary": "Glacial",
        "rarity": "Uncommon",
        "catch_rate": 100,
        "base_stats": {
            "hp": 80,
            "atk": 16,
            "def": 15,
            "spa": 14,
            "spd": 15,
            "spe": 14
        },
        "abilities": {
            "primary": "Venom Shot",
            "hidden": "Camouflage"
        },
        "evolution": {"evolves_to": None, "level": None, "item": None},
        "lore": "A venomous dragon that can turn invisible. Extremely territorial and aggressive.",
        "movie": "Dragons: Race to the Edge",
        "rider": "Tuffnut",
        "height": 2.4,
        "weight": 98.7,
        "starter_moves": ["venom_spit", "constrict", "stealth"]
    },
    
    # ========================================================================
    # COMMON DRAGONS
    # ========================================================================
    
    14: {
        "id": 14,
        "name": "Meatlug",
        "movie_name": "Gronckle",
        "emoji": "🟤",
        "type_primary": "Terra",
        "type_secondary": "Ember",
        "rarity": "Common",
        "catch_rate": 180,
        "base_stats": {
            "hp": 90,
            "atk": 12,
            "def": 18,
            "spa": 10,
            "spd": 16,
            "spe": 6
        },
        "abilities": {
            "primary": "Rock Eater",
            "hidden": "Lava Breather"
        },
        "evolution": {"evolves_to": None, "level": None, "item": None},
        "lore": "A gentle Gronckle that eats rocks and breathes lava. Slow but incredibly strong and loyal.",
        "movie": "How to Train Your Dragon",
        "rider": "Fishlegs",
        "height": 1.5,
        "weight": 156.8,
        "starter_moves": ["lava_blast", "rock_crunch", "body_slam"]
    },
    
    15: {
        "id": 15,
        "name": "Dart",
        "movie_name": "Night Light",
        "emoji": "⚫👶",
        "type_primary": "Storm",
        "type_secondary": "Astral",
        "rarity": "Epic",
        "catch_rate": 45,
        "base_stats": {
            "hp": 65,
            "atk": 18,
            "def": 13,
            "spa": 17,
            "spd": 13,
            "spe": 21
        },
        "abilities": {
            "primary": "Young Fury",
            "hidden": "Hybrid Power"
        },
        "evolution": {"evolves_to": None, "level": None, "item": None},
        "lore": "One of Toothless and Light Fury's offspring. A Night Light with both parents' abilities.",
        "movie": "How to Train Your Dragon: The Hidden World",
        "rider": "None",
        "height": 1.2,
        "weight": 42.8,
        "starter_moves": ["plasma_blast", "quick_attack", "glide"]
    },
    
    16: {
        "id": 16,
        "name": "Pouncer",
        "movie_name": "Night Light",
        "emoji": "⚫🐾",
        "type_primary": "Storm",
        "type_secondary": "Astral",
        "rarity": "Epic",
        "catch_rate": 45,
        "base_stats": {
            "hp": 68,
            "atk": 19,
            "def": 12,
            "spa": 16,
            "spd": 12,
            "spe": 22
        },
        "abilities": {
            "primary": "Young Fury",
            "hidden": "Hybrid Power"
        },
        "evolution": {"evolves_to": None, "level": None, "item": None},
        "lore": "One of Toothless and Light Fury's offspring. Playful but fierce when protecting family.",
        "movie": "How to Train Your Dragon: The Hidden World",
        "rider": "None",
        "height": 1.3,
        "weight": 45.1,
        "starter_moves": ["plasma_blast", "pounce", "tail_slam"]
    },
    
    17: {
        "id": 17,
        "name": "Ruffrunner",
        "movie_name": "Night Light",
        "emoji": "⚫🏃",
        "type_primary": "Storm",
        "type_secondary": "Astral",
        "rarity": "Epic",
        "catch_rate": 45,
        "base_stats": {
            "hp": 66,
            "atk": 17,
            "def": 13,
            "spa": 18,
            "spd": 13,
            "spe": 23
        },
        "abilities": {
            "primary": "Young Fury",
            "hidden": "Hybrid Power"
        },
        "evolution": {"evolves_to": None, "level": None, "item": None},
        "lore": "One of Toothless and Light Fury's offspring. The fastest of the three siblings.",
        "movie": "How to Train Your Dragon: The Hidden World",
        "rider": "None",
        "height": 1.2,
        "weight": 43.6,
        "starter_moves": ["plasma_blast", "speed_boost", "dive"]
    }
}

# ============================================================================
# TYPE EFFECTIVENESS CHART
# ============================================================================

TYPE_EFFECTIVENESS = {
    "Ember": {
        "strong_against": ["Terra", "Glacial"],
        "weak_against": ["Glacial", "Storm"],
        "immune_to": []
    },
    "Glacial": {
        "strong_against": ["Terra", "Storm"],
        "weak_against": ["Ember", "Terra"],
        "immune_to": []
    },
    "Terra": {
        "strong_against": ["Storm", "Ember"],
        "weak_against": ["Glacial", "Storm"],
        "immune_to": []
    },
    "Storm": {
        "strong_against": ["Glacial", "Terra"],
        "weak_against": ["Ember", "Terra"],
        "immune_to": []
    },
    "Astral": {
        "strong_against": ["Ember", "Glacial", "Terra", "Storm"],
        "weak_against": [],
        "immune_to": ["Astral"]
    }
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_dragon_by_id(dragon_id: int) -> dict:
    """Get dragon data by ID"""
    return DRAGONS.get(dragon_id)

def get_dragon_by_name(name: str) -> dict:
    """Get dragon data by name (case-insensitive)"""
    for dragon in DRAGONS.values():
        if dragon["name"].lower() == name.lower():
            return dragon
    return None

def get_dragons_by_rarity(rarity: str) -> list:
    """Get all dragons of a specific rarity"""
    return [d for d in DRAGONS.values() if d["rarity"].lower() == rarity.lower()]

def get_dragons_by_type(dragon_type: str) -> list:
    """Get all dragons of a specific type"""
    return [d for d in DRAGONS.values() 
            if d["type_primary"] == dragon_type or d["type_secondary"] == dragon_type]

def get_dragons_by_movie(movie: str) -> list:
    """Get all dragons from a specific movie"""
    return [d for d in DRAGONS.values() if movie.lower() in d["movie"].lower()]

def get_dragons_by_rider(rider: str) -> list:
    """Get all dragons ridden by a specific character"""
    return [d for d in DRAGONS.values() if rider.lower() in d["rider"].lower()]

def calculate_type_effectiveness(attack_type: str, defense_type: str, defense_type2: str = None) -> float:
    """Calculate damage multiplier based on types"""
    multiplier = 1.0
    
    if attack_type in TYPE_EFFECTIVENESS:
        # Check primary defense type
        if defense_type in TYPE_EFFECTIVENESS[attack_type]["strong_against"]:
            multiplier *= 2.0
        elif defense_type in TYPE_EFFECTIVENESS[attack_type]["weak_against"]:
            multiplier *= 0.5
        
        # Check secondary defense type if exists
        if defense_type2:
            if defense_type2 in TYPE_EFFECTIVENESS[attack_type]["strong_against"]:
                multiplier *= 2.0
            elif defense_type2 in TYPE_EFFECTIVENESS[attack_type]["weak_against"]:
                multiplier *= 0.5
    
    return multiplier

def get_stat_bar(base_stat: int, max_bars: int = 5) -> str:
    """Generate visual stat bar (■□□□□)"""
    if base_stat < 40:
        bars = 1
    elif base_stat < 60:
        bars = 2
    elif base_stat < 90:
        bars = 3
    elif base_stat < 120:
        bars = 4
    else:
        bars = 5
    
    return "■" * bars + "□" * (max_bars - bars)

def calculate_stat_range(base_stat: int, level: int = 100) -> tuple:
    """Calculate min and max stat values at a given level"""
    if base_stat == 85:  # HP formula
        min_stat = int((2 * base_stat + 0 + 0) * level / 100 + level + 10)
        max_stat = int((2 * base_stat + 31 + 255) * level / 100 + level + 10)
    else:
        min_stat = int((2 * base_stat + 0 + 0) * level / 100 + 5)
        max_stat = int((2 * base_stat + 31 + 255) * level / 100 + 5)
    return min_stat, max_stat

def search_dragons(query: str) -> list:
    """Search dragons by name, movie, or rider"""
    query = query.lower()
    results = []
    for dragon in DRAGONS.values():
        if (query in dragon["name"].lower() or 
            query in dragon["movie_name"].lower() or
            query in dragon["rider"].lower() or
            query in dragon["movie"].lower()):
            results.append(dragon)
    return results

def format_dragon_card(dragon: dict, level: int = 1) -> str:
    """Format a dragon as a beautiful card for Telegram"""
    stats = dragon["base_stats"]
    
    card = f"""
🐉 **{dragon['name']}** {dragon['emoji']}
*{dragon['movie_name']}*

○ **𝙴𝙻𝙼** : {dragon['movie'].split(':')[0]}
● **𝚃𝚈𝙿𝚂** : {dragon['type_primary']} {dragon['type_secondary'] or ''}
○ **𝚁𝙰𝙸𝚈** : {dragon['rarity']}
● **𝙲𝙰𝚃𝙲𝙷 𝚁𝙰𝙴** : {dragon['catch_rate']} ({dragon['catch_rate']/2.55:.2f}%)

○ **𝙳𝚁𝙶𝙾𝙽𝙳𝙴𝚇 𝙸** : #{dragon['id']:03d}
● **𝙰𝙸𝙻𝙸𝚃𝙴** : {dragon['abilities']['primary']}
○ **𝙷𝙳𝙳𝙽 𝙰𝙱𝙻𝚃** : {dragon['abilities']['hidden']}

**𝙱𝙰𝙴 𝚂𝙰𝚂** (Level {level})
"""
    
    # Add stats with bars
    stat_names = {"hp": "HP", "atk": "Atk", "def": "Def", "spa": "SpA", "spd": "SpD", "spe": "Spe"}
    for stat_key, stat_name in stat_names.items():
        base = stats[stat_key]
        min_val, max_val = calculate_stat_range(base, level)
        bar = get_stat_bar(base)
        card += f"{stat_name}: {base:<3} ({min_val}-{max_val:<3}) {bar}\n"
    
    card += f"\n*{dragon['lore']}*"
    card += f"\n\n🎬 **Movie**: {dragon['movie']}"
    card += f"\n👤 **Rider**: {dragon['rider']}"
    
    return card

# ============================================================================
# TEST & DEMO (Run this file directly)
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🐉 HTTYD DRAGON DATABASE - TEST MODE")
    print("=" * 70)
    print(f"\n✅ Total Dragons Loaded: {len(DRAGONS)}\n")
    
    # Show rarity distribution
    print("📊 **RARITY DISTRIBUTION**:")
    rarities = {}
    for dragon in DRAGONS.values():
        rarity = dragon["rarity"]
        rarities[rarity] = rarities.get(rarity, 0) + 1
    
    for rarity, count in sorted(rarities.items()):
        print(f"   {rarity}: {count} dragons")
    
    # Show all dragons
    print("\n" + "=" * 70)
    print("📖 **COMPLETE DRAGON LIST**:")
    print("=" * 70)
    
    for dragon_id in sorted(DRAGONS.keys()):
        dragon = DRAGONS[dragon_id]
        print(f"\n#{dragon_id:03d} {dragon['name']} {dragon['emoji']}")
        print(f"    Type: {dragon['type_primary']}{'/' + dragon['type_secondary'] if dragon['type_secondary'] else ''}")
        print(f"    Rarity: {dragon['rarity']}")
        print(f"    Movie: {dragon['movie']}")
        print(f"    Rider: {dragon['rider']}")
        print(f"    Stats: HP {dragon['base_stats']['hp']} | ATK {dragon['base_stats']['atk']} | DEF {dragon['base_stats']['def']} | SPE {dragon['base_stats']['spe']}")
    
    # Demo: Show Toothless card
    print("\n" + "=" * 70)
    print("🎯 **SAMPLE DRAGON CARD (Toothless)**:")
    print("=" * 70)
    toothless = get_dragon_by_id(1)
    print(format_dragon_card(toothless, level=50))
    
    # Demo: Type effectiveness
    print("\n" + "=" * 70)
    print("⚔️ **TYPE EFFECTIVENESS EXAMPLES**:")
    print("=" * 70)
    examples = [
        ("Storm", "Ember"),
        ("Ember", "Glacial"),
        ("Glacial", "Terra"),
        ("Terra", "Storm")
    ]
    
    for attack, defense in examples:
        multiplier = calculate_type_effectiveness(attack, defense)
        if multiplier > 1:
            effect = "SUPER EFFECTIVE! 🔥"
        elif multiplier < 1:
            effect = "not very effective..."
        else:
            effect = "neutral"
        print(f"   {attack} → {defense}: {multiplier}x ({effect})")
    
    # Demo: Search function
    print("\n" + "=" * 70)
    print("🔍 **SEARCH DEMO** (Searching 'Night'):")
    print("=" * 70)
    results = search_dragons("Night")
    for dragon in results:
        print(f"   ✓ {dragon['name']} - {dragon['movie_name']}")
    
    print("\n" + "=" * 70)
    print("✅ DATABASE TEST COMPLETE!")
    print("=" * 70)
    print("\n💡 **Next Steps:**")
    print("   1. Import this file in your Telegram bot: from dex import *")
    print("   2. Use get_dragon_by_id() to fetch dragon data")
    print("   3. Use format_dragon_card() to display dragons in Telegram")
    print("   4. Use calculate_type_effectiveness() for battle calculations")
    print("\n🚀 Ready to build your HTTYD Telegram Bot!")
    print("=" * 70 + "\n")
