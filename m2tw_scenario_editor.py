#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tzeentch Scenario Editor : éditeur de scénarios multijoueur (descr_battle.txt) pour Medieval II : Total War
Testé sur le format du mod Warhammer « Battle of the End Times ».

- Lit la liste des unités dans export_descr_unit.txt du mod (aucune liste en dur).
- Permet de définir des armées « Joueur » ou « IA », les équipes, la carte, la météo, etc.
- Place automatiquement les troupes dans les zones de déploiement.
- Écrit data/world/maps/battle/custom/<NOM>/descr_battle.txt.

Aucune dépendance externe : Python 3.8+ avec tkinter (inclus avec Python sous Windows).
Lancement :  python m2tw_scenario_editor.py
"""
import json
import math
import os
import random
import re
import shutil
import sys
import time
import types
import unicodedata
from dataclasses import dataclass, field, asdict

# --------------------------------------------------------------------------------------
#  DONNÉES PAR DÉFAUT
# --------------------------------------------------------------------------------------

# Identifiants internes (ceux que le jeu attend dans descr_battle) -> nom affiché dans le mod.
# Remplacés automatiquement par ceux de text/expanded.txt s'il est trouvé.
DEFAULT_FACTIONS = {
    'aztecs': 'Chaos Dwarfs', 'byzantium': 'Ostland', 'denmark': 'Chaos Undivided',
    'egypt': 'Lizardmen', 'england': 'High Elves', 'france': 'Ostermark', 'hre': 'Reikland',
    'hungary': 'Vampire Counts', 'kalmar_union': 'Dogs of War',
    'lithuania': 'Minions of Tzeentch', 'milan': 'Beastmen', 'mongols': 'Dark Elves',
    'moors': 'Night Goblins', 'normans': 'Wood Elves', 'norway': 'Warriors of Khorne',
    'novgorod': 'Children of Nurgle', 'ogres': 'Ogre Kingdoms', 'papal_states': 'Bretonnia',
    'poland': 'Dwarfs', 'portugal': 'Mousillon', 'saxons': 'Clan Pestilens',
    'scotland': 'Middenland', 'sicily': 'Zombie Pirates', 'skaven': 'Skaven',
    'spain': 'Talabecland', 'teutonic_order': 'Devotees of Slaanesh', 'timurids': 'Tomb Kings',
    'turks': 'Orcs & Goblins', 'ukraine': 'Kislev', 'venice': 'Averland',
    'slave': 'Minor Factions',
}

BUILTIN_MAPS = []        # les lieux viennent de custom_locations.txt, des dossiers du mod et des coordonnées libres

WEATHERS = ['clear', 'cloudy']      # valeurs vues dans les scénarios du jeu de base (champ modifiable)
SEASONS = ['summer', 'winter']

# Données du mod Battle of the End Times (weather_db.xml, custom_locations.txt) : utilisées si les fichiers sont introuvables.
EMBEDDED_WEATHER_IDS = ['clear', 'clear winter', 'clear winter north', 'clear desert', 'clear badlands', 'rain', 'rain badlands', 'rain mountainous', 'storm', 'snow', 'blizzard', 'cloudy', 'cloudy mountainous', 'cloudy winter', 'cloudy badlands', 'dusty desert', 'dusty badlands', 'light fog', 'light fog winter', 'heavy fog', 'heavy fog winter', 'fog mountainous', 'fog mountainous winter', 'darklands default', 'darklands volcano', 'storm magic', 'realm of chaos']
EMBEDDED_CLIMATES = {'summer': {'mediterranean': [('clear', 38.0), ('cloudy', 30.0), ('rain', 10.0), ('storm', 5.0), ('light fog', 10.0), ('heavy fog', 5.0), ('storm magic', 2.0)], 'sandy_desert': [('clear desert', 65.0), ('dusty desert', 33.0), ('storm magic', 2.0)], 'rocky_desert': [('clear badlands', 30.0), ('cloudy badlands', 30.0), ('dusty badlands', 33.0), ('rain badlands', 5.0), ('storm magic', 2.0)], 'unused1': [('clear', 35.0), ('cloudy', 28.0), ('rain', 10.0), ('storm', 5.0), ('light fog', 15.0), ('heavy fog', 5.0), ('storm magic', 2.0)], 'steppe': [('clear', 20.0), ('cloudy mountainous', 30.0), ('rain mountainous', 15.0), ('storm', 10.0), ('fog mountainous', 10.0), ('snow', 13.0), ('storm magic', 2.0)], 'temperate_deciduous_forest': [('clear', 35.0), ('cloudy', 25.0), ('rain', 15.0), ('storm', 15.0), ('light fog', 5.0), ('heavy fog', 3.0), ('storm magic', 2.0)], 'temperate_coniferous_forest': [('clear', 25.0), ('cloudy', 25.0), ('rain', 20.0), ('storm', 10.0), ('light fog', 5.0), ('heavy fog', 3.0), ('snow', 10.0), ('storm magic', 2.0)], 'unused2': [('realm of chaos', 100.0)], 'highland': [('clear', 15.0), ('cloudy mountainous', 33.0), ('rain mountainous', 25.0), ('storm', 10.0), ('fog mountainous', 15.0), ('storm magic', 2.0)], 'alpine': [('clear winter north', 25.0), ('cloudy winter', 25.0), ('snow', 20.0), ('blizzard', 10.0), ('light fog winter', 10.0), ('heavy fog winter', 5.0), ('storm magic', 4.0), ('realm of chaos', 1.0)], 'tropical': [('clear', 35.0), ('cloudy', 20.0), ('rain', 30.0), ('storm', 13.0), ('storm magic', 2.0)], 'semi_arid': [('darklands default', 75.0), ('darklands volcano', 23.0), ('storm magic', 2.0)]}, 'winter': {'mediterranean': [('clear', 33.0), ('cloudy', 30.0), ('rain', 15.0), ('storm', 5.0), ('light fog', 10.0), ('heavy fog', 5.0), ('storm magic', 2.0)], 'sandy_desert': [('clear desert', 65.0), ('dusty desert', 33.0), ('storm magic', 2.0)], 'rocky_desert': [('clear badlands', 30.0), ('cloudy badlands', 33.0), ('dusty badlands', 10.0), ('rain badlands', 25.0), ('storm magic', 2.0)], 'unused1': [('clear winter', 37.5), ('cloudy winter', 22.5), ('snow', 18.0), ('light fog winter', 15.0), ('heavy fog winter', 5.0), ('storm magic', 2.0)], 'steppe': [('clear winter north', 20.0), ('cloudy winter', 20.0), ('snow', 33.0), ('blizzard', 15.0), ('fog mountainous winter', 10.0), ('storm magic', 2.0)], 'temperate_deciduous_forest': [('clear winter', 27.5), ('cloudy winter', 22.5), ('snow', 20.0), ('blizzard', 8.0), ('light fog winter', 10.0), ('heavy fog winter', 5.0), ('rain', 5.0), ('storm magic', 2.0)], 'temperate_coniferous_forest': [('clear winter north', 25.0), ('cloudy winter', 20.0), ('snow', 20.0), ('blizzard', 18.0), ('light fog winter', 10.0), ('heavy fog winter', 5.0), ('storm magic', 2.0)], 'unused2': [('realm of chaos', 100.0)], 'highland': [('clear winter', 15.0), ('cloudy winter', 33.0), ('snow', 25.0), ('blizzard', 10.0), ('fog mountainous winter', 15.0), ('storm magic', 2.0)], 'alpine': [('clear winter north', 25.0), ('cloudy winter', 25.0), ('snow', 20.0), ('blizzard', 10.0), ('light fog winter', 10.0), ('heavy fog winter', 5.0), ('storm magic', 4.0), ('realm of chaos', 1.0)], 'tropical': [('clear', 30.0), ('cloudy', 20.0), ('rain', 30.0), ('storm', 10.0), ('light fog', 5.0), ('heavy fog', 3.0), ('storm magic', 2.0)], 'semi_arid': [('darklands default', 75.0), ('darklands volcano', 23.0), ('storm magic', 2.0)]}}
EMBEDDED_LOCATIONS = [('Arabyan Oasis', 133, 10, 'sandy_desert', True, False), ('Badlands', 259, 62, 'rocky_desert', False, False), ('Bretonnian Island', 107, 163, 'temperate_deciduous_forest', False, False), ('Chaos Wastes', 91, 257, 'unused2', False, False), ('Dark Lands', 362, 97, 'semi_arid', True, False), ('Ellyrian Plains', 46, 127, 'unused1', False, False), ('Estalia', 143, 79, 'mediterranean', True, False), ('Glacial Bay', 193, 270, 'alpine', False, False), ('Kislev', 262, 237, 'temperate_coniferous_forest', False, False), ('Lustrian Volcano', 74, 30, 'tropical', True, False), ('Lustrian River Bend', 23, 2, 'tropical', True, False), ('Naggaroth', 8, 226, 'steppe', False, False), ('Nehekhara', 197, 12, 'sandy_desert', True, False), ('Reikland Floodplain', 184, 171, 'temperate_deciduous_forest', False, True), ('Sea of Chill', 64, 239, 'alpine', False, True), ('Sylvania', 276, 155, 'highland', False, False), ('Worlds Edge Mountains', 289, 122, 'highland', False, True), ('Yvresse Shore', 101, 115, 'unused1', False, False), ('Bridge - River Mortis', 198, 12, 'sandy_desert', True, True), ('Crossing - Varenka Ford', 244, 98, 'mediterranean', True, True)]

# Option « Faithful Alliances » (Alliances Loyales) des scénarios aléatoires : deux factions ne peuvent être dans la même
# équipe que si une alliance les réunit. Modifiable dans l'éditeur d'alliances (enregistré dans le fichier de configuration).
DEFAULT_ALLIANCES = [        # (nom français, nom anglais, factions)
    ('Conclave de Lumière', 'Conclave of Light',
     ['hre', 'venice', 'scotland', 'spain', 'byzantium', 'france', 'ukraine', 'papal_states', 'poland', 'kalmar_union']),
    ('Gardiens du Grand Dessein', 'The Great Plan', ['normans', 'england', 'egypt']),
    ('Hordes du Chaos', 'Hordes of Chaos', ['denmark', 'norway', 'lithuania', 'novgorod', 'teutonic_order', 'milan']),
    ('Empire de Zharr', 'Empire of Zharr', ['aztecs', 'turks', 'moors', 'denmark']),
    ('Conseil des Treize', 'Council of Thirteen', ['skaven', 'saxons']),
    ('Confrérie de la Pestilence', 'Pestilent Brotherhood', ['saxons', 'novgorod']),
    ("GRAND' WAAAGH!", 'DA GREAT WAAAGH!', ['turks', 'moors']),
    ('Légions Morts-Vivantes', 'Legions of Unlife', ['hungary', 'portugal', 'sicily']),
    ('Flotte Maudite', 'Dreadfleet', ['timurids', 'sicily']),
    ('Culte du Plaisir', 'Cult of Pleasure', ['mongols', 'teutonic_order']),
    ("Alliance d'Athel Loren", 'Alliance of Athel Loren', ['normans', 'papal_states']),
    ('Mercenaires', 'Mercenaries', ['ogres', 'kalmar_union']),
]
ALLIANCES_REV = 3          # change quand les alliances par défaut changent : la liste enregistrée est alors remplacée
DEFAULT_FAITHFUL_GROUPS = [list(x[2]) for x in DEFAULT_ALLIANCES]
FAITHFUL_NAMES = [{'fr': x[0], 'en': x[1]} for x in DEFAULT_ALLIANCES]
FAITHFUL_GROUPS = [set(g) for g in DEFAULT_FAITHFUL_GROUPS]
_FADJ = {}


ALLIANCES = [{'fr': x[0], 'en': x[1], 'f': list(x[2])} for x in DEFAULT_ALLIANCES]     # toutes, même vides


def set_alliances(al):
    """Définit toutes les alliances (dicts fr / en / f) ; seules celles de 2 factions au moins servent au tirage."""
    global ALLIANCES
    ALLIANCES = [{'fr': x.get('fr', ''), 'en': x.get('en', ''), 'f': list(x.get('f', []))} for x in al]
    set_faithful_groups([x['f'] for x in ALLIANCES], [{'fr': x['fr'], 'en': x['en']} for x in ALLIANCES])


def set_faithful_groups(groups, names=None):
    """Remplace les alliances (listes d'identifiants de factions, 2 factions au moins) et recalcule les compatibilités."""
    global FAITHFUL_GROUPS, _FADJ, FAITHFUL_NAMES
    keep = [i for i, g in enumerate(groups) if len(set(g)) >= 2]
    FAITHFUL_GROUPS = [set(groups[i]) for i in keep]
    if names is not None:
        FAITHFUL_NAMES = [dict(names[i]) if i < len(names) else {'fr': '', 'en': ''} for i in keep]
    adj = {}
    for g in FAITHFUL_GROUPS:
        for f in g:
            adj.setdefault(f, set()).update(g)
    _FADJ = adj


set_faithful_groups(DEFAULT_FAITHFUL_GROUPS, FAITHFUL_NAMES)


def faithful_ok(f1, f2):
    return f1 == f2 or f2 in _FADJ.get(f1, ())


class RandomError(Exception):
    pass


def faithful_pick(facs, n_arm, nums, rng=random, tries=400):
    """Choisit n_arm factions parmi `facs` et les répartit dans les équipes `nums` (chacune non vide, toutes les paires d'une
    équipe compatibles). Construction directe équipe par équipe : rapide. Retourne (factions, {faction: équipe}) ou None."""
    k = len(nums)
    facs = list(facs)
    if n_arm < k or n_arm > len(facs):
        return None
    for _ in range(tries):
        cuts = sorted(rng.sample(range(1, n_arm), k - 1)) if k > 1 else []
        sizes = [b - a for a, b in zip([0] + cuts, cuts + [n_arm])]
        rng.shuffle(sizes)
        left = set(facs)
        team_of, chosen, ok = {}, [], True
        for n, size in zip(nums, sizes):
            if size >= 2 and rng.random() < 0.85:         # une alliance tirée au hasard (toutes à égalité), puis ses membres
                opts = [g for g in FAITHFUL_GROUPS if len(g & left) >= size]
                if opts:
                    members = rng.sample(sorted(rng.choice(opts) & left), size)
                    for f in members:
                        team_of[f] = n
                        left.discard(f)
                        chosen.append(f)
                    continue
            seeds = [f for f in left if size == 1 or len(_FADJ.get(f, set()) & left) >= size]
            if not seeds:
                ok = False
                break
            members = [rng.choice(seeds)]
            while len(members) < size:
                cands = [f for f in left if f not in members and all(faithful_ok(f, m) for m in members)]
                if not cands:
                    ok = False
                    break
                members.append(rng.choice(cands))
            if not ok:
                break
            for f in members:
                team_of[f] = n
                left.discard(f)
                chosen.append(f)
        if ok:
            return chosen, team_of
    return None




# Menu « Settlement » de la bataille personnalisée du mod, dans l'ordre du jeu :
# (libellé, niveau écrit dans descr_battle, mot-clé « settlement », niveau de défense maximum)
SETTLEMENTS = [
    ('Fort', 'fort', '', 1),
    ('Village', 'village', '', 1),
    ('Town', 'town', '', 1),
    ('Large Town', 'large_town', '', 1),
    ('City', 'city', '', 1),
    ('Large City', 'large_city', '', 1),
    ('Huge City', 'huge_city', '', 3),
    ('Motte and Bailey', 'village', 'castle', 1),      # relevé en jeu : le niveau « village » + mot-clé castle donne le Motte and Bailey
    ('Wooden Castle', 'wooden_castle', 'castle', 1),
    ('Castle', 'castle', 'castle', 3),
    ('Fortress', 'fortress', 'castle', 3),
    ('Citadel', 'citadel', 'castle', 3),
]
CULTURES = [('Humans', 'southern_european'), ('Elves', 'northern_european'),
            ('Ancient Civilisations', 'mesoamerican'), ('Savages', 'middle_eastern')]
# Relevé Procmon (menu « bataille personnalisée » du jeu) : le jeu cherche la colonie dans settlements\<culture>\... et prend
# l'aspect (textures « faction_variations\<faction> ») de la faction type de la culture.
CULTURE_FACTION = {'Humans': 'hre', 'Elves': 'england', 'Ancient Civilisations': 'timurids', 'Savages': 'turks'}
CULTURE_DIR = {'Humans': 'South_European', 'Elves': 'North_European', 'Savages': 'Middle_Eastern'}
# Colonies qui ne proposent jamais la culture « Ancient Civilisations » dans le menu du mod
NO_ANCIENT = {'Motte and Bailey', 'Wooden Castle', 'Castle', 'Fortress', 'Citadel'}
# Engins de siège proposés par colonie : (béliers, échelles, tours). Village : aucun engin et aucune unité de siège obligatoire.
SIEGE_ENGINES = {'Village': (0, 0, 0), 'Fort': (1, 0, 0), 'Town': (1, 0, 0), 'Motte and Bailey': (1, 0, 0), 'Huge City': (1, 0, 1)}
_AZ = 'Settlements/Aztec/Settlements/'
# (sous-dossier, nom de fichier avec {c} = culture, rayon en m depuis le centre jusqu'aux limites de la colonie)
TYPE_PKG = {
    'Fort': ('Settlements/Fort/', '{c}_fort_A', 135),
    'Village': ('Settlements/Village/', '{c}_village_A', 242),
    'Town': ('Settlements/Town/', '{c}_town_A', 266),
    'Large Town': ('Settlements/large_town/', '{c}_large_town_A', 450),
    'City': ('Settlements/City/', '{c}_city_A', 500),
    'Large City': ('Settlements/Large City/', '{c}_large_city_A', 550),
    'Huge City': ('Settlements/Huge_City/', '{c}_huge_city_A', 650),
    'Motte and Bailey': ('Castles/Wooden_Fort/', '{c}_wooden_fort_A', 135),
    'Wooden Castle': ('Castles/Stone_Keep/', '{c}_stone_keep_A', 245),
    'Castle': ('Castles/Castle/', '{c}_castle_A', 240),
    'Fortress': ('Castles/Large_Castle/', '{c}_large_castle_A', 322),
    'Citadel': ('Castles/Fortress/', '{c}_fortress_A', 370),
}
# Paquets présents dans le mod (fichiers .world vus par Procmon ou listés par les .worldpkgdesc) : culture « Elves »
MOD_PKG = {
    ('Elves', 'Village'): 'north_european_village_A', ('Elves', 'Town'): 'north_european_town_A',
    ('Elves', 'Motte and Bailey'): 'north_european_wooden_fort_A', ('Elves', 'Wooden Castle'): 'TC_Stone_Keep_A',
    ('Elves', 'Castle'): 'TC_Castle_A', ('Elves', 'Fortress'): 'TC_Large_Castle_A', ('Elves', 'Citadel'): 'TC_Fortress_A',
}
PKG_ANCIENT = {       # paquets Aztèques du mod (le Huge City Ancient a été relevé : Aztec_City.world)
    'Village': (_AZ + 'Village/Aztec_Village_A.world', 134),
    'Town': (_AZ + 'Town/AZ_Town.world', 235),
    'Large Town': (_AZ + 'Large_Town/AZ_Large_Town.world', 437),
    'City': (_AZ + 'City/Aztec_City.world', 600),
    'Large City': (_AZ + 'City/Aztec_City.world', 600),
    'Huge City': (_AZ + 'City/Aztec_City.world', 600),
}
# Demi-côté (m) de la zone commune des défenseurs lorsqu'elle est plus petite que le rayon estimé de la colonie
# (retour d'essais : zone trop large pour ces trois colonies)
DEF_ZONE = {'Fort': 68, 'Large Town': 300, 'City': 302, 'Large City': 365, 'Huge City': 390, 'Fortress': 306, 'Citadel': 370, 'Wooden Castle': 150}
# City : carré inscrit dans l'ancien polygone à 12 côtés (demi-côté = rayon x cos 45° = 302 m)
# Zone des défenseurs rectangulaire décalée (x min, x max, y min, y max) en m depuis le centre de la colonie, d'après les retours d'essais :
# la colonie n'est pas centrée sur son point (x : est +, y : nord +)
DEF_RECT = {'Castle': (-176.0, 154.0, -200.0, 176.0), 'Fortress': (-282.0, 294.0, -294.0, 306.0), 'Wooden Castle': (-195.0, 195.0, -158.0, 175.0), 'Citadel': (-330.0, 370.0, -370.0, 370.0)}
DEF_ZONE_CULTURE = {('Large City', 'Ancient Civilisations'): 383, ('Large Town', 'Ancient Civilisations'): 250, ('Village', 'Humans'): 190}     # demi-côté (m) propre à une culture
# Nombre de côtés du polygone des défenseurs selon la colonie (4 = carré)
DEF_SIDES = {'Town': 8, 'Large Town': 8}       # les autres colonies : carré dont les côtés touchent les côtés cardinaux les plus éloignés
PKG_SAVAGES = {'Village': ('settlements/greenskins/settlements/village/orc_village.world', 100)}
SIEGE_TESTED = {('Castle', 'Elves')}      # (les chemins Town/Humans et Castle/Savages sont confirmés par Procmon, pas leurs noms de fichiers)
# siège aléatoire : uniquement des paquets présents dans le mod
SIEGE_RANDOM = [(st, 'Elves') for st in ('Wooden Castle', 'Castle', 'Fortress', 'Citadel', 'Village', 'Town')] + \
    [(st, 'Ancient Civilisations') for st in ('Village', 'Town', 'Large Town', 'Fort')] + [('Fort', 'Elves'), ('Fort', 'Humans'), ('Fort', 'Savages')]
CUSTOM_LABEL = 'Personnalisée (X / Y ci-contre)'

ROLES = {'attacking': 'Attaquant', 'defending': 'Défenseur'}
MAX_ARMIES = 8        # nombre maximum de joueurs (armées) dans une partie
MAX_UNITS = 20        # les armées du jeu de base ont 17 à 20 unités
MAX_EXP = 9
MAX_WEAPON = 1
TIMES_OF_DAY = [('Lever du jour', 6.0), ('Matin', 8.0), ('Midi', 12.0), ('Après-midi', 15.0),
                ('Coucher du soleil', 18.0), ('Nuit', 22.0)]   # heures supposées (à confirmer en jeu)
# Coût d'une unité : (coût de base + 100/niveau d'armure + 100/niveau d'arme) x multiplicateur d'expérience.
# Multiplicateurs relevés en jeu (niveaux 0 à 9) ; l'écart restant est inférieur à 2 %.
EXP_MULT = [1.0, 1.24, 1.48, 1.80, 2.20, 2.68, 3.24, 3.88, 4.60, 5.40]
GOLD_MIN, GOLD_MAX = 80, 1000000        # min : unité la moins chère (skavenslaves 80) ; max : 8 armées de 20 unités les plus chères en respectant les maximums d'exemplaires (556 240) -> 1 000 000
TEAM_GOLD_MAX = 1000000
ARMY_FLOOR = 500                       # valeur minimum visée par armée générée (abaissée si le budget demandé est plus faible)


def army_floor(v):
    return max(GOLD_MIN, min(ARMY_FLOOR, int(v)))
SOLD_MIN, SOLD_MAX = 7, 100000          # min : plus petite unité (anvil of doom, 7) ; max : 8 armées x 20 x 187 = 29 920 -> 100 000
LIMIT_SOLDIERS = 4000                  # au-delà, le jeu affiche un avertissement de performances
LIMIT_TEAMS = 4                        # le jeu de base et le mod ne proposent que 4 équipes
ARMY_GAP_MAX = 100                     # écart maximum (or) entre deux armées d'une même équipe
ARMY_TOLERANCE = 300                   # écart maximum (or) entre la cible et une armée générée (< 300 entre équipes)
TIME_NAMES_EN = ['Sunrise', 'Morning', 'Midday', 'Afternoon', 'Sunset', 'Night']
RANDOM_MAX_EXP = 3    # armées et scénarios aléatoires : niveau maximum
RANDOM_MAX_ARMOUR = 2
RANDOM_MAX_WEAPON = 1

# --- Données du mod BOTET v3 intégrées (utilisées si les fichiers du mod ne sont pas trouvés) ---


CAMPAIGN_SIZE = (369, 282)
# Lieux dont les coordonnées de custom_locations.txt tombent dans l'eau (unités placées dans la mer) : coordonnées corrigées
# vers la terre ferme la plus proche, de même climat (alpine).
COORD_FIXES = {'Sea of Chill': (57, 242)}
CAMPAIGN_CLIMATES = ['alpine', 'highland', 'mediterranean', 'rocky_desert', 'sandy_desert', 'semi_arid', 'steppe', 'temperate_coniferous_forest', 'temperate_deciduous_forest', 'tropical', 'unused1', 'unused2']
# carte de campagne du mod : 1 octet par case (bits 0-3 = climat, bit 4 = terrain dégagé : sol sec, plat, sans eau ; bit 5 = fleuve à moins d'une case : exclu des lieux libres aléatoires), origine en bas à gauche
EMBEDDED_CAMPAIGN = (
    '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'
)


class CampaignMap:
    """Carte de campagne du mod : climat et nature du terrain à chaque coordonnée de bataille."""

    def __init__(self):
        import base64, zlib
        self.w, self.h = CAMPAIGN_SIZE
        self.grid = zlib.decompress(base64.b64decode(EMBEDDED_CAMPAIGN))
        self.clear_points = {}

    def inside(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def climate_at(self, x, y):
        if not self.inside(x, y):
            return None
        i = self.grid[y * self.w + x] & 15
        return CAMPAIGN_CLIMATES[i] if i < len(CAMPAIGN_CLIMATES) else None

    def is_clear(self, x, y):
        return self.inside(x, y) and bool(self.grid[y * self.w + x] & 16)

    def random_point(self, climate=None):
        key = climate or ''
        pts = self.clear_points.get(key)
        if pts is None:
            w, h, g = self.w, len(self.grid) // self.w, self.grid
            # une rivière à moins de 2 cases (relevé : Fortress plantait au lancement à 1 case d'une rivière) exclut la case
            near = lambda x, y: any(g[yy * w + xx] & 32 for yy in range(max(0, y - 2), min(h, y + 3)) for xx in range(max(0, x - 2), min(w, x + 3)))
            pts = [(i % self.w, i // self.w) for i, b in enumerate(self.grid)
                   if b & 16 and not b & 32 and not near(i % self.w, i // self.w) and (climate is None or (b & 15) < len(CAMPAIGN_CLIMATES) and CAMPAIGN_CLIMATES[b & 15] == climate)]
            self.clear_points[key] = pts
        return random.choice(pts) if pts else None


ROW_STEP = 32.0       # distance entre deux lignes de troupes (mètres)
UNIT_GAP = 4.0        # espace entre deux unités d'une même ligne
MAP_WARN = 800.0      # au-delà, on prévient que les unités risquent de sortir de la carte
SIEGE_DIST_SPAN = 150      # siège : distance assaillants au plus minimum + 150 m (l'IA n'utilise pas tous ses engins si elle part trop loin)
SIEGE_MAP_LIMIT = 700.0   # siège : aucun point de zone d'assaillants au-delà de ±700 m (testé : 683 m passe, ~870 m sort de la carte)
DEF_CIRC_MAX = 520.0
DEF_RECT_CULTURE = {
    ('Village', 'Elves'): (-242.0, 242.0, -212.0, 242.0), ('Town', 'Humans'): (-196.0, 196.0, -196.0, 196.0),
    ('Town', 'Ancient Civilisations'): (-190.0, 200.0, -170.0, 170.0), ('Town', 'Savages'): (-186.0, 176.0, -196.0, 186.0),
    ('Large Town', 'Humans'): (-220.0, 220.0, -220.0, 220.0), ('Large Town', 'Elves'): (-220.0, 220.0, -220.0, 220.0),
    ('Large Town', 'Savages'): (-205.0, 225.0, -205.0, 220.0), ('City', 'Ancient Civilisations'): (-387.0, 397.0, -387.0, 387.0),
    ('Large City', 'Ancient Civilisations'): (-383.0, 391.0, -385.0, 385.0), ('Large City', 'Savages'): (-360.0, 355.0, -355.0, 360.0),
    ('Huge City', 'Savages'): (-385.0, 385.0, -376.0, 370.0), ('Motte and Bailey', 'Elves'): (-135.0, 135.0, -125.0, 135.0),
    ('Wooden Castle', 'Humans'): (-195.0, 175.0, -203.0, 195.0), ('Wooden Castle', 'Savages'): (-195.0, 195.0, -198.0, 175.0),
    ('Castle', 'Humans'): (-206.0, 264.0, -220.0, 226.0), ('Castle', 'Savages'): (-171.0, 219.0, -220.0, 226.0),
    ('Fortress', 'Humans'): (-232.0, 294.0, -294.0, 306.0), ('Citadel', 'Humans'): (-375.0, 370.0, -352.0, 370.0),
    ('Citadel', 'Elves'): (-325.0, 370.0, -370.0, 370.0), ('Citadel', 'Savages'): (-350.0, 330.0, -315.0, 370.0),
}      # zone propre à une culture (x min, x max, y min, y max)
DEF_HALF_MAX = 450.0       # demi-côté maximum d'une zone de défenseurs carrée


# --------------------------------------------------------------------------------------
#  LECTURE DES FICHIERS
# --------------------------------------------------------------------------------------

def read_text(path):
    """Lit un fichier texte du jeu (UTF-8, UTF-16 ou ANSI)."""
    with open(path, 'rb') as fh:
        raw = fh.read()
    if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
        text = raw.decode('utf-16')
    else:
        if raw[:3] == b'\xef\xbb\xbf':
            raw = raw[3:]
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError:
            text = raw.decode('latin-1')
    return text.replace('\r\n', '\n').replace('\r', '\n')


def ascii_only(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    return s.strip()


def to_float_list(value):
    out = []
    for part in value.split(','):
        part = part.strip()
        try:
            out.append(float(part))
        except ValueError:
            pass
    return out


UNIT_SCALE_LARGE = 1.875      # « Large Unit Scale » : soldats en jeu = int(base x 1,875) + officiers (non mis à l'échelle)
OFFICERS = {}                 # type d'unité -> nombre d'officiers (EDU)


def large_soldiers(n, officers=0):
    return int(n * UNIT_SCALE_LARGE + 1e-9) + officers


@dataclass
class UnitDef:
    type: str
    dictionary: str = ''
    category: str = 'infantry'
    cls: str = 'light'
    soldiers: int = 40
    extras: int = 0
    officers: int = 0
    attrs: set = field(default_factory=set)
    ownership: set = field(default_factory=set)
    era0: set = field(default_factory=set)     # factions auxquelles l'unité est proposée de base (ligne « era 0 »)
    cost: int = 0
    wpn_cost: int = 0
    arm_cost: int = 0
    max_copies: int = 1       # exemplaires par armée au coût normal (stat_cost, 7e valeur) ; 1 si inconnu
    armour_levels: int = 0
    spacing: float = 1.2
    ranks: int = 4
    attack: float = 0
    charge: float = 0
    armour: float = 0
    name: str = ''            # nom affiché (export_units.txt) ou nom prettifié

    @property
    def is_general(self):
        return 'general_unit' in self.attrs

    @property
    def no_custom(self):
        return 'no_custom' in self.attrs


    @property
    def max_armour(self):
        # armour_ug_levels liste le niveau de base + les améliorations : 4 entrées = niveaux 0, 1, 2, 3
        return max(0, min(3, self.armour_levels - 1))

    def owned_by(self, faction):
        return 'all' in self.ownership or faction in self.ownership


UnitDef.ls = property(lambda self: large_soldiers(self.soldiers, self.officers))


def parse_edu(text):
    """Parse export_descr_unit.txt -> liste de UnitDef."""
    units = []
    cur = None
    for line in text.split('\n'):
        s = line.split(';', 1)[0].strip()
        if not s:
            continue
        parts = s.split(None, 1)
        key = parts[0].lower()
        val = parts[1].strip() if len(parts) > 1 else ''
        if key == 'type':
            cur = UnitDef(type=val)
            units.append(cur)
            continue
        if cur is None:
            continue
        if key == 'dictionary':
            cur.dictionary = val
        elif key == 'category':
            cur.category = val.lower()
        elif key == 'class':
            cur.cls = val.lower()
        elif key == 'officer':
            cur.officers += 1
        elif key == 'soldier':
            f = [p.strip() for p in val.split(',')]
            try:
                cur.soldiers = int(float(f[1]))
                cur.extras = int(float(f[2])) if len(f) > 2 else 0
            except (IndexError, ValueError):
                pass
        elif key == 'attributes':
            cur.attrs = {a.strip().lower() for a in val.split(',') if a.strip()}
        elif key == 'ownership':
            cur.ownership = {a.strip().lower() for a in val.split(',') if a.strip()}
        elif key == 'era' and val.split()[:1] == ['0']:
            cur.era0 = {a.strip().lower() for a in val.split(None, 1)[1].split(',')} if len(val.split(None, 1)) > 1 else set()
            cur.era0.discard('')
        elif key == 'formation':
            f = [p.strip() for p in val.split(',')]
            try:
                cur.spacing = float(f[0])
                cur.ranks = max(1, int(float(f[4])))
            except (IndexError, ValueError):
                pass
        elif key == 'stat_cost':
            f = to_float_list(val)
            if len(f) > 5:
                cur.cost = int(f[5])          # coût en bataille personnalisée
            elif len(f) > 1:
                cur.cost = int(f[1])
            if len(f) > 4:
                cur.wpn_cost, cur.arm_cost = int(f[3]), int(f[4])
            if len(f) > 6 and f[6] >= 1:
                cur.max_copies = int(f[6])
        elif key == 'armour_ug_levels':
            cur.armour_levels = len(to_float_list(val))
        elif key == 'stat_pri':
            f = to_float_list(val)
            if len(f) > 1:
                cur.attack, cur.charge = f[0], f[1]
        elif key == 'stat_pri_armour':
            f = to_float_list(val)
            if f:
                cur.armour = f[0]
    for u in units:
        u.name = prettify(u.type)
    for u in units:
        OFFICERS[u.type] = u.officers
    return units


def prettify(type_name):
    return ' '.join(w.capitalize() if w.islower() else w for w in type_name.split())


def parse_dictionary_file(text):
    """{tag}Texte -> dict (en minuscules)."""
    out = {}
    for line in text.split('\n'):
        m = re.match(r'^\{([^}]+)\}\s*(.*)$', line.strip().lstrip('¬'))
        if m:
            out.setdefault(m.group(1).strip().lower(), m.group(2).strip())
    return out


def parse_faction_names(text, known):
    """Extrait {FRANCE}Ostermark depuis expanded.txt, pour les identifiants connus."""
    names = {}
    d = parse_dictionary_file(text)
    for fid in known:
        if fid in d and d[fid]:
            names[fid] = d[fid]
    return names


def find_first(*paths):
    for p in paths:
        if p and os.path.isfile(p):
            return p
    return None


class Availability:
    """Quelles unités sont proposées à chaque faction.
    Règle du jeu (vérifiée sur Reikland : 37 + 76 = 113 ; Dwarves : 28 + 21 = 49) :
      - armée de base      = unités dont la ligne « era 0 » nomme la faction ;
      - armée auxiliaire   = les autres unités de la faction (« ownership »), hors « no_custom »."""

    def __init__(self, units, factions):
        self.base, self.aux = {}, {}
        usable = [u for u in units if u.category != 'ship' and not u.no_custom]
        for fid in factions:
            owned = [u for u in usable if u.owned_by(fid)]
            self.base[fid] = [u for u in owned if fid in u.era0]
            self.aux[fid] = [u for u in owned if fid not in u.era0]

    def units_for(self, fid, with_aux=False, aux_only=False):
        base = list(self.base.get(fid, []))
        aux = list(self.aux.get(fid, []))
        if aux_only:
            return aux
        return base + aux if with_aux else base

    def allowed(self, fid, with_aux=True):
        return {u.type.lower() for u in self.units_for(fid, with_aux)}


_COST_CACHE = {}


def entry_cost(u, e, copy_no=1):
    """Coût d'une unité avec son expérience / armure / arme.
    copy_no = rang de cet exemplaire dans l'armée : au-delà de max_copies, chaque exemplaire coûte
    (rang - max_copies + 1) fois le prix normal (ex. max 4 : 5e = x2, 6e = x3 ... 10e = x7)."""
    if u is None:
        return 0
    lvl = max(0, min(len(EXP_MULT) - 1, int(e.exp)))
    key = (u.cost, u.arm_cost, u.wpn_cost, u.max_copies, lvl, e.armour, e.weapon, copy_no)
    hit = _COST_CACHE.get(key)
    if hit is not None:
        return hit
    tot = u.cost + u.arm_cost * e.armour + u.wpn_cost * e.weapon
    hund = (tot // 25) * 25          # relevé en jeu : le multiplicateur d'expérience ne s'applique qu'aux multiples de 25 du coût (580 -> 575 x mult + 5 ; 640 -> 625 x mult + 15)
    base = hund * EXP_MULT[lvl] + (tot - hund)
    mult = max(1, copy_no - max(1, u.max_copies) + 1)
    res = _COST_CACHE[key] = int(round(base * mult))
    return res


def entry_costs(entries, udict):
    """Liste des coûts de chaque unité d'une armée (surcoût d'exemplaires compris)."""
    seen, out = {}, []
    for e in entries:
        k = e.type.lower()
        seen[k] = seen.get(k, 0) + 1
        out.append(entry_cost(udict.get(k), e, seen[k]))
    return out


def army_value(entries, udict):
    return sum(entry_costs(entries, udict))


def army_pool(avail, units, fid, use_aux):
    base = avail.units_for(fid, use_aux) if avail else [u for u in units if u.owned_by(fid)]
    return [u for u in base if u.category in ('infantry', 'cavalry', 'siege') and u.cost > 0]


def _top_cost(u, upgrades):
    if not upgrades:
        return u.cost
    arm = min(u.max_armour, RANDOM_MAX_ARMOUR)
    wpn = RANDOM_MAX_WEAPON if u.wpn_cost > 0 else 0
    return int(round((u.cost + u.arm_cost * arm + u.wpn_cost * wpn) * EXP_MULT[RANDOM_MAX_EXP]))


def army_limits(pool, max_units, upgrades, max_soldiers=10 ** 9):
    """(valeur minimale, valeur maximale) qu'une armée de cette liste peut atteindre."""
    if not pool:
        return 0, 0
    lo = min(u.cost for u in pool)
    hi, n, siege, sold = 0, 0, 0, 0
    for u in sorted(pool, key=lambda u: -_top_cost(u, upgrades)):
        for _ in range(max(1, u.max_copies)):
            if n >= max_units or sold + u.ls > max_soldiers:
                break
            if u.category == 'siege':
                if siege >= 2:
                    break
                siege += 1
            hi += _top_cost(u, upgrades)
            n += 1
            sold += u.ls
    return lo, hi


def possible_purchases(entries, pool, target, max_units, upgrades, max_soldiers=10 ** 9):
    """Achats encore possibles avec l'or restant : [(coût, 'add'|'set', indice, entrée)]."""
    byt = {u.type: u for u in pool}
    bytl = {u.type.lower(): u for u in pool}
    count = {}
    for e in entries:
        count[e.type] = count.get(e.type, 0) + 1
    ns = sum(1 for e in entries if byt[e.type].category == 'siege')
    total = sum(entry_costs(entries, bytl))
    rem = target - total
    out = []
    if rem <= 0:
        return out
    sold = sum(e.ls for e in entries)
    if len(entries) < max_units:
        for u in pool:
            if count.get(u.type, 0) < max(1, u.max_copies) and not (u.category == 'siege' and ns >= 2) \
                    and sold + u.ls <= max_soldiers:
                e2 = UnitEntry(u.type, u.soldiers, 0, 0, 0)
                d = entry_cost(u, e2, count.get(u.type, 0) + 1)
                if 0 < d <= rem:
                    out.append((d, 'add', None, e2))
    if upgrades:
        seen = {}
        for i, e in enumerate(entries):
            u = byt[e.type]
            seen[e.type] = seen.get(e.type, 0) + 1
            base = entry_cost(u, e, seen[e.type])
            for attr, cap, ok in (('exp', RANDOM_MAX_EXP, True), ('armour', min(u.max_armour, RANDOM_MAX_ARMOUR), True),
                                  ('weapon', RANDOM_MAX_WEAPON, u.wpn_cost > 0)):
                if ok and getattr(e, attr) < cap:
                    e2 = UnitEntry(**asdict(e))
                    setattr(e2, attr, getattr(e, attr) + 1)
                    d = entry_cost(u, e2, seen[e.type]) - base
                    if 0 < d <= rem:
                        out.append((d, 'set', i, e2))
    return out


def fill_army(pool, udict, target, max_units, upgrades, tol=ARMY_TOLERANCE, need_siege=False, max_soldiers=10 ** 9):
    """Armée aléatoire dont la valeur est dans [target - tol, target].
    Respecte le nombre d'exemplaires par unité, 20 unités, au plus 2 sièges ; général = unité « bon général » tirée, sinon l'une des 3 plus chères hors siège."""
    byt = {u.type: u for u in pool}
    kind = {u.type: unit_kind(u, 1) for u in pool}
    limit = {u.type: max(1, u.max_copies) for u in pool}
    count = {}
    entries = []

    def cost(e):
        return entry_cost(byt[e.type], e)

    def n_siege():
        return sum(1 for e in entries if kind[e.type] == 'siege')

    lsc = {u.type: u.ls for u in pool}
    st = [0]            # soldats (Large Unit Scale) de l'armée, tenus à jour à chaque ajout / remplacement

    def sold():
        return st[0]

    sg_min = min([u.cost for u in pool if kind[u.type] == 'siege'] or [0]) if need_siege else 0
    if need_siege and not sg_min:
        need_siege = False        # faction sans unité de siège : elle utilisera des engins (béliers, échelles, tours)
    nonsiege = [u for u in pool if kind[u.type] != 'siege' and u.cost <= target - sg_min and u.ls <= max_soldiers]
    if not nonsiege:
        return [], 0
    wk = {'inf': 40, 'ranged': 25, 'cav': 25}          # première unité : tirée au hasard (le général est choisi à la fin)
    kk = [k for k in wk if any(kind[u.type] == k for u in nonsiege)] or [kind[nonsiege[0].type]]
    k0 = random.choices(kk, weights=[wk.get(x, 10) for x in kk])[0]
    g = random.choice([u for u in nonsiege if kind[u.type] == k0] or nonsiege)
    entries.append(UnitEntry(g.type, g.soldiers, 0, 0, 0))
    st[0] += lsc[g.type]
    count[g.type] = 1
    total = g.cost
    reserve = target * 0.2 if upgrades else 0
    if need_siege:          # siège : l'armée attaquante contient au moins une unité de siège
        sg = [u for u in pool if kind[u.type] == 'siege' and u.cost <= target - total and sold() + u.ls <= max_soldiers]
        if sg:
            u = random.choice(sg)
            entries.append(UnitEntry(u.type, u.soldiers, 0, 0, 0))
            st[0] += lsc[u.type]
            count[u.type] = count.get(u.type, 0) + 1
            total += u.cost
    weights = {'inf': 40, 'ranged': 25, 'cav': 25, 'siege': 8}
    while len(entries) < max_units:
        room = target - total - reserve
        ok = [u for u in pool if u.cost <= room and count.get(u.type, 0) < limit[u.type]
              and not (kind[u.type] == 'siege' and n_siege() >= 2) and sold() + u.ls <= max_soldiers]
        kinds = [k for k in weights if any(kind[u.type] == k for u in ok)]
        if not kinds:
            break
        k = random.choices(kinds, weights=[weights[x] for x in kinds])[0]
        u = random.choice([u for u in ok if kind[u.type] == k])
        entries.append(UnitEntry(u.type, u.soldiers, 0, 0, 0))
        st[0] += lsc[u.type]
        count[u.type] = count.get(u.type, 0) + 1
        total += u.cost
    # affinage : améliorations, ajouts et remplacements jusqu'à tomber dans la tolérance
    for _ in range(600):
        total = sum(cost(e) for e in entries)
        rem = target - total
        if rem <= tol:
            break
        cands = []
        for i, e in enumerate(entries):
            u = byt[e.type]
            if upgrades:
                for attr, cap, ok in (('exp', RANDOM_MAX_EXP, True),
                                      ('armour', min(u.max_armour, RANDOM_MAX_ARMOUR), True),
                                      ('weapon', RANDOM_MAX_WEAPON, u.wpn_cost > 0)):
                    if ok and getattr(e, attr) < cap:
                        e2 = UnitEntry(**asdict(e))
                        setattr(e2, attr, getattr(e, attr) + 1)
                        d = cost(e2) - cost(e)
                        if 0 < d <= rem:
                            cands.append((d, 'set', i, e2))
        for i in random.sample(range(len(entries)), min(8, len(entries))):
            e = entries[i]
            for u2 in pool:
                if need_siege and kind[e.type] == 'siege' and kind[u2.type] != 'siege' and n_siege() <= 1:
                    continue        # on garde au moins une unité de siège
                if kind[u2.type] == 'siege' and kind[e.type] != 'siege' and len(entries) - n_siege() <= 1:
                    continue        # on garde au moins une unité hors siège (le général)
                if u2.type != e.type and count.get(u2.type, 0) < limit[u2.type] and \
                        sold() - lsc[e.type] + lsc[u2.type] <= max_soldiers and \
                        (kind[u2.type] != 'siege' or kind[e.type] == 'siege' or n_siege() < 2):
                    e2 = UnitEntry(u2.type, u2.soldiers, 0, 0, 0)
                    d = cost(e2) - cost(e)
                    if 0 < d <= rem:
                        cands.append((d, 'set', i, e2))
        if len(entries) < max_units:
            for u2 in pool:
                if u2.cost <= rem and count.get(u2.type, 0) < limit[u2.type] and sold() + lsc[u2.type] <= max_soldiers and \
                        not (kind[u2.type] == 'siege' and n_siege() >= 2):
                    cands.append((u2.cost, 'add', None, UnitEntry(u2.type, u2.soldiers, 0, 0, 0)))
        if not cands:
            break
        if rem < 1200:
            best = max(c[0] for c in cands)
            move = random.choice([c for c in cands if c[0] >= best * 0.97])
        else:
            move = random.choice(cands)
        _, how, i, e2 = move
        if how == 'add':
            entries.append(e2)
            st[0] += lsc[e2.type]
        else:
            count[entries[i].type] -= 1
            st[0] += lsc[e2.type] - lsc[entries[i].type]
            entries[i] = e2
        count[e2.type] = count.get(e2.type, 0) + 1
    # saturation : l'armée ne doit plus pouvoir acheter ou améliorer une unité avec l'or restant
    for _ in range(200):
        moves = possible_purchases(entries, pool, target, max_units, upgrades, max_soldiers)
        if not moves:
            break
        d, how, i, e2 = max(moves, key=lambda m: (m[0], random.random()))
        if how == 'add':
            entries.append(e2)
        else:
            entries[i] = e2
    total = sum(entry_costs(entries, {u.type.lower(): u for u in pool}))
    ns = [e for e in entries if kind[e.type] != 'siege']
    if not ns:
        return [], 0
    goods = [e for e in ns if byt[e.type].is_general]            # unité « bon général » tirée : toujours général
    if goods:
        best = max(goods, key=cost)
    else:                                                        # sinon : une des 3 unités les plus chères du tirage (hors siège)
        best = random.choice(sorted(ns, key=cost, reverse=True)[:3])
    entries.pop(next(k for k, x in enumerate(entries) if x is best))          # retrait par identité (remove() retirait la 1re unité égale : doublon du même objet)
    entries.insert(0, best)
    return entries, total


def load_tga(path):
    """TGA 24/32 bits (brut ou RLE) -> (largeur, hauteur, octets BGR(A) du haut vers le bas, octets par pixel)."""
    import struct
    d = open(path, 'rb').read()
    idl, typ = d[0], d[2]
    w, h = struct.unpack('<HH', d[12:16])
    bp = d[16] // 8
    desc = d[17]
    pos = 18 + idl
    n = w * h * bp
    if typ == 10:
        out = bytearray()
        while len(out) < n and pos < len(d):
            c = d[pos]
            pos += 1
            if c & 128:
                out += d[pos:pos + bp] * ((c & 127) + 1)
                pos += bp
            else:
                k = (c + 1) * bp
                out += d[pos:pos + k]
                pos += k
        raw = bytes(out[:n])
    else:
        raw = d[pos:pos + n]
    if not (desc & 0x20):                      # origine en bas : on retourne verticalement
        rows = [raw[i * w * bp:(i + 1) * w * bp] for i in range(h)]
        raw = b''.join(reversed(rows))
    return w, h, raw, bp


def _blend(c1, c2, t):
    """Mélange deux couleurs #rrggbb (t = part de c2)."""
    a_ = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b_ = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return '#%02x%02x%02x' % tuple(int(round(x + (y - x) * t)) for x, y in zip(a_, b_))


def int_only(sp, var, lo=0):
    """Champ numérique entier : seuls les chiffres sont acceptés ; au-delà du maximum du Spinbox la valeur retombe au maximum,
    et en deçà du minimum (à la sortie du champ) elle remonte au minimum."""
    def hi():
        try:
            return int(float(sp.cget('to')))
        except (tk.TclError, ValueError):
            return 10 ** 9

    def on_write(*_a):
        v = var.get()
        c = ''.join(ch for ch in v if ch.isdigit())
        if c and int(c) > hi():
            c = str(hi())
        if c != v:
            var.set(c)

    def on_leave(_e=None):
        c = var.get()
        n = int(c) if c.isdigit() else lo
        n = max(lo, min(hi(), n))
        if str(n) != c:
            var.set(str(n))
    var.trace_add('write', on_write)
    sp.bind('<FocusOut>', on_leave, add='+')
    sp.bind('<Return>', on_leave, add='+')
    return sp


def lock_columns(tree):
    """Redimensionnement des colonnes d'un tableau à la souris : tirer le séparateur d'une colonne agrandit / réduit cette colonne,
    et la différence est reprise / rendue par les colonnes situées à sa droite : la largeur totale reste égale à celle du tableau
    (rien ne sort du cadre, aucun vide à droite)."""
    st = {'col': None, 'snap': None}

    def cols():
        return list(tree.cget('displaycolumns')) if tree.cget('displaycolumns') not in ('#all', ('#all',)) else list(tree.cget('columns'))

    def mn(c):
        return max(int(tree.column(c, 'minwidth') or 20), 24)

    def press(e):
        st['col'], st['snap'] = None, None
        try:
            if tree.identify_region(e.x, e.y) == 'separator':
                n = int(tree.identify_column(e.x).lstrip('#') or 0) - 1
                cs = cols()
                if 0 <= n < len(cs):
                    st['col'] = cs[n]
                    st['snap'] = {c: int(tree.column(c, 'width')) for c in cs}
        except Exception:
            pass

    def fix(_e=None):
        c, snap = st['col'], st['snap']
        if not c or not snap:
            return
        try:
            W = tree.winfo_width() - 4
            cs = cols()
            if W < 100 or c not in cs:
                return
            i = cs.index(c)
            right = cs[i + 1:]
            left_sum = sum(snap[k] for k in cs[:i])
            want = int(tree.column(c, 'width'))
            if not right:                          # dernière colonne : elle occupe toujours le reste
                tree.column(c, width=max(mn(c), W - left_sum))
                return
            avail = sum(snap[k] - mn(k) for k in right)          # ce que les colonnes de droite peuvent céder
            want = max(mn(c), min(want, snap[c] + avail))
            delta = want - snap[c]
            widths = dict(snap)
            widths[c] = want
            if delta > 0:                            # on prend d'abord sur la voisine, puis sur les suivantes
                for k in right:
                    cut = min(delta, snap[k] - mn(k))
                    widths[k] = snap[k] - cut
                    delta -= cut
                    if delta <= 0:
                        break
            elif delta < 0:                          # la place libérée va à la voisine de droite
                widths[right[0]] = snap[right[0]] - delta
            for k, w in widths.items():
                if int(tree.column(k, 'width')) != w:
                    tree.column(k, width=w)
        except Exception:
            pass

    def release(_e=None):
        fix()
        try:
            W = tree.winfo_width() - 4
            cs = cols()
            total = sum(int(tree.column(k, 'width')) for k in cs)
            if W >= 100 and total != W:              # écart résiduel (arrondis) : repris par la dernière colonne
                last = cs[-1]
                tree.column(last, width=max(mn(last), int(tree.column(last, 'width')) + W - total))
        except Exception:
            pass
        st['col'], st['snap'] = None, None
    def trim(_e=None):
        """Redimensionnement de la fenêtre : si les colonnes dépassent le cadre, on rogne les plus larges (jamais sous leur minimum)."""
        try:
            W = tree.winfo_width() - 4
            cs = cols()
            if W < 100 or not cs:
                return
            excess = sum(int(tree.column(k, 'width')) for k in cs) - W
            room = {k: max(0, int(tree.column(k, 'width')) - mn(k)) for k in cs}
            tot = float(sum(room.values()))
            if excess <= 0 or tot <= 0:
                return
            for k in cs:                         # on rogne chaque colonne proportionnellement à sa marge (au-dessus de son minimum)
                tree.column(k, width=int(tree.column(k, 'width')) - int(round(excess * room[k] / tot)) if excess < tot else mn(k))
        except Exception:
            pass
    tree._lock_trim = trim
    tree.bind('<Configure>', lambda e: tree.after_idle(trim), add='+')
    tree.bind('<<TreeviewSelect>>', lambda e: tree.after_idle(lambda: tree.xview_moveto(0)), add='+')      # un clic sur une ligne ne décale jamais les colonnes
    tree.bind('<ButtonPress-1>', press, add='+')
    tree.bind('<B1-Motion>', lambda e: tree.after_idle(fix), add='+')
    tree.bind('<ButtonRelease-1>', lambda e: (release(), tree.after_idle(release)), add='+')


def tga_to_ppm(path):
    w, h, raw, bp = load_tga(path)
    rgb = bytearray(w * h * 3)
    rgb[0::3] = raw[2::bp]
    rgb[1::3] = raw[1::bp]
    rgb[2::3] = raw[0::bp]
    return w, h, b'P6 %d %d 255\n' % (w, h) + bytes(rgb)


def nearest_battlefield_pic(data_dir, x, y, infos):
    """Image .tga de data/menu/battlefield_pics du lieu de custom_locations.txt le plus proche de (x, y)."""
    pics = os.path.join(data_dir, 'menu', 'battlefield_pics')
    if not os.path.isdir(pics):
        return None
    best = None
    for name, inf in infos.items():
        if not inf.get('location'):
            continue
        cands = []
        if inf.get('image'):
            cands.append(os.path.basename(inf['image'].replace('\\', '/')))
        base = re.sub(r'^.*\s-\s', '', name).lower()
        cands.append(re.sub(r'[^a-z0-9]+', '_', base).strip('_') + '.tga')
        for c in cands:
            fp = os.path.join(pics, c)
            if os.path.isfile(fp):
                dist = (inf['x'] - x) ** 2 + (inf['y'] - y) ** 2
                if best is None or dist < best[0]:
                    best = (dist, fp)
                break
    return best[1] if best else None


TEAM_GAP_MAX = 100             # écart maximum (or) entre les valeurs totales de deux équipes


def army_max_value(pool, max_units, upgrades, cap):
    """Majorant de la valeur qu'une armée de ce pool peut atteindre (20 unités, exemplaires et plafond de soldats respectés)."""
    tops = []
    for u in pool:
        top = entry_cost(u, UnitEntry(u.type, u.soldiers, RANDOM_MAX_EXP, min(u.max_armour, RANDOM_MAX_ARMOUR),
                                      RANDOM_MAX_WEAPON if u.wpn_cost > 0 else 0)) if upgrades else u.cost
        tops.append((top, u))
    tops.sort(key=lambda x: -x[0])
    n, tot, sold = 0, 0, 0
    for top, u in tops:
        for _ in range(max(1, u.max_copies)):
            if n >= max_units or sold + u.ls > cap:
                break
            n += 1
            tot += top
            sold += u.ls
    return tot


def roll_army(pool, udict, target, max_units, upgrades, need_siege, cap, tries=30, good=15):
    """Plusieurs armées aléatoires pour la même cible : on garde celle dont la valeur est la plus proche (sous la cible).
    Retourne (reste, entrées, valeur) ou None."""
    best = None
    for _ in range(tries):
        e, tot = fill_army(pool, udict, target, max_units, upgrades, good, need_siege, cap)
        if not e or tot > target:
            continue
        d = target - tot
        if best is None or d < best[0]:
            best = (d, e, tot)
            if d <= good:
                break
    return best


_DEADLINE = [0.0]          # heure limite (time.time) de la génération d'armées en cours : au-delà, on garde le meilleur résultat obtenu
GEN_TIME_LIMIT = 5.0       # secondes maximum pour générer des armées (valeurs inatteignables : l'éditeur ne doit jamais se figer)


def build_balanced_armies(pools, teams, udict, team_value, max_units, upgrades, floor=GOLD_MIN, needs=None, max_soldiers=10 ** 9):
    own = not _DEADLINE[0]
    if own:
        _DEADLINE[0] = time.time() + GEN_TIME_LIMIT
    try:
        return _build_balanced_armies(pools, teams, udict, team_value, max_units, upgrades, floor, needs, max_soldiers)
    finally:
        if own:
            _DEADLINE[0] = 0.0


def _build_balanced_armies(pools, teams, udict, team_value, max_units, upgrades, floor=GOLD_MIN, needs=None, max_soldiers=10 ** 9):
    """Une armée par liste ; chaque équipe a la même valeur totale (écart <= 100 or), partagée à parts égales
    entre ses armées (armées d'une même équipe de valeurs très proches). Retourne (listes, valeur par équipe, réussite)."""
    sizes = {}
    for t in teams:
        sizes[t] = sizes.get(t, 0) + 1
    t_val = min(int(team_value), TEAM_GOLD_MAX)
    cap = max(1, int(max_soldiers // max(1, len(pools))))          # soldats par armée : total / nombre d'armées
    # valeur inatteignable (20 unités, plafond de soldats) : on la ramène d'emblée à ce que les armées peuvent atteindre
    bound = [army_max_value(p, max_units, upgrades, cap) for p in pools]
    for t in sizes:
        mb = min(b for b, tt in zip(bound, teams) if tt == t)
        t_val = min(t_val, int(0.93 * mb * sizes[t]))
    t_val = max(t_val, int(floor))
    for attempt in range(14):
        if attempt and time.time() > _DEADLINE[0]:
            break
        res, tots, ok = [], [], True
        for ai, (pool, team) in enumerate(zip(pools, teams)):
            target = int(t_val / sizes[team])
            ns = bool(needs and needs[ai])
            got = roll_army(pool, udict, target, max_units, upgrades, ns, cap)
            if got is None or (got[0] > 120 and possible_purchases(got[1], pool, target, max_units, upgrades, cap)):
                ok = False
                break
            res.append(got[1])
            tots.append(got[2])
        if not ok:
            t_val = max(floor, int(t_val * 0.97))
            continue
        # égalisation : (1) armées d'une même équipe à 100 or près, (2) équipes à 100 or près ; on relance les armées fautives
        def spread(t):
            vals = [tots[i] for i, tt in enumerate(teams) if tt == t]
            return max(vals) - min(vals) if len(vals) > 1 else 0

        def team_totals():
            tv_ = {}
            for t_, v_ in zip(teams, tots):
                tv_[t_] = tv_.get(t_, 0) + v_
            return tv_
        for _round in range(80):
            if time.time() > _DEADLINE[0]:
                break
            tv = team_totals()
            top, low = max(tv.values()), min(tv.values())
            viol = [t for t in sizes if sizes[t] > 1 and spread(t) > ARMY_GAP_MAX]
            if top - low <= TEAM_GAP_MAX and not viol:
                break
            if viol:                         # une équipe dont les armées s'écartent de plus de 100 or
                t = random.choice(viol)
                idx = [i for i, tt in enumerate(teams) if tt == t]
                vals = [tots[i] for i in idx]
                hi_v, lo_v = max(vals), min(vals)
                if random.random() < 0.5:
                    i, tgt = idx[vals.index(lo_v)], hi_v          # la plus faible monte vers la plus forte
                else:
                    i, tgt = idx[vals.index(hi_v)], lo_v          # la plus forte descend vers la plus faible
                before = spread(t)
                got = roll_army(pools[i], udict, tgt, max_units, upgrades, bool(needs and needs[i]), cap)
                if got is not None:
                    old = tots[i]
                    tots[i] = got[2]
                    if spread(t) < before:
                        res[i] = got[1]
                    else:
                        tots[i] = old
                continue
            lt = min(tv, key=tv.get)
            idx = [i for i, t in enumerate(teams) if t == lt]
            i = random.choice(idx)
            tgt = tots[i] + (top - tv[lt])
            got = roll_army(pools[i], udict, tgt, max_units, upgrades, bool(needs and needs[i]), cap)
            if got is not None and abs(top - (tv[lt] - tots[i] + got[2])) < top - tv[lt]:
                res[i], tots[i] = got[1], got[2]
        tv = team_totals()
        if max(tv.values()) - min(tv.values()) <= TEAM_GAP_MAX and not any(sizes[t] > 1 and spread(t) > ARMY_GAP_MAX for t in sizes):
            return res, t_val, True
        if attempt >= 5:
            return res, t_val, False
        t_val = max(floor, int(t_val * 0.99))
    res = []
    for ai, (pool, team) in enumerate(zip(pools, teams)):
        e, _ = fill_army(pool, udict, int(t_val / sizes[team]), max_units, upgrades, ARMY_TOLERANCE, bool(needs and needs[ai]), cap)
        res.append(e)
    return res, t_val, False


def engine_rule_problems(settlement, army, udict):
    """Règle des engins : chaque faction attaquante porte au moins un engin de siège (1 bélier au plus pour les armées aléatoires) ;
    Fortress et Citadel : toujours un bélier. Retourne la liste des problèmes (vide si la règle est respectée)."""
    ok = engine_allowed(settlement)
    if not any(ok.values()):
        return []
    cnt = {'ram': 0, 'ladder': 0, 'tower': 0}
    for e in army.units:
        if e.engine in cnt:
            cnt[e.engine] += 1
    out = []
    if not sum(cnt.values()):
        out.append('no_engine')
    if settlement in ('Fortress', 'Citadel') and ok.get('ram') and not cnt['ram']:
        out.append('no_ram')
    return out


def build_armies_siege(pools, teams, udict, target, max_units, upgrades, floor, att_flags, settlement, max_soldiers=10 ** 9):
    """build_balanced_armies + siège : le général n'est jamais une unité de siège ; chaque armée attaquante reçoit des engins
    (au moins un, 1 bélier au plus ; Fortress / Citadel : toujours un bélier). Les unités de siège sont tirées comme les autres."""
    needs = [False] * len(pools)
    lists, t_val, ok = [], target, True
    own = not _DEADLINE[0]
    if own:
        _DEADLINE[0] = time.time() + GEN_TIME_LIMIT
    try:
        return _build_armies_siege(pools, teams, udict, target, max_units, upgrades, floor, att_flags, settlement, max_soldiers, needs)
    finally:
        if own:
            _DEADLINE[0] = 0.0


def _build_armies_siege(pools, teams, udict, target, max_units, upgrades, floor, att_flags, settlement, max_soldiers, needs):
    lists, t_val, ok = [], target, True
    for _ in range(10):
        lists, t_val, ok = build_balanced_armies(pools, teams, udict, target, max_units, upgrades, floor, needs, max_soldiers)
        bad = False
        for i, (lst, att) in enumerate(zip(lists, att_flags)):
            ensure_general(lst, udict)
            if not att or not settlement:
                continue
            random_engines(Army(faction='x', units=lst), settlement, udict)
            if engine_rule_problems(settlement, Army(faction='x', units=lst), udict):
                bad = True
        if not bad or time.time() > _DEADLINE[0]:
            break
    return lists, t_val, ok


def parse_weather_patterns(text):
    out = []
    for pid in re.findall(r'<pattern\s+id="([^"]+)"\s+audio_type', text):
        if pid not in out:
            out.append(pid)
    return out


WEATHER_CHANCE = {}      # (saison, climat, météo) -> probabilité dans weather_db.xml


def parse_weather_climates(text):
    """weather_db.xml -> {saison: {climat: [identifiants de météo]}}."""
    out = {}
    i = text.find('<seasons')
    if i < 0:
        return out
    for sm in re.finditer(r'<season\s+id="([^"]+)"\s*>(.*?)</season>', text[i:], re.S):
        clim = {}
        for cm in re.finditer(r'<climate\s+id="([^"]+)"\s*>(.*?)</climate>', sm.group(2), re.S):
            clim[cm.group(1)] = re.findall(r'<pattern\s+id="([^"]+)"', cm.group(2))
            for pid, ch in re.findall(r'<pattern\s+id="([^"]+)"\s+chance="([0-9.]+)"', cm.group(2)):
                WEATHER_CHANCE[(sm.group(1), cm.group(1), pid)] = float(ch)
        out[sm.group(1)] = clim
    return out


def default_climates():
    """Table climats -> météos intégrée (si weather_db.xml est introuvable)."""
    out = {}
    for se, cl in EMBEDDED_CLIMATES.items():
        out[se] = {}
        for c, lst in cl.items():
            out[se][c] = [p for p, _ in lst]
            for p, ch in lst:
                WEATHER_CHANCE[(se, c, p)] = ch
    return out


def find_weather_db(data_dir):
    base = data_dir.rstrip('/\\')
    for c in (os.path.join(base, 'weather_db.xml'), os.path.join(os.path.dirname(base), 'weather_db.xml'),
              os.path.join(base, 'world', 'weather_db.xml'), os.path.join(os.path.dirname(os.path.dirname(base)), 'weather_db.xml')):
        if os.path.isfile(c):
            return c
    for root, dirs, files in os.walk(os.path.dirname(base)):
        if root[len(os.path.dirname(base)):].count(os.sep) > 3:
            dirs[:] = []
            continue
        for fn in files:
            if fn.lower() == 'weather_db.xml':
                return os.path.join(root, fn)
    return None


def parse_custom_locations(text):
    """custom_locations.txt -> liste de dict(name, x, y, climate, summer_only, locked)."""
    out, cur = [], None
    for line in text.split('\n'):
        s = line.split(';', 1)[0].strip()
        if not s:
            continue
        m = re.match(r'^custom_location\s+(.+)$', s)
        if m:
            cur = {'name': m.group(1).strip(), 'x': 0, 'y': 0, 'climate': '', 'summer_only': False, 'locked': False}
            out.append(cur)
            continue
        if cur is None:
            continue
        m = re.match(r'^location\s+(-?\d+)\s+(-?\d+)', s)
        if m:
            cur['x'], cur['y'] = int(m.group(1)), int(m.group(2))
            continue
        k = s.split(None, 1)
        if len(k) == 2:
            if k[0] == 'image':
                cur['image'] = k[1].strip()
            elif k[0] == 'climate':
                cur['climate'] = k[1].strip()
            elif k[0] == 'summer':
                cur['summer_only'] = k[1].strip().lower() == 'yes'
            elif k[0] == 'sett_locked':
                cur['locked'] = k[1].strip().lower() == 'yes'
    return out


def season_choices(info, chaos=False):
    """Saisons proposées pour une carte : une seule (été) si la carte est verrouillée ou « summer yes » (sauf « climats chaotiques »)."""
    if not chaos and info and (info.get('locked') or info.get('summer_only')):
        return ['summer']
    return list(SEASONS)


def weather_choices(climates, info, season, all_patterns, chaos=False):
    """Météos du climat de la carte (weather_db.xml) ; avec « climats chaotiques », toutes celles du mod à la suite."""
    first = []
    if info and info.get('climate') and climates:
        first = list(dict.fromkeys(climates.get(season, {}).get(info['climate'], [])))
    if not first:
        return list(all_patterns)
    return first + ([w for w in all_patterns if w not in first] if chaos else [])


RANDOM_BANNED_WEATHER = set()      # jamais tirées par le générateur aléatoire


def random_weather(climates, info, season, all_patterns, chaos=False):
    """Météo tirée au hasard parmi celles du climat de la carte (valeurs sûres), sinon parmi les courantes ;
    « climats chaotiques » : parmi toutes les météos du mod."""
    if chaos and all_patterns:
        allw = [w for w in all_patterns if w not in RANDOM_BANNED_WEATHER] or list(all_patterns)
        native = []
        if info and info.get('climate') and climates:
            native = [p for p in dict.fromkeys(climates.get(season, {}).get(info['climate'], [])) if p in allw]
        others = [w for w in allw if w not in native]
        if native and others:                      # une chance sur deux : météo du climat de la carte, sinon une météo « chaotique »
            return random.choice(native if random.random() < 0.5 else others)
        return random.choice(allw)
    if info and info.get('climate') and climates:
        lst = climates.get(season, {}).get(info['climate'])
        if lst:
            lst = [p for p in dict.fromkeys(lst) if p not in RANDOM_BANNED_WEATHER] or list(dict.fromkeys(lst))
            return random.choice(lst)                  # toutes les météos du climat à égalité
    safe = [w for w in ('clear', 'cloudy', 'rain', 'storm') if w in all_patterns]
    return random.choice(safe or ['clear'])


def pretty_words(text):
    return ' '.join(w.capitalize() for w in re.sub(r'[^A-Za-z0-9]+', ' ', ascii_only(text)).split())


def tod_name(hour):
    """Période de la journée d'une heure : chaque période dure jusqu'à la suivante (Nuit : 22:0 à 5:5)."""
    h = hour % 24
    name = TIMES_OF_DAY[-1][0]
    for n, t in TIMES_OF_DAY:
        if h >= t:
            name = n
    return name


def time_name(hour):
    idx = min(range(len(TIMES_OF_DAY)), key=lambda i: abs(TIMES_OF_DAY[i][1] - hour))
    return TIME_NAMES_EN[idx]


def clean_map_label(label):
    """Retire le symbole des cartes préconstruites et les coordonnées « (x, y) » d'une étiquette de carte."""
    lab = (label or '').strip()
    return re.sub(r'\s*\(\s*\d+\s*,\s*\d+\s*\)\s*$', '', lab).strip()


def random_scenario_name(weather, map_label, hour, team_sizes=None, settlement=''):
    """Ex. « Arabyan Oasis Night » : nom de la carte + (siège : type de colonie) + période de la journée."""
    return ' '.join(p for p in (pretty_words(clean_map_label(map_label)), settlement, time_name(hour)) if p)


# --------------------------------------------------------------------------------------
#  MODÈLE DE SCÉNARIO
# --------------------------------------------------------------------------------------

@dataclass
class UnitEntry:
    type: str
    soldiers: int = 40
    exp: int = 0
    armour: int = 0
    weapon: int = 0
    engine: str = ''          # siège : engin porté par cette unité d'infanterie ('ram', 'ladder', 'tower' ou '')

    @property
    def ls(self):
        return large_soldiers(self.soldiers, OFFICERS.get(self.type, 0))


@dataclass
class Army:
    faction: str
    human: bool = True
    team: int = 1
    general: str = ''
    gender: str = 'male'                           # 'male' ou 'female' (genre du général)
    age: int = 30                                  # âge du général (16 à 127)
    units: list = field(default_factory=list)      # liste de UnitEntry


@dataclass
class Scenario:
    name: str = 'Mon_Scenario_MP'
    map_x: int = 94
    map_y: int = 131
    map_label: str = ''
    hour: float = 12.0
    param2: float = 0.0
    weather: str = 'clear'
    year: int = 2304
    season: str = 'summer'
    gap: int = 160            # distance entre les lignes de front
    depth: int = 150          # profondeur d'une zone de déploiement
    army_width: int = 450     # largeur d'une zone par armée
    aux: bool = False         # afficher les unités auxiliaires dans la bibliothèque
    chaos: bool = False                            # « climats chaotiques » : météos et saisons hors climat de la carte
    solo: bool = False                             # scénario solo : « singleplayer not_multiplayer » (les autres factions humaines sont jouées par l'IA)
    team_roles: dict = field(default_factory=dict)  # "1" -> 'defending'
    home_faction: str = ''
    cx: float = 0.0           # décalage / rotation du plan de déploiement (cartes préconstruites)
    cy: float = 0.0
    rot: float = 0.0
    siege: bool = False
    siege_type: str = 'Castle'          # libellé du menu Settlement
    siege_culture: str = 'Humans'
    siege_dlevel: int = 3               # niveau de défense (1 à 3)
    siege_side: str = 'Sud'          # ancien réglage (ignoré)
    siege_same: bool = False         # siège : tous les assaillants partagent une seule zone (« same spawn »)
    description: str = ''     # texte ajouté à la fin de la description du scénario
    siege_dist: int = 0       # distance de la ligne d'assaut au centre de la colonie (0 = automatique)
    ram: int = 1
    ladder: int = 2
    tower: int = 1
    armies: list = field(default_factory=list)

    def role_of(self, team):
        r = self.team_roles.get(str(team))
        if r in ROLES:
            return r
        return 'defending' if team == min([a.team for a in self.armies] or [1]) else 'attacking'


def safe_name(name):
    name = ascii_only(name).replace(' ', '_')
    name = re.sub(r'[^A-Za-z0-9_\-()\.]', '', name)
    return name


def folder_name(name):
    """Nom du dossier du scénario : mots séparés par « _ » (le jeu lit un seul mot sur la ligne « battle »)."""
    return safe_name(name)


# --------------------------------------------------------------------------------------
#  PLACEMENT AUTOMATIQUE DES TROUPES
# --------------------------------------------------------------------------------------

def unit_kind(u, index):
    if index == 0:
        return 'general'
    if u.category == 'siege':
        return 'siege'
    if u.category == 'cavalry':
        return 'cav'
    if u.cls in ('missile', 'skirmish'):
        return 'ranged'
    return 'inf'


def unit_width(u, soldiers):
    if u.category == 'siege':
        return 8.0
    files = math.ceil(max(1, soldiers) / max(1, u.ranks))
    return max(6.0, min(120.0, files * max(0.8, u.spacing)))


def _pack_rows(items, avail):
    """items: [(idx, width)] -> liste de lignes, chaque ligne = liste d'items."""
    rows, cur, curw = [], [], 0.0
    for it in items:
        w = it[1] + UNIT_GAP
        if cur and curw + w > avail:
            rows.append(cur)
            cur, curw = [], 0.0
        cur.append(it)
        curw += w
    if cur:
        rows.append(cur)
    return rows


def local_layout(army, udict, slot_w, row_step=None):
    """Place les unités d'une armée dans un repère local.
    u = décalage latéral (droite positive), v = distance derrière la ligne de front.
    Retourne ({index: (u, v, width)}, profondeur nécessaire)."""
    avail = max(80.0, slot_w - 40.0)
    groups = {'inf': [], 'cav': [], 'ranged': [], 'siege': [], 'general': []}
    for i, e in enumerate(army.units):
        u = udict.get(e.type.lower())
        if u is None:
            u = UnitDef(type=e.type)
        groups[unit_kind(u, i)].append((i, unit_width(u, e.soldiers)))

    # ligne de front : cavalerie aux ailes, infanterie au centre
    left = groups['cav'][0::2]
    right = groups['cav'][1::2][::-1]
    front = left + groups['inf'] + right
    rows = _pack_rows(front, avail)
    rows += _pack_rows(groups['ranged'], avail)
    back = groups['general'] + groups['siege']
    rows += _pack_rows(back, avail)

    pos = {}
    step = row_step or ROW_STEP
    for r, row in enumerate(rows):
        total = sum(w for _, w in row) + UNIT_GAP * (len(row) - 1)
        x = -total / 2.0
        v = 25.0 + r * step
        for idx, w in row:
            pos[idx] = (x + w / 2.0, v, w)
            x += w + UNIT_GAP
    needed = 25.0 + max(0, len(rows) - 1) * step + 30.0
    return pos, needed


def norm_angle(a):
    a = (a + 180.0) % 360.0 - 180.0
    return 180.0 if a == -180.0 else a


# Cartes du mod dont les zones de base sont décalées (coordonnées de la carte de campagne -> (décalage X, décalage Y) en m)
LOCATION_OFFSET = {(107, 163): (-100.0, -400.0)}        # Bretonnian Island : zones au sud-ouest, hors de l'eau
# Cartes traversées par un fleuve au milieu : les équipes sont réparties de part et d'autre, jamais sur le fleuve
RIVER_LOCATIONS = {(198, 12): 'vertical',              # Bridge - River Mortis
                   (244, 98): 'horizontal'}            # Crossing - Varenka Ford
RIVER_HALF_WIDTH = 150.0           # demi-largeur du fleuve (m) : aucune zone ne commence avant
RIVER_BANK_HALF = 650.0            # demi-longueur utilisable d'une rive le long du fleuve
# Crossing : le fleuve se rapproche de la rive sud à l'est (x >= 100) et à l'ouest (x <= -100) -> zones reculées (côté, x min, x max, recul en m)
RIVER_EXTRA = {(244, 98): [(0, 100.0, 9999.0, 110.0), (0, -9999.0, -100.0, 150.0)]}
RIVER_TEAM_GAP = 180.0             # espace minimal entre deux équipes d'une même rive


def _river_extra(sc, side, x):
    for sd, x0, x1, e in RIVER_EXTRA.get((sc.map_x, sc.map_y), []):
        if sd == side and x0 <= x <= x1:
            return e
    return 0.0


def _river_layout(sc, udict, vertical):
    """Zones de déploiement de part et d'autre d'un fleuve central, jamais dessus : les équipes sont réparties en alternance sur les deux
    rives ; sur une même rive, chaque équipe a son bloc, les blocs étant éloignés les uns des autres (pas d'équipes ennemies côte à côte).
    Un bloc trop large est replié en plusieurs rangées vers l'arrière."""
    warnings = []
    layout = {}
    teams = sorted({a.team for a in sc.armies})
    members = {t: [i for i, a in enumerate(sc.armies) if a.team == t] for t in teams}
    side_of = {t: ti % 2 for ti, t in enumerate(teams)}          # 0 : sud (ou ouest), 1 : nord (ou est)
    front_r = max(sc.gap / 2.0, RIVER_HALF_WIDTH)
    length = 2.0 * RIVER_BANK_HALF                               # longueur utilisable d'une rive, le long du fleuve
    for side in (0, 1):
        ts = [t for t in teams if side_of[t] == side]
        k = len(ts)
        if not k:
            continue
        phi = 180.0 if side == 0 else 0.0
        h = (phi + 180.0) % 360.0
        fx, fy = math.sin(math.radians(h)), math.cos(math.radians(h))
        rx, ry = math.cos(math.radians(h)), -math.sin(math.radians(h))
        c_phi = math.cos(math.radians(phi))
        block = (length - (k - 1) * RIVER_TEAM_GAP) / k           # largeur maximale d'un bloc d'équipe
        for ti, t in enumerate(ts):
            idxs = members[t]
            n = len(idxs)
            w = min(float(sc.army_width), 1500.0 / n)
            per_row = max(1, int(block // w))
            w = min(w, block / min(n, per_row))
            rows = -(-n // per_row)
            locs, need = {}, float(sc.depth)
            for i in idxs:
                locs[i], nd = local_layout(sc.armies[i], udict, w)
                need = max(need, nd)
            depth = need
            cx_t = -length / 2.0 + block / 2.0 + ti * (block + RIVER_TEAM_GAP) if k > 1 else 0.0
            for j, i in enumerate(idxs):
                row, col = divmod(j, per_row)
                in_row = min(per_row, n - row * per_row)
                ccx = cx_t + (col - (in_row - 1) / 2.0) * w * (1 if side == 0 else -1)
                extra_r = _river_extra(sc, side, ccx)
                ccy = (front_r + extra_r + depth / 2.0 + row * (depth + 50.0)) * c_phi
                hw, hd = w / 2.0 - 8.0, depth / 2.0
                zone = [(ccx + rx * hw * su + fx * (hd * sv + 20 * sv - 20), ccy + ry * hw * su + fy * (hd * sv + 20 * sv - 20))
                        for su, sv in ((1, 1), (1, -1), (-1, -1), (-1, 1))]
                front_x, front_y = ccx + fx * hd, ccy + fy * hd
                units = []
                for idx in range(len(sc.armies[i].units)):
                    u, v, ww = locs[i][idx]
                    units.append((front_x + rx * u - fx * v, front_y + ry * u - fy * v, norm_angle(round(h)), ww))
                layout[i] = {'zone': zone, 'units': units, 'team': t}
            if getattr(sc, 'siege_same', False) and n > 1 and rows == 1:
                hwa = n * w / 2.0 - 8.0
                hd = depth / 2.0
                cy_c = (front_r + _river_extra(sc, side, cx_t) + depth / 2.0) * c_phi
                common = [(cx_t + rx * hwa * su + fx * (hd * sv + 20 * sv - 20), cy_c + ry * hwa * su + fy * (hd * sv + 20 * sv - 20))
                          for su, sv in ((1, 1), (1, -1), (-1, -1), (-1, 1))]
                for i in idxs:
                    layout[i]['zone'] = common
    if vertical:                         # fleuve vertical : équipes à l'ouest et à l'est (rotation de 90° dans le sens horaire)
        for L in layout.values():
            L['zone'] = [(y, -x) for x, y in L['zone']]
            L['units'] = [(y, -x, norm_angle(round(o + 90.0)), ww) for x, y, o, ww in L['units']]
    return layout, warnings


def compute_layout(sc, udict):
    """Retourne (layout, avertissements).
    layout[i] = {'zone': [(x,y)]*4, 'units': [(x, y, orient, width)], 'team': t}"""
    if getattr(sc, 'siege', False):
        return compute_siege_layout(sc, udict)
    warnings = []
    teams = sorted({a.team for a in sc.armies})
    T = len(teams)
    layout = {}
    if not sc.armies:
        return layout, warnings
    river = RIVER_LOCATIONS.get((sc.map_x, sc.map_y)) if not (sc.rot or sc.cx or sc.cy) else None
    if river:
        return _river_layout(sc, udict, river == 'vertical')
    members_by_team = {t: [i for i, a in enumerate(sc.armies) if a.team == t] for t in teams}
    slot_w = {}
    for t in teams:
        n = len(members_by_team[t])
        slot_w[t] = min(float(sc.army_width), 1500.0 / n)

    team_widths = [slot_w[t] * len(members_by_team[t]) for t in teams]
    if T <= 2:
        front_r = sc.gap / 2.0
    else:
        front_r = max(sc.gap / 2.0, (max(team_widths) / 2.0) / math.tan(math.pi / T))

    for ti, t in enumerate(teams):
        idxs = members_by_team[t]
        if T == 1:
            phi = 180.0
        elif T == 2:
            phi = 180.0 if ti == 0 else 0.0
        else:
            phi = (180.0 + 360.0 * ti / T) % 360.0
        locs = {}
        need = float(sc.depth)
        for i in idxs:
            pos, needed = local_layout(sc.armies[i], udict, slot_w[t])
            locs[i] = pos
            need = max(need, needed)
        if need > sc.depth + 0.5:
            warnings.append("Zone de l'équipe %d agrandie à %d m de profondeur pour contenir toutes les unités." % (t, need))
        depth = need
        s_phi, c_phi = math.sin(math.radians(phi)), math.cos(math.radians(phi))
        radial = front_r + depth / 2.0
        cx, cy = radial * s_phi, radial * c_phi
        h = (phi + 180.0) % 360.0
        fx, fy = math.sin(math.radians(h)), math.cos(math.radians(h))        # vers l'ennemi
        rx, ry = math.cos(math.radians(h)), -math.sin(math.radians(h))      # à droite
        n = len(idxs)
        for j, i in enumerate(idxs):
            off = (j - (n - 1) / 2.0) * slot_w[t]
            ccx, ccy = cx + rx * off, cy + ry * off
            hw = slot_w[t] / 2.0 - 8.0
            hd = depth / 2.0
            zone = []
            for su, sv in ((1, 1), (1, -1), (-1, -1), (-1, 1)):
                zone.append((ccx + rx * hw * su + fx * (hd * sv + 20 * sv - 20), ccy + ry * hw * su + fy * (hd * sv + 20 * sv - 20)))
            front_x, front_y = ccx + fx * hd, ccy + fy * hd
            units = []
            for idx in range(len(sc.armies[i].units)):
                u, v, w = locs[i][idx]
                x = front_x + rx * u - fx * v
                y = front_y + ry * u - fy * v
                units.append((x, y, norm_angle(round(h)), w))
            layout[i] = {'zone': zone, 'units': units, 'team': t}
        if getattr(sc, 'siege_same', False) and n > 1:        # même spawn : une seule zone pour toute l'équipe
            hwa = n * slot_w[t] / 2.0 - 8.0
            hd = depth / 2.0
            common = [(cx + rx * hwa * su + fx * (hd * sv + 20 * sv - 20), cy + ry * hwa * su + fy * (hd * sv + 20 * sv - 20))
                      for su, sv in ((1, 1), (1, -1), (-1, -1), (-1, 1))]
            for i in idxs:
                layout[i]['zone'] = common
    off = LOCATION_OFFSET.get((sc.map_x, sc.map_y)) if not (sc.rot or sc.cx or sc.cy) and T <= 4 else None
    cx_, cy_, rot_ = (off[0], off[1], 0.0) if off else (sc.cx, sc.cy, sc.rot)
    if rot_ or cx_ or cy_:        # carte préconstruite : axe et centre de ses zones de déploiement
        th = math.radians(rot_)
        c, sn = math.cos(th), math.sin(th)

        def tf(x, y):
            return x * c + y * sn + cx_, -x * sn + y * c + cy_
        for L in layout.values():
            L['zone'] = [tf(x, y) for x, y in L['zone']]
            L['units'] = [tf(x, y) + (norm_angle(round(o + rot_)), w) for x, y, o, w in L['units']]
    m = 0.0
    for L in layout.values():
        for x, y in L['zone']:
            m = max(m, abs(x - cx_), abs(y - cy_))
    if m > MAP_WARN:
        warnings.append("Certaines zones de déploiement dépassent ±%d m : elles risquent de sortir de la carte "
                        "(réduisez la largeur par armée ou la distance entre camps)." % MAP_WARN)
    return layout, warnings


# --------------------------------------------------------------------------------------
#  SIÈGE
# --------------------------------------------------------------------------------------

def siege_package(settlement, culture):
    """(package_path, rayon, origine) ; origine : 'mod' (fichier du mod) ou 'vanilla' (paquet du jeu, nom supposé).
    None si la colonie n'est pas proposée pour cette culture."""
    if settlement == 'Fort':          # le Fort est un élément « fort » du script : aucun package_path
        return ('', 135, 'vanilla') if culture in CULTURE_FACTION else None
    if settlement not in TYPE_PKG:
        return None
    if culture == 'Ancient Civilisations':
        if settlement in NO_ANCIENT or settlement not in PKG_ANCIENT:
            return None
        return PKG_ANCIENT[settlement] + ('mod',)
    if culture == 'Savages' and settlement in PKG_SAVAGES:
        return PKG_SAVAGES[settlement] + ('mod',)
    cd = CULTURE_DIR.get(culture)
    if not cd:
        return None
    sub, fn, radius = TYPE_PKG[settlement]
    name = MOD_PKG.get((culture, settlement))
    origin = 'mod' if name else 'vanilla'
    if not name:
        name = fn.format(c=cd.lower())
    return ('settlements/%s/%s%s.world' % (cd, sub, name), radius, origin)


def siege_has_package(sc):
    """package_path n'est écrit que pour un .world que le mod contient réellement (relevé Procmon du menu). Sinon le jeu construit la
    colonie lui-même à partir de blockset\\<culture>, exactement comme dans le menu « bataille personnalisée »."""
    pk = siege_package(sc.siege_type, getattr(sc, 'siege_culture', 'Humans'))
    return bool(pk and pk[2] == 'mod')


def siege_available(settlement, culture):
    return siege_package(settlement, culture) is not None


def settlement_cultures(settlement):
    """Cultures proposées par le menu du jeu pour cette colonie."""
    return [c[0] for c in CULTURES if c[0] != 'Ancient Civilisations' or settlement not in NO_ANCIENT]


def siege_engine_limits(settlement):
    """(béliers, échelles, tours) : 1 si l'engin est proposé pour cette colonie."""
    return SIEGE_ENGINES.get(settlement, (1, 1, 1))


ENGINE_NAMES = {'ram': 'Bélier', 'ladder': 'Échelle', 'tower': 'Tour'}
ENGINE_KINDS = ('ladder', 'tower', 'ram')          # ordre de priorité du hasard : échelles > tours > béliers
ENGINE_MAX = {'ram': 9, 'ladder': 9, 'tower': 9}   # par armée attaquante (maximum du jeu, mode escarmouche)
ENGINE_TOTAL_MAX = 20                                 # total d'engins par armée attaquante
ENGINE_RATIO = {'ram': 1, 'tower': 2, 'ladder': 3}    # répartition aléatoire : 1 bélier / 2 tours / 3 échelles


def engine_allowed(settlement):
    """{type d'engin: proposé ?} pour cette colonie."""
    r, l, tw = siege_engine_limits(settlement)
    return {'ram': bool(r), 'ladder': bool(l), 'tower': bool(tw)}


ENGINE_CARRIER_MIN = 21   # une unité de 20 soldats ou moins (mages, trolls, monstres…) ne porte pas d'engin : le jeu ne le fait pas apparaître


def engine_carriers(army, udict):
    """Indices des unités qui peuvent porter un engin : infanterie, hors général (1re unité). Les unités de tir en dernier."""
    c = []
    for i, e in enumerate(army.units):
        u = udict.get(e.type.lower())
        if i == 0 or u is None or u.category != 'infantry' or (e.soldiers or 0) < ENGINE_CARRIER_MIN:
            continue
        c.append((1 if u.cls in ('missile', 'skirmish') else 0, i))
    c.sort()
    return [i for _, i in c]


def clear_engines(army):
    for e in army.units:
        e.engine = ''


def siege_clamp(sc, udict=None):
    """Culture et engins ramenés à ce que le menu du jeu propose pour la colonie choisie ; engins retirés hors siège
    et pour les armées qui ne sont pas assaillantes."""
    st = getattr(sc, 'siege_type', 'Castle')
    if getattr(sc, 'siege_culture', 'Humans') not in settlement_cultures(st):
        sc.siege_culture = 'Humans'
    ok = engine_allowed(st)
    r, l, tw = siege_engine_limits(st)
    sc.ram, sc.ladder, sc.tower = (sc.ram if r else 0), (sc.ladder if l else 0), (sc.tower if tw else 0)
    if getattr(sc, 'siege_dist', 0):
        sc.siege_dist = max(siege_min_distance(sc), min(int(sc.siege_dist), siege_max_distance(sc)))
    roles = siege_roles(sc) if getattr(sc, 'siege', False) else None
    for a in sc.armies:
        if not roles or a.team != roles[1]:
            clear_engines(a)
            continue
        cnt = {'ram': 0, 'ladder': 0, 'tower': 0}
        can = set(engine_carriers(a, udict)) if udict else None
        for i, e in enumerate(a.units):
            if e.engine:
                if (not ok.get(e.engine) or cnt[e.engine] >= ENGINE_MAX[e.engine] or sum(cnt.values()) >= ENGINE_TOTAL_MAX
                        or (can is not None and i not in can)):
                    e.engine = ''
                else:
                    cnt[e.engine] += 1
    return sc


def migrate_engines(sc, udict):
    """Anciens projets : béliers / échelles / tours du scénario -> engins portés par l'infanterie de chaque armée attaquante."""
    if not (sc.ram or sc.ladder or sc.tower):
        return sc
    roles = siege_roles(sc) if getattr(sc, 'siege', False) else None
    if roles:
        for a in sc.armies:
            if a.team != roles[1] or any(e.engine for e in a.units):
                continue
            order = engine_carriers(a, udict)
            for kind, n in (('ram', sc.ram), ('tower', sc.tower), ('ladder', sc.ladder)):
                for _ in range(max(0, n)):
                    if order:
                        a.units[order.pop(0)].engine = kind
    sc.ram = sc.ladder = sc.tower = 0
    return siege_clamp(sc, udict)


def random_engines(army, settlement, udict, rng=random):
    """Siège aléatoire : un engin par unité capable d'en porter (20 au plus), les unités porteuses sont tirées au hasard ;
    répartition 1 bélier / 2 tours / 3 échelles (maximum 9 par type), types tirés au hasard selon ce rapport.
    Au moins un engin ; Fortress et Citadel : au moins 1 bélier. Retourne le nombre d'engins placés."""
    clear_engines(army)
    ok = engine_allowed(settlement)
    kinds = [k for k in ENGINE_KINDS if ok.get(k)]
    carriers = list(engine_carriers(army, udict))
    if not kinds or not carriers:
        return 0
    rng.shuffle(carriers)
    carriers = carriers[:ENGINE_TOTAL_MAX]
    n = min(len(carriers), ENGINE_TOTAL_MAX, ENGINE_MAX_SUM(kinds))
    must_ram = settlement in ('Fortress', 'Citadel') and ok.get('ram')
    W = float(sum(ENGINE_RATIO[k] for k in kinds))
    cnt = {k: min(ENGINE_MAX[k], int(n * ENGINE_RATIO[k] / W)) for k in kinds}
    if must_ram and not cnt.get('ram'):
        cnt['ram'] = 1
    while sum(cnt.values()) < n:               # reste : tirage selon le rapport, dans les maximums
        left = [k for k in kinds if cnt[k] < ENGINE_MAX[k]]
        cnt[rng.choices(left, weights=[ENGINE_RATIO[k] for k in left])[0]] += 1
    while sum(cnt.values()) > n:               # (bélier obligatoire en trop) : retire sur un autre type
        cand = [k for k in kinds if cnt[k] > (1 if (k == 'ram' and must_ram) else 0)]
        cnt[rng.choice(cand)] -= 1
    seq = [k for k in kinds for _ in range(cnt[k])]
    rng.shuffle(seq)
    for i, k in zip(carriers, seq):
        army.units[i].engine = k
    return len(seq)


def ENGINE_MAX_SUM(kinds):
    return sum(ENGINE_MAX[k] for k in kinds)


def ensure_general(entries, udict):
    """Le général (1re unité) n'est jamais une unité de siège : la première unité hors siège passe en tête."""
    def is_siege(e):
        u = udict.get(e.type.lower())
        return bool(u and u.category == 'siege')
    if entries and is_siege(entries[0]):
        for i, e in enumerate(entries):
            if not is_siege(e):
                entries.insert(0, entries.pop(i))
                break
    return entries






def siege_def(sc):
    """(libellé, mot-clé, niveau, culture, package, rayon en m, testé, faction type de la culture)."""
    st = next((x for x in SETTLEMENTS if x[0] == sc.siege_type), SETTLEMENTS[9])
    cult = next((c for c in CULTURES if c[0] == getattr(sc, 'siege_culture', 'Humans')), CULTURES[0])
    pk = siege_package(st[0], cult[0]) or ('', 300, 'inconnu')
    return (st[0], st[2], st[1], cult[1], pk[0], pk[1], (st[0], cult[0]) in SIEGE_TESTED, CULTURE_FACTION.get(cult[0], 'spain'))


def siege_fort_values(sc):
    """walls / towers / gates / gate_defences selon le niveau de défense choisi (1 à 3)."""
    mx = next((x[3] for x in SETTLEMENTS if x[0] == sc.siege_type), 1)
    d = max(1, min(max(mx, 1), int(getattr(sc, 'siege_dlevel', 1) or 1)))
    return {1: (0, 0, 0, 0), 2: (0, 1, 1, 0), 3: (0, 2, 1, 1)}[d]


def siege_roles(sc):
    """(équipe défenseuse, équipe attaquante), ou None s'il n'y a pas exactement deux équipes de rôles différents."""
    teams = sorted({a.team for a in sc.armies})
    if len(teams) != 2:
        return None
    r = [sc.role_of(t) for t in teams]
    if r[0] == r[1]:
        return None
    return teams[r.index('defending')], teams[r.index('attacking')]


def siege_radius(sc):
    return siege_def(sc)[5]


def siege_def_sides(sc):
    return DEF_SIDES.get(sc.siege_type, 4)


def siege_def_rect(sc):
    """Zone rectangulaire décalée des défenseurs (x min, x max, y min, y max), ou None."""
    if sc.siege_type == 'Fort':          # nord inchangé (±68), sud / est / ouest élargis de 10 m ; Humans : repère tourné de 90° (assaillants à l'est)
        return (-78.0, 68.0, -78.0, 78.0) if getattr(sc, 'siege_culture', '') == 'Humans' else (-78.0, 78.0, -78.0, 68.0)
    rc = DEF_RECT_CULTURE.get((sc.siege_type, getattr(sc, 'siege_culture', '')))
    if rc:
        return rc
    if sc.siege_type == 'Fort':          # Sud / Est / Ouest +10 m, Nord inchangé ; Fort Humans : disposition pivotée (assaillants à l'est)
        return (-78.0, 68.0, -78.0, 78.0) if getattr(sc, 'siege_culture', '') == 'Humans' else (-78.0, 78.0, -78.0, 68.0)
    return DEF_RECT.get(sc.siege_type)


def siege_def_half(sc):
    """Apothème (m) du polygone des défenseurs : taille de la colonie, bornée pour laisser de la place aux assaillants dans la carte
    (rectangle décalé : plus petite demi-dimension)."""
    r = siege_def_rect(sc)
    if r:
        return min((r[1] - r[0]) / 2.0, (r[3] - r[2]) / 2.0)
    n = siege_def_sides(sc)
    z = float(DEF_ZONE_CULTURE.get((sc.siege_type, getattr(sc, 'siege_culture', '')), DEF_ZONE.get(sc.siege_type, siege_radius(sc))))
    cap = DEF_HALF_MAX if n == 4 else DEF_CIRC_MAX * math.cos(math.pi / n)      # carré : les zones des assaillants sont des carrés (plus de cercle)
    return min(z, cap)


def siege_def_center(sc):
    r = siege_def_rect(sc)
    return ((r[0] + r[1]) / 2.0, (r[2] + r[3]) / 2.0) if r else (0.0, 0.0)




def siege_def_extent(sc):
    """Plus grande coordonnée (en valeur absolue) du polygone des défenseurs : les zones des assaillants sont des carrés / crochets."""
    return max(max(abs(x), abs(y)) for x, y in siege_def_polygon(sc))


def siege_def_polygon(sc):
    r = siege_def_rect(sc)
    if r:
        return [(r[0], r[3]), (r[1], r[3]), (r[1], r[2]), (r[0], r[2])]
    n = siege_def_sides(sc)
    rc = siege_def_half(sc) / math.cos(math.pi / n)
    off = 180.0 / n if n != 4 else 45.0
    return [(rc * math.sin(math.radians(off + 360.0 * k / n)), rc * math.cos(math.radians(off + 360.0 * k / n))) for k in range(n)]


def siege_min_distance(sc):
    """Distance minimum (centre -> bord proche des assaillants) : jamais dans le polygone des défenseurs."""
    base = int(math.ceil(siege_def_extent(sc))) + 20
    return base


def siege_max_distance(sc):
    """Plus grande distance (centre -> bord proche des assaillants) proposée : au plus SIEGE_DIST_SPAN m au-delà du minimum
    (une IA trop éloignée n'utilise pas tous ses engins), et il reste au moins 80 m de profondeur dans la carte."""
    return max(siege_min_distance(sc), int(SIEGE_MAP_LIMIT) - 80)       # toutes les distances jusqu'à la limite de la carte


def siege_dist_values(sc):
    """Valeurs proposées pour « Distance siège » : la fourchette utile par pas de 10 m."""
    mn, mx = siege_min_distance(sc), siege_max_distance(sc)
    vals = [mn] + [v for v in range(int(math.ceil(mn / 10.0)) * 10, mx + 1, 10) if v > mn]
    return vals


def siege_attack_distance(sc):
    """Distance entre le centre de la colonie et le bord proche de la zone des assaillants (0 = automatique : le maximum,
    ajusté ensuite selon les armées par siege_attack_slots)."""
    mn = siege_min_distance(sc)
    if sc.siege_dist:
        return max(mn, min(int(sc.siege_dist), siege_max_distance(sc)))
    return max(mn, siege_max_distance(sc))


def ring_point(c, s, o=0.0):
    """Point d'un anneau carré de demi-côté c (crochets des assaillants) : s = abscisse curviligne depuis le milieu du côté sud, vers
    l'ouest ; o = décalage perpendiculaire vers l'extérieur. Périmètre 8c, angles droits uniquement."""
    P = 8.0 * c
    s = s % P
    if s <= c:
        return (-s, -(c + o))
    if s <= 3 * c:
        return (-(c + o), -c + (s - c))
    if s <= 5 * c:
        return (-c + (s - 3 * c), c + o)
    if s <= 7 * c:
        return (c + o, c - (s - 5 * c))
    return (c - (s - 7 * c), -(c + o))


def ring_slice_polygon(c, depth, s0, s1):
    """Morceau [s0, s1] (abscisses sur la ligne médiane de demi-côté c) de la bande carrée d'épaisseur `depth` : sommets aux angles
    droits (extérieur, puis intérieur en sens inverse). Le crochet « [ » d'une armée seule = moitié de l'anneau."""
    h = depth / 2.0
    co, ci = c + h, c - h
    corners = [(-1, -1), (-1, 1), (1, 1), (1, -1)]
    mlo = int(math.floor((s0 - c) / (2.0 * c))) - 1
    mhi = int(math.ceil((s1 - c) / (2.0 * c))) + 1
    ks = [(c + 2.0 * c * m, m) for m in range(mlo, mhi + 1) if s0 + 1e-6 < c + 2.0 * c * m < s1 - 1e-6]
    outer = [ring_point(c, s0, h)] + [(corners[m % 4][0] * co, corners[m % 4][1] * co) for _s, m in ks] + [ring_point(c, s1, h)]
    inner = [ring_point(c, s1, -h)] + [(corners[m % 4][0] * ci, corners[m % 4][1] * ci) for _s, m in reversed(ks)] + [ring_point(c, s0, -h)]
    return [(round(x, 2), round(y, 2)) for x, y in outer + inner]


def siege_attack_slots(sc, udict, idxs):
    """Zones des assaillants, toujours à angles droits : crochet « [ » (moitié d'un anneau carré autour des défenseurs) pour une seule
    armée ; plusieurs armées -> anneau carré complet divisé entre les factions ; « même spawn » : une seule zone partagée.
    Distance automatique : la plus grande possible sans sortir de la carte.
    Retourne (tranches (centre, longueur) en fraction du périmètre, même spawn, r_in, besoins, placements, 0, 0, r_front)."""
    n = len(idxs)
    same = bool(getattr(sc, 'siege_same', False)) and n > 1
    # fractions du périmètre : une armée -> 1/2 anneau centré au sud ; plusieurs -> 1/n chacune (la 1re centrée au sud)
    slices = [(0.0, 0.5)] if n == 1 else [(j / float(n), 1.0 / n) for j in range(n)]

    def build(r_in):
        r_front = r_in + 4.0
        room = (SIEGE_MAP_LIMIT - 5.0) - r_front - 12.0         # profondeur disponible avant le bord de la carte
        locs, needs, fits = {}, {}, True
        for j, i in enumerate(idxs):
            frac = slices[j][1]          # « même spawn » : zone commune, mais chaque armée garde sa part de l'anneau (pas de superposition)
            arc_len = 8.0 * (r_front + 25.0) * frac - 20.0
            for step in (ROW_STEP, 26.0, 20.0, 16.0):
                locs[i], nd = local_layout(sc.armies[i], udict, max(120.0, arc_len), step)
                if nd <= room:
                    break
            else:
                fits = fits and nd <= room
            needs[i] = max(80.0, float(nd))
        fits = fits and (SIEGE_MAP_LIMIT - 5.0 - r_in) >= 84.0          # la bande garde au moins 80 m de profondeur avant le bord de la carte
        return r_front, locs, needs, fits

    mn = float(siege_min_distance(sc))
    if sc.siege_dist:
        r_in = float(siege_attack_distance(sc))
        while True:          # distance choisie : ramenée au plus près si la zone sortirait de la carte
            r_front, locs, needs, fits = build(r_in)
            if fits or r_in <= mn:
                break
            r_in -= 5.0
        r_in = max(mn, r_in)
    else:
        r_in = float(max(siege_max_distance(sc), int(SIEGE_MAP_LIMIT) - 80))      # automatique : le plus loin possible tant que l'armée tient dans la bande
        while True:
            r_front, locs, needs, fits = build(r_in)
            if fits or r_in <= mn:
                break
            r_in -= 5.0
        r_in = max(mn, r_in)
    return slices, same, r_in, needs, locs, 0.0, 0.0, r_front


def siege_gate_north(sc):
    """Le jeu pose le Motte and Bailey de culture Humans porte au nord (les autres colonies : porte au sud)."""
    return getattr(sc, 'siege_type', '') == 'Motte and Bailey' and getattr(sc, 'siege_culture', '') == 'Humans'


def compute_siege_layout(sc, udict):
    layout, warnings = _compute_siege_layout(sc, udict)
    if layout and getattr(sc, 'siege_type', '') == 'Fort' and getattr(sc, 'siege_culture', '') == 'Humans':
        for L in layout.values():          # Fort Humans (SE_Fort_A) : portes sud et est, assaillants à l'est (rotation anti-horaire de 90°)
            L['zone'] = [(-y, x) for x, y in L['zone']]
            L['units'] = [(-y, x, norm_angle(round(o - 90.0)), w) for x, y, o, w in L['units']]
            if L.get('extra'):
                L['extra'] = [([(-y, x) for x, y in z], m) for z, m in L['extra']]
        return layout, warnings
    if layout and siege_gate_north(sc):          # demi-tour : attaquants au nord, devant la porte
        for L in layout.values():
            L['zone'] = [(-x, -y) for x, y in L['zone']]
            L['units'] = [(-x, -y, norm_angle(round(o + 180.0)), w) for x, y, o, w in L['units']]
            for k in ('extra',):
                if L.get(k):
                    L[k] = [([(-x, -y) for x, y in z], m) for z, m in L[k]]
    return layout, warnings


def _compute_siege_layout(sc, udict):
    """Siège : la colonie est posée par le jeu au centre (0, 0).
    Défenseurs : UNE zone commune carrée, de la taille de la colonie (toutes les armées défenseuses la partagent).
    Assaillants : une armée -> demi-anneau autour de la colonie ; plusieurs -> anneau complet divisé entre les factions
    (une zone en arc par armée) ; « même spawn » : une seule zone en demi-anneau. Aucun point de zone au-delà de ±SIEGE_MAP_LIMIT."""
    warnings, layout = [], {}
    roles = siege_roles(sc)
    if not roles or not sc.armies:
        return layout, ["Siège : il faut exactement deux équipes, l'une « Attaquant », l'autre « Défenseur »."]
    R = siege_radius(sc)
    BASE = 180.0
    for team in roles:
        is_def = team == roles[0]
        idxs = [i for i, a in enumerate(sc.armies) if a.team == team]
        n = len(idxs)
        if not n:
            continue
        if is_def:
            Z = float(siege_def_half(sc))
            H = 0.45 * Z                       # demi-côté de la cour où sont placées les unités
            cols = min(n, 3)
            rows_n = int(math.ceil(n / float(cols)))
            slot_w = 2.0 * H / cols
            locs, need = {}, 80.0                  # profondeur / distance de l'éditeur : sans effet sur les défenseurs
            for i in idxs:
                locs[i], nd = local_layout(sc.armies[i], udict, max(slot_w, 120.0))
                need = max(need, nd)
            if need * rows_n > 2.0 * H * 1.05:
                warnings.append("Défenseurs : zone de %d m de profondeur, plus grande que la cour de la colonie (≈ %d m) : certaines unités "
                                "seront sur les remparts ou dehors (peu grave)." % (need * rows_n, 2 * H))
            h = BASE
            fx, fy = math.sin(math.radians(h)), math.cos(math.radians(h))
            rx, ry = math.cos(math.radians(h)), -math.sin(math.radians(h))
            common = siege_def_polygon(sc)
            cx0, cy0 = siege_def_center(sc)
            for j, i in enumerate(idxs):
                r_, c_ = divmod(j, cols)
                in_row = min(cols, n - r_ * cols)
                off = (c_ - (in_row - 1) / 2.0) * slot_w
                voff = (r_ - (rows_n - 1) / 2.0) * need
                ccx, ccy = rx * off + fx * voff + cx0, ry * off + fy * voff + cy0
                hd = need / 2.0
                front_x, front_y = ccx + fx * hd, ccy + fy * hd
                units = []
                for idx in range(len(sc.armies[i].units)):
                    u, v, w = locs[i][idx]
                    units.append((front_x + rx * u - fx * v, front_y + ry * u - fy * v, norm_angle(round(h)), w))
                layout[i] = {'zone': common, 'units': units, 'team': team}
            continue
        slices, same, r_in, needs, locs, _st, _tt, r_front = siege_attack_slots(sc, udict, idxs)
        depth = max(max(needs.values()) + (r_front - r_in), SIEGE_MAP_LIMIT - 5.0 - r_in)      # profondeur toujours maximale (jusqu'à la limite de carte)
        c = r_in + depth / 2.0                      # demi-côté de la ligne médiane de la bande
        P = 8.0 * c
        shared = None
        if same or n == 1:
            shared = ring_slice_polygon(c, depth, -P / 4.0, P / 4.0) if n == 1 else ring_slice_polygon(c, depth, -P / 2.0 + 1.0, P / 2.0 - 1.0)
        for j, i in enumerate(idxs):
            fc, fl = slices[j]
            sc_, sl = fc * P, fl * P
            zone = shared if shared else ring_slice_polygon(c, depth, sc_ - sl / 2.0 + 0.5, sc_ + sl / 2.0 - 0.5)
            if n == 1:
                sc_, sl = 0.0, P / 2.0
            units = []
            for idx in range(len(sc.armies[i].units)):
                u, v, w = locs[i][idx]
                o = (v + (r_front - r_in)) - depth / 2.0                # décalage perpendiculaire par rapport à la ligne médiane
                x, y = ring_point(c, sc_ - u, o)
                ang = math.degrees(math.atan2(x, y))
                units.append((x, y, norm_angle(round(ang + 180.0)), w))
            layout[i] = {'zone': zone, 'units': units, 'team': team}
    return layout, warnings


def optimize_zones(sc, udict):
    """Choisit largeur par armée, profondeur (et au besoin distance entre camps) : zones compactes qui contiennent toutes les unités."""
    roles = siege_roles(sc) if getattr(sc, 'siege', False) else None
    if roles:                    # siège : zones en arc ; seule la profondeur des assaillants est ajustée
        idxs = [i for i, a in enumerate(sc.armies) if a.team == roles[1]]
        if idxs:
            needs = siege_attack_slots(sc, udict, idxs)[3]
            sc.depth = int(min(500, max(80, math.ceil(max(needs.values()) / 10.0) * 10)))
        return
    best = None
    for w in range(250, 1501, 50):
        sc.army_width, sc.depth = w, 1
        lay, _w = compute_layout(sc, udict)
        need = 0.0
        for L in lay.values():
            if roles and L.get('team') != roles[1]:
                continue                      # siège : seuls les assaillants dépendent de la largeur
            for z in [L['zone']] + [z2 for z2, _m in L.get('extra', [])]:
                need = max(need, math.hypot(z[0][0] - z[1][0], z[0][1] - z[1][1]) - 40.0)
        if need <= 130:
            best = (w, need)
            break
        if best is None or need < best[1] - 1:
            best = (w, need)
    if best is None:
        return
    sc.army_width = best[0]
    sc.depth = int(min(500, max(80, math.ceil(best[1] / 10.0) * 10)))
    for _ in range(12):
        _l, wr = compute_layout(sc, udict)
        if any('dépassent' in x for x in wr) and not roles and sc.gap > 40:
            sc.gap = max(40, sc.gap - 40)
        else:
            break


def siege_engine_plan(army, udict, *_ignored):
    """Engins portés : ({indice d'unité: type}, {type: nombre}) d'après UnitEntry.engine (infanterie hors général seulement)."""
    plan, got = {}, {'ram': 0, 'ladder': 0, 'tower': 0}
    ok = set(engine_carriers(army, udict))
    for i, e in enumerate(army.units):
        if e.engine in got and i in ok:
            plan[i] = e.engine
            got[e.engine] += 1
    return plan, got


# --------------------------------------------------------------------------------------
#  VALIDATION ET GÉNÉRATION
# --------------------------------------------------------------------------------------

def validate(sc, udict, avail=None, with_aux=True, weathers=None):
    errors, warnings = [], []
    if not safe_name(sc.name):
        errors.append("Le nom du scénario est vide ou ne contient aucun caractère valide.")
    if len(sc.armies) < 2:
        errors.append("Il faut au moins deux armées.")
    if len(sc.armies) > MAX_ARMIES:
        errors.append("Plus de %d armées : le jeu n'en gère pas davantage." % MAX_ARMIES)
    if not (0 <= sc.map_x < CAMPAIGN_SIZE[0] and 0 <= sc.map_y < CAMPAIGN_SIZE[1]):
        errors.append("Coordonnées %d / %d hors de la carte de campagne du mod (X 0 à %d, Y 0 à %d) : le menu du jeu plante."
                      % (sc.map_x, sc.map_y, CAMPAIGN_SIZE[0] - 1, CAMPAIGN_SIZE[1] - 1))
    if weathers and sc.weather not in weathers:
        errors.append("Météo « %s » inconnue du mod (absente de weather_db.xml) : le jeu risque de se bloquer au menu. "
                      "Choisissez une météo de la liste." % sc.weather)
    seen_f = set()
    for a in sc.armies:
        if a.faction in seen_f:
            errors.append("Faction « %s » présente plusieurs fois : interdit (une seule armée par faction)." % a.faction)
        seen_f.add(a.faction)
    for a in sc.armies:
        if not a.units:
            errors.append("L'armée « %s » n'a aucune unité." % a.faction)
        if len(a.units) > MAX_UNITS:
            errors.append("Armée « %s » : %d unités, le maximum est %d." % (a.faction, len(a.units), MAX_UNITS))
        allowed = avail.allowed(a.faction, True) if avail else None
        base_allowed = avail.allowed(a.faction, False) if avail else None
        outside, auxiliary = [], []
        for e in a.units:
            u = udict.get(e.type.lower())
            if u is None:
                errors.append("Unité inconnue dans l'armée « %s » : %s" % (a.faction, e.type))
                continue
            if allowed is not None and e.type.lower() not in allowed:
                if u.name not in outside:
                    outside.append(u.name)
            elif base_allowed is not None and not getattr(sc, 'aux', False) and e.type.lower() not in base_allowed:
                if u.name not in auxiliary:
                    auxiliary.append(u.name)
            if e.armour > u.max_armour:
                warnings.append("« %s » (%s) : armure %d impossible (maximum %d)." % (u.name, a.faction, e.armour, u.max_armour))
            if e.exp > (MAX_EXP if getattr(sc, 'solo', False) else 3) or e.weapon > MAX_WEAPON:
                warnings.append("« %s » (%s) : expérience ou arme hors limites." % (u.name, a.faction))
        if outside:
            warnings.append("Armée « %s » : unités absentes de la liste de la faction (risque de crash ou d'unité invisible) : %s."
                            % (a.faction, ', '.join(outside)))
        if auxiliary:
            warnings.append("Armée « %s » : unités auxiliaires (cochez « Unités auxiliaires » si le mode escarmouche les propose) : %s."
                            % (a.faction, ', '.join(auxiliary)))
    for tm in sorted({a.team for a in sc.armies}):
        tot = team_gold(sc, udict, tm)
        if tot > TEAM_GOLD_MAX:
            errors.append("Équipe %d : %d or au total, le maximum est %d par équipe." % (tm, tot, TEAM_GOLD_MAX))
    if getattr(sc, 'siege', False):
        roles = siege_roles(sc)
        if not roles:
            errors.append("Siège : il faut exactement deux équipes, l'une « Attaquant » et l'autre « Défenseur ».")
        elif not siege_available(sc.siege_type, sc.siege_culture):
            errors.append("Siège : « %s » n'a pas de défenses : choisissez un autre settlement." % sc.siege_type)
        elif {a.team for a in sc.armies} != {1, 2}:
            errors.append("Siège : les deux équipes doivent porter les numéros 1 et 2.")
        else:
            for a in sc.armies:
                if a.team == roles[1]:
                    for pb in engine_rule_problems(sc.siege_type, a, udict):
                        if pb == 'no_engine':
                            warnings.append("Siège : l'armée attaquante « %s » n'a aucun engin de siège (bélier, échelle ou tour)." % a.faction)
                        else:
                            warnings.append("Siège %s : l'armée attaquante « %s » doit avoir un bélier." % (sc.siege_type, a.faction))
    if not any(a.human for a in sc.armies):
        warnings.append("Aucune armée « Joueur » : personne ne pourra rejoindre la partie.")
    teams = {a.team for a in sc.armies}
    if len(teams) < 2:
        warnings.append("Toutes les armées sont dans la même équipe : il n'y aura pas d'ennemi.")
    w = team_warning(sc)
    if w:
        warnings.append(w)
    return errors, warnings


def team_warning(sc):
    if len({a.team for a in sc.armies}) >= MAX_ARMIES - 1:        # 7 ou 8 équipes
        return "Attention, les dernières armées risquent d'être impossibles à sélectionner"
    return ''


def team_gold(sc, udict, team):
    """Or total d'une équipe (somme de la valeur de ses armées)."""
    return sum(army_value(a.units, udict) for a in sc.armies if a.team == team)


def total_soldiers(sc):
    return sum(e.ls for a in sc.armies for e in a.units)


def limit_warning(sc):
    """Texte rouge de l'interface quand les limites du jeu (4 équipes / 4000 soldats) sont dépassées ; n'empêche rien."""
    if len({a.team for a in sc.armies}) > LIMIT_TEAMS or total_soldiers(sc) > LIMIT_SOLDIERS:
        return "attention limite de %d soldats / %d équipes dépassée" % (LIMIT_SOLDIERS, LIMIT_TEAMS)
    return ''


SCRIPT_HEADER = '; Custom battle script generated by Tzeentch Scenario Editor (Python)'


def faction_groups(sc):
    """(factions dans l'ordre d'apparition, {faction: [indices des armées]}, {indice d'armée: rang dans sa faction}).
    Une faction peut avoir plusieurs armées : elles sont écrites ensemble sous un seul bloc « faction »."""
    order, groups, rank = [], {}, {}
    for i, a in enumerate(sc.armies):
        if a.faction not in groups:
            groups[a.faction] = []
            order.append(a.faction)
        rank[i] = len(groups[a.faction])
        groups[a.faction].append(i)
    return order, groups, rank


def _siege_block(sc, owner):
    name, kind, level, culture, path = siege_def(sc)[:5]
    creator = siege_def(sc)[7]
    wl, tw, gt, gd = siege_fort_values(sc)
    return [('settlement %s' % kind).strip(), '{', '\tlevel %s' % level, '\ttile %d %d' % (sc.map_x, sc.map_y), '',
            '\tyear_founded 1', '\tfortification 0 %s, walls %d towers %d gates %d gate_defences %d' % (culture, wl, tw, gt, gd),
            '\tpopulation 1000', '\tplan_set default_set', '\tfaction_creator %s' % creator] + \
        (['package_path %s' % path] if siege_has_package(sc) else []) + ['}']


def _character_line(sc, a, rank):
    gname = ascii_only(a.general) or ('General %s%s' % (a.faction.title(), (' %d' % (rank + 1)) if rank else ''))
    gender = a.gender if a.gender in ('male', 'female') else 'male'
    age = max(16, min(127, int(getattr(a, 'age', 30) or 30)))
    return 'character\t%s, general, %s, age %d, x %d, y %d' % (gname, gender, age, sc.map_x, sc.map_y)


def _head_lines(sc, A):
    A(SCRIPT_HEADER)
    A('; auxiliary %s' % ('on' if getattr(sc, 'aux', False) else 'off'))
    A('')
    A('battle\t\t%s\t\t%s' % (safe_name(sc.name), 'singleplayer\t\tnot_multiplayer' if getattr(sc, 'solo', False) else 'multiplayer\t\tnot_singleplayer'))
    order, groups, _r = faction_groups(sc)
    A('playable')
    solo = getattr(sc, 'solo', False)           # solo : toutes les armées peuvent être choisies par le joueur
    for f in order:
        if solo or any(sc.armies[i].human for i in groups[f]):
            A('\t' + f)
    A('end')
    A('nonplayable')
    for f in order:
        if not solo and not any(sc.armies[i].human for i in groups[f]):
            A('\t' + f)
    A('end')
    A('')
    A('')
    A('start_date\t%d %s' % (sc.year, sc.season))
    A('end_date\t%d %s' % (sc.year, sc.season))
    A('')
    A('')


def _team_factions(sc, t):
    out = []
    for a in sc.armies:
        if a.team == t and a.faction not in out:
            out.append(a.faction)
    return out


def generate_siege_battle(sc, udict, layout):
    roles = siege_roles(sc)
    def_team, att_team = roles
    owner = next(a for a in sc.armies if a.team == def_team).faction
    fort = sc.siege_type == 'Fort'        # Fort : élément « fort » de la section bataille (ni settlement ni sieging)
    nl = []
    A = nl.append
    _head_lines(sc, A)
    bar = ';' * 150
    A(bar)
    A('; >>>> start of factions section <<<<')
    A('')
    plans = {}
    order, groups, rank = faction_groups(sc)
    for f in order:
        A('faction\t%s' % f)
        if f == owner and not fort:
            for ln in _siege_block(sc, owner):
                A(ln)
        for i in groups[f]:
            a = sc.armies[i]
            A(_character_line(sc, a, rank[i]))
            A('army')
            for e in a.units:
                A('unit\t\t%s\t\t\t\tsoldiers %d exp %d armour %d weapon_lvl %d' % (e.type, e.soldiers, e.exp, e.armour, e.weapon))
            if a.team == att_team:
                plans[i], got = siege_engine_plan(a, udict)
                A('sieging\t')
                A('')
                for k in ('ram', 'ladder', 'tower'):
                    if got[k]:
                        A('siege_equipment \t%s %d' % (k, got[k]))
            A('')
    A(bar)
    A('; >>>> start of battle section <<<<')
    A('')
    A('battle\t%d, %d' % (sc.map_x, sc.map_y))
    A('battle_time\t%.2f\t%.2f' % (sc.hour, sc.param2))
    A('weather\t%s' % sc.weather)
    if fort:       # sur UNE ligne, juste après weather (relevé system.log)
        A('fort\towner %s creator %s' % (owner, CULTURE_FACTION.get(getattr(sc, 'siege_culture', 'Humans'), owner)))
    A('')
    A('home_faction\t%s' % owner)
    for t, role in ((def_team, 'defending'), (att_team, 'attacking')):
        A('alliance\tcan_deploy\tcan_view\t%s, %s' % (', '.join(_team_factions(sc, t)), role))
    A('')
    for i, a in enumerate(sc.armies):
        L = layout[i]
        A('army\t%s, %d, no_withdraw, supporting_armies 0' % (a.faction, rank[i]))
        A('')
        extra = L.get('extra', [])
        taken = {k for _z, m in extra for k in m}
        for zone, members in [(L['zone'], [k for k in range(len(L['units'])) if k not in taken])] + list(extra):
            if not zone or not members:
                continue
            for x, y in zone:
                A('deployment_area_point\t%.3f, %.3f' % (x, y))
            A('')
            for idx in members:
                x, y, o, w = L['units'][idx]
                eng = plans.get(i, {}).get(idx)
                A('unit\t\t\t%d, %.3f, %.3f, %d, formation_type square, formation_width %.3f%s'
                  % (idx, x, y, o, 6.0 if eng else w, (', attach_engine ' + eng) if eng else ''))
            A('')
        A('')
    A(bar)
    A('; >>>> start of objectives scripting section <<<<')
    A('')
    A('objectives')
    A('')
    A('alliance 0')
    A('condition destroy_or_rout_enemy')
    A('')
    A('alliance 1')
    A('condition destroy_or_rout_enemy')
    if True:
        A('condition capture_major_settlement ')
    A('')
    return '\r\n'.join(nl) + '\r\n'


def generate_descr_battle(sc, udict, layout=None):
    if layout is None:
        layout, _ = compute_layout(sc, udict)
    if getattr(sc, 'siege', False):
        if not layout:
            return '; siège impossible : il faut deux équipes (un attaquant, un défenseur)\r\n'
        return generate_siege_battle(sc, udict, layout)
    nl = []
    A = nl.append
    _head_lines(sc, A)
    bar = ';' * 150
    A(bar)
    A('; >>>> start of factions section <<<<')
    A('')
    order, groups, rank = faction_groups(sc)
    for f in order:
        A('faction\t%s' % f)
        for i in groups[f]:
            a = sc.armies[i]
            A(_character_line(sc, a, rank[i]))
            A('army')
            for e in a.units:
                A('unit\t\t%s\t\t\t\tsoldiers %d exp %d armour %d weapon_lvl %d'
                  % (e.type, e.soldiers, e.exp, e.armour, e.weapon))
            A('')
    A(bar)
    A('; >>>> start of battle section <<<<')
    A('')
    A('battle\t%d, %d' % (sc.map_x, sc.map_y))
    A('battle_time\t%.2f\t%.2f' % (sc.hour, sc.param2))
    A('weather\t%s' % sc.weather)
    A('')
    teams = sorted({a.team for a in sc.armies})
    home = sc.home_faction
    if not home or home not in [a.faction for a in sc.armies]:
        defenders = [a for a in sc.armies if sc.role_of(a.team) == 'defending']
        home = (defenders or sc.armies)[0].faction
    A('home_faction\t%s' % home)
    for t in teams:
        A('alliance\tcan_deploy\tcan_view\t%s, %s' % (', '.join(_team_factions(sc, t)), sc.role_of(t)))
    A('')
    for i, a in enumerate(sc.armies):
        L = layout[i]
        A('army\t%s, %d, no_withdraw, supporting_armies 0' % (a.faction, rank[i]))
        A('')
        for x, y in L['zone']:
            A('deployment_area_point\t%.3f, %.3f' % (x, y))
        A('')
        for idx, (x, y, o, w) in enumerate(L['units']):
            A('unit\t\t\t%d, %.3f, %.3f, %d, formation_type square, formation_width %.3f' % (idx, x, y, o, w))
        A('')
        A('')
    A(bar)
    A('; >>>> start of objectives scripting section <<<<')
    A('')
    A('objectives')
    A('')
    for k, _ in enumerate(teams):
        A('alliance %d' % k)
        A('condition destroy_or_rout_enemy')
        A('')
    return '\r\n'.join(nl) + '\r\n'


def write_descr_battle(sc, udict, out_root, text=None, template=None, copy_wfc=True, snapshot=None, loading=None):
    """Écrit <out_root>/<nom>/descr_battle.txt (out_root = dossier de l'éditeur).
    template = chemin d'un fichier map.wfc à copier."""
    if text is None:
        text = generate_descr_battle(sc, udict)
    folder = os.path.join(out_root, folder_name(sc.name) or safe_name(sc.name))
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, 'descr_battle.txt')
    if os.path.exists(path):
        shutil.copyfile(path, path + '.bak_' + time.strftime('%Y%m%d_%H%M%S'))
    with open(path, 'w', encoding='latin-1', newline='') as fh:
        fh.write(text)
    copied = []
    if snapshot and os.path.isfile(snapshot):
        shutil.copyfile(snapshot, os.path.join(folder, 'snapshot_battle.tga'))
        copied.append('snapshot_battle.tga')
    if loading and os.path.isfile(loading):
        shutil.copyfile(loading, os.path.join(folder, 'loading_screen.tga'))
        copied.append('loading_screen.tga')
    if template and copy_wfc and os.path.isfile(template):
        shutil.copyfile(template, os.path.join(folder, 'map.wfc'))
        copied.append('map.wfc')
    return path, copied


# --------------------------------------------------------------------------------------
#  DESCRIPTIONS DES SCÉNARIOS (battle_descriptions.txt)
# --------------------------------------------------------------------------------------
DESC_FILE = 'battle_descriptions.txt'
DESC_HEADER = '\u00ac Generated by Tzeentch v9.9.9'
DESC_MARK = '\u00ac scenario:'
DESC_WIDTH = 33          # le jeu coupe les phrases au-delà de 33 caractères


def read_bytes(path):
    with open(path, 'rb') as fh:
        return fh.read()


def desc_decode(data):
    """Lit battle_descriptions.txt quel que soit son encodage (UTF-16 avec BOM comme le fichier du jeu, UTF-8, ANSI)."""
    if data[:2] == b'\xff\xfe':
        return data[2:].decode('utf-16-le', 'replace')
    if data[:2] == b'\xfe\xff':
        return data[2:].decode('utf-16-be', 'replace')
    if data[:3] == b'\xef\xbb\xbf':
        return data[3:].decode('utf-8', 'replace')
    if len(data) > 3 and (data[1:2] == b'\x00' or data[0:1] == b'\x00') and data.count(b'\x00') > len(data) // 4:
        return data.decode('utf-16-le' if data[1:2] == b'\x00' else 'utf-16-be', 'replace')       # UTF-16 sans BOM
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        return data.decode('cp1252', 'replace')


def desc_encode(text):
    """Texte -> octets du fichier : UTF-16 little endian avec BOM (encodage du battle_descriptions.txt du jeu)."""
    return b'\xff\xfe' + text.replace('\r\n', '\n').replace('\n', '\r\n').encode('utf-16-le')


def desc_wrap(text, width=DESC_WIDTH):
    lines, cur = [], ''
    for w in text.split():
        w = w[:width]
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + ' ' + w) if cur else w
    if cur:
        lines.append(cur)
    return lines


def desc_key(folder):
    return re.sub(r'[^A-Z0-9_]', '', folder.upper().replace(' ', '_'))


def desc_lines(sc, factions, udict, siege, extra=''):
    timer = 'Unlimited' if not sc.param2 else ('%g' % sc.param2)
    nh = sum(1 for a in sc.armies if a.human)
    lines = ['Players: %d Human / %d AI' % (nh, len(sc.armies) - nh)]
    if siege:
        lines.append('Settlement: %s' % getattr(sc, 'siege_type', 'Castle'))
    lines += ['Timer: %s' % timer,
             'Auxiliary units: %s' % ('On' if getattr(sc, 'aux', False) else 'Off'),
             'Victory Conditions: %s' % ('Annihilation or Capture' if siege else 'Annihilation'),
             'Weather: %s' % sc.weather, 'Time: %s (%gh)' % (time_name(sc.hour), sc.hour)]
    if siege:
        lines.append('Siege battle')
    lines.append('')
    for t in sorted({a.team for a in sc.armies}):
        role = ''
        r = sc.team_roles.get(str(t))
        if siege and r:
            role = ' - ' + ('Attack' if r == 'attacking' else 'Defence')
        lines.append('Team %d%s' % (t, role))
        for a in [a for a in sc.armies if a.team == t]:
            nm = factions.get(a.faction, a.faction)
            nm = nm.get('name', a.faction) if isinstance(nm, dict) else str(nm)
            lines.append('%s (%s)' % (nm, 'Player' if a.human else 'AI'))
            lines.append('%d gold' % army_value(a.units, udict))
        lines.append('')
    if extra and extra.strip():
        for para in extra.strip().split('\n'):
            lines.append(para.strip())
    out = []
    for ln in lines:
        out.extend(desc_wrap(ln) if ln.strip() else [''])
    while out and not out[-1]:
        out.pop()
    return out


def desc_entry(folder, title, lines):
    descr = '\\n'.join(lines) + ' .'
    return [DESC_MARK + folder, '{%s_TITLE}%s' % (desc_key(folder), title), '{%s_DESCR}%s' % (desc_key(folder), descr)]


def desc_block(folder, descr_text, factions, udict):
    """Bloc du fichier de descriptions pour un dossier de scénario existant (relu depuis son descr_battle.txt)."""
    try:
        sc = parse_descr_battle(descr_text, factions)
        lines = desc_lines(sc, factions, udict, bool(re.search(r'^sieging', descr_text, re.M | re.I)))
    except Exception:       # noqa : description minimale si le fichier n'est pas lisible
        lines = ['Custom battle']
    return desc_entry(folder, folder.replace('_', ' '), lines)


def desc_block_sc(folder, sc, factions, udict):
    """Bloc du fichier de descriptions pour le scénario qui vient d'être créé (texte de l'utilisateur compris)."""
    return desc_entry(folder, sc.name or folder.replace('_', ' '), desc_lines(sc, factions, udict, bool(sc.siege), sc.description))


def desc_split(text):
    """(lignes hors blocs, {dossier: [lignes]}) : un bloc commence par « ¬ scenario:<dossier> »."""
    head, blocks, cur = [], {}, None
    for ln in text.replace('\r\n', '\n').split('\n'):
        if ln.startswith(DESC_MARK):
            cur = ln[len(DESC_MARK):].strip()
            blocks[cur] = [ln]
        elif cur is not None and ln.startswith('{'):
            blocks[cur].append(ln)
        else:
            cur = None
            head.append(ln)
    return head, blocks


def desc_join(head, blocks):
    """Texte final. Pas de retour à la ligne à la fin : le jeu refuse le fichier sinon."""
    out = list(head)
    while out and not out[-1].strip():
        out.pop()
    if out and out[0].startswith('\u00ac Generated by'):
        out[0] = DESC_HEADER
    elif not out or out[0] != DESC_HEADER:
        out.insert(0, DESC_HEADER)
    for lines in blocks.values():
        out.extend(lines)
    return '\r\n'.join(out)


def scenario_folders(root):
    res = []
    try:
        for d in sorted(os.listdir(root)):
            if os.path.isfile(os.path.join(root, d, 'descr_battle.txt')):
                res.append(d)
    except OSError:
        pass
    return res


# --------------------------------------------------------------------------------------
#  IMPORT D'UN descr_battle.txt EXISTANT
# --------------------------------------------------------------------------------------

def resolve_faction(token, factions):
    t = token.strip()
    if t.lower() in factions:
        return t.lower()
    for fid, disp in factions.items():
        if disp.lower() == t.lower():
            return fid
    return t.lower()


def parse_alliance(s, factions):
    """Ligne « alliance [can_deploy] [can_view] f1, f2, defending|attacking » -> ([factions], rôle) ou None."""
    rest = re.sub(r'^alliance\s+', '', s.strip(), flags=re.I)
    rest = re.sub(r'\b(can_deploy|can_not_deploy|can_view|can_not_view)\b\s*', '', rest, flags=re.I)
    parts = [p.strip() for p in rest.split(',') if p.strip()]
    if len(parts) < 2:
        return None
    return [resolve_faction(p, factions) for p in parts[:-1]], parts[-1].lower()


def _gender_of(parts):
    for p in parts:
        w = p.strip().lower()
        if w in ('male', 'female'):
            return w
    return 'male'


def _age_of(parts):
    for p in parts:
        m = re.match(r'^\s*age\s+(\d+)\s*$', p, re.I)
        if m:
            return max(16, min(127, int(m.group(1))))
    return 30


def parse_descr_battle(text, factions):
    """Retourne un Scenario (positions ignorées : elles sont recalculées). Une faction peut avoir plusieurs armées
    (une par ligne « character » du bloc de la faction)."""
    sc = Scenario()
    sc.map_label = 'Importée'
    playable, nonplayable = [], []
    mode = None
    section = 'head'
    cur = None
    cur_army = None
    cur_b = None
    by_fac = {}
    order = []
    alliances = []
    sg = {'kind': None, 'level': '', 'style': '', 'tw': 0, 'gd': 0, 'creator': '', 'fort_owner': '', 'fort_creator': ''}
    eq_max = {'ram': 0, 'ladder': 0, 'tower': 0}
    zones = {}
    for raw in text.split('\n'):
        mm = re.match(r'^\s*;\s*auxiliary\s+(on|off)\b', raw, re.I)
        if mm:
            sc.aux = mm.group(1).lower() == 'on'
        if re.match(r'^\s*battle\s+\S+\s+singleplayer\b', raw, re.I):
            sc.solo = True
        s = raw.split(';', 1)[0].strip()
        if not s:
            continue
        toks = s.split()
        k = toks[0].lower()
        if k == 'battle':
            rest = s[len(toks[0]):].strip()
            m = re.match(r'^(-?\d+)\s*,\s*(-?\d+)', rest)
            if m:
                sc.map_x, sc.map_y = int(m.group(1)), int(m.group(2))
                section = 'battle'
            elif len(toks) > 1:
                sc.name = toks[1]
            continue
        if k in ('playable', 'nonplayable'):
            mode = k
            for extra in toks[1:]:          # faction écrite sur la même ligne
                (playable if k == 'playable' else nonplayable).append(resolve_faction(extra, factions))
            continue
        if k == 'end':
            mode = None
            continue
        if mode == 'playable':
            playable.append(resolve_faction(s, factions))
            continue
        if mode == 'nonplayable':
            nonplayable.append(resolve_faction(s, factions))
            continue
        if k in ('start_date', 'end_date') and len(toks) >= 3:
            try:
                sc.year = int(toks[1])
                sc.season = toks[2].lower()
            except ValueError:
                pass
        elif k == 'battle_time' and len(toks) >= 3:
            try:
                sc.hour, sc.param2 = float(toks[1]), float(toks[2])
            except ValueError:
                pass
        elif k == 'weather' and len(toks) >= 2:
            sc.weather = toks[1]
        elif k == 'home_faction' and len(toks) >= 2:
            sc.home_faction = resolve_faction(toks[1], factions)
        elif k == 'alliance':
            al = parse_alliance(s, factions)
            if al:
                alliances.append(al)
        elif k == 'settlement' and section == 'head':
            sg['kind'] = toks[1].lower() if len(toks) > 1 else ''
        elif k == 'level' and sg['kind'] is not None and len(toks) > 1 and section == 'head':
            sg['level'] = toks[1].lower()
        elif k == 'fortification' and section == 'head':
            ms = re.search(r'fortification\s+\d+\s+(\w+)', s, re.I)
            if ms:
                sg['style'] = ms.group(1).lower()
            mt = re.search(r'towers\s+(\d+)', s, re.I)
            mg = re.search(r'gate_defences\s+(\d+)', s, re.I)
            sg['tw'] = int(mt.group(1)) if mt else 0
            sg['gd'] = int(mg.group(1)) if mg else 0
        elif k == 'faction_creator' and len(toks) > 1 and section == 'head':
            sg['creator'] = toks[1].lower()
        elif k == 'siege_equipment' and len(toks) >= 3 and section == 'head':
            try:
                if toks[1].lower() in eq_max:
                    eq_max[toks[1].lower()] = max(eq_max[toks[1].lower()], int(toks[2]))
            except ValueError:
                pass
        elif k == 'fort' and section == 'battle':
            mf = re.search(r'owner\s+(\S+)\s+creator\s+(\S+)', s, re.I)
            sg['kind'] = ''
            sg['level'] = 'fort'
            if mf:
                sg['fort_owner'], sg['fort_creator'] = mf.group(1).lower(), mf.group(2).lower()
        elif section == 'battle' and k == 'deployment_area_point' and cur_b is not None:
            zones.setdefault(id(cur_b), []).append(tuple(re.findall(r'-?\d+\.?\d*', s)[:2]))
        elif section == 'battle' and k == 'army' and len(toks) >= 2:
            mb = re.match(r'^army\s+(\S+?)\s*,\s*(\d+)', s, re.I)
            cur_b = None
            if mb:
                lst = by_fac.get(resolve_faction(mb.group(1), factions)) or []
                if int(mb.group(2)) < len(lst):
                    cur_b = lst[int(mb.group(2))]
        elif section == 'battle' and k == 'unit' and cur_b is not None:
            mu = re.match(r'^unit\s+(\d+)\s*,.*attach_engine\s+(ram|ladder|tower)', s, re.I)
            if mu and int(mu.group(1)) < len(cur_b.units):
                cur_b.units[int(mu.group(1))].engine = mu.group(2).lower()
        elif section == 'head' and k == 'faction' and len(toks) >= 2:
            cur = resolve_faction(toks[1], factions)
            cur_army = None
            if cur not in by_fac:
                by_fac[cur] = []
                order.append(cur)
        elif section == 'head' and k == 'character' and cur:
            parts = s.split(None, 1)[1].split(',') if len(toks) > 1 else ['']
            cur_army = Army(faction=cur, human=True, general=parts[0].strip(), gender=_gender_of(parts[1:]), age=_age_of(parts[1:]))
            by_fac[cur].append(cur_army)
        elif section == 'head' and k == 'unit' and cur:
            m = re.match(r'^unit\s+(.+?)\s+soldiers\s+(\d+)\s+exp\s+(\d+)\s+armour\s+(\d+)\s+weapon_lvl\s+(\d+)', s, re.I)
            if m:
                if cur_army is None:
                    cur_army = Army(faction=cur, human=True)
                    by_fac[cur].append(cur_army)
                cur_army.units.append(UnitEntry(m.group(1).strip(), int(m.group(2)), int(m.group(3)),
                                                int(m.group(4)), int(m.group(5))))
    for f in playable + nonplayable:
        if f not in by_fac:
            by_fac[f] = [Army(faction=f)]
            order.append(f)
    for f in order:
        if not by_fac[f]:
            by_fac[f] = [Army(faction=f)]
        for a in by_fac[f]:
            a.human = f not in nonplayable
    team_of = {}
    for ti, (facs, role) in enumerate(alliances, start=1):
        sc.team_roles[str(ti)] = role if role in ROLES else 'attacking'
        for f in facs:
            team_of.setdefault(f, ti)
    for i, f in enumerate(order):
        for a in by_fac[f]:
            a.team = team_of.get(f, (i % 2) + 1)
    sc.armies = [a for f in order for a in by_fac[f]]
    if sg['kind'] is not None and sg['level']:          # scénario de siège : colonie, culture, défense, engins, même spawn
        sc.siege = True
        if sg['level'] == 'fort':
            sc.siege_type = 'Fort'
            sc.siege_culture = next((c for c, f in CULTURE_FACTION.items() if f == sg['fort_creator']), 'Humans')
        else:
            sc.siege_type = next((x[0] for x in SETTLEMENTS if x[1] == sg['level'] and x[2] == sg['kind']), sc.siege_type)
            sc.siege_culture = (next((c for c, st in CULTURES if st == sg['style']), None)
                                or next((c for c, f in CULTURE_FACTION.items() if f == sg['creator']), 'Humans'))
            sc.siege_dlevel = 3 if sg['gd'] else (2 if sg['tw'] else 1)
        if sg['level'] == 'fort':
            sc.siege_dlevel = 1
        sc.ram, sc.ladder, sc.tower = eq_max['ram'], eq_max['ladder'], eq_max['tower']
        roles = siege_roles(sc)
        if roles:
            att = [a for a in sc.armies if a.team == roles[1]]
            pts = [zones.get(id(a)) for a in att]
            sc.siege_same = len(att) > 1 and all(p and p == pts[0] for p in pts)
    return sc


def scan_maps(data_dir, dirs=None, info=None):
    """Cherche des emplacements de bataille : (étiquette, x, y).
    dirs : étiquette -> dossier modèle (map.wfc) ; info : étiquette -> climat, saison, verrou, météo fixe."""
    found = []
    seen = set()
    if not data_dir:
        return found
    # custom_locations.txt : lieux de bataille personnalisés (carte, climat, saison, verrou de colonie)
    cands = [os.path.join(data_dir, 'custom_locations.txt')]
    world = os.path.join(data_dir, 'world')
    for dirpath, dirnames, filenames in os.walk(world):
        if dirpath[len(world):].count(os.sep) > 3:
            dirnames[:] = []
            continue
        for fn in filenames:
            if fn.lower() == 'custom_locations.txt':
                cands.append(os.path.join(dirpath, fn))
    all_locs = []
    for c in cands:
        if not os.path.isfile(c):
            continue
        try:
            all_locs.append(parse_custom_locations(read_text(c)))
        except OSError:
            continue
    if not all_locs and os.path.isdir(os.path.join(data_dir, 'world')) and \
            os.path.isfile(os.path.join(data_dir, 'export_descr_unit.txt')):
        all_locs.append([{'name': n, 'x': x, 'y': y, 'climate': c, 'summer_only': so, 'locked': lk}
                         for n, x, y, c, so, lk in EMBEDDED_LOCATIONS])      # données intégrées du mod
    for locs in all_locs:
        for L in locs:
            key = (L['x'], L['y'])
            L['location'] = True
            if L['name'] in COORD_FIXES:
                L['orig_xy'] = (L['x'], L['y'])
                L['x'], L['y'] = COORD_FIXES[L['name']]
                key = (L['x'], L['y'])
            if info is not None:
                info[L['name']] = L
            if key not in seen:
                seen.add(key)
                found.append((L['name'], L['x'], L['y']))
    return found


# --------------------------------------------------------------------------------------
#  INTERFACE (tkinter)
# --------------------------------------------------------------------------------------

# --------------------------------------------------------------------------------------
#  LANGUE (français / anglais) : les textes de l'éditeur sont écrits en français dans le code ; `tr()` les traduit à l'affichage.
#  Les textes du jeu (noms d'unités, de factions, météos, descriptions, fichiers générés) ne sont jamais traduits.
# --------------------------------------------------------------------------------------
LANG = 'fr'

# valeurs de listes déroulantes / colonnes : le code travaille toujours avec la valeur française
VALUE_PAIRS = [
    ('Homme', 'Male'), ('Femme', 'Female'), ('Joueur', 'Player'), ('IA', 'AI'), ('Attaquant', 'Attacker'),
    ('Défenseur', 'Defender'), ('Lever du jour', 'Sunrise'), ('Matin', 'Morning'), ('Midi', 'Midday'),
    ('Après-midi', 'Afternoon'), ('Coucher du soleil', 'Sunset'), ('Nuit', 'Night'), ('Aléatoire', 'Random'),
    ('Nord', 'North'), ('Est', 'East'), ('Sud', 'South'), ('Ouest', 'West'), ('(toutes les factions)', '(all factions)'),
    ('(toutes)', '(all)'), ('Armée de base', 'Base army'), ('Armée auxiliaire', 'Auxiliary army'),
    ('Base + auxiliaire', 'Base + auxiliary'), ('Bélier', 'Ram'), ('Échelle', 'Ladder'), ('Tour', 'Tower'),
    ('Clair', 'Light'), ('Sombre (défaut)', 'Dark (default)'),
    ('Personnalisée (X / Y ci-contre)', 'Custom (X / Y opposite)'),
]
VALUE_EN = dict(VALUE_PAIRS)
VALUE_FR = {v: k for k, v in VALUE_PAIRS}

FR_TEXT = {      # seuls changements du français
    'Faithful Alliances': 'Alliances Loyales',
    'Snapshot': 'Vignette', 'Loading Screen': 'Image de Chargement',
}
EN_TEXT = {
    '(sans nom)': '(unnamed)', 'Nouvelle alliance': 'New alliance',
    'Dossier « data » du mod :': 'Mod "data" folder:', 'Parcourir…': 'Browse…', 'Nouveau': 'New',
    'Importer un scénario': 'Import a scenario', 'Ouvrir un descr_battle.txt': 'Open a descr_battle.txt',
    'Remettre à zéro tous les paramètres': 'Reset all parameters', 'Scénario aléatoire…': 'Random scenario…',
    '▶  GÉNÉRER LE SCÉNARIO': '▶  GENERATE SCENARIO', 'Scénario solo': 'Solo scenario', 'Climats chaotiques': 'Chaotic Climates',
    "Les météos et saisons hors du climat de la carte (par exemple de la neige dans le désert, ou l'hiver sur une carte d'été) peuvent aussi être tirées.": 'Weathers and seasons outside the map\'s climate (for example snow in the desert, or winter on a summer-only map) can also be drawn.',
    "Le scénario est écrit pour le mode solo (singleplayer) : toutes les armées peuvent être contrôlées par le joueur. L'expérience des unités peut aller jusqu'au niveau 9 (limitée à 3 en multijoueur).": 'The scenario is written for solo mode (singleplayer): every army can be controlled by the player. Unit experience can go up to level 9 (limited to 3 in multiplayer).', 'Scénario': 'Scenario',
    'Nom (dossier)': 'Name (folder)', 'Carte': 'Map', 'Coordonnées X / Y': 'Coordinates X / Y', 'Heure': 'Time',
    'Limite de Temps': 'Time Limit', 'Météo': 'Weather', 'Date (année / saison)': 'Date (year / season)',
    'Distance siège (m)': 'Siege distance (m)',
    'Unités auxiliaires': 'Auxiliary units',  'Distance': 'Distance', 'Nom': 'Name',
    'Heure': 'Time', 'Optimiser': 'Optimize', 'Carte…': 'Map…', 'une seule zone par équipe': 'one zone per team',
    'Carte Perso': 'Custom Map', '0.0=Temps illimité': '0.0=No Time Limit', 'Toutes les saisons et météos peuvent être choisies': 'Any season and weather can be chosen', 'Choisir les coordonnées sur la carte': 'Pick coordinates on the map',
    'Taille / Hauteur / Largeur': 'Size / Height / Width', 'Optionnel : map.wfc (vide=world map)': 'Optional: map.wfc (empty=world map)',
    'Optionnel : snapshot.tga (vide=image du mod)': 'Optional: snapshot.tga (empty=mod image)',
    'Optionnel : loading_screen.tga (vide=image du mod)': 'Optional: loading_screen.tga (empty=mod image)',
    'Étoile : coordonnées actuelles · points rouges : lieux du mod (custom_locations.txt)': 'Star: current coordinates · red dots: mod locations (custom_locations.txt)',
    "Option Alliance Loyale active : pas assez d'alliances": 'Faithful Alliances option active: not enough alliances',
    'Ajouter une description': 'Add a description', 'Description du scénario': 'Scenario description',
    'Armées du scénario': 'Scenario armies', 'Siège': 'Siege', 'Mode siège': 'Siege mode', 'Défense': 'Defence',
    'Contrôle': 'Control', 'Équipe': 'Team', 'Équipe \u25bc': 'Team \u25bc', 'Unités': 'Units', 'Coût': 'Cost',
    '+ Ajouter une armée': '+ Add an army', '− Supprimer': '− Delete', 'Armée sélectionnée': 'Selected army',
    "Rôle de l'équipe": 'Team role', "(valable pour toute l'équipe)": '(applies to the whole team)',
    'Nom du général': 'General name', 'Âge du général': 'General age',
    '(16 à 127 ans).': '(16 to 127).',
    'Armée aléatoire (unités de la faction)': 'Random army (faction units)', 'Valeur': 'Value', 'Unités max': 'Max units',
    'Soldats max': 'Max soldiers', 'Améliorations': 'Upgrades', 'Or aléatoire': 'Random gold',
    "Générer l'armée": 'Generate army', 'Générer toutes les armées (même valeur)': 'Generate all armies (same value)',
    'Retirer': 'Remove', 'Dupliquer': 'Duplicate', 'Monter': 'Move up', 'Descendre': 'Move down', 'Vider': 'Clear',
    'Expérience': 'Experience', 'Armure': 'Armour', 'Arme': 'Weapon', 'Appliquer à la sélection': 'Apply to selection',
    "Unités de l'armée (la 1re unité = général)": 'Army units (1st unit = general)', 'Unité': 'Unit', 'Soldats': 'Soldiers', 'Auxiliaire': 'Auxiliary',
    '+ Bélier': '+ Ram', '+ Échelle': '+ Ladder', '+ Tour': '+ Tower', 'Engin de siège': 'Siege engine',
    'Déploiement': 'Deployment', 'Fichier': 'File', 'Rechercher': 'Search', 'Catégorie': 'Category', 'Classe': 'Class',
    'Affichage': 'Display', "⇦ Ajouter à l'armée sélectionnée": '⇦ Add to selected army',
    '%d unités affichées  (★ = bon général)%s': '%d units shown  (★ = good general)%s',
    '  · choisissez une faction pour filtrer base / auxiliaire': '  · pick a faction to filter base / auxiliary',
    'Ajouter à l\'armée sélectionnée': 'Add to selected army',
    'Cartes préconstruites': 'Pre-built maps', 'Carte préconstruite': 'Pre-built map',
    'dossier non trouvé': 'folder not found', '\n\nDossier cherché : %s': '\n\nFolder searched: %s',
    'Afficher aussi les Cartes Préconstruites (repérées par ': 'Also show the pre-built maps (marked with ',
    'Aléatoire': 'Random', 'Plus de %d équipes': 'More than %d teams', 'Siège : 2 équipes max': 'Siege: 2 teams max',
    'Lieu libre sur la carte du mod': 'Free place on the mod map', "Nombre d'équipes": 'Number of teams',
    'Joueurs humains (2 minimum)': 'Human players (2 minimum)', 'Armées IA': 'AI armies',
    "Valeur minimum d'une armée": 'Minimum army value', "Valeur maximum d'une armée": 'Maximum army value',
    'Unités max par armée': 'Max units per army', 'Maximum de soldats (total, toutes armées)': 'Max soldiers (total, all armies)',
    'Générer': 'Generate', 'Éditer…': 'Edit…', 'Faithful Alliances': 'Faithful Alliances',
    'total %d / %d': 'total %d / %d',
    "Valeur d'or aléatoire, équipes de même valeur totale, carte du mod (sans map.wfc),\nfactions, équipes, heure et météo aléatoires. Le scénario actuel sera remplacé.":
        'Random gold value, teams of equal total value, mod map (no map.wfc),\nrandom factions, teams, time and weather. The current scenario will be replaced.',
    "Modifier les alliances possibles : une équipe d'un scénario aléatoire ne réunit que des factions appartenant à une même alliance.":
        'Edit the possible alliances: a team of a random scenario only gathers factions belonging to the same alliance.',
    'Alliances': 'Alliances', "Factions de l'alliance sélectionnée": 'Factions of the selected alliance',
    '+ Alliance': '+ Alliance', 'Réinitialiser': 'Reset', 'Annuler': 'Cancel',
    'Scénario aléatoire': 'Random scenario', 'Armées générées': 'Generated armies', 'Données': 'Data',
    "Chargez d'abord le dossier « data » du mod.": 'Load the mod "data" folder first.',
    'Valeur visée par équipe : %d\nTotaux réels : %s': 'Target per team: %d\nActual totals: %s',
    "\nLes équipes n'ont pas pu être rapprochées à moins de 100 or (peu d'unités / améliorations disponibles).":
        "\nTeams could not be brought within 100 gold of each other (few units / upgrades available).",
    "Valeur minimum trop élevée pour ces options (aucune amélioration / peu d'unités) : réduite.":
        'Minimum value too high for these options (no upgrades / few units): lowered.',
    'équipe %d : %d': 'team %d: %d',
    'Aucune armée': 'No army', "Sélectionnez ou ajoutez d'abord une armée.": 'Select or add an army first.',
    'Armée complète': 'Army full', 'Une armée contient au maximum %d unités.': 'An army holds at most %d units.',
    'Unité refusée': 'Unit refused',
    "Ces unités n'appartiennent pas à la faction %s (ni à ses auxiliaires prévues) et ne peuvent pas être ajoutées :\n%s":
        'These units do not belong to faction %s (nor to its planned auxiliaries) and cannot be added:\n%s',
    'Aucune unité': 'No unit', 'Aucune unité disponible pour la faction « %s ».': 'No unit available for faction "%s".',
    "Aucune unité d'infanterie de plus de 20 soldats disponible pour porter cet engin.": 'No infantry unit with more than 20 soldiers available to carry this engine.',
    "Une faction n'a aucune unité disponible.": 'A faction has no available unit.',
    'Remplacer': 'Replace', "Remplacer les unités actuelles de l'armée ?": "Replace the army's current units?",
    'Remplacer les unités de TOUTES les armées (équipes de même valeur totale) ?': 'Replace the units of ALL armies (teams of equal total value)?',
    'Vider': 'Clear', 'Retirer toutes les unités de cette armée ?': 'Remove all units from this army?',
    'Faction déjà utilisée': 'Faction already used',
    'Cette faction est déjà présente dans le scénario : une même faction ne peut pas être ajoutée deux fois.':
        'This faction is already in the scenario: the same faction cannot be added twice.',
    'Factions': 'Factions',
    'Toutes les factions sont déjà dans le scénario (une faction ne peut pas être ajoutée deux fois).':
        'All factions are already in the scenario (a faction cannot be added twice).',
    'Nom déjà utilisé': 'Name already used',
    "Un scénario « %s » existe déjà : le nouveau est nommé « %s » (l'ancien n'est pas modifié).":
        'A scenario "%s" already exists: the new one is named "%s" (the old one is unchanged).',
    'Un seul joueur humain': 'Only one human player',
    "Attention : il n'y a qu'un seul emplacement pour joueur humain dans ce scénario (une seule armée « Joueur »).\n\nCréer quand même la carte ?":
        'Warning: there is only one human player slot in this scenario (a single "Player" army).\n\nCreate the map anyway?',
    'Scénario incomplet': 'Incomplete scenario', 'Avertissements': 'Warnings', '\n\nGénérer quand même ?': '\n\nGenerate anyway?',
    'Scénario généré': 'Scenario generated', 'Erreur': 'Error', 'Erreur : %s': 'Error: %s',
    'Écriture impossible : %s': 'Cannot write: %s', 'Impossible de lire %s\n%s': 'Cannot read %s\n%s',
    'Lecture impossible : %s': 'Cannot read: %s',
    'Import': 'Import', 'Scénario importé. Les positions des unités sont recalculées automatiquement.':
        'Scenario imported. Unit positions are recalculated automatically.',
    '\nFichiers créés : %s': '\nFiles created: %s', '\n(aucun map.wfc / snapshot copié)': '\n(no map.wfc / snapshot copied)',
    "Dossier créé à côté de l'éditeur :\n%s%s\n\nCopiez ce dossier dans :\n...\\mods\\<votre mod>\\data\\world\\maps\\battle\\\npuis relancez le jeu.":
        'Folder created next to the editor:\n%s%s\n\nCopy this folder into:\n...\\mods\\<your mod>\\data\\world\\maps\\battle\\\nthen restart the game.',
    'battle_descriptions.txt non mis à jour : %s': 'battle_descriptions.txt not updated: %s',
    'Nouveau': 'New', 'Abandonner le scénario en cours ?': 'Discard the current scenario?',
    'Reprendre aussi les armées de la carte (factions, équipes, contrôle) ? Les unités actuelles seront retirées.':
        "Also take the map's armies (factions, teams, control)? Current units will be removed.",
    'attention paramètres modifiés': 'warning: parameters modified',
    '⚠ Choisissez le dossier « data » du mod.': '⚠ Choose the mod "data" folder.',
    '%d unités · %d météos (%s) · %d climats%s': '%d units · %d weathers (%s) · %d climates%s',
    'intégrées au programme': 'built into the program',
    '  (noms internes : export_units.txt introuvable)': '  (internal names: export_units.txt not found)',
    'Choisir le dossier « data » du mod (celui qui contient export_descr_unit.txt)': 'Choose the mod "data" folder (the one containing export_descr_unit.txt)',
    'Dossier contenant map.wfc et snapshot (scénario LAN du jeu de base ou carte de maps/custom)':
        'Folder containing map.wfc and snapshot (base-game LAN scenario or maps/custom map)',
    'descr_battle.txt à importer': 'descr_battle.txt to import', 'Fichier map.wfc': 'map.wfc file', 'Tous': 'All',
    'Image .tga du snapshot': 'Snapshot .tga image', "Image .tga de l'écran de chargement": 'Loading-screen .tga image',
    'map_composite.tga introuvable dans data\\menu du mod.': 'map_composite.tga not found in the mod data\\menu folder.',
    'Carte de campagne du mod : cliquez pour choisir le lieu de bataille': 'Mod campaign map: click to choose the battle location',
    'Points rouges : lieux du mod (custom_locations.txt)': 'Red dots: mod locations (custom_locations.txt)',
    '  (terrain non vérifié)': '  (terrain not verified)',
    'Texte ajouté à la fin de la description (mise en page automatique : 33 caractères par ligne) :':
        'Text added at the end of the description (automatic layout: 33 characters per line):',
    'Distance : %d à %d m': 'Distance: %d to %d m',
    'sans défense': 'no defences', 'testé': 'tested', 'paquet du mod (non testé)': 'mod package (untested)',
    'paquet du jeu, nom supposé (non testé)': 'game package, assumed name (untested)',
    "Le siège demande exactement deux équipes : une « Attaquant », l'autre « Défenseur ». Réglez les équipes des armées.":
        'A siege needs exactly two teams: one "Attacker", the other "Defender". Set the armies\' teams.',
    'Les armées sont toujours affichées par numéro d\'équipe croissant.': 'Armies are always listed by increasing team number.',
    "Les armées sont toujours affichées par numéro d'équipe croissant.": 'Armies are always listed by increasing team number.',
    'Plan (nord = haut)': 'Plan (north = top)', '  Colonie : %s': '  Settlement: %s', '(aucune armée)': '(no army)',
    '%d / %d unités%s · coût estimé %d · %d soldats': '%d / %d units%s · estimated cost %d · %d soldiers',
    ' (complet)': ' (full)', '(aux) ': '(aux) ',
    '+ de %d soldats': '+ of %d soldiers', '+ de %d soldats (total du scénario : %d)': '+ of %d soldiers (scenario total: %d)',
    "Limite d'or": 'Gold limit', 'Le maximum est de %d or par équipe : modification annulée.': 'The maximum is %d gold per team: change cancelled.',
    'Total de soldats de toutes les armées (Large Unit Scale). Le jeu affiche un avertissement de performances à partir de %d. Vous pouvez dépasser cette valeur.':
        'Total soldiers of all armies (Large Unit Scale). The game shows a performance warning from %d. You may exceed this value.',
    "Le jeu de base et le mod ne proposent que %d équipes ; les scénarios à 5-8 équipes fonctionnent mais les dernières armées risquent d'être impossibles à sélectionner.":
        'The base game and the mod only offer %d teams; scenarios with 5-8 teams work but the last armies might not be selectable.',
    'attention limite de %d soldats / %d équipes dépassée': 'warning: limit of %d soldiers / %d teams exceeded',
    "Attention, les dernières armées risquent d'être impossibles à sélectionner": 'Warning: the last armies might not be selectable',
    'Descriptions': 'Descriptions', 'Ajouter': 'Add', 'Supprimer': 'Delete', 'Écraser': 'Overwrite', 'Actualiser': 'Refresh',
    "Ajoute, à la suite du texte, les scénarios dont le dossier est à côté de l'éditeur et qui n'y figurent pas encore (titre avec espaces, météo, heure, joueurs et or). Écrit le fichier.":
        "Appends to the text the scenarios whose folder is next to the editor and that are not in it yet (title with spaces, weather, time, players and gold). Writes the file.",
    "Enlève du texte les scénarios dont le dossier n'est plus à côté de l'éditeur (seuls les blocs créés par l'éditeur sont concernés). Écrit le fichier.":
        'Removes from the text the scenarios whose folder is no longer next to the editor (only blocks created by the editor are affected). Writes the file.',
    "Écrit dans le fichier le texte tel qu'il est affiché ici (vos modifications manuelles comprises).":
        'Writes the text to the file as displayed here (including your manual edits).',
    "Recharge le fichier battle_descriptions.txt situé dans le dossier de l'éditeur.":
        "Reloads the battle_descriptions.txt file located in the editor's folder.",
    'Copiez %s dans le dossier mod/data/text.': 'Copy %s into the mod/data/text folder.',
    "Ajoute (ou remplace) le bloc du scénario qui vient d'être créé dans battle_descriptions.txt.":
        'Adds (or replaces) the block of the scenario just created in battle_descriptions.txt.',
    "Siège : ce lieu n'est pas vérifié comme terrain plat (pentes, eau) : les troupes peuvent mal apparaître ou le jeu planter au chargement.":
        'Siege: this location is not verified as flat terrain (slopes, water): troops may spawn badly or the game may crash on loading.',
    "La valeur choisie sera celle de l'équipe": "The chosen value will be the team's value",
    'Siège : ce lieu du mod a une colonie fixe (sett_locked) : le fort ajouté risque de ne pas se charger ou de faire planter le jeu.':
        'Siege: this mod location has a fixed settlement (sett_locked): the added fort may not load or may crash the game.',
    'Désactivé : chaque armée a sa propre zone. Activé : toutes les armées d\'une même équipe partagent une seule zone (taille ajustée aux armées). En siège : les assaillants.':
        'Off: each army has its own zone. On: all armies of a team share one zone (size adjusted to the armies). In a siege: the attackers.',
    "Désactivé : chaque armée a sa propre zone. Activé : toutes les armées d'une même équipe partagent une seule zone (taille ajustée aux armées).":
        'Off: each army has its own zone. On: all armies of a team share one zone (size adjusted to the armies).',
    'Optimiser les spawn (redimensionne automatiquement Taille / Hauteur / Largeur)':
        'Optimize spawns (automatically resizes Size / Height / Width)',
    'Carte préconstruite : reprend les paramètres de son descr_battle.txt (convertis pour le mod).':
        'Pre-built map: takes the parameters of its descr_battle.txt (converted for the mod).',
    'Saisons et météos : toutes celles du mod, celles du climat de la carte (custom_locations.txt) en premier.':
        "Seasons and weathers: all those of the mod, those of the map's climate (custom_locations.txt) first.",
    'Siège : il faut exactement deux équipes, l\'une « Attaquant », l\'autre « Défenseur ».':
        'Siege: exactly two teams are needed, one "Attacker", the other "Defender".',
    'Défenseurs : zone de %d m de profondeur, plus grande que la cour de la colonie (≈ %d m) : certaines unités seront sur les remparts ou dehors (peu grave).':
        "Defenders: zone %d m deep, larger than the settlement courtyard (≈ %d m): some units will be on the ramparts or outside (minor).",
    'Certaines zones de déploiement dépassent ±%d m : elles risquent de sortir de la carte (réduisez la largeur par armée ou la distance entre camps).':
        'Some deployment zones exceed ±%d m: they may leave the map (reduce the width per army or the distance between camps).',
    "Zone de l'équipe %d agrandie à %d m de profondeur pour contenir toutes les unités.":
        'Zone of team %d enlarged to %d m deep to hold all units.',
    'Le nom du scénario est vide ou ne contient aucun caractère valide.': 'The scenario name is empty or contains no valid character.',
    'Il faut au moins deux armées.': 'At least two armies are needed.',
    "Plus de %d armées : le jeu n'en gère pas davantage.": 'More than %d armies: the game does not handle more.',
    'Coordonnées %d / %d hors de la carte de campagne du mod (X 0 à %d, Y 0 à %d) : le menu du jeu plante.':
        'Coordinates %d / %d outside the mod campaign map (X 0 to %d, Y 0 to %d): the game menu crashes.',
    'Météo « %s » inconnue du mod (absente de weather_db.xml) : le jeu risque de se bloquer au menu. Choisissez une météo de la liste.':
        'Weather "%s" unknown to the mod (missing from weather_db.xml): the game may hang at the menu. Pick a weather from the list.',
    'Faction « %s » présente plusieurs fois : interdit (une seule armée par faction).': 'Faction "%s" present several times: forbidden (one army per faction).',
    "L'armée « %s » n'a aucune unité.": 'Army "%s" has no unit.', 'Armée « %s » : %d unités, le maximum est %d.': 'Army "%s": %d units, the maximum is %d.',
    "Armée « %s » : unités absentes de la liste de la faction (risque de crash ou d'unité invisible) : %s.":
        'Army "%s": units missing from the faction list (risk of crash or invisible unit): %s.',
    'Armée « %s » : unités auxiliaires (cochez « Unités auxiliaires » si le mode escarmouche les propose) : %s.':
        'Army "%s": auxiliary units (tick "Auxiliary units" if skirmish mode offers them): %s.',
    'Équipe %d : %d or au total, le maximum est %d par équipe.': 'Team %d: %d gold in total, the maximum is %d per team.',
    "Unité inconnue dans l'armée « %s » : %s": 'Unknown unit in army "%s": %s',
    '« %s » (%s) : expérience ou arme hors limites.': '"%s" (%s): experience or weapon out of range.',
    "Siège : « %s » n'a pas de défenses : choisissez un autre settlement.": 'Siege: "%s" has no defences: choose another settlement.',
    'Siège : les deux équipes doivent porter les numéros 1 et 2.': 'Siege: the two teams must be numbered 1 and 2.',
    "Siège : l'armée attaquante « %s » doit contenir une unité de siège ou porter des engins (béliers, échelles, tours).":
        'Siege: attacking army "%s" must contain a siege unit or carry engines (rams, ladders, towers).',
    "Siège : il faut exactement deux équipes, l'une « Attaquant » et l'autre « Défenseur ».":
        'Siege: exactly two teams are needed, one "Attacker" and the other "Defender".',
    'Aucune armée « Joueur » : personne ne pourra rejoindre la partie.': 'No "Player" army: nobody will be able to join the game.',
    "Toutes les armées sont dans la même équipe : il n'y aura pas d'ennemi.": 'All armies are in the same team: there will be no enemy.',
    'Langue': 'Language', 'Couleurs': 'Colors', 'Couleurs de l\'éditeur': 'Editor colors',
    'Thème': 'Theme', 'Clair': 'Light', 'Sombre (défaut)': 'Dark (default)', 'Nouveau thème': 'New theme', 'Réinitialiser': 'Reset', 'Supprimer tous les thèmes': 'Delete all themes', 'Nom du thème :': 'Theme name:', 'Fond': 'Background', 'Texte': 'Text',
    'Champs de saisie': 'Input fields', 'Boutons': 'Buttons', 'Sélection': 'Selection',
    'Équipe %d (plan)': 'Team %d (plan)', 'Fermer': 'Close',
    'Choisir…': 'Choose…', 'Éléments': 'Elements', 'Équipes du plan de déploiement': 'Deployment plan teams', 'Titres': 'Titles',
    'Thèmes prédéfinis': 'Preset themes',
}
_TEMPLATES = {}


def _compile_templates(d):
    out = []
    for fr, en in d.items():
        if '%' not in fr:
            continue
        rx = re.escape(fr).replace('%d', r'(-?\d+)').replace('%s', r'(.*?)')
        out.append((re.compile(rx + r'\Z', re.S), en.replace('%d', '%s')))
    return out


def tr_lang(s, lang):
    d = FR_TEXT if lang == 'fr' else EN_TEXT
    return d.get(s, s)


def tr(s):
    """Texte de l'éditeur dans la langue choisie (les textes du jeu ne passent jamais par ici)."""
    if not isinstance(s, str) or not s:
        return s
    d = FR_TEXT if LANG == 'fr' else EN_TEXT
    r = d.get(s)
    if r is not None:
        return r
    tp = _TEMPLATES.get(LANG)
    if tp is None:
        tp = _TEMPLATES[LANG] = _compile_templates(d)
    for rx, out in tp:
        m = rx.match(s)
        if m:
            try:
                return out % tuple(tr(g) for g in m.groups())
            except (TypeError, ValueError):
                return s
    if LANG == 'en' and '\n' in s:                  # messages composés de plusieurs lignes : chaque ligne séparément
        parts = s.split('\n')
        new = [tr(p) if p else p for p in parts]
        if new != parts:
            return '\n'.join(new)
    return s


def tr_value(v):
    """Valeur de liste / colonne (voir VALUE_PAIRS)."""
    if LANG == 'en' and isinstance(v, str):
        return VALUE_EN.get(v, v)
    return v


def fr_value(v):
    if LANG == 'en' and isinstance(v, str):
        return VALUE_FR.get(v, v)
    return v


_I18N_VARS = {}          # nom de variable -> variable (listes déroulantes : le code lit toujours la valeur française)
_I18N_FREEZE = [False]
_VAR_ORIG = {}


def sync_i18n_vars():
    """Affiche dans la langue courante la valeur initiale des variables de listes déroulantes (créées avant l'installation)."""
    if LANG == 'fr' or not _VAR_ORIG:
        return
    for v in list(_I18N_VARS.values()):
        try:
            _VAR_ORIG['set'](v, tr_value(fr_value(_VAR_ORIG['get'](v))))
        except Exception:           # noqa
            pass


def install_i18n():
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    if getattr(tk, '_tz_i18n', False):
        return
    tk._tz_i18n = True
    orig_options = tk.Misc._options

    def _options(self, cnf, kw=None):
        cnf = tk._cnfmerge((cnf, kw)) if kw else tk._cnfmerge(cnf)
        if 'text' in cnf and isinstance(cnf['text'], str) and not isinstance(self, tk.Canvas):
            if not _I18N_FREEZE[0]:
                self.__dict__.setdefault('_i18n', {})['text'] = cnf['text']
            cnf['text'] = tr(cnf['text'])
        if 'values' in cnf and isinstance(self, (ttk.Combobox, ttk.Spinbox, tk.Spinbox)):
            vals = cnf['values']
            if isinstance(vals, (list, tuple)):
                if not _I18N_FREEZE[0]:
                    self.__dict__.setdefault('_i18n', {})['values'] = list(vals)
                cnf['values'] = [tr_value(x) for x in vals]
        tvar = cnf.get('textvariable')
        if tvar is not None and isinstance(self, (ttk.Combobox, ttk.Spinbox)) and isinstance(tvar, tk.StringVar):
            _I18N_VARS[str(tvar)] = tvar
        return orig_options(self, cnf)
    tk.Misc._options = _options

    o_get, o_set = tk.StringVar.get, tk.StringVar.set
    _VAR_ORIG['get'], _VAR_ORIG['set'] = o_get, o_set

    def vget(self):
        v = o_get(self)
        if LANG != 'fr' and str(self) in _I18N_VARS:
            return fr_value(v)
        return v

    def vset(self, value):
        if LANG != 'fr' and str(self) in _I18N_VARS and isinstance(value, str):
            value = tr_value(value)
        o_set(self, value)
    tk.StringVar.get, tk.StringVar.set = vget, vset

    o_head = ttk.Treeview.heading

    def heading(self, column, option=None, **kw):
        if 'text' in kw and isinstance(kw['text'], str):
            if not _I18N_FREEZE[0]:
                self.__dict__.setdefault('_i18n_heads', {})[column] = kw['text']
            kw['text'] = tr(kw['text'])
        return o_head(self, column, option, **kw)
    ttk.Treeview.heading = heading

    o_ins, o_item = ttk.Treeview.insert, ttk.Treeview.item

    def _vals(kw):
        if 'values' in kw and isinstance(kw['values'], (list, tuple)):
            kw['values'] = [tr_value(x) for x in kw['values']]
        return kw

    def insert(self, parent, index, iid=None, **kw):
        return o_ins(self, parent, index, iid, **_vals(kw))

    def item(self, item, option=None, **kw):
        return o_item(self, item, option, **_vals(kw))
    ttk.Treeview.insert, ttk.Treeview.item = insert, item

    o_add, o_tab = ttk.Notebook.add, ttk.Notebook.tab

    def nb_add(self, child, **kw):
        if isinstance(kw.get('text'), str):
            if not _I18N_FREEZE[0]:
                self.__dict__.setdefault('_i18n_tabs', {})[str(child)] = kw['text']
            kw['text'] = tr(kw['text'])
        return o_add(self, child, **kw)

    def nb_tab(self, tab_id, option=None, **kw):
        if isinstance(kw.get('text'), str):
            kw['text'] = tr(kw['text'])
        return o_tab(self, tab_id, option, **kw)
    ttk.Notebook.add, ttk.Notebook.tab = nb_add, nb_tab

    for fn in ('showinfo', 'showwarning', 'showerror', 'askyesno', 'askokcancel', 'askquestion', 'askretrycancel'):
        def mk(f):
            def w(title=None, message=None, **kw):
                return f(tr(title), tr(message), **kw)
            return w
        setattr(messagebox, fn, mk(getattr(messagebox, fn)))
    for fn in ('askopenfilename', 'asksaveasfilename', 'askdirectory'):
        def mkf(f):
            def w(*a, **kw):
                if isinstance(kw.get('title'), str):
                    kw['title'] = tr(kw['title'])
                if kw.get('filetypes'):
                    kw['filetypes'] = [(tr(n), p) for n, p in kw['filetypes']]
                return f(*a, **kw)
            return w
        setattr(filedialog, fn, mkf(getattr(filedialog, fn)))


def retranslate(root):
    """Réapplique la langue courante à tous les widgets existants."""
    from tkinter import ttk
    import tkinter as tk
    _I18N_FREEZE[0] = True
    try:
        def walk(w):
            d = w.__dict__.get('_i18n')
            if d:
                try:
                    if 'text' in d:
                        w.configure(text=d['text'])
                    if 'values' in d:
                        w.configure(values=d['values'])
                except tk.TclError:
                    pass
            hd = w.__dict__.get('_i18n_heads')
            if hd:
                for col, t in hd.items():
                    try:
                        w.heading(col, text=t)
                    except tk.TclError:
                        pass
            tb = w.__dict__.get('_i18n_tabs')
            if tb:
                for ch, t in tb.items():
                    try:
                        w.tab(ch, text=t)
                    except tk.TclError:
                        pass
            for c in w.winfo_children():
                walk(c)
        walk(root)
    finally:
        _I18N_FREEZE[0] = False


def set_language(lang, root=None):
    """Change la langue : les variables des listes déroulantes gardent leur valeur (convertie), les textes sont retraduits."""
    global LANG
    if lang == LANG:
        return
    cur = {n: v.get() for n, v in _I18N_VARS.items()}      # valeurs françaises (lecture avec l'ancienne langue)
    LANG = lang
    if root is not None:
        retranslate(root)
    for n, v in _I18N_VARS.items():
        try:
            v.set(cur[n])
        except Exception:               # noqa
            pass



DEFAULT_THEME = 'Sombre (défaut)'
DEFAULT_COLORS = {'bg': '#2b2d30', 'fg': '#e6e6e6', 'field': '#1e1f22', 'button': '#3c3f41', 'select': '#2f65ca',
                  'accent': '#e8b44c', 'muted': '#a0a0a0'}
COLOR_THEMES = {
    DEFAULT_THEME: dict(DEFAULT_COLORS),
    'Clair': {'bg': '#dcdad5', 'fg': '#000000', 'field': '#ffffff', 'button': '#cfcdc8', 'select': '#4a6984',
              'accent': '#000000', 'muted': '#555555'},
}


class Tooltip:
    """Bulle de texte affichée au survol d'un widget."""

    def __init__(self, widget, text, when=None):
        import tkinter as tk
        self.tk, self.widget, self.text, self.tip, self.when = tk, widget, text, None, when
        widget.bind('<Enter>', self.show, add='+')
        widget.bind('<Leave>', self.hide, add='+')

    def show(self, _e=None):
        if self.tip:
            return
        if self.when is not None and not self.when():
            return
        self.tip = tw = self.tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        sw, sh = self.widget.winfo_screenwidth(), self.widget.winfo_screenheight()
        wrap = max(160, min(360, sw // 3))
        self.tk.Label(tw, text=tr(self.text), justify='left', background='#ffffe1', relief='solid', borderwidth=1,
                      wraplength=wrap, padx=6, pady=3).pack()
        tw.update_idletasks()
        w, h = tw.winfo_reqwidth(), tw.winfo_reqheight()
        x = self.widget.winfo_rootx() + 18
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        if x + w > sw - 4:
            x = max(0, sw - w - 4)
        if y + h > sh - 4:                 # pas la place en dessous : au-dessus du widget
            y = max(0, self.widget.winfo_rooty() - h - 4)
        tw.wm_geometry('+%d+%d' % (x, y))

    def hide(self, _e=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class HeadingTip:
    """Bulle au survol de l'en-tête d'une colonne d'un Treeview ({id de colonne: texte})."""

    def __init__(self, tree, tips):
        import tkinter as tk
        self.tk, self.tree, self.tips, self.tip, self.col = tk, tree, tips, None, None
        tree.bind('<Motion>', self.move, add='+')
        tree.bind('<Leave>', self.hide, add='+')

    def move(self, e):
        col = None
        if self.tree.identify_region(e.x, e.y) == 'heading':
            cols = list(self.tree['displaycolumns'])
            if not cols or cols[0] == '#all':
                cols = list(self.tree['columns'])
            try:
                col = cols[int(self.tree.identify_column(e.x)[1:]) - 1]
            except (ValueError, IndexError):
                col = None
        if col == self.col:
            return
        self.hide()
        self.col = col
        if col in self.tips:
            self.tip = tw = self.tk.Toplevel(self.tree)
            tw.wm_overrideredirect(True)
            self.tk.Label(tw, text=tr(self.tips[col]), background='#ffffe1', relief='solid', borderwidth=1,
                          padx=6, pady=3).pack()
            tw.wm_geometry('+%d+%d' % (e.x_root + 12, e.y_root + 18))

    def hide(self, _e=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None
        if _e is not None:
            self.col = None


def run_gui(autorun=True):
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    install_i18n()

    here = os.path.dirname(os.path.abspath(sys.argv[0] if sys.argv and sys.argv[0] else __file__))
    cfg_path = os.path.join(here, 'm2tw_scenario_editor_config.json')

    TEAM_COLORS = ['#c0392b', '#2471a3', '#1e8449', '#b7950b', '#7d3c98', '#117a8b', '#af601a', '#566573']

    class App(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("Tzeentch Scenario Editor - Medieval II : Total War (Battle of the End Times)")
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
            self.geometry('%dx%d' % (min(1500, sw - 40), sh - 70))
            try:                                  # fenêtre agrandie à tout l'écran (Windows) : la liste des armées gagne de la hauteur
                self.state('zoomed')
            except tk.TclError:
                pass
            self.minsize(1100, 650)
            try:
                ttk.Style(self).theme_use('clam')
            except tk.TclError:
                pass
            st = ttk.Style(self)
            st.configure('Treeview', rowheight=22)
            st.configure('Title.TLabel', font=('Segoe UI', 10, 'bold'))
            st.configure('Treeview.Heading', padding=(2, 4, 2, 4))       # en-têtes : hauteur suffisante pour les accents
            self.cfg = {}
            try:
                with open(cfg_path, 'r', encoding='utf-8') as fh:
                    self.cfg = json.load(fh)
            except (OSError, ValueError):
                pass
            self.data_dir = self.cfg.get('data_dir', '')
            self.team_colors = list(self.cfg.get('team_colors') or TEAM_COLORS)
            if self.cfg.get('faithful_alliances') and self.cfg.get('alliances_rev') == ALLIANCES_REV:
                set_alliances(self.cfg['faithful_alliances'])
            set_language(self.cfg.get('lang') if self.cfg.get('lang') in ('fr', 'en') else 'en')
            self.themes = {n_: dict(p_) for n_, p_ in COLOR_THEMES.items()}
            for n_, p_ in (self.cfg.get('themes') or {}).items():          # thèmes enregistrés (les deux d'origine peuvent avoir été modifiés)
                if isinstance(p_, dict):
                    self.themes[n_] = {k: p_.get(k, DEFAULT_COLORS[k]) for k in DEFAULT_COLORS}
            self.theme = self.cfg.get('theme') if self.cfg.get('theme') in self.themes else DEFAULT_THEME
            self.colors = dict(self.themes[self.theme])
            self.units = []
            self.udict = {}
            self.factions = dict(DEFAULT_FACTIONS)
            self.maps = list(BUILTIN_MAPS)
            self.all_maps = list(BUILTIN_MAPS)
            self.avail = None
            self.map_dirs = {}
            self.map_info = {}
            self.climates = {}
            self.weather_values = list(WEATHERS)
            self.sc = Scenario()
            self.sel = None
            self._loading = False
            self._preview_job = None
            self._lib_sort = (None, False)
            self._unit_sort = (None, False)
            self.preset_ref = None
            self.cur_map_label = None
            self._build()
            self.apply_colors()
            self.new_scenario(initial=True)
            sync_i18n_vars()
            self.after(150, self.auto_load)

        # ---------------------------------------------------------------- construction
        def _build(self):
            top = ttk.Frame(self, padding=6)
            top.pack(fill='x')
            ttk.Label(top, text='Dossier « data » du mod :', style='Title.TLabel').pack(side='left')
            self.v_data = tk.StringVar(value=self.data_dir)
            ttk.Entry(top, textvariable=self.v_data, width=70).pack(side='left', padx=4)
            ttk.Button(top, text='Parcourir…', command=self.pick_data).pack(side='left')
            ttk.Button(top, text='Couleurs', command=self.open_colors).pack(side='right')
            mb = ttk.Menubutton(top, text='Langue')
            mb.pack(side='right', padx=4)
            lm = tk.Menu(mb, tearoff=0)
            self.v_lang = tk.StringVar(value=LANG)
            lm.add_radiobutton(label='Français', variable=self.v_lang, value='fr', command=lambda: self.on_language('fr'))
            lm.add_radiobutton(label='English', variable=self.v_lang, value='en', command=lambda: self.on_language('en'))
            mb['menu'] = lm
            self.lbl_status = ttk.Label(top, text='', foreground='#555')
            self.lbl_status.pack(side='left', padx=10)

            bar = ttk.Frame(self, padding=(6, 0, 6, 6))
            bar.pack(fill='x')
            _bn = ttk.Button(bar, text='Nouveau', command=self.new_scenario)
            _bn.pack(side='left')
            Tooltip(_bn, 'Remettre à zéro tous les paramètres')
            _bi = ttk.Button(bar, text='Importer un scénario', command=self.import_battle)
            _bi.pack(side='left', padx=2)
            Tooltip(_bi, 'Ouvrir un descr_battle.txt')
            ttk.Button(bar, text='Scénario aléatoire…', command=self.random_scenario).pack(side='left', padx=(12, 2))
            ttk.Button(bar, text='▶  GÉNÉRER LE SCÉNARIO', command=self.generate).pack(side='right')
            self.v_solo = tk.BooleanVar(value=False)
            _cs = ttk.Checkbutton(bar, text='Scénario solo', variable=self.v_solo, command=self.on_solo_toggle)
            _cs.pack(side='right', padx=6)
            Tooltip(_cs, "Le scénario est écrit pour le mode solo (singleplayer) : toutes les armées peuvent être contrôlées par le "
                         "joueur. L'expérience des unités peut aller jusqu'au niveau 9 (limitée à 3 en multijoueur).")
            self.lbl_limit = ttk.Label(bar, text='', style='Title.TLabel')
            self.lbl_limit.pack(side='right', padx=6)

            pw = ttk.PanedWindow(self, orient='horizontal')
            pw.pack(fill='both', expand=True, padx=6, pady=(0, 6))
            left = ttk.Frame(pw, width=430)
            mid = ttk.Frame(pw, width=500)
            right = ttk.Frame(pw, width=420)
            for fr in (left, mid, right):
                fr.pack_propagate(False)
            pw.add(left, weight=0)
            pw.add(mid, weight=1)
            pw.add(right, weight=1)
            self._build_left(left)
            self._build_mid(mid)
            self._build_right(right)
            def lock_all(w):
                for ch in w.winfo_children():
                    if ch.winfo_class() == 'Treeview':
                        lock_columns(ch)
                    lock_all(ch)
            lock_all(self)
            self.minsize(1120, 560)
            MINW = (400, 480, 400)

            def clamp_h(_e=None):
                try:
                    W = pw.winfo_width()
                    if W < sum(MINW) + 10:
                        return
                    a, b = pw.sashpos(0), pw.sashpos(1)
                    a2 = max(MINW[0], min(a, W - MINW[1] - MINW[2]))
                    b2 = max(a2 + MINW[1], min(b, W - MINW[2]))
                    if a2 != a:
                        pw.sashpos(0, a2)
                    if b2 != b:
                        pw.sashpos(1, b2)
                except tk.TclError:
                    pass
            pw.bind('<B1-Motion>', lambda e: self.after_idle(clamp_h), add='+')
            pw.bind('<ButtonRelease-1>', clamp_h, add='+')
            pw.bind('<Configure>', lambda e: self.after_idle(clamp_h), add='+')

        def _build_left(self, p):
            vpw = ttk.PanedWindow(p, orient='vertical')       # séparateur déplaçable : la liste des armées peut descendre
            vpw.pack(fill='both', expand=True)
            f = ttk.LabelFrame(vpw, text='Scénario', padding=6)
            vpw.add(f, weight=0)
            self.v_name = tk.StringVar()
            self.v_map = tk.StringVar()
            self.v_mx = tk.StringVar()
            self.v_my = tk.StringVar()
            self.v_hour = tk.StringVar()
            self.v_hour.trace_add('write', lambda *a: self.on_hour_edit())
            self.v_p2 = tk.StringVar()
            self.v_weather = tk.StringVar()
            self.v_year = tk.StringVar()
            self.v_season = tk.StringVar()
            self.v_gap = tk.StringVar()
            self.v_depth = tk.StringVar()
            self.v_awidth = tk.StringVar()
            self.v_tpl = tk.StringVar(value='')      # vide : aucun map.wfc (sauf carte à dossier)
            self.v_aux = tk.BooleanVar(value=False)
            self.v_tod = tk.StringVar()
            self.v_snap = tk.StringVar(value='')
            self.v_loading = tk.StringVar(value='')
            self.import_mode = False
            self.v_siege = tk.BooleanVar(value=False)
            self.v_stype = tk.StringVar(value='Castle')
            self.v_scult = tk.StringVar(value='Humans')
            self.v_sdlev = tk.StringVar(value='3')
            self.v_sdist = tk.StringVar(value='')
            self.v_same = tk.BooleanVar(value=False)
            self.force_no_wfc = False
            self.campaign = CampaignMap()
            self.all_maps = []
            self.cb_weather = ttk.Combobox(f, textvariable=self.v_weather, values=self.weather_values, width=24)
            self.v_chaos = tk.BooleanVar(value=False)
            rows = [
                ('Nom (dossier)', None),
                ('Carte', None),
                ('Coordonnées X / Y', None),
                ('Heure', None),
                ('Limite de Temps', ttk.Spinbox(f, from_=0, to=999, increment=0.5, textvariable=self.v_p2, width=8)),
                ('Météo', self.cb_weather),
                ('Climats chaotiques', ttk.Checkbutton(f, text='', variable=self.v_chaos, command=self.update_weather_choices)),
                ('Date (année / saison)', None),
                ('Spawn', None),
                ('Same spawn', None),
                ('Distance siège (m)', None),
                ('Unités auxiliaires', ttk.Checkbutton(f, text='', variable=self.v_aux)),
                ('Carte Perso', None),
                ('Snapshot', None),
                ('Loading Screen', None),
            ]
            for r, (lab, w) in enumerate(rows):
                _lb = ttk.Label(f, text=lab)
                _lb.grid(row=r, column=0, sticky='w', pady=1)
                if lab == 'Climats chaotiques':
                    Tooltip(_lb, 'Toutes les saisons et météos peuvent être choisies')
                    Tooltip(w, 'Toutes les saisons et météos peuvent être choisies')
                if lab == 'Limite de Temps':
                    Tooltip(_lb, '0.0=Temps illimité')
                    Tooltip(w, '0.0=Temps illimité')
                if lab.startswith('Distance'):
                    self.lbl_dist_row = _lb
                if lab.startswith('Nom'):
                    sub = ttk.Frame(f)
                    sub.grid(row=r, column=1, sticky='ew', pady=1)
                    ttk.Entry(sub, textvariable=self.v_name, width=14).pack(side='left', fill='x', expand=True)
                    bdesc = ttk.Button(sub, text='Description', width=11, command=self.edit_description)
                    bdesc.pack(side='left', padx=(4, 0))
                    Tooltip(bdesc, 'Ajouter une description')
                elif lab == 'Carte':
                    sub = ttk.Frame(f)
                    sub.grid(row=r, column=1, sticky='ew', pady=1)
                    self.cb_map = ttk.Combobox(sub, textvariable=self.v_map, state='readonly', width=22)
                    self.cb_map.pack(side='left', fill='x', expand=True)
                    self.cb_map.bind('<<ComboboxSelected>>', self.on_map)
                elif lab.startswith('Heure'):
                    sub = ttk.Frame(f)
                    sub.grid(row=r, column=1, sticky='w')
                    ttk.Spinbox(sub, from_=0, to=24, increment=0.5, wrap=True, textvariable=self.v_hour, width=5).pack(side='left')
                    cbt = ttk.Combobox(sub, textvariable=self.v_tod, values=[t for t, _ in TIMES_OF_DAY], state='readonly', width=16)
                    cbt.pack(side='left', padx=4)
                    cbt.bind('<<ComboboxSelected>>', self.on_tod)
                elif lab.startswith('Coordonn'):
                    sub = ttk.Frame(f)
                    sub.grid(row=r, column=1, sticky='w')
                    self.sp_mx = ttk.Spinbox(sub, from_=0, to=CAMPAIGN_SIZE[0] - 1, textvariable=self.v_mx, width=6)
                    self.sp_mx.pack(side='left')
                    self.sp_my = ttk.Spinbox(sub, from_=0, to=CAMPAIGN_SIZE[1] - 1, textvariable=self.v_my, width=6)
                    self.sp_my.pack(side='left', padx=4)
                    self.b_pickmap = ttk.Button(sub, text='Carte…', width=7, command=self.pick_on_map)
                    self.b_pickmap.pack(side='left')
                    Tooltip(self.b_pickmap, 'Choisir les coordonnées sur la carte')
                    for v in (self.v_mx, self.v_my):
                        v.trace_add('write', lambda *a: self.on_xy_change())
                elif lab == 'Spawn':
                    sub = ttk.Frame(f)
                    sub.grid(row=r, column=1, sticky='w')
                    self.lbl_spawn_row, self.sub_spawn, self.spawn_row = _lb, sub, r
                    Tooltip(_lb, 'Taille / Hauteur / Largeur')
                    self.sp_gap = ttk.Spinbox(sub, from_=40, to=800, increment=10, textvariable=self.v_gap, width=5)
                    self.sp_gap.pack(side='left')
                    self.sp_depth = ttk.Spinbox(sub, from_=80, to=500, increment=10, textvariable=self.v_depth, width=5)
                    self.sp_depth.pack(side='left', padx=4)
                    self.sp_awidth = ttk.Spinbox(sub, from_=200, to=1500, increment=25, textvariable=self.v_awidth, width=6)
                    self.sp_awidth.pack(side='left')
                    for _w3 in (self.sp_gap, self.sp_depth, self.sp_awidth):
                        Tooltip(_w3, 'Taille / Hauteur / Largeur')
                    bopt = ttk.Button(sub, text='Optimiser', width=9, command=self.optimize_spawns)
                    bopt.pack(side='left', padx=(6, 0))
                    Tooltip(bopt, 'Optimiser les spawn (redimensionne automatiquement Taille / Hauteur / Largeur)')
                elif lab == 'Same spawn':
                    csame = ttk.Checkbutton(f, text='', variable=self.v_same)
                    csame.grid(row=r, column=1, sticky='w', pady=1)
                    Tooltip(csame, "Désactivé : chaque armée a sa propre zone. Activé : toutes les armées d'une même équipe "
                                   "partagent une seule zone (taille ajustée aux armées).")
                elif lab.startswith('Distance'):
                    self.sub_dist = ttk.Frame(f)
                    self.sub_dist.grid(row=r, column=1, sticky='w')
                    self.sp_dist = ttk.Spinbox(self.sub_dist, values=list(range(20, 701, 10)), textvariable=self.v_sdist, width=6)
                    self.sp_dist.pack(side='left')
                    self.lbl_sauto = ttk.Label(self.sub_dist, text='', foreground='#555')
                    self.lbl_sauto.pack(side='left', padx=4)
                elif lab == 'Carte Perso':
                    Tooltip(_lb, 'Optionnel : map.wfc (vide=world map)')
                    sub = ttk.Frame(f)
                    sub.grid(row=r, column=1, sticky='ew')
                    self.e_tpl = ttk.Entry(sub, textvariable=self.v_tpl)
                    self.e_tpl.pack(side='left', fill='x', expand=True)
                    self.b_tpl = ttk.Button(sub, text='…', width=3, command=self.pick_template)
                    self.b_tpl.pack(side='left', padx=2)
                    self.v_tpl.trace_add('write', lambda *a: self.update_tpl_state())
                    for w_ in (self.e_tpl, self.b_tpl):
                        Tooltip(w_, 'Optionnel : map.wfc (vide=world map)')
                elif lab.startswith('Snapshot'):
                    Tooltip(_lb, 'Optionnel : snapshot.tga (vide=image du mod)')
                    sub = ttk.Frame(f)
                    sub.grid(row=r, column=1, sticky='ew')
                    _e1 = ttk.Entry(sub, textvariable=self.v_snap)
                    _e1.pack(side='left', fill='x', expand=True)
                    Tooltip(_e1, 'Optionnel : snapshot.tga (vide=image du mod)')
                    _b1 = ttk.Button(sub, text='…', width=3, command=self.pick_snapshot)
                    _b1.pack(side='left', padx=2)
                    Tooltip(_b1, 'Optionnel : snapshot.tga (vide=image du mod)')
                elif lab.startswith('Loading'):
                    Tooltip(_lb, 'Optionnel : loading_screen.tga (vide=image du mod)')
                    sub = ttk.Frame(f)
                    sub.grid(row=r, column=1, sticky='ew')
                    _e2 = ttk.Entry(sub, textvariable=self.v_loading)
                    _e2.pack(side='left', fill='x', expand=True)
                    Tooltip(_e2, 'Optionnel : loading_screen.tga (vide=image du mod)')
                    _b2 = ttk.Button(sub, text='…', width=3, command=self.pick_loading)
                    _b2.pack(side='left', padx=2)
                    Tooltip(_b2, 'Optionnel : loading_screen.tga (vide=image du mod)')
                elif lab.startswith('Date'):
                    sub = ttk.Frame(f)
                    sub.grid(row=r, column=1, sticky='w')
                    ttk.Spinbox(sub, from_=1, to=3000, textvariable=self.v_year, width=7).pack(side='left')
                    self.cb_season = ttk.Combobox(sub, textvariable=self.v_season, values=SEASONS, width=8)
                    self.cb_season.pack(side='left', padx=4)
                    self.cb_season.bind('<<ComboboxSelected>>', lambda e: self.update_weather_choices())
                else:
                    w.grid(row=r, column=1, sticky='w' if not isinstance(w, ttk.Entry) else 'ew', pady=1)
            self.lbl_preset = ttk.Label(f, text='', foreground='#d00000')
            self.lbl_preset.grid(row=len(rows), column=0, columnspan=2, sticky='w')
            self.lbl_preset.grid_remove()
            f.columnconfigure(1, weight=1)
            for v in (self.v_gap, self.v_depth, self.v_awidth):
                v.trace_add('write', lambda *a: self.schedule_preview())
            self.v_aux.trace_add('write', lambda *a: self.on_aux_toggle())

            lnb = ttk.Notebook(vpw)
            vpw.add(lnb, weight=1)
            sg = ttk.Frame(lnb, padding=6)
            g = ttk.Frame(lnb, padding=6)
            lnb.add(g, text='Armées du scénario')
            lnb.add(sg, text='Siège')
            ttk.Checkbutton(sg, text='Mode siège', variable=self.v_siege,
                            command=self.on_siege_toggle).pack(anchor='w')
            self.siege_opts = ttk.Frame(sg)
            so = self.siege_opts
            ttk.Label(so, text='Settlement').grid(row=0, column=0, sticky='w', pady=2)
            self.cb_stype = ttk.Combobox(so, textvariable=self.v_stype, state='readonly', width=16,
                                         values=[t[0] for t in SETTLEMENTS if t[3] > 0])
            self.cb_stype.grid(row=0, column=1, columnspan=2, sticky='w', pady=2)
            ttk.Label(so, text='Défense').grid(row=0, column=3, sticky='e', padx=(8, 2))
            self.sp_dlev = ttk.Spinbox(so, from_=1, to=3, textvariable=self.v_sdlev, width=4)
            self.sp_dlev.grid(row=0, column=4, sticky='w')
            ttk.Label(so, text='Culture').grid(row=1, column=0, sticky='w', pady=2)
            self.cb_scult = ttk.Combobox(so, textvariable=self.v_scult, state='readonly', width=20,
                                         values=[c[0] for c in CULTURES])
            self.cb_scult.grid(row=1, column=1, columnspan=3, sticky='w')
            self.lbl_savail = ttk.Label(so, text='')          # non affiché
            for v in (self.v_stype, self.v_scult, self.v_sdlev, self.v_same, self.v_sdist):
                v.trace_add('write', lambda *a: (self.update_siege_auto(), self.schedule_preview()))
            cols = ('faction', 'ctrl', 'team', 'n', 'cost')
            self.t_armies = ttk.Treeview(g, columns=cols, show='headings', selectmode='browse', height=22)
            for c, t, w in (('faction', 'Faction', 150), ('ctrl', 'Contrôle', 65), ('team', 'Équipe \u25bc', 88),
                            ('n', 'Unités', 50), ('cost', 'Coût', 70)):
                self.t_armies.heading(c, text=t, anchor='w' if c == 'team' else 'center')
                self.t_armies.column(c, width=w, anchor='w' if c == 'faction' else 'center')
            for c in cols:
                self.t_armies.column(c, stretch=(c == 'faction'))     # seule « Faction » s'élargit : la position des autres est fixe

            self.lbl_team_warn = ttk.Label(g, text='', foreground='#b03a00', wraplength=380, justify='left')
            b = ttk.Frame(g)
            b.pack(side='bottom', fill='x', pady=(6, 0))
            self._btn_row = b
            self.btn_add = ttk.Button(b, text='+ Ajouter une armée', command=self.add_army)
            self.btn_add.pack(side='left')
            ttk.Button(b, text='− Supprimer', command=self.del_army).pack(side='left', padx=4)
            sba = ttk.Scrollbar(g, orient='vertical', command=self.t_armies.yview)
            self.t_armies.configure(yscrollcommand=sba.set)
            sba.pack(side='right', fill='y')
            self.t_armies.pack(side='left', fill='both', expand=True)
            self.t_armies.configure(style='Plain.Treeview')          # entêtes sans surbrillance
            self.t_armies.bind('<<TreeviewSelect>>', self.on_army_select)

            def _army_click(e):          # un clic sélectionne toujours la ligne visée (pas seulement le cadre de focus)
                if self.t_armies.identify_region(e.x, e.y) in ('cell', 'tree'):
                    iid = self.t_armies.identify_row(e.y)
                    if iid and self.t_armies.selection() != (iid,):
                        self.t_armies.selection_set(iid)
                        self.t_armies.focus(iid)
            self.t_armies.bind('<ButtonRelease-1>', _army_click, add='+')

            self._sash_user = False

            def fit_sash(_e=None):          # le tableau des armées prend tout l'espace libre sous « Scénario »
                if self._sash_user:
                    return
                try:
                    vpw.sashpos(0, f.winfo_reqheight() + 6)
                except tk.TclError:
                    pass

            def sash_click(e):
                if 'sash' in str(vpw.identify(e.x, e.y)):
                    self._sash_user = True
            def clamp_v(_e=None):           # ni le bloc « Scénario » ni le tableau des armées ne peuvent disparaître
                try:
                    H = vpw.winfo_height()
                    if H < 400:
                        return
                    pos = vpw.sashpos(0)
                    pos2 = max(min(f.winfo_reqheight() - 40, 300), min(pos, H - 170))
                    if pos2 != pos:
                        vpw.sashpos(0, pos2)
                except tk.TclError:
                    pass
            vpw.bind('<B1-Motion>', lambda e: self.after_idle(clamp_v), add='+')
            vpw.bind('<ButtonRelease-1>', clamp_v, add='+')
            vpw.bind('<Configure>', fit_sash, add='+')
            vpw.bind('<ButtonPress-1>', sash_click, add='+')
            self.after(300, fit_sash)

        def _build_mid(self, p):
            f = ttk.LabelFrame(p, text='Armée sélectionnée', padding=6)
            f.pack(fill='x')
            self.v_faction = tk.StringVar()
            self.v_ctrl = tk.StringVar()
            self.v_team = tk.StringVar()
            self.v_role = tk.StringVar()
            self.v_gen = tk.StringVar()
            ttk.Label(f, text='Faction').grid(row=0, column=0, sticky='w')
            self.cb_faction = ttk.Combobox(f, textvariable=self.v_faction, state='readonly', width=28)
            self.cb_faction.grid(row=0, column=1, columnspan=3, sticky='ew', pady=2)
            self.cb_faction.bind('<<ComboboxSelected>>', self.on_army_edit)
            ttk.Label(f, text='Contrôle').grid(row=1, column=0, sticky='w')
            cb = ttk.Combobox(f, textvariable=self.v_ctrl, state='readonly', values=['Joueur', 'IA'], width=10)
            cb.grid(row=1, column=1, sticky='w', pady=2)
            cb.bind('<<ComboboxSelected>>', self.on_army_edit)
            tf = ttk.Frame(f)
            tf.grid(row=1, column=2, sticky='e', padx=(10, 2))
            ttk.Label(tf, text='Équipe \u25bc').pack(side='left')
            sp = ttk.Spinbox(f, from_=1, to=8, textvariable=self.v_team, width=4, command=self.on_army_edit)
            sp.grid(row=1, column=3, sticky='w')
            sp.bind('<FocusOut>', self.on_army_edit)
            sp.bind('<Return>', self.on_army_edit)
            ttk.Label(f, text="Rôle de l'équipe").grid(row=2, column=0, sticky='w')
            cb2 = ttk.Combobox(f, textvariable=self.v_role, state='readonly', values=list(ROLES.values()), width=12)
            cb2.grid(row=2, column=1, sticky='w', pady=2)
            cb2.bind('<<ComboboxSelected>>', self.on_army_edit)
            ttk.Label(f, text='(valable pour toute l\'équipe)', foreground='#555').grid(row=2, column=2, columnspan=2, sticky='w', padx=(10, 0))
            ttk.Label(f, text='Nom du général').grid(row=3, column=0, sticky='w')
            e = ttk.Entry(f, textvariable=self.v_gen)
            e.grid(row=3, column=1, columnspan=2, sticky='ew', pady=2)
            e.bind('<FocusOut>', self.on_army_edit)
            e.bind('<Return>', self.on_army_edit)
            self.v_gender = tk.StringVar(value='Homme')
            cbg = ttk.Combobox(f, textvariable=self.v_gender, state='readonly', values=['Homme', 'Femme'], width=8)
            cbg.grid(row=3, column=3, sticky='w', padx=(6, 0), pady=2)
            cbg.bind('<<ComboboxSelected>>', self.on_army_edit)
            self.v_age = tk.StringVar(value='30')
            ttk.Label(f, text='Âge du général').grid(row=4, column=0, sticky='w')
            spa = ttk.Spinbox(f, from_=16, to=127, increment=1, textvariable=self.v_age, width=5, command=self.on_army_edit)
            spa.grid(row=4, column=1, sticky='w', pady=2)
            spa.bind('<FocusOut>', self.on_army_edit)
            spa.bind('<Return>', self.on_army_edit)
            Tooltip(spa, '(16 à 127 ans).')
            f.columnconfigure(3, weight=1)

            self.v_exp = tk.StringVar(value='0')
            self.v_arm = tk.StringVar(value='0')
            self.v_wpn = tk.StringVar(value='0')
            self.v_budget = tk.StringVar(value=str(self.cfg.get('budget', 14000)))
            self.v_maxu = tk.StringVar(value=str(MAX_UNITS))
            self.v_maxs = tk.StringVar(value=str(LIMIT_SOLDIERS))
            self.v_rnd_aux = tk.BooleanVar(value=False)
            self.v_rnd_upg = tk.BooleanVar(value=False)
            self.v_rnd_gold = tk.BooleanVar(value=False)

            # les barres du bas sont empilées en premier pour rester toujours visibles
            self.lbl_total = ttk.Label(p, text='', style='Title.TLabel')
            self.lbl_total.pack(side='bottom', anchor='w', pady=(6, 0))
            rnd = ttk.LabelFrame(p, text='Armée aléatoire (unités de la faction)', padding=6)
            rnd.pack(side='bottom', fill='x', pady=(6, 0))
            r1 = ttk.Frame(rnd)
            r1.pack(fill='x')
            ttk.Label(r1, text='Valeur').pack(side='left')
            int_only(ttk.Spinbox(r1, from_=0, to=GOLD_MAX, increment=500, textvariable=self.v_budget, width=11), self.v_budget, 0).pack(side='left', padx=(2, 10))
            ttk.Label(r1, text='Unités max').pack(side='left')
            int_only(ttk.Spinbox(r1, from_=1, to=MAX_UNITS, textvariable=self.v_maxu, width=4), self.v_maxu, 1).pack(side='left', padx=(2, 10))
            ttk.Label(r1, text='Soldats max').pack(side='left')
            _sm = int_only(ttk.Spinbox(r1, from_=0, to=SOLD_MAX, increment=100, textvariable=self.v_maxs, width=7), self.v_maxs, 0)
            _sm.pack(side='left', padx=(2, 10))
            Tooltip(_sm, 'Large Unit Scale')
            r2 = ttk.Frame(rnd)
            r2.pack(fill='x', pady=(4, 0))
            ttk.Checkbutton(r2, text='Unités auxiliaires', variable=self.v_rnd_aux).pack(side='left')
            ttk.Checkbutton(r2, text='Améliorations', variable=self.v_rnd_upg).pack(side='left', padx=8)
            ttk.Checkbutton(r2, text='Or aléatoire', variable=self.v_rnd_gold).pack(side='left')
            r3 = ttk.Frame(rnd)
            r3.pack(fill='x', pady=(4, 0))
            ttk.Button(r3, text="Générer l'armée", command=self.auto_army).pack(side='left')
            _ba = ttk.Button(r3, text='Générer toutes les armées (même valeur)', command=self.auto_all_armies)
            _ba.pack(side='left', padx=8)
            Tooltip(_ba, "La valeur choisie sera celle de l'équipe")
            h2b = ttk.Frame(p)
            h2b.pack(side='bottom', fill='x', pady=(6, 0))
            ttk.Button(h2b, text='Retirer', command=self.del_units).pack(side='left')
            ttk.Button(h2b, text='Dupliquer', command=self.dup_units).pack(side='left', padx=4)
            ttk.Button(h2b, text='Monter', command=lambda: self.move_units(-1)).pack(side='left')
            ttk.Button(h2b, text='Descendre', command=lambda: self.move_units(1)).pack(side='left', padx=4)
            ttk.Button(h2b, text='Vider', command=self.clear_units).pack(side='left')
            he = ttk.Frame(p)
            he.pack(side='bottom', fill='x', pady=(6, 0))
            self.engine_btns = {}
            for kind in ('ram', 'ladder', 'tower'):
                b_ = ttk.Button(he, text='+ %s' % ENGINE_NAMES[kind], command=lambda k=kind: self.add_engine(k))
                b_.pack(side='left', padx=(0, 4))
                self.engine_btns[kind] = b_
            h = ttk.Frame(p)
            h.pack(side='bottom', fill='x', pady=(6, 0))
            for lab, var, lo, hi, w in (('Expérience', self.v_exp, 0, 3, 3), ('Armure', self.v_arm, 0, 3, 3),
                                        ('Arme', self.v_wpn, 0, MAX_WEAPON, 3)):
                ttk.Label(h, text=lab).pack(side='left', padx=(0, 2))
                spb = ttk.Spinbox(h, from_=lo, to=hi, textvariable=var, width=w)
                spb.pack(side='left', padx=(0, 8))
                if lab == 'Expérience':
                    self.sp_exp = spb
                elif lab == 'Armure':
                    self.sp_arm = spb
                    pass
                elif lab == 'Arme':
                    self.sp_wpn = spb
            ttk.Button(h, text='Appliquer à la sélection', command=self.apply_unit_values).pack(side='left')

            g = ttk.LabelFrame(p, text="Unités de l'armée (la 1re unité = général)", padding=6)
            g.pack(fill='both', expand=True, pady=(8, 0))
            cols = ('n', 'name', 'cat', 'sold', 'exp', 'arm', 'wpn', 'cost')
            self.t_units = ttk.Treeview(g, columns=cols, show='headings', selectmode='extended', height=6)
            for c, t, w in (('n', '#', 28), ('name', 'Unité', 100), ('cat', 'Catégorie', 78), ('sold', 'Soldats', 62), ('exp', 'Expérience', 40),
                            ('arm', 'Armure', 62), ('wpn', 'Arme', 48), ('cost', 'Coût', 52)):
                self.t_units.heading(c, text=t, command=lambda c=c: self.sort_units(c))
                self.t_units.column(c, width=w, anchor='w' if c in ('name', 'cat') else 'center', stretch=(c == 'name'), minwidth=20)
            sb = ttk.Scrollbar(g, orient='vertical', command=self.t_units.yview)
            self.t_units.configure(yscrollcommand=sb.set)
            sb.pack(side='right', fill='y')                 # barre posée en premier : toujours visible, largeur normale
            self.t_units.pack(side='left', fill='both', expand=True)
            HeadingTip(self.t_units, {'sold': 'Large Unit Scale'})
            self.t_units.bind('<<TreeviewSelect>>', self.on_unit_select)
            self.t_units.bind('<Delete>', lambda e: self.del_units())

        def _build_right(self, p):
            nb = ttk.Notebook(p)
            nb.pack(fill='both', expand=True)
            self.nb = nb
            lib = ttk.Frame(nb, padding=4)
            plan = ttk.Frame(nb, padding=4)
            prev = ttk.Frame(nb, padding=4)
            nb.add(lib, text='Unités')
            nb.add(plan, text='Déploiement')
            nb.add(prev, text='Fichier')
            desc = ttk.Frame(nb, padding=4)
            nb.add(desc, text='Description')
            nb.bind('<<NotebookTabChanged>>', self.on_tab)

            fl = ttk.Frame(lib)
            fl.pack(fill='x')
            self.v_search = tk.StringVar()
            self.v_ffilter = tk.StringVar(value='(toutes les factions)')
            self.v_cat = tk.StringVar(value='(toutes)')
            self.v_cls = tk.StringVar(value='(toutes)')
            self.LIB_MODES = ['Armée de base', 'Armée auxiliaire', 'Base + auxiliaire']
            self.v_libmode = tk.StringVar(value=self.LIB_MODES[0])
            fl.columnconfigure(1, weight=1)
            fl.columnconfigure(3, weight=1)
            ttk.Label(fl, text='Rechercher').grid(row=0, column=0, sticky='w', pady=2)
            ttk.Entry(fl, textvariable=self.v_search).grid(row=0, column=1, columnspan=3, sticky='ew', padx=4)
            ttk.Label(fl, text='Faction').grid(row=1, column=0, sticky='w', pady=2)
            self.cb_ff = ttk.Combobox(fl, textvariable=self.v_ffilter, state='readonly')
            self.cb_ff.grid(row=1, column=1, columnspan=3, sticky='ew', padx=4)
            ttk.Label(fl, text='Catégorie').grid(row=2, column=0, sticky='w', pady=2)
            ttk.Combobox(fl, textvariable=self.v_cat, state='readonly', width=12,
                         values=['(toutes)', 'infantry', 'cavalry', 'siege', 'ship']).grid(row=2, column=1, sticky='ew', padx=4)
            ttk.Label(fl, text='Classe').grid(row=2, column=2, sticky='e', padx=(10, 2))
            ttk.Combobox(fl, textvariable=self.v_cls, state='readonly', width=12,
                         values=['(toutes)', 'light', 'heavy', 'missile', 'skirmish', 'spearmen']).grid(row=2, column=3, sticky='ew', padx=4)
            ttk.Label(fl, text='Affichage').grid(row=3, column=0, sticky='w', pady=2)
            ttk.Combobox(fl, textvariable=self.v_libmode, state='readonly', values=self.LIB_MODES).grid(
                row=3, column=1, columnspan=3, sticky='ew', padx=4)
            for v in (self.v_search, self.v_ffilter, self.v_cat, self.v_cls, self.v_libmode):
                v.trace_add('write', lambda *a: self.refresh_library())
            cols = ('aux', 'name', 'type', 'cat', 'cls', 'sold', 'cost')
            self.lbl_lib = ttk.Label(lib, text='')
            self.lbl_lib.pack(side='top', anchor='w')
            self.t_lib = ttk.Treeview(lib, columns=cols, show='headings', selectmode='extended')
            spec = (('aux', 'Auxiliaire', 30, False), ('name', 'Nom', 130, False), ('type', 'Type', 100, False),
                    ('cat', 'Catégorie', 50, False), ('cls', 'Classe', 50, False), ('sold', 'Soldats', 38, True),
                    ('cost', 'Coût', 42, True))
            self.lib_min = {'aux': 30, 'name': 60, 'type': 44, 'cat': 62, 'cls': 46, 'sold': 54, 'cost': 42}
            self.lib_weights = {'aux': 1, 'name': 14, 'type': 9, 'cat': 7, 'cls': 5, 'sold': 6, 'cost': 5}
            for c, t, w, num in spec:
                self.t_lib.heading(c, text=t, command=lambda c=c, num=num: self.sort_lib(c, num))
                self.t_lib.column(c, width=w, anchor='center' if c in ('aux', 'cost') else 'w')
            sb = ttk.Scrollbar(lib, orient='vertical', command=self.t_lib.yview)
            self.t_lib.configure(yscrollcommand=sb.set)
            sb.pack(side='right', fill='y', pady=4)
            self.t_lib.pack(side='left', fill='both', expand=True, pady=4)
            HeadingTip(self.t_lib, {'sold': 'Large Unit Scale'})
            self.t_lib.bind('<Configure>', self.fit_lib_columns, add='+')
            self.t_lib.bind('<Double-1>', lambda e: self.add_from_library())
            self.t_lib.bind('<Return>', lambda e: self.add_from_library())
            lb = ttk.Frame(p)
            lb.pack(fill='x', pady=4)
            ttk.Button(lb, text="⇦ Ajouter à l'armée sélectionnée", command=self.add_from_library).pack(side='left')

            self.canvas = tk.Canvas(plan, background='#f4f1e8', highlightthickness=0)
            self.canvas.pack(fill='both', expand=True)
            self.canvas.bind('<Configure>', lambda e: self.draw_plan())
            self.lbl_warn = ttk.Label(plan, text='', foreground='#a04000', wraplength=520, justify='left')
            self.lbl_warn.pack(fill='x')

            self.build_desc_tab(desc)
            tb = ttk.Frame(prev)
            tb.pack(fill='x')
            ttk.Button(tb, text='Actualiser', command=self.refresh_text).pack(side='left')
            self.txt = tk.Text(prev, wrap='none', font=('Consolas', 9))
            ys = ttk.Scrollbar(prev, orient='vertical', command=self.txt.yview)
            xs = ttk.Scrollbar(prev, orient='horizontal', command=self.txt.xview)
            self.txt.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
            xs.pack(side='bottom', fill='x')
            ys.pack(side='right', fill='y')
            self.txt.pack(fill='both', expand=True)

        # ---------------------------------------------------------------- chargement des données
        def pick_data(self):
            d = filedialog.askdirectory(title='Choisir le dossier « data » du mod (celui qui contient export_descr_unit.txt)')
            if d:
                self.v_data.set(d)
                self.auto_load()

        def pick_template(self):
            f = filedialog.askopenfilename(initialdir=os.path.join(self.v_data.get() or '', 'world', 'maps'),
                                           title='Fichier map.wfc', filetypes=[('map.wfc', '*.wfc'), ('Tous', '*.*')])
            if f:
                self.v_tpl.set(f)

        def resolve_data_dir(self, d):
            d = d.strip().strip('"')
            if not d:
                return ''
            if os.path.isfile(os.path.join(d, 'export_descr_unit.txt')):
                return d
            if os.path.isfile(os.path.join(d, 'data', 'export_descr_unit.txt')):
                return os.path.join(d, 'data')
            return d

        def auto_load(self):
            d = self.resolve_data_dir(self.v_data.get())
            if not d:
                for cand in (os.getcwd(), os.path.join(os.getcwd(), 'data'), here, os.path.join(here, 'data')):
                    c = self.resolve_data_dir(cand)
                    if os.path.isfile(os.path.join(c, 'export_descr_unit.txt')):
                        d = c
                        break
            if not d or not os.path.isfile(os.path.join(d, 'export_descr_unit.txt')):
                self.lbl_status.config(text="⚠ Choisissez le dossier « data » du mod.")
                return
            self.v_data.set(d)
            self.data_dir = d
            self.cfg['data_dir'] = d
            self._save_cfg()
            text_dir = os.path.join(d, 'text')
            self.load_files(os.path.join(d, 'export_descr_unit.txt'),
                            find_first(os.path.join(text_dir, 'expanded.txt'), os.path.join(d, 'expanded.txt')),
                            find_first(os.path.join(text_dir, 'export_units.txt'), os.path.join(d, 'export_units.txt')))
            self.map_dirs = {}
            self.map_info = {}
            self.all_maps = list(BUILTIN_MAPS) + scan_maps(d, self.map_dirs, self.map_info)
            self.rebuild_maps()
            self.sync_map_label()

        def load_files(self, edu, expanded, export_units):
            try:
                self.units = [u for u in parse_edu(read_text(edu))]
            except OSError as ex:
                messagebox.showerror('Erreur', 'Impossible de lire %s\n%s' % (edu, ex))
                return
            self.factions = dict(DEFAULT_FACTIONS)
            if expanded:
                try:
                    self.factions.update(parse_faction_names(read_text(expanded), DEFAULT_FACTIONS.keys()))
                except OSError:
                    pass
            n_named = 0
            if export_units:
                try:
                    names = parse_dictionary_file(read_text(export_units))
                    for u in self.units:
                        nm = names.get(u.dictionary.lower())
                        if nm:
                            u.name = nm
                            n_named += 1
                except OSError:
                    pass
            self.udict = {}
            for u in self.units:
                self.udict.setdefault(u.type.lower(), u)
            owners = set()
            for u in self.units:
                owners |= {o for o in u.ownership if o != 'all'}
            for o in owners:
                self.factions.setdefault(o, o)
            self.fac_order = sorted((f for f in self.factions if f != 'slave'), key=lambda f: self.factions[f].lower())   # 30 factions jouables
            # unités proposées à chaque faction : règle « era 0 » (base) / reste de la faction (auxiliaires)
            self.avail = Availability(self.units, self.factions)
            # météos valides : weather_db.xml du mod (dossier parent de data)
            self.weather_values = list(EMBEDDED_WEATHER_IDS)
            self.climates = default_climates()
            self.weather_src = 'intégrées au programme'
            if self.data_dir:
                wx = find_weather_db(self.data_dir)
                if wx:
                    try:
                        wtxt = read_text(wx)
                        found = parse_weather_patterns(wtxt)
                        cl = parse_weather_climates(wtxt)
                        if found:
                            self.weather_values = found
                            self.weather_src = wx
                        if cl:
                            self.climates = cl
                    except OSError:
                        pass
            self.cb_weather['values'] = self.weather_values
            disp = [self.fac_label(f) for f in self.fac_order]
            self.cb_faction['values'] = disp
            self.cb_ff['values'] = ['(toutes les factions)'] + disp
            self.lbl_status.config(text='%d unités · %d météos (%s) · %d climats%s' % (
                len(self.units), len(self.weather_values), 'weather_db.xml' if self.weather_src.endswith('.xml') else self.weather_src,
                len({c for se in self.climates.values() for c in se}),
                '' if n_named else '  (noms internes : export_units.txt introuvable)'))
            self.refresh_library()
            self.refresh_armies()
            self.refresh_units()
            self.schedule_preview()

        def fac_label(self, fid):
            return '%s  [%s]' % (self.factions.get(fid, fid), fid)

        def fac_from_label(self, label):
            m = re.search(r'\[([^\]]+)\]\s*$', label)
            return m.group(1) if m else label.strip().lower()

        def _save_cfg(self):
            try:
                with open(cfg_path, 'w', encoding='utf-8') as fh:
                    json.dump(self.cfg, fh, indent=2)
            except OSError:
                pass

        # ---------------------------------------------------------------- scénario <-> widgets
        def new_scenario(self, initial=False):
            if not initial and self.sc.armies and not messagebox.askyesno('Nouveau', 'Abandonner le scénario en cours ?'):
                return
            self.sc = Scenario()
            self.sc.armies = [Army(faction='venice', human=True, team=1), Army(faction='france', human=True, team=2)]
            self.import_mode = False
            self.v_tpl.set('')
            self.sel = 0
            self.preset_ref = None
            self.push_settings()
            self.refresh_armies()
            self.refresh_units()
            self.schedule_preview()

        def push_settings(self):
            sc = self.sc
            self._loading = True
            self.v_name.set(sc.name)
            self.v_mx.set(str(sc.map_x))
            self.v_my.set(str(sc.map_y))
            self.v_hour.set(str(sc.hour))
            self.v_p2.set(str(sc.param2))
            self.v_weather.set(sc.weather)
            self.v_year.set(str(sc.year))
            self.v_season.set(sc.season)
            self.v_gap.set(str(sc.gap))
            self.v_depth.set(str(sc.depth))
            self.v_awidth.set(str(sc.army_width))
            self.v_aux.set(bool(sc.aux))
            self.v_solo.set(bool(getattr(sc, 'solo', False)))
            if hasattr(self, 'sp_exp'):
                self.sp_exp.config(to=self.exp_cap())
            self.v_chaos.set(bool(getattr(sc, 'chaos', False)))
            self.v_tod.set(tod_name(sc.hour))
            self.v_siege.set(bool(sc.siege))
            self.v_stype.set(sc.siege_type)
            self.v_same.set(bool(sc.siege_same))
            self.v_sdist.set(str(sc.siege_dist) if sc.siege_dist else '')
            self.v_scult.set(sc.siege_culture)
            self.v_sdlev.set(str(sc.siege_dlevel))
            self._loading = False
            self.show_siege_opts()
            self.update_center_label()
            self._from_project = True        # scénario chargé : une météo / saison hors climat active les climats chaotiques
            try:
                self.sync_map_label()
            finally:
                self._from_project = False

        def on_aux_toggle(self):
            # l'option du scénario règle l'affichage par défaut de la bibliothèque (modifiable ensuite)
            if hasattr(self, 'v_libmode'):
                self.v_libmode.set(self.LIB_MODES[2] if self.v_aux.get() else self.LIB_MODES[0])
            self.refresh_library()

        def map_text(self, m):
            return '%s  (%d, %d)' % (m[0], m[1], m[2])


        def tpl_active(self):
            return bool(self.v_tpl.get().strip().strip('"'))

        def update_tpl_state(self):
            """Un dossier « Carte Perso » est indiqué : Carte et Coordonnées sont grisées."""
            if not hasattr(self, 'sp_mx'):
                return
            on = not self.tpl_active()
            self.cb_map.config(state='readonly' if on else 'disabled')
            for w_ in (self.sp_mx, self.sp_my, self.b_pickmap):
                w_.config(state='normal' if on else 'disabled')
            if not on:
                self.v_map.set(os.path.basename(os.path.dirname(self.v_tpl.get().strip().strip('"'))) or CUSTOM_LABEL)
            else:
                self.sync_map_label()

        def sync_map_label(self):
            if self.tpl_active():
                self.v_map.set(os.path.basename(os.path.dirname(self.v_tpl.get().strip().strip('"'))) or CUSTOM_LABEL)
                return
            try:
                x, y = int(float(self.v_mx.get())), int(float(self.v_my.get()))
            except ValueError:
                return
            cands = [m for m in self.maps if (m[1], m[2]) == (x, y)]
            if cands:
                m = next((c for c in cands if c[0] == getattr(self, 'cur_map_label', None)), cands[0])
                self.v_map.set(self.map_text(m))
            else:
                self.v_map.set(CUSTOM_LABEL)
            self.update_weather_choices()

        def rebuild_maps(self):
            self.maps = sorted((m for m in getattr(self, 'all_maps', []) if self.map_info.get(m[0], {}).get('location')),
                               key=lambda m: m[0].lower())
            self.cb_map['values'] = [self.map_text(m) for m in self.maps] + [CUSTOM_LABEL]
            self.sync_map_label()

        def update_center_label(self):
            if hasattr(self, 'lbl_center'):
                sc = self.sc
                self.lbl_center.config(text=('centre %d, %d · axe %d°' % (sc.cx, sc.cy, sc.rot)) if (sc.cx or sc.cy or sc.rot) else '')

        def preset_sig(self):
            sc = self.sc
            teams = sorted({a.team for a in sc.armies})
            return (sc.map_x, sc.map_y, round(sc.hour, 2), sc.weather, sc.season, round(sc.param2, 2), bool(sc.siege),
                    sc.siege_type, sc.siege_culture, sc.siege_dlevel, sc.siege_same, sc.siege_dist, sc.ram, sc.ladder, sc.tower,
                    sc.gap, sc.depth, sc.army_width,
                    tuple((a.faction, a.team, a.human) for a in sc.armies), tuple((tm, sc.role_of(tm)) for tm in teams))

        def update_preset_flag(self):
            if not hasattr(self, 'lbl_preset'):
                return
            ref = getattr(self, 'preset_ref', None)
            txt = ''
            if ref and ref[1] != self.preset_sig():
                txt = 'attention paramètres modifiés'
            self.lbl_preset.config(text=txt)
            if txt:
                self.lbl_preset.grid()
            else:
                self.lbl_preset.grid_remove()

        def current_map_info(self):
            try:
                x, y = int(float(self.v_mx.get())), int(float(self.v_my.get()))
            except ValueError:
                return None
            for m in self.maps:
                if (m[1], m[2]) == (x, y):
                    return self.map_info.get(m[0])
            c = self.campaign.climate_at(x, y)       # coordonnées libres : climat lu sur la carte de campagne
            return {'climate': c, 'free': True} if c else None

        def on_xy_change(self, force=False):
            if getattr(self, '_loading', False) and not force:
                return
            try:
                x, y = int(float(self.v_mx.get())), int(float(self.v_my.get()))
            except ValueError:
                return
            self.sync_map_label()

        def pick_snapshot(self):
            f = filedialog.askopenfilename(title='Image .tga du snapshot', filetypes=[('TGA', '*.tga'), ('Tous', '*.*')],
                                           initialdir=os.path.join(self.v_data.get() or '', 'menu', 'battlefield_pics'))
            if f:
                self.v_snap.set(f)

        def pick_on_map(self):
            comp = os.path.join(self.data_dir or '', 'menu', 'map_composite.tga')
            if not os.path.isfile(comp):
                messagebox.showinfo('Carte', "map_composite.tga introuvable dans data\\menu du mod.")
                return
            try:
                w, h, ppm = tga_to_ppm(comp)
            except Exception as ex:   # noqa
                messagebox.showerror('Carte', 'Lecture impossible : %s' % ex)
                return
            top = tk.Toplevel(self)
            top.title('Carte de campagne du mod : cliquez pour choisir le lieu de bataille')
            img = tk.PhotoImage(data=ppm)
            cv = tk.Canvas(top, width=w, height=h, highlightthickness=0)
            cv.pack()
            cv.create_image(0, 0, image=img, anchor='nw')
            cv.image = img
            for name, inf in self.map_info.items():
                if inf.get('location'):
                    px, py = 2 * inf['x'] + 1, h - 2 * inf['y'] - 2
                    cv.create_oval(px - 4, py - 4, px + 4, py + 4, outline='white', fill='#d02020')
            try:                      # étoile : coordonnées actuelles du scénario
                cx_, cy_ = int(float(self.v_mx.get())), int(float(self.v_my.get()))
                px, py = 2 * cx_ + 1, h - 2 * cy_ - 2
                pts = []
                for k in range(10):
                    r_ = 11 if k % 2 == 0 else 4.5
                    ang = math.radians(-90 + 36 * k)
                    pts += [px + r_ * math.cos(ang), py + r_ * math.sin(ang)]
                cv.create_polygon(pts, outline='black', fill='#ffd21f', width=1.5)
            except ValueError:
                pass
            info = ttk.Label(top, text='Étoile : coordonnées actuelles · points rouges : lieux du mod (custom_locations.txt)')
            info.pack(anchor='w', padx=6, pady=3)

            def to_xy(ev):
                return int(ev.x // 2), int((h - 1 - ev.y) // 2)

            def move(ev):
                x, y = to_xy(ev)
                c = self.campaign.climate_at(x, y)
                info.config(text='X %d  Y %d  ·  %s%s' % (x, y, c or '?', '' if self.campaign.is_clear(x, y) else tr('  (terrain non vérifié)')))

            def click(ev):
                x, y = to_xy(ev)
                if self.campaign.inside(x, y):
                    self.v_mx.set(str(x))
                    self.v_my.set(str(y))
                    top.destroy()

            cv.bind('<Motion>', move)
            cv.bind('<Button-1>', click)

        def update_weather_choices(self):
            """Saisons et météos : toutes celles du mod, celles du climat de la carte (custom_locations.txt) en premier."""
            if not hasattr(self, 'cb_season'):
                return
            info = self.current_map_info()
            if getattr(self, '_from_project', False) and not self.v_chaos.get():
                _s0 = self.v_season.get() or 'summer'
                if _s0 not in season_choices(info) or self.v_weather.get() not in weather_choices(self.climates, info, _s0, self.weather_values):
                    if self.v_weather.get() in self.weather_values:
                        self.v_chaos.set(True)
            seasons = season_choices(info, self.v_chaos.get())
            self.cb_season['values'] = seasons
            if self.v_season.get() not in seasons:
                self.v_season.set(seasons[0])
            ws = weather_choices(self.climates, info, self.v_season.get() or 'summer', self.weather_values, self.v_chaos.get())
            self.cb_weather['values'] = ws
            if self.v_weather.get() not in ws:
                fw = (info or {}).get('file_weather', '')
                self.v_weather.set(fw if fw in ws else ('clear' if 'clear' in ws else ws[0]))

        def on_hour_edit(self):
            """Le nombre d'heures change : la période (Nuit, Lever du jour…) suit."""
            try:
                n = tod_name(float(self.v_hour.get().replace(',', '.')))
            except ValueError:
                return
            if hasattr(self, 'v_tod') and self.v_tod.get() != n:
                self.v_tod.set(n)

        def on_tod(self, _e=None):
            for name, hour in TIMES_OF_DAY:
                if name == self.v_tod.get():
                    self.v_hour.set(str(hour))

        def on_map(self, _e=None):
            i = self.cb_map.current()
            self.sc.cx = self.sc.cy = self.sc.rot = 0.0
            self.preset_ref = None
            if 0 <= i < len(self.maps):
                m = self.maps[i]
                self.cur_map_label = m[0]
                self.v_mx.set(str(m[1]))
                self.v_my.set(str(m[2]))
            else:
                self.sync_map_label()
            self.update_center_label()
            self.update_weather_choices()
            self.schedule_preview()

        def edit_description(self):
            top = tk.Toplevel(self)
            top.title('Description du scénario')
            top.transient(self)
            ttk.Label(top, text="Texte ajouté à la fin de la description (mise en page automatique : 33 caractères par ligne) :").pack(anchor='w', padx=8, pady=(8, 2))
            tx = tk.Text(top, width=48, height=8, wrap='word')
            tx.pack(padx=8)
            tx.insert('1.0', self.sc.description)

            def ok():
                self.sc.description = tx.get('1.0', 'end').strip()
                top.destroy()
            ttk.Button(top, text='OK', command=ok).pack(pady=8)

        def optimize_spawns(self):
            self.collect()
            optimize_zones(self.sc, self.udict)
            self.v_gap.set(str(int(self.sc.gap)))
            self.v_depth.set(str(int(self.sc.depth)))
            self.v_awidth.set(str(int(self.sc.army_width)))
            self.schedule_preview()

        def pick_loading(self):
            f = filedialog.askopenfilename(title="Image .tga de l'écran de chargement", filetypes=[('TGA', '*.tga'), ('Tous', '*.*')],
                                           initialdir=os.path.join(self.v_data.get() or '', 'loading_screen'))
            if f:
                self.v_loading.set(f)

        def show_siege_opts(self):
            sg = bool(self.v_siege.get())
            for w_ in (self.sp_gap, self.sp_depth, self.sp_awidth):          # siège : crochets à angles droits, profondeur toujours maximale (seule la distance se règle)
                w_.config(state='disabled' if sg else 'normal')
            if self.v_siege.get():
                self.siege_opts.pack(fill='x', pady=(4, 0))
                self.lbl_spawn_row.grid_remove()
                self.sub_spawn.grid_remove()
                self.lbl_dist_row.grid(row=self.spawn_row, column=0, sticky='w', pady=1)      # la distance remplace le spawn
                self.sub_dist.grid(row=self.spawn_row, column=1, sticky='w')
            else:
                self.siege_opts.pack_forget()
                self.lbl_dist_row.grid_remove()
                self.sub_dist.grid_remove()
                self.lbl_spawn_row.grid(row=self.spawn_row, column=0, sticky='w', pady=1)
                self.sub_spawn.grid(row=self.spawn_row, column=1, sticky='w')
            self.update_siege_auto()


        def update_siege_auto(self):
            if not hasattr(self, 'lbl_sauto'):
                return
            import types
            st = self.v_stype.get()
            cults = settlement_cultures(st)
            self.cb_scult['values'] = cults
            if self.v_scult.get() not in cults:          # ex. « Ancient Civilisations » n'existe pas pour les châteaux
                self.v_scult.set('Humans')
            t = siege_def(types.SimpleNamespace(siege_type=st, siege_culture=self.v_scult.get()))
            mn = siege_min_distance(types.SimpleNamespace(siege_type=st, siege_culture=self.v_scult.get()))
            ns = types.SimpleNamespace(siege_type=st, siege_culture=self.v_scult.get(), siege_dist=0)
            self.sp_dist.config(values=siege_dist_values(ns))      # 0 (auto), puis directement la fourchette utile
            self.lbl_sauto.config(text='Distance : %d à %d m' % (mn, siege_max_distance(ns)))
            mxd = siege_max_distance(ns)
            cur, last = self.v_sdist.get().strip(), getattr(self, '_sd_max', None)
            self._sd_max = mxd
            if cur in ('', '0', 'X') or (last is not None and cur == str(last) and last != mxd):
                self.v_sdist.set(str(mxd))          # par défaut : la distance la plus éloignée
            mx = next((x[3] for x in SETTLEMENTS if x[0] == st), 1)
            self.sp_dlev.config(to=max(1, mx), state='normal' if mx > 1 else 'disabled')
            if mx <= 1:
                self.v_sdlev.set('1')
            if not self._loading and self.v_siege.get():
                self.sync_engines()
                self.refresh_units()
            pk = siege_package(st, self.v_scult.get())
            if not pk:
                msg = 'sans défense'
            elif (st, self.v_scult.get()) in SIEGE_TESTED:
                msg = 'testé'
            elif pk[2] == 'mod':
                msg = 'paquet du mod (non testé)'
            else:
                msg = 'paquet du jeu, nom supposé (non testé)'
            self.lbl_savail.config(text=msg)

        def on_siege_toggle(self):
            self.show_siege_opts()
            if self.v_siege.get():
                self.collect()
                teams = sorted({a.team for a in self.sc.armies})
                if len(teams) == 2:
                    if self.sc.role_of(teams[0]) == self.sc.role_of(teams[1]):
                        self.sc.team_roles[str(teams[0])] = 'defending'
                        self.sc.team_roles[str(teams[1])] = 'attacking'
                    r0, r1 = self.sc.role_of(teams[0]), self.sc.role_of(teams[1])
                    for a in self.sc.armies:
                        a.team = 1 if a.team == teams[0] else 2
                    self.sc.team_roles = {'1': r0, '2': r1}
                    self.refresh_armies()
                else:
                    messagebox.showinfo('Siège', "Le siège demande exactement deux équipes : une « Attaquant », l'autre « Défenseur ». "
                                                 "Réglez les équipes des armées.")
                self.import_mode = False
            self.sync_engines()
            self.refresh_units()
            self.sync_map_label()
            self.schedule_preview()

        def _num(self, var, cast, default, lo=None, hi=None):
            try:
                v = cast(float(var.get().replace(',', '.')))
            except ValueError:
                return default
            if lo is not None:
                v = max(lo, v)
            if hi is not None:
                v = min(hi, v)
            return v

        def collect(self):
            sc = self.sc
            sc.name = self.v_name.get().strip()
            sc.map_x = self._num(self.v_mx, int, sc.map_x, 0)
            sc.map_y = self._num(self.v_my, int, sc.map_y, 0)
            sc.map_label = self.v_map.get()
            sc.hour = self._num(self.v_hour, float, sc.hour, 0, 24)
            sc.param2 = self._num(self.v_p2, float, sc.param2, 0)
            sc.weather = self.v_weather.get().strip() or 'clear'
            sc.year = self._num(self.v_year, int, sc.year, 1)
            sc.season = self.v_season.get().strip() or 'summer'
            sc.gap = self._num(self.v_gap, int, sc.gap, 40, 800)
            sc.depth = self._num(self.v_depth, int, sc.depth, 80, 500)
            sc.army_width = self._num(self.v_awidth, int, sc.army_width, 200, 1500)
            sc.aux = bool(self.v_aux.get())
            sc.solo = bool(self.v_solo.get())
            sc.chaos = bool(self.v_chaos.get())
            sc.siege = bool(self.v_siege.get())
            sc.siege_type = self.v_stype.get() or 'Castle'
            sc.siege_same = bool(self.v_same.get())
            sc.siege_culture = self.v_scult.get() or 'Humans'
            sc.siege_dlevel = int(self._num(self.v_sdlev, int, 1, 1, 3))
            _d = int(self._num(self.v_sdist, int, 0, 0, 1000))
            sc.siege_dist = 0 if _d >= siege_max_distance(types.SimpleNamespace(siege_type=sc.siege_type, siege_culture=sc.siege_culture, siege_dist=0)) else _d
            siege_clamp(sc, self.udict)
            return sc

        # ---------------------------------------------------------------- armées
        def cur_army(self):
            if self.sel is not None and 0 <= self.sel < len(self.sc.armies):
                return self.sc.armies[self.sel]
            return None

        def army_cost(self, a):
            return army_value(a.units, self.udict)

        def refresh_armies(self):
            self.sort_armies()          # armées toujours regroupées par équipe, dans l'ordre numérique
            t = self.t_armies
            t.delete(*t.get_children())
            for i, a in enumerate(self.sc.armies):
                t.insert('', 'end', iid=str(i), values=(self.factions.get(a.faction, a.faction),
                                                        'Joueur' if a.human else 'IA', a.team, len(a.units),
                                                        self.army_cost(a)))
            if self.sel is not None and 0 <= self.sel < len(self.sc.armies):
                t.selection_set(str(self.sel))
            self.btn_add.config(state='disabled' if len(self.sc.armies) >= MAX_ARMIES else 'normal')
            tw_ = team_warning(self.sc)
            self.lbl_team_warn.config(text=tw_)
            if tw_:                          # l'avertissement n'occupe de la place que s'il existe (le tableau des armées prend le reste)
                self.lbl_team_warn.pack(side='bottom', anchor='w', pady=(4, 0), after=self._btn_row)
            else:
                self.lbl_team_warn.pack_forget()
            self.update_limit_label()
            self.load_army_editor()

        def on_army_select(self, _e=None):
            sel = self.t_armies.selection()
            if sel:
                self.sel = int(sel[0])
                self.load_army_editor()
                self.sync_lib_filter()
                self.refresh_units()

        def sync_lib_filter(self):
            a = self.cur_army()
            if a:
                self.v_ffilter.set(self.fac_label(a.faction))

        def load_army_editor(self):
            a = self.cur_army()
            self._loading = True
            if a:
                self.v_faction.set(self.fac_label(a.faction))
                self.v_ctrl.set('Joueur' if a.human else 'IA')
                self.v_team.set(str(a.team))
                self.v_role.set(ROLES[self.sc.role_of(a.team)])
                self.v_gen.set(a.general)
                self.v_gender.set('Femme' if a.gender == 'female' else 'Homme')
                self.v_age.set(str(getattr(a, 'age', 30)))
            else:
                for v in (self.v_faction, self.v_ctrl, self.v_team, self.v_role, self.v_gen):
                    v.set('')
            self._loading = False

        def on_army_edit(self, _e=None):
            if self._loading:
                return
            a = self.cur_army()
            if not a:
                return
            fid = self.fac_from_label(self.v_faction.get())
            if fid and fid != a.faction:
                if any(o is not a and o.faction == fid for o in self.sc.armies):
                    messagebox.showwarning('Faction déjà utilisée', "Cette faction est déjà présente dans le scénario : "
                                           "une même faction ne peut pas être ajoutée deux fois.")
                    self._loading = True
                    self.v_faction.set(self.fac_label(a.faction))
                    self._loading = False
                    return
                a.faction = fid
                self.sync_lib_filter()
            a.human = self.v_ctrl.get() != 'IA'
            try:
                a.team = max(1, min(2 if self.v_siege.get() else 8, int(float(self.v_team.get()))))
            except ValueError:
                pass
            role_label = self.v_role.get()
            for k, v in ROLES.items():
                if v == role_label:
                    changed = self.sc.role_of(a.team) != k
                    self.sc.team_roles[str(a.team)] = k
                    others = sorted({x.team for x in self.sc.armies} - {a.team})
                    if changed and self.v_siege.get() and len(others) == 1:       # siège : l'autre équipe prend le rôle opposé
                        self.sc.team_roles[str(others[0])] = 'defending' if k == 'attacking' else 'attacking'
            a.general = self.v_gen.get().strip()
            a.gender = 'female' if self.v_gender.get() == 'Femme' else 'male'
            try:
                a.age = max(16, min(127, int(float(self.v_age.get()))))
            except ValueError:
                a.age = 30
            self.v_age.set(str(a.age))
            self.sync_engines()
            self.refresh_armies()
            self.refresh_units()
            self.schedule_preview()

        def add_army(self):
            if len(self.sc.armies) >= MAX_ARMIES:
                return
            used = {a.faction for a in self.sc.armies}
            order = [f for f in getattr(self, 'fac_order', list(self.factions)) if f != 'slave']
            fid = next((f for f in order if f not in used), None)
            if not fid:
                messagebox.showinfo('Factions', "Toutes les factions sont déjà dans le scénario (une faction ne peut pas être ajoutée deux fois).")
                return
            n1 = sum(1 for a in self.sc.armies if a.team == 1)
            n2 = sum(1 for a in self.sc.armies if a.team == 2)
            self.sc.armies.append(Army(faction=fid, human=False, team=1 if n1 <= n2 else 2))
            self.sel = len(self.sc.armies) - 1
            self.refresh_armies()
            self.sync_lib_filter()
            self.refresh_units()
            self.schedule_preview()

        def del_army(self):
            if self.sel is None or not self.sc.armies:
                return
            del self.sc.armies[self.sel]
            self.sel = min(self.sel, len(self.sc.armies) - 1) if self.sc.armies else None
            self.refresh_armies()
            self.refresh_units()
            self.schedule_preview()

        # ---------------------------------------------------------------- unités de l'armée
        def refresh_units(self):
            t = self.t_units
            t.delete(*t.get_children())
            a = self.cur_army()
            if a:
                allowed = base = None
                if self.avail:
                    allowed = self.avail.allowed(a.faction, True)
                    base = self.avail.allowed(a.faction, False)
                costs = entry_costs(a.units, self.udict)
                rows = []
                for i, e in enumerate(a.units):
                    u = self.udict.get(e.type.lower())
                    name = ('\u2605 ' if (i == 0 or (u and u.is_general)) else '') + (u.name if u else '? ' + e.type)
                    mark = ''
                    if u and allowed is not None:
                        if e.type.lower() not in allowed:
                            mark = '! '
                        elif e.type.lower() not in base:
                            mark = '(aux) '
                    rows.append((i, (i + 1, mark + name, (u.category if u else ''), e.ls, e.exp, e.armour, e.weapon, costs[i])))
                col, rev = self._unit_sort
                if col:       # tri d'affichage seulement : l'ordre réel de l'armée (1re unité = général) ne change pas
                    k = {'n': 0, 'name': 1, 'cat': 2, 'sold': 3, 'exp': 4, 'arm': 5, 'wpn': 6, 'cost': 7}[col]
                    if col in ('name', 'cat'):
                        rows.sort(key=lambda r: str(r[1][k]).replace('(aux) ', '').replace('! ', '').replace('\u2605 ', '').lower(), reverse=rev)
                    else:
                        rows.sort(key=lambda r: float(r[1][k]), reverse=rev)
                t.tag_configure('over', foreground='#c00000')
                t.tag_configure('gen_m', foreground='#1f5fd6')
                t.tag_configure('gen_f', foreground='#e0409a')
                seen, overs = {}, set()
                for i, e in enumerate(a.units):
                    k = e.type.lower()
                    seen[k] = seen.get(k, 0) + 1
                    u = self.udict.get(k)
                    if u and seen[k] > max(1, u.max_copies):
                        overs.add(i)
                t.tag_configure('engine', foreground='#1a8f2e')
                for i, vals in rows:
                    tg = ['over'] if i in overs else []
                    if i == 0:
                        tg.append('gen_f' if a.gender == 'female' else 'gen_m')
                    t.insert('', 'end', iid=str(i), values=vals, tags=tuple(tg))
                    if a.units[i].engine in ENGINE_NAMES:
                        t.insert('', 'end', iid='e%d' % i, values=('', '    \u21b3 ' + ENGINE_NAMES[a.units[i].engine], '', '', '', '', '', ''),
                                 tags=('engine',))
                over = len(a.units) >= MAX_UNITS
                self.lbl_total.config(text="%d / %d unités%s · coût estimé %d · %d soldats"
                                      % (len(a.units), MAX_UNITS, ' (complet)' if over else '', self.army_cost(a),
                                         sum(e.ls for e in a.units)))
            else:
                self.lbl_total.config(text='')
            self.update_lib_tags()
            self.refresh_armies_row()
            self.update_engine_buttons()

        def sort_units(self, col):
            last, rev = self._unit_sort
            rev = (not rev) if last == col else False
            self._unit_sort = (col, rev)
            keep = self.t_units.selection()
            self.refresh_units()
            try:
                self.t_units.selection_set(keep)
            except tk.TclError:
                pass

        def update_limit_label(self):
            if hasattr(self, 'lbl_limit'):
                self.lbl_limit.config(text=limit_warning(self.sc))

        def gold_ok(self, a):
            """Refuse (message) un changement qui ferait dépasser TEAM_GOLD_MAX or à l'équipe de l'armée."""
            if a is not None and team_gold(self.sc, self.udict, a.team) > TEAM_GOLD_MAX:
                messagebox.showwarning('Limite d\'or', "Le maximum est de %d or par équipe : modification annulée." % TEAM_GOLD_MAX)
                return False
            return True

        def refresh_armies_row(self):
            self.update_limit_label()
            a = self.cur_army()
            if a is not None and self.sel is not None and self.t_armies.exists(str(self.sel)):
                self.t_armies.item(str(self.sel), values=(self.factions.get(a.faction, a.faction),
                                                          'Joueur' if a.human else 'IA', a.team, len(a.units),
                                                          self.army_cost(a)))

        def selected_unit_indices(self):
            return sorted(int(i) for i in self.t_units.selection() if not str(i).startswith('e'))

        def selected_engine_indices(self):
            return sorted(int(str(i)[1:]) for i in self.t_units.selection() if str(i).startswith('e'))

        def siege_attacker(self, a=None):
            """Vrai si l'armée est assaillante dans un scénario de siège (seules ces armées portent des engins)."""
            a = a or self.cur_army()
            if a is None or not self.v_siege.get():
                return False
            roles = siege_roles(self.collect())
            return bool(roles) and a.team == roles[1]

        def update_engine_buttons(self):
            if not hasattr(self, 'engine_btns'):
                return
            on = self.siege_attacker()
            ok = engine_allowed(self.v_stype.get())
            for k, b_ in self.engine_btns.items():
                b_.config(state='normal' if (on and ok.get(k)) else 'disabled')

        def sync_engines(self):
            """Les engins n'existent que pour les armées attaquantes d'un siège (ex. : l'équipe devient défenseuse -> engins retirés)."""
            siege_clamp(self.collect(), self.udict)

        def add_engine(self, kind):
            a = self.cur_army()
            if not a or not self.siege_attacker(a):
                return
            n = sum(1 for e in a.units if e.engine == kind)
            carriers = [i for i in engine_carriers(a, self.udict) if not a.units[i].engine]
            if n >= ENGINE_MAX[kind] or not carriers or sum(1 for e in a.units if e.engine) >= ENGINE_TOTAL_MAX:
                messagebox.showerror('Engin de siège', "Aucune unité d'infanterie de plus de 20 soldats disponible pour porter cet engin.")
                return
            a.units[carriers[0]].engine = kind
            self.refresh_units()
            self.t_units.selection_set('e%d' % carriers[0])
            self.schedule_preview()

        def move_engine(self, d):
            a = self.cur_army()
            idx = self.selected_engine_indices()
            if not a or not idx:
                return
            carriers = sorted(engine_carriers(a, self.udict))
            new_sel = []
            for i in (idx if d < 0 else idx[::-1]):
                pos = [c for c in carriers if (c < i if d < 0 else c > i) and not a.units[c].engine]
                if not pos:
                    new_sel.append(i)
                    continue
                j = pos[-1] if d < 0 else pos[0]
                a.units[j].engine, a.units[i].engine = a.units[i].engine, ''
                new_sel.append(j)
            self.refresh_units()
            self.t_units.selection_set(['e%d' % i for i in new_sel])
            self.schedule_preview()

        def on_unit_select(self, _e=None):
            a = self.cur_army()
            idx = self.selected_unit_indices()
            if a and idx:
                e = a.units[idx[0]]
                self.v_exp.set(str(e.exp))
                self.v_arm.set(str(e.armour))
                self.v_wpn.set(str(e.weapon))
                # armure / arme : maximum réellement disponible pour les unités sélectionnées
                us = [self.udict.get(a.units[i].type.lower()) for i in idx]
                us = [u for u in us if u]
                amax = min([u.max_armour for u in us] or [3])
                wmax = 1 if any(u.wpn_cost > 0 for u in us) else 0
                self.sp_exp.config(to=self.exp_cap())
                self.sp_arm.config(to=amax)
                self.sp_wpn.config(to=wmax)

        def exp_cap(self):
            """Niveau d'expérience maximum : 3 en multijoueur (le jeu refuse davantage), 9 en scénario solo."""
            return MAX_EXP if self.v_solo.get() else 3

        def on_solo_toggle(self):
            cap = self.exp_cap()
            if hasattr(self, 'sp_exp'):
                self.sp_exp.config(to=cap)
            try:
                if int(float(self.v_exp.get())) > cap:
                    self.v_exp.set(str(cap))
            except ValueError:
                pass
            changed = False
            for a_ in self.sc.armies:
                for e_ in a_.units:
                    if e_.exp > cap:
                        e_.exp = cap
                        changed = True
            if changed:
                self.refresh_units()
                self.refresh_armies()
            self.schedule_preview()

        def apply_unit_values(self):
            a = self.cur_army()
            if not a:
                return
            try:
                x = max(0, min(self.exp_cap(), int(float(self.v_exp.get()))))
                ar = max(0, min(3, int(float(self.v_arm.get()))))
                w = max(0, min(MAX_WEAPON, int(float(self.v_wpn.get()))))
            except ValueError:
                return
            before = [UnitEntry(**asdict(e)) for e in a.units]
            for i in self.selected_unit_indices():
                e = a.units[i]
                u = self.udict.get(e.type.lower())
                e.exp = x
                e.armour = min(ar, u.max_armour) if u else ar     # certaines unités n'ont pas d'amélioration d'armure
                e.weapon = min(w, 1 if (u is None or u.wpn_cost > 0) else 0)
            if not self.gold_ok(a):
                a.units[:] = before
            keep = self.t_units.selection()
            self.refresh_units()
            self.t_units.selection_set(keep)
            self.schedule_preview()

        def del_units(self):
            a = self.cur_army()
            if not a:
                return
            for i in self.selected_engine_indices():
                a.units[i].engine = ''
            for i in reversed(self.selected_unit_indices()):
                del a.units[i]
            self.refresh_units()
            self.schedule_preview()

        def clear_units(self):
            a = self.cur_army()
            if a and a.units and messagebox.askyesno('Vider', "Retirer toutes les unités de cette armée ?"):
                a.units.clear()
                self.refresh_units()
                self.schedule_preview()

        def dup_units(self):
            a = self.cur_army()
            if not a:
                return
            before = [UnitEntry(**asdict(e)) for e in a.units]
            for i in reversed(self.selected_unit_indices()):
                if len(a.units) >= MAX_UNITS:
                    messagebox.showinfo('Armée complète', "Une armée contient au maximum %d unités." % MAX_UNITS)
                    break
                a.units.insert(i + 1, UnitEntry(**asdict(a.units[i])))
                a.units[i + 1].engine = ''
            if not self.gold_ok(a):
                a.units[:] = before
            self.refresh_units()
            self.schedule_preview()

        def move_units(self, d):
            a = self.cur_army()
            idx = self.selected_unit_indices()
            if a and not idx and self.selected_engine_indices():
                self.move_engine(d)
                return
            if not a or not idx:
                return
            if d < 0 and idx[0] == 0 or d > 0 and idx[-1] == len(a.units) - 1:
                return
            order = idx if d < 0 else idx[::-1]
            for i in order:
                a.units[i], a.units[i + d] = a.units[i + d], a.units[i]
            self.refresh_units()
            self.t_units.selection_set([str(i + d) for i in idx])
            self.schedule_preview()

        def new_entry(self, u):
            return UnitEntry(u.type, u.soldiers, 0, 0, 0)       # expérience 0 par défaut

        def add_from_library(self):
            a = self.cur_army()
            if not a:
                messagebox.showinfo('Aucune armée', "Sélectionnez ou ajoutez d'abord une armée.")
                return
            full = False
            before = list(a.units)
            allowed = self.avail.allowed(a.faction, True) if self.avail else None
            refused = []
            for iid in self.t_lib.selection():
                u = self.udict.get(iid.lower())
                if u:
                    if allowed is not None and u.type.lower() not in allowed:
                        refused.append(u.name)          # unité d'une autre faction : interdit (sauf auxiliaires prévues)
                        continue
                    if len(a.units) >= MAX_UNITS:
                        full = True
                        break
                    a.units.append(self.new_entry(u))
                    if self.avail and u.type in {x.type for x in self.avail.aux.get(a.faction, [])} \
                            and u.type not in {x.type for x in self.avail.base.get(a.faction, [])} and not self.v_aux.get():
                        self.v_aux.set(True)      # unité auxiliaire ajoutée : l'option du scénario est activée
            if not self.gold_ok(a):
                a.units[:] = before
            self.refresh_units()
            self.schedule_preview()
            kids = self.t_units.get_children()
            if kids:
                self.t_units.see(kids[-1])
            if full:
                messagebox.showinfo('Armée complète', "Une armée contient au maximum %d unités." % MAX_UNITS)
            if refused:
                messagebox.showwarning('Unité refusée', "Ces unités n'appartiennent pas à la faction %s (ni à ses auxiliaires prévues) "
                                       "et ne peuvent pas être ajoutées :\n%s" % (self.fac_label(a.faction), ', '.join(refused)))

        def build_random_army(self, fid, budget, max_units, use_aux, upgrades, max_soldiers=10 ** 9, need_siege=False):
            """Armée aléatoire de valeur proche de `budget` (jamais au-dessus), général = unité « bon général » tirée, sinon l'une des 3 plus chères hors siège."""
            pool = army_pool(self.avail, self.units, fid, use_aux)
            if not pool:
                return []
            for _ in range(8):
                e, tot = fill_army(pool, self.udict, budget, max_units, upgrades, ARMY_TOLERANCE, need_siege, max_soldiers)
                if e and budget - tot <= ARMY_TOLERANCE:
                    break
            return ensure_general(e, self.udict)

        def random_value(self, factions, lo, hi, max_units, use_aux, upgrades):
            """Valeur d'or aléatoire (entre lo et hi) atteignable par toutes les factions données."""
            los, his = [], []
            for f in factions:
                l, h = army_limits(army_pool(self.avail, self.units, f, use_aux), max_units, upgrades)
                los.append(l)
                his.append(h)
            lo = max([lo, ARMY_FLOOR] + los)
            hi = min([hi, GOLD_MAX] + [int(h * 0.93) for h in his])
            if hi < lo:
                hi = lo
            return int(round(random.randint(lo, hi) / 50.0) * 50)

        def random_team_value(self, factions, teams, vmin, vmax, max_units, use_aux, upgrades, max_soldiers=10 ** 9):
            """Valeur d'équipe aléatoire : chaque armée reçoit valeur / taille de son équipe, dans [vmin, vmax]."""
            sizes = {}
            for t in teams:
                sizes[t] = sizes.get(t, 0) + 1
            lo, hi = max(ARMY_FLOOR, vmin), min(GOLD_MAX, vmax)       # sous 500 or l'équilibrage des armées est impossible
            lo_t, hi_t = 0, TEAM_GOLD_MAX
            cap = max(1, int(max_soldiers // max(1, len(factions))))
            for f, t in zip(factions, teams):
                n = sizes[t]
                l, h = army_limits(army_pool(self.avail, self.units, f, use_aux), max_units, upgrades, cap)
                lo_t = max(lo_t, max(l, lo) * n)
                hi_t = min(hi_t, int(min(h * 0.93, hi)) * n)
            self.value_note = ''
            if hi_t < lo_t:         # minimum demandé hors d'atteinte avec ces factions / options : on prend le maximum possible
                self.value_note = "Valeur minimum trop élevée pour ces options (aucune amélioration / peu d'unités) : réduite."
                lo_t = hi_t
            return int(round(random.randint(lo_t, hi_t) / 50.0) * 50)

        def sort_armies(self):
            """Regroupe les armées par équipe, dans l'ordre numérique (tri stable)."""
            cur = self.cur_army()
            self.sc.armies.sort(key=lambda a: a.team)
            if cur is not None:
                self.sel = next((i for i, a in enumerate(self.sc.armies) if a is cur), self.sel)

        def auto_army(self):
            a = self.cur_army()
            if not a:
                messagebox.showinfo('Aucune armée', "Sélectionnez ou ajoutez d'abord une armée.")
                return
            max_units = int(self._num(self.v_maxu, int, MAX_UNITS, 1, MAX_UNITS))
            if self.v_rnd_gold.get():
                budget = self.random_value([a.faction], ARMY_FLOOR, GOLD_MAX, max_units, self.v_rnd_aux.get(), self.v_rnd_upg.get())
            else:
                budget = int(self._num(self.v_budget, int, 14000, GOLD_MIN, GOLD_MAX))
                others = sum(army_value(o.units, self.udict) for o in self.sc.armies if o.team == a.team and o is not a)
                budget = max(GOLD_MIN, min(budget, TEAM_GOLD_MAX - others))
                self.cfg['budget'] = budget
                self._save_cfg()
            if a.units and not messagebox.askyesno('Remplacer', "Remplacer les unités actuelles de l'armée ?"):
                return
            ms = int(self._num(self.v_maxs, int, LIMIT_SOLDIERS, SOLD_MIN, SOLD_MAX))
            ms = max(100, ms - sum(sum(e.ls for e in o.units) for o in self.sc.armies if o is not a))     # le total du scénario reste sous le maximum
            entries = self.build_random_army(a.faction, budget, max_units, self.v_rnd_aux.get(), self.v_rnd_upg.get(), ms)
            if not entries:
                messagebox.showinfo('Aucune unité', 'Aucune unité disponible pour la faction « %s ».' % a.faction)
                return
            a.units = entries
            a.gender = random.choice(['male', 'female'])
            if self.siege_attacker(a):
                st = self.v_stype.get()
                for _t in range(10):
                    random_engines(a, st, self.udict)
                    if not engine_rule_problems(st, a, self.udict):
                        break
                    e2 = self.build_random_army(a.faction, budget, max_units, self.v_rnd_aux.get(), self.v_rnd_upg.get(), ms)
                    if e2:
                        a.units = e2
                else:
                    random_engines(a, st, self.udict)
                if engine_rule_problems(st, a, self.udict):
                    messagebox.showwarning('Siège', "L'armée attaquante « %s » ne respecte pas la règle des engins de siège "
                                                    "(au moins un engin ; un bélier pour Fortress et Citadel)." % a.faction)
            self.refresh_units()
            self.schedule_preview()
            self.refresh_armies()

        def auto_all_armies(self):
            if len(self.sc.armies) < 1:
                return
            if any(a.units for a in self.sc.armies) and not messagebox.askyesno(
                    'Remplacer', "Remplacer les unités de TOUTES les armées (équipes de même valeur totale) ?"):
                return
            max_units = int(self._num(self.v_maxu, int, MAX_UNITS, 1, MAX_UNITS))
            aux, upg = self.v_rnd_aux.get(), self.v_rnd_upg.get()
            self.sort_armies()
            facs = [a.faction for a in self.sc.armies]
            teams = [a.team for a in self.sc.armies]
            biggest = max(teams.count(t) for t in set(teams))
            if self.v_rnd_gold.get():
                target = self.random_team_value(facs, teams, ARMY_FLOOR, GOLD_MAX, max_units, aux, upg)
            else:
                target = min(TEAM_GOLD_MAX, int(self._num(self.v_budget, int, 14000, GOLD_MIN, GOLD_MAX)))
            pools = [army_pool(self.avail, self.units, f, aux) for f in facs]
            if not all(pools):
                messagebox.showinfo('Aucune unité', "Une faction n'a aucune unité disponible.")
                return
            ms = int(self._num(self.v_maxs, int, LIMIT_SOLDIERS, SOLD_MIN, SOLD_MAX))
            att = [self.siege_attacker(a) for a in self.sc.armies]
            lists, t, ok = build_armies_siege(pools, teams, self.udict, target, max_units, upg, army_floor(target // biggest), att,
                                               self.v_stype.get() if any(att) else '', ms)
            for a, e in zip(self.sc.armies, lists):
                a.units = e
                a.gender = random.choice(['male', 'female'])
            self.refresh_units()
            self.schedule_preview()
            self.refresh_armies()
            tot = {}
            for a in self.sc.armies:
                tot[a.team] = tot.get(a.team, 0) + army_value(a.units, self.udict)
            msg = 'Valeur visée par équipe : %d\nTotaux réels : %s' % (t, ', '.join('équipe %d : %d' % (k, v) for k, v in sorted(tot.items())))
            if not ok:
                msg += "\nLes équipes n'ont pas pu être rapprochées à moins de 100 or (peu d'unités / améliorations disponibles)."
            messagebox.showinfo('Armées générées', msg)

        # ---------------------------------------------------------------- langue et couleurs
        def on_language(self, lang):
            self.collect() if hasattr(self, 'sc') and self.sel is not None else None
            set_language(lang, self)
            self.cfg['lang'] = lang
            self._save_cfg()
            self.v_lang.set(lang)
            for fn in ('refresh_armies', 'refresh_units', 'refresh_library', 'update_siege_auto', 'update_center_label'):
                try:
                    getattr(self, fn)()
                except Exception:           # noqa
                    pass
            self.schedule_preview()

        def apply_colors(self):
            c = self.colors
            bg, fg, field, button, select, accent = (c[k] for k in ('bg', 'fg', 'field', 'button', 'select', 'accent'))
            muted = c['muted']
            st = ttk.Style(self)
            st.configure('.', background=bg, foreground=fg, fieldbackground=field, troughcolor=bg, insertcolor=fg,
                         bordercolor=button, lightcolor=button, darkcolor=button, selectbackground=select, selectforeground='#ffffff')
            st.configure('TButton', background=button, foreground=fg)
            st.map('TButton', background=[('active', select), ('disabled', bg)], foreground=[('active', '#ffffff'), ('disabled', muted)])
            st.configure('TMenubutton', background=button, foreground=fg)
            st.configure('Treeview', background=field, fieldbackground=field, foreground=fg)
            st.map('Treeview', background=[('selected', select)], foreground=[('selected', '#ffffff')])
            st.configure('Treeview.Heading', background=button, foreground=fg)
            st.configure('Plain.Treeview', background=field, fieldbackground=field, foreground=fg)
            st.map('Plain.Treeview', background=[('selected', select)], foreground=[('selected', '#ffffff')])
            st.configure('Plain.Treeview.Heading', background=button, foreground=fg, padding=(2, 4, 2, 4))
            st.map('Plain.Treeview.Heading', background=[('active', button), ('pressed', button)], foreground=[('active', fg), ('pressed', fg)],
                   relief=[('active', 'flat'), ('pressed', 'flat')])
            for w in ('TEntry', 'TCombobox', 'TSpinbox'):
                st.configure(w, fieldbackground=field, foreground=fg, background=button, arrowcolor=fg)
            hov = _blend(button, '#ffffff', 0.12)
            for w in ('TCombobox', 'TSpinbox'):          # flèches : survol = couleur des boutons légèrement plus claire
                edge = field if w == 'TSpinbox' else button          # Spinbox : cases de flèches rectangulaires, sans coins arrondis
                st.configure(w, bordercolor=edge, lightcolor=edge, darkcolor=edge)
                st.map(w, background=[('disabled', bg), ('pressed', hov), ('active', hov)],
                       lightcolor=[('pressed', hov), ('active', hov)], darkcolor=[('pressed', hov), ('active', hov)])
            st.map('TCombobox', fieldbackground=[('readonly', field), ('disabled', bg)], foreground=[('disabled', muted)])
            st.map('TEntry', fieldbackground=[('disabled', bg)])
            st.map('TSpinbox', fieldbackground=[('disabled', bg)])
            st.configure('TScrollbar', background=button, troughcolor=bg, arrowcolor=fg, bordercolor=bg, lightcolor=button, darkcolor=button,
                         gripcount=0)
            for sty in ('TScrollbar', 'Vertical.TScrollbar', 'Horizontal.TScrollbar'):       # survol / clic / inactif : jamais le gris clair du thème
                st.map(sty, background=[('disabled', bg), ('pressed', select), ('active', hov)],
                       lightcolor=[('disabled', bg), ('pressed', select), ('active', hov)],
                       darkcolor=[('disabled', bg), ('pressed', select), ('active', hov)],
                       bordercolor=[('disabled', bg)], troughcolor=[('disabled', bg)], arrowcolor=[('disabled', muted)])
            st.configure('TLabelframe', background=bg)
            st.configure('TNotebook', background=bg, bordercolor=button, lightcolor=button, darkcolor=button)
            st.configure('TNotebook.Tab', background=button, foreground=fg, bordercolor=button, lightcolor=button, darkcolor=button)
            st.map('TNotebook.Tab', background=[('selected', hov)], lightcolor=[('selected', hov)], bordercolor=[('selected', hov)],
                   foreground=[('selected', accent)])
            st.configure('TLabelframe.Label', background=bg, foreground=accent)
            st.configure('Title.TLabel', foreground=accent)
            st.configure('TCheckbutton', background=bg, foreground=fg)
            st.map('TCheckbutton', background=[('active', bg)], foreground=[('disabled', muted)])
            st.configure('TPanedwindow', background=bg)
            self.configure(background=bg)
            for opt, val in (('*TCombobox*Listbox.background', field), ('*TCombobox*Listbox.foreground', fg),
                             ('*TCombobox*Listbox.selectBackground', select), ('*TCombobox*Listbox.selectForeground', '#ffffff'),
                             ('*Toplevel.background', bg), ('*Listbox.background', field), ('*Listbox.foreground', fg),
                             ('*Canvas.background', field), ('*Text.background', field), ('*Text.foreground', fg),
                             ('*Menu.background', button), ('*Menu.foreground', fg)):
                self.option_add(opt, val)

            def walk(w):
                try:
                    cls = w.winfo_class()
                    if cls in ('Canvas', 'Listbox'):
                        w.configure(background=field)
                    elif cls == 'Text':
                        w.configure(background=field, foreground=fg, insertbackground=fg)
                    elif cls == 'Label':        # tk.Label (flèche rouge du tri) : fond de l'en-tête
                        if w.__dict__.get('_hdr'):
                            w.configure(background=button)
                    elif cls == 'TLabel':
                        cur = str(w.cget('foreground'))
                        if cur.lower() in ('#555', '#555555') or w.__dict__.get('_muted'):
                            w.__dict__['_muted'] = True
                            w.configure(foreground=muted)
                except tk.TclError:
                    pass
                for ch in w.winfo_children():
                    walk(ch)
            walk(self)

            def combos(w):                 # listes déroulantes déjà créées : le thème sombre ne s'y applique pas tout seul
                try:
                    if w.winfo_class() == 'TCombobox':
                        lb = '%s.f.l' % self.tk.call('ttk::combobox::PopdownWindow', str(w))
                        self.tk.call(lb, 'configure', '-background', field, '-foreground', fg,
                                     '-selectbackground', select, '-selectforeground', '#ffffff')
                except tk.TclError:
                    pass
                for ch in w.winfo_children():
                    combos(ch)
            combos(self)
            if hasattr(self, 'canvas'):
                self.canvas.configure(bg=field)

        def open_colors(self):
            """Fenêtre « Couleurs » : thèmes prédéfinis et couleur de chaque élément de l'éditeur (appliquée tout de suite)."""
            from tkinter import colorchooser
            win = tk.Toplevel(self)
            win.title(tr('Couleurs de l\'éditeur'))
            win.transient(self)
            f = ttk.Frame(win, padding=10)
            f.pack(fill='both', expand=True)
            ttk.Label(f, text='Thème', style='Title.TLabel').grid(row=0, column=0, sticky='w')
            v_theme = tk.StringVar(value=self.theme)
            cbt = ttk.Combobox(f, textvariable=v_theme, state='readonly', width=18, values=list(self.themes))
            cbt.grid(row=0, column=1, columnspan=2, sticky='w', pady=2)
            swatches = {}

            def paint():
                for k, b in swatches.items():
                    try:
                        b.configure(background=self.colors[k] if not k.startswith('team') else self.team_colors[int(k[4:])])
                    except tk.TclError:
                        pass

            def save():
                self.themes[self.theme] = dict(self.colors)          # une modification ne concerne que le thème courant
                self.cfg['theme'] = self.theme
                self.cfg['themes'] = {n: dict(p) for n, p in self.themes.items()}
                self.cfg['team_colors'] = list(self.team_colors)
                self._save_cfg()

            def pick(k):
                cur = self.colors[k] if not k.startswith('team') else self.team_colors[int(k[4:])]
                res = colorchooser.askcolor(color=cur, parent=win)
                if not res or not res[1]:
                    return
                if k.startswith('team'):
                    self.team_colors[int(k[4:])] = res[1]
                else:
                    self.colors[k] = res[1]
                    self.apply_colors()
                save()
                paint()
                self.schedule_preview()

            def theme(_e=None):
                t = self.themes.get(v_theme.get())
                if t:
                    self.theme = v_theme.get()
                    self.colors = dict(t)
                    self.apply_colors()
                    save()
                    paint()
                    self.schedule_preview()
            cbt.bind('<<ComboboxSelected>>', theme)
            names = [('bg', 'Fond'), ('fg', 'Texte'), ('field', 'Champs de saisie'), ('button', 'Boutons'),
                     ('select', 'Sélection'), ('accent', 'Titres')]
            for r, (k, lab) in enumerate(names, start=1):
                ttk.Label(f, text=lab).grid(row=r, column=0, sticky='w', pady=2)
                b = tk.Button(f, width=8, relief='solid', borderwidth=1, command=lambda k=k: pick(k))
                b.grid(row=r, column=1, sticky='w', padx=6)
                swatches[k] = b
            ttk.Label(f, text='Équipes du plan de déploiement', style='Title.TLabel').grid(row=8, column=0, columnspan=3, sticky='w', pady=(10, 2))
            tf = ttk.Frame(f)
            tf.grid(row=9, column=0, columnspan=3, sticky='w')
            for i in range(8):
                b = tk.Button(tf, width=3, relief='solid', borderwidth=1, command=lambda i=i: pick('team%d' % i))
                b.pack(side='left', padx=2)
                swatches['team%d' % i] = b

            def new_theme():
                from tkinter import simpledialog
                n = simpledialog.askstring(tr('Nouveau thème'), tr('Nom du thème :'), parent=win)
                n = (n or '').strip()
                if not n:
                    return
                while n in self.themes:
                    n += ' 2'
                self.theme = n
                self.themes[n] = dict(self.colors)          # copie du thème courant
                cbt['values'] = list(self.themes)
                v_theme.set(n)
                save()

            def reset():
                self.themes = {n: dict(p) for n, p in COLOR_THEMES.items()}
                self.theme = DEFAULT_THEME
                v_theme.set(DEFAULT_THEME)
                cbt['values'] = list(self.themes)
                self.colors = dict(DEFAULT_COLORS)
                self.team_colors = list(TEAM_COLORS)
                self.apply_colors()
                save()
                paint()
                self.schedule_preview()
            bb = ttk.Frame(f)
            bb.grid(row=10, column=0, columnspan=3, sticky='e', pady=(10, 0))
            ttk.Button(bb, text='Nouveau thème', command=new_theme).pack(side='left', padx=4)
            _br = ttk.Button(bb, text='Réinitialiser', command=reset)
            _br.pack(side='left', padx=4)
            Tooltip(_br, 'Supprimer tous les thèmes')
            ttk.Button(bb, text='Fermer', command=win.destroy).pack(side='left')
            paint()

        def edit_alliances(self, parent=None):
            """Fenêtre d'édition des alliances (Faithful Alliances) : chaque alliance a un nom choisi par l'utilisateur et sa couleur."""
            import tkinter as tk
            import colorsys
            from tkinter import ttk
            win = tk.Toplevel(parent or self)
            win.title('Faithful Alliances')
            win.transient(parent or self)
            win.geometry('800x560')
            groups = [sorted(x['f']) for x in ALLIANCES]
            names = [{'fr': x['fr'], 'en': x['en']} for x in ALLIANCES]
            facs = [f for f in self.fac_order if f != 'slave']
            for g in groups:
                for f in g:
                    if f not in facs:
                        facs.append(f)
            facs.sort(key=lambda f: self.factions.get(f, f).lower())
            sel = {'i': 0}
            vars_ = {f: tk.BooleanVar(value=False) for f in facs}
            bgc = ttk.Style(win).lookup('TFrame', 'background') or win.cget('background')

            def col(i):          # une couleur différente par alliance (teintes réparties selon le nombre d'or)
                h = (i * 0.61803398875) % 1.0
                r, g, b = colorsys.hsv_to_rgb(h, 0.80 if i % 2 == 0 else 0.55, 0.78 if i % 3 else 0.95)
                return '#%02x%02x%02x' % (int(r * 255), int(g * 255), int(b * 255))

            SYMS = ('●', '▲', '◆', '★', '■', '▼', '♣', '♠', '♥', '♦', '✚', '✦', '☀', '☾', '❖', '✖', '✿', '⚑', '☘', '✪', '◗', '⬢', '⬟', '✸')

            def sym(i):          # un symbole propre à chaque alliance (même symbole dans la liste et devant les factions)
                return SYMS[i % len(SYMS)]

            def nm(i):
                d = names[i]
                return d.get(LANG) or d.get('fr') or d.get('en') or tr('(sans nom)')

            left = ttk.Frame(win, padding=6)
            left.pack(side='left', fill='y')
            ttk.Label(left, text='Alliances', style='Title.TLabel').pack(anchor='w')
            lb = tk.Listbox(left, width=34, height=18, exportselection=False, activestyle='none')
            lb.pack(fill='y', expand=True)
            fn = ttk.Frame(left)
            fn.pack(fill='x', pady=(6, 0))
            ttk.Label(fn, text='Nom').pack(side='left')
            v_name = tk.StringVar()
            ent = ttk.Entry(fn, textvariable=v_name, width=28)
            ent.pack(side='left', padx=4, fill='x', expand=True)
            right = ttk.Frame(win, padding=6)
            right.pack(side='left', fill='both', expand=True)
            ttk.Label(right, text="Factions de l'alliance sélectionnée", style='Title.TLabel').pack(anchor='w')
            cv = tk.Canvas(right, highlightthickness=0, bd=0, bg=bgc)
            sb = ttk.Scrollbar(right, orient='vertical', command=cv.yview)
            inner = ttk.Frame(cv)
            inner.bind('<Configure>', lambda e: cv.configure(scrollregion=cv.bbox('all')))
            cv.create_window((0, 0), window=inner, anchor='nw')
            cv.configure(yscrollcommand=sb.set)
            sb.pack(side='right', fill='y')
            cv.pack(side='left', fill='both', expand=True)
            marks = {}

            def wheel(e):
                d = -1 if (getattr(e, 'num', 0) == 4 or getattr(e, 'delta', 0) > 0) else 1
                cv.yview_scroll(d * 2, 'units')
                return 'break'

            def bind_wheel(_e=None):
                win.bind_all('<MouseWheel>', wheel)
                win.bind_all('<Button-4>', wheel)
                win.bind_all('<Button-5>', wheel)

            def unbind_wheel(_e=None):
                for ev in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
                    win.unbind_all(ev)
            right.bind('<Enter>', bind_wheel)
            right.bind('<Leave>', unbind_wheel)
            win.bind('<Destroy>', lambda e: unbind_wheel() if e.widget is win else None)
            loading = {'on': False}

            def refresh_list():
                lb.delete(0, 'end')
                for i in range(len(groups)):
                    lb.insert('end', '%s %s' % (sym(i), nm(i)))
                    lb.itemconfig(i, foreground=col(i), selectforeground='white', selectbackground=col(i))
                if groups:
                    sel['i'] = max(0, min(sel['i'], len(groups) - 1))
                    lb.selection_set(sel['i'])

            def refresh_marks():
                for f, frm in marks.items():
                    for w in frm.winfo_children():
                        w.destroy()
                    for i, g in enumerate(groups):
                        if f in g:
                            tk.Label(frm, text=sym(i), fg=col(i), bg=bgc, bd=0, padx=1, pady=0,
                                     font=('Segoe UI Symbol', 10)).pack(side='left')

            def load_sel(_e=None):
                cur = lb.curselection()
                if cur:
                    sel['i'] = cur[0]
                g = groups[sel['i']] if groups else []
                for f, v in vars_.items():
                    v.set(f in g)
                loading['on'] = True
                v_name.set(nm(sel['i']) if groups and (names[sel['i']].get(LANG) or names[sel['i']].get('fr')
                                                       or names[sel['i']].get('en')) else '')
                loading['on'] = False

            def on_name(*_a):
                if loading['on'] or not groups:
                    return
                i = sel['i']
                names[i][LANG] = v_name.get()
                other = 'en' if LANG == 'fr' else 'fr'
                if not names[i].get(other) or names[i][other] in (tr_lang('Nouvelle alliance', 'fr'), tr_lang('Nouvelle alliance', 'en')):
                    names[i][other] = v_name.get()
                lb.delete(i)
                lb.insert(i, '%s %s' % (sym(i), nm(i)))
                lb.itemconfig(i, foreground=col(i), selectforeground='white', selectbackground=col(i))
                lb.selection_set(i)
            v_name.trace_add('write', on_name)

            def toggle(f):
                if not groups:
                    return
                g = set(groups[sel['i']])
                if vars_[f].get():
                    g.add(f)
                else:
                    g.discard(f)
                if g and any(j != sel['i'] and set(groups[j]) == g for j in range(len(groups))):
                    vars_[f].set(not vars_[f].get())          # composition identique à une autre alliance : refusé
                    messagebox.showwarning('Faithful Alliances', "Une autre alliance a exactement la même composition.", parent=win)
                    return
                groups[sel['i']] = sorted(g)
                refresh_marks()

            for f in facs:
                row = ttk.Frame(inner)
                row.pack(fill='x', anchor='w')
                ttk.Checkbutton(row, text=self.factions.get(f, f), variable=vars_[f], width=26,
                                command=lambda f=f: toggle(f)).pack(side='left')
                m = ttk.Frame(row)                              # symboles des alliances qui contiennent la faction, après son nom
                m.pack(side='left')
                marks[f] = m

            def add():
                groups.append([])
                names.append({'fr': tr_lang('Nouvelle alliance', 'fr'), 'en': tr_lang('Nouvelle alliance', 'en')})
                sel['i'] = len(groups) - 1
                refresh_list()
                load_sel()
                refresh_marks()
                ent.focus_set()
                ent.selection_range(0, 'end')

            def remove():
                if groups:
                    del groups[sel['i']]
                    del names[sel['i']]
                    refresh_list()
                    load_sel()
                    refresh_marks()

            def reset():
                groups[:] = [sorted(x[2]) for x in DEFAULT_ALLIANCES]
                names[:] = [{'fr': x[0], 'en': x[1]} for x in DEFAULT_ALLIANCES]
                sel['i'] = 0
                refresh_list()
                load_sel()
                refresh_marks()

            def ok():
                al = [{'fr': names[i].get('fr', ''), 'en': names[i].get('en', ''), 'f': list(groups[i])} for i in range(len(groups))]
                set_alliances(al)              # les alliances de moins de 2 factions sont conservées mais ignorées au tirage
                self.cfg['faithful_alliances'] = al
                self.cfg['alliances_rev'] = ALLIANCES_REV
                self._save_cfg()
                win.destroy()

            lb.bind('<<ListboxSelect>>', load_sel)
            bb = ttk.Frame(left)
            bb.pack(fill='x', pady=(6, 0))
            ttk.Button(bb, text='+ Alliance', command=add).pack(side='left')
            ttk.Button(bb, text='− Supprimer', command=remove).pack(side='left', padx=4)
            ttk.Button(bb, text='Réinitialiser', command=reset).pack(side='left')
            bo = ttk.Frame(left)
            bo.pack(fill='x', pady=(6, 0))
            ttk.Button(bo, text='OK', command=ok).pack(side='right')
            ttk.Button(bo, text='Annuler', command=win.destroy).pack(side='right', padx=4)
            refresh_list()
            load_sel()
            refresh_marks()

        def random_scenario(self):
            if not self.units or not self.avail:
                messagebox.showinfo('Données', "Chargez d'abord le dossier « data » du mod.")
                return
            top = tk.Toplevel(self)
            top.title('Scénario aléatoire')
            top.transient(self)
            top.resizable(False, False)
            sv = getattr(self, '_rnd_saved', {})          # options de la dernière ouverture (session en cours)
            v_h = tk.StringVar(value=sv.get('h', '2'))
            v_ai = tk.StringVar(value=sv.get('ai', '2'))
            v_min = tk.StringVar(value=sv.get('min', str(ARMY_FLOOR)))
            v_max = tk.StringVar(value=sv.get('max', str(GOLD_MAX)))
            v_mu = tk.StringVar(value=sv.get('mu', str(MAX_UNITS)))
            v_aux = tk.BooleanVar(value=sv.get('aux', False))
            v_up = tk.BooleanVar(value=sv.get('up', False))
            v_sold = tk.StringVar(value=sv.get('sold', str(LIMIT_SOLDIERS)))
            v_more = tk.BooleanVar(value=sv.get('more', False))
            f = ttk.Frame(top, padding=10)
            f.pack()
            ttk.Label(f, text='Joueurs humains (2 minimum)').grid(row=0, column=0, sticky='w', pady=2)
            sp_h = int_only(ttk.Spinbox(f, from_=2, to=MAX_ARMIES, textvariable=v_h, width=5), v_h, 2)
            sp_h.grid(row=0, column=1, padx=6)
            ttk.Label(f, text='Armées IA').grid(row=1, column=0, sticky='w', pady=2)
            sp_ai = int_only(ttk.Spinbox(f, from_=0, to=MAX_ARMIES - 2, textvariable=v_ai, width=5), v_ai, 0)
            sp_ai.grid(row=1, column=1, padx=6)
            lbl_tot = ttk.Label(f, text='', foreground='#555')
            lbl_tot.grid(row=1, column=2, sticky='w')

            def limits(*_a):
                # humains + IA <= 8 : on borne l'autre champ à chaque modification
                try:
                    nh = max(2, min(MAX_ARMIES, int(float(v_h.get()))))
                except ValueError:
                    nh = 2
                try:
                    na = max(0, int(float(v_ai.get())))
                except ValueError:
                    na = 0
                if nh + na > MAX_ARMIES:
                    na = MAX_ARMIES - nh
                    v_ai.set(str(na))
                sp_ai.config(to=MAX_ARMIES - nh)
                sp_h.config(to=MAX_ARMIES - na)
                lbl_tot.config(text='total %d / %d' % (nh + na, MAX_ARMIES))

            v_h.trace_add('write', limits)
            v_ai.trace_add('write', limits)
            limits()
            ttk.Label(f, text="Valeur minimum d'une armée").grid(row=2, column=0, sticky='w', pady=2)
            int_only(ttk.Spinbox(f, from_=0, to=GOLD_MAX, increment=500, textvariable=v_min, width=11), v_min, 0).grid(row=2, column=1, padx=6)
            ttk.Label(f, text="Valeur maximum d'une armée").grid(row=3, column=0, sticky='w', pady=2)
            int_only(ttk.Spinbox(f, from_=0, to=GOLD_MAX, increment=500, textvariable=v_max, width=11), v_max, 0).grid(row=3, column=1, padx=6)
            ttk.Label(f, text='Unités max par armée').grid(row=4, column=0, sticky='w', pady=2)
            int_only(ttk.Spinbox(f, from_=1, to=MAX_UNITS, textvariable=v_mu, width=5), v_mu, 1).grid(row=4, column=1, padx=6)
            ttk.Label(f, text='Maximum de soldats (total, toutes armées)').grid(row=4, column=2, sticky='e', padx=(10, 2))
            sp_sold = int_only(ttk.Spinbox(f, from_=0, to=SOLD_MAX, increment=100, textvariable=v_sold, width=7), v_sold, 0)
            sp_sold.grid(row=4, column=3, sticky='w')
            Tooltip(sp_sold, "Total de soldats de toutes les armées (Large Unit Scale). Le jeu affiche un avertissement de performances à partir de %d. "
                             "Vous pouvez dépasser cette valeur." % LIMIT_SOLDIERS)
            ttk.Checkbutton(f, text='Unités auxiliaires', variable=v_aux).grid(row=5, column=0, columnspan=2, sticky='w')
            ttk.Checkbutton(f, text='Améliorations', variable=v_up).grid(row=6, column=0, columnspan=2, sticky='w')
            v_teams = tk.StringVar(value=sv.get('teams', 'Aléatoire'))
            ttk.Label(f, text="Nombre d'équipes").grid(row=7, column=2, sticky='e', padx=(10, 2))
            cb_teams = ttk.Combobox(f, textvariable=v_teams, state='readonly', width=10, values=['Aléatoire'] + [str(i) for i in range(2, LIMIT_TEAMS + 1)])
            cb_teams.grid(row=7, column=3, sticky='w')
            cb_more = ttk.Checkbutton(f, text='Plus de %d équipes' % LIMIT_TEAMS, variable=v_more)
            cb_more.grid(row=6, column=2, columnspan=2, sticky='e')
            Tooltip(cb_more, "Le jeu de base et le mod ne proposent que %d équipes ; les scénarios à 5-8 équipes fonctionnent mais "
                             "les dernières armées risquent d'être impossibles à sélectionner." % LIMIT_TEAMS)

            def team_limit(*_a):
                try:
                    n = int(float(v_h.get())) + int(float(v_ai.get()))
                except ValueError:
                    n = 2
                kmax = max(2, min(n, MAX_ARMIES if v_more.get() else LIMIT_TEAMS))        # jamais plus d'équipes que d'armées (joueurs + IA)
                cb_teams['values'] = ['Aléatoire'] + [str(i) for i in range(2, kmax + 1)]
                if v_teams.get() != 'Aléatoire' and int(v_teams.get()) > kmax:
                    v_teams.set(str(kmax))

            v_h.trace_add('write', team_limit)
            v_ai.trace_add('write', team_limit)
            v_more.trace_add('write', team_limit)
            team_limit()
            v_free = tk.BooleanVar(value=sv.get('free', False))
            v_siege = tk.BooleanVar(value=sv.get('siege', False))
            v_faith = tk.BooleanVar(value=sv.get('faith', False))
            v_chaos = tk.BooleanVar(value=sv.get('chaos', False))
            ttk.Checkbutton(f, text='Lieu libre sur la carte du mod', variable=v_free).grid(row=7, column=0, columnspan=2, sticky='w')
            ttk.Checkbutton(f, text='Siège : 2 équipes max', variable=v_siege).grid(row=10, column=0, columnspan=3, sticky='w')

            def siege_state(*_a):            # siège : toujours 2 équipes, le nombre d'équipes et « plus de 4 équipes » sont inutilisables
                on = bool(v_siege.get())
                cb_teams.config(state='disabled' if on else 'readonly')
                cb_more.config(state='disabled' if on else 'normal')
            v_siege.trace_add('write', siege_state)
            siege_state()
            ttk.Label(f, text="Valeur d'or aléatoire, équipes de même valeur totale, carte du mod (sans map.wfc),\n"
                              "factions, équipes, heure et météo aléatoires. Le scénario actuel sera remplacé.",
                      foreground='#555').grid(row=13, column=0, columnspan=4, sticky='w', pady=(8, 0))

            ttk.Checkbutton(f, text='Faithful Alliances', variable=v_faith).grid(row=9, column=0, columnspan=2, sticky='w')
            bal = ttk.Button(f, text='Éditer…', width=9, command=lambda: self.edit_alliances(top))
            bal.grid(row=9, column=2, sticky='w')
            Tooltip(bal, "Modifier les alliances possibles : une équipe d'un scénario aléatoire ne réunit que des factions "
                         "appartenant à une même alliance.")

            def remember(*_a):
                try:
                    self._rnd_saved = {'h': v_h.get(), 'ai': v_ai.get(), 'min': v_min.get(), 'max': v_max.get(), 'mu': v_mu.get(),
                                       'aux': v_aux.get(), 'up': v_up.get(), 'sold': v_sold.get(), 'more': v_more.get(),
                                       'teams': v_teams.get(), 'free': v_free.get(), 'siege': v_siege.get(), 'faith': v_faith.get(), 'chaos': v_chaos.get()}
                except tk.TclError:
                    pass

            def close():
                remember()
                top.destroy()
            top.protocol('WM_DELETE_WINDOW', close)

            def go():
                remember()
                try:
                    nh = max(2, min(MAX_ARMIES, int(float(v_h.get()))))
                    na = max(0, min(MAX_ARMIES - nh, int(float(v_ai.get()))))
                    vmin = max(0, min(GOLD_MAX, int(float(v_min.get()))))
                    vmax = max(vmin, min(GOLD_MAX, int(float(v_max.get()))))
                    mu = max(1, min(MAX_UNITS, int(float(v_mu.get()))))
                    sold = max(SOLD_MIN, min(SOLD_MAX, int(float(v_sold.get()))))
                    nt = None if v_teams.get() == 'Aléatoire' else int(v_teams.get())
                except ValueError:
                    return
                if nt and nh + na < nt:             # autant d'armées que d'équipes demandées : on ajoute des armées IA
                    na = min(MAX_ARMIES - nh, nt - nh)
                if v_faith.get() and not self.faithful_enough(nh + na):
                    messagebox.showerror('Faithful Alliances', 'Option Alliance Loyale active : pas assez d\'alliances', parent=top)
                    return
                top.destroy()
                self.make_random_scenario(nh, na, vmin, vmax, mu, v_aux.get(), v_up.get(), v_free.get(),
                                         nt, v_siege.get(),
                                         sold, v_more.get(), v_faith.get(), v_chaos.get())

            cch = ttk.Checkbutton(f, text='Climats chaotiques', variable=v_chaos)
            cch.grid(row=11, column=0, columnspan=3, sticky='w')
            Tooltip(cch, "Les météos et saisons hors du climat de la carte (par exemple de la neige dans le désert, ou l'hiver sur une carte "
                         "d'été) peuvent aussi être tirées.")
            ttk.Button(f, text='Générer', command=go).grid(row=12, column=0, columnspan=3, pady=(10, 0))

        def make_random_scenario(self, nh, na, vmin, vmax, mu, use_aux, upgrades, free_place=False, n_teams=None, siege=False,
                                 max_soldiers=LIMIT_SOLDIERS, more_teams=False, faithful=False, chaos=False):
            """Génère un scénario aléatoire et recommence (6 essais) jusqu'à ce qu'il soit valide.
            max_soldiers : total de soldats de toutes les armées ; more_teams : autorise plus de LIMIT_TEAMS équipes."""
            last = None
            for _try in range(6):
                try:
                    res = self._build_random(nh, na, vmin, vmax, mu, use_aux, upgrades, free_place, n_teams, siege, max_soldiers,
                                         more_teams, faithful, chaos)
                except RandomError as ex:
                    messagebox.showerror('Faithful Alliances', str(ex))
                    return
                sc = res[0]
                self._fit_zones(sc)
                errs, _w = validate(sc, self.udict, self.avail, True, self.weather_values)
                lw = compute_layout(sc, self.udict)[1]
                last = res
                eng_bad = bool(sc.siege and siege_roles(sc) and vmax >= ARMY_FLOOR and any(
                    engine_rule_problems(sc.siege_type, a, self.udict) for a in sc.armies if a.team == siege_roles(sc)[1]))
                gap_bad = False
                tv_, per_ = {}, {}
                for a_ in sc.armies:
                    v_ = army_value(a_.units, self.udict)
                    tv_[a_.team] = tv_.get(a_.team, 0) + v_
                    per_.setdefault(a_.team, []).append(v_)
                if len(tv_) > 1 and max(tv_.values()) - min(tv_.values()) > TEAM_GAP_MAX:
                    gap_bad = True
                if any(max(v_) - min(v_) > ARMY_GAP_MAX or min(v_) < min(ARMY_FLOOR, vmax) for v_ in per_.values()):
                    gap_bad = True
                if not errs and not lw and not eng_bad and not gap_bad:
                    break
            sc, target, ok = last
            if sc.siege and siege_roles(sc) and vmax >= ARMY_FLOOR:          # or trop basse : aucune unité n'est placée, pas d'avertissement
                bad_f = [a.faction for a in sc.armies if a.team == siege_roles(sc)[1] and engine_rule_problems(sc.siege_type, a, self.udict)]
                if bad_f:
                    messagebox.showwarning('Siège', "Règle des engins de siège non respectée pour : %s (au moins un engin par faction attaquante ; "
                                                    "un bélier pour Fortress et Citadel)." % ', '.join(bad_f))
            self.sc = sc
            self.import_mode = False
            self.v_tpl.set('')
            self.v_snap.set('')
            self.v_loading.set('')
            self.after_load()
            self.force_no_wfc = True          # un scénario aléatoire ne charge jamais de map.wfc

        def faithful_enough(self, n_arm):
            """Alliances Loyales : seules les factions d'au moins une alliance (2 factions ou plus) peuvent être tirées."""
            elig = set()
            for g in FAITHFUL_GROUPS:
                elig |= set(g)
            facs = [f for f in self.fac_order if f != 'slave' and self.avail.base.get(f) and f in elig]
            return len(facs) >= n_arm

        def _fit_zones(self, sc):
            optimize_zones(sc, self.udict)

        def _build_random(self, nh, na, vmin, vmax, mu, use_aux, upgrades, free_place=False, n_teams=None, siege=False,
                          max_soldiers=LIMIT_SOLDIERS, more_teams=False, faithful=False, chaos=False):
            facs = [f for f in self.fac_order if f != 'slave' and self.avail.base.get(f)]
            if faithful:                # Alliances Loyales : les factions sans alliance sont exclues du tirage
                elig = set()
                for g_ in FAITHFUL_GROUPS:
                    elig |= set(g_)
                facs = [f for f in facs if f in elig]
                if len(facs) < nh + na:
                    raise RandomError("Option Alliance Loyale active : pas assez d'alliances")
            n_arm = min(len(facs), nh + na)
            sc = Scenario()
            self.collect()
            for k in ('gap', 'depth', 'army_width'):
                setattr(sc, k, getattr(self.sc, k))
            sc.year = 2304
            sc.param2 = 0.0                  # 2e valeur de battle_time : toujours 0
            sc.aux = use_aux
            # carte : uniquement le mod (lieux de custom_locations.txt, sans map.wfc) ou un lieu libre de la carte de campagne
            places = [m for m in self.all_maps if self.map_info.get(m[0], {}).get('location')]
            if siege:           # siège : toutes les cartes du mod sauf celles traversées par un fleuve (colonie dans l'eau)
                places = [m for m in places if not m[0].startswith(('Bridge', 'Crossing')) and not (self.map_info.get(m[0]) or {}).get('locked')] or places
                n_teams = 2
            pt = self.campaign.random_point() if free_place else None
            if pt:
                x, y = pt
                near = min((m for m in places), key=lambda m: (m[1] - x) ** 2 + (m[2] - y) ** 2) if places else None
                label = ('Near ' + near[0]) if near else 'Free place'
                info = {'climate': self.campaign.climate_at(x, y), 'free': True}
            else:
                label, x, y = random.choice(places or self.maps)
                info = self.map_info.get(label)
            sc.map_label, sc.map_x, sc.map_y = label, x, y
            sc.hour = random.choice(TIMES_OF_DAY)[1]
            sc.season = random.choice(season_choices(info, chaos))
            sc.weather = random_weather(self.climates, info, sc.season, self.weather_values, chaos)
            sc.chaos = bool(chaos)
            # équipes : un numéro de 1 à 8 par armée, au moins deux équipes différentes
            kmax = MAX_ARMIES if more_teams else LIMIT_TEAMS
            if nh > MAX_ARMIES - 2:         # 7 ou 8 humains : jamais 7 ou 8 équipes (la 7e et la 8e armée ne sont pas jouables)
                kmax = min(kmax, MAX_ARMIES - 2)
                n_teams = min(n_teams or kmax, kmax)
            if not n_teams:
                n_teams = 2 if siege else random.randint(2, max(2, min(kmax, n_arm)))
            k = max(2, min(n_teams, n_arm, kmax))
            nums = [1, 2] if siege else random.sample(range(1, MAX_ARMIES + 1), k)
            chosen, team_of = None, None
            if faithful:        # « Faithful Alliances » : une équipe ne réunit que des factions compatibles (FAITHFUL_GROUPS)
                pick = faithful_pick(facs, n_arm, nums)
                if not pick:
                    raise RandomError("Option Alliance Loyale active : pas assez d'alliances")
                chosen, team_of = pick
            if chosen is None:
                chosen = random.sample(facs, n_arm)
                members = list(chosen)
                random.shuffle(members)
                team_of = {f: nums[i] for i, f in enumerate(members[:k])}     # chaque équipe a au moins une armée
                for f in members[k:]:
                    team_of[f] = random.choice(nums)
            humans = random.sample(chosen, min(nh, len(chosen)))
            teams = [team_of[f] for f in chosen]
            pools = [army_pool(self.avail, self.units, f, use_aux) for f in chosen]
            target = self.random_team_value(chosen, teams, vmin, vmax, mu, use_aux, upgrades, max_soldiers)
            att_team = None
            att_flags = [False] * len(chosen)
            if siege:
                tl0 = sorted(set(teams))
                att_team = random.choice(tl0)
                sc.siege = True
                types_ = {}
                for t_ in SETTLEMENTS:
                    if t_[3] > 0:
                        cs_ = [c_ for c_ in settlement_cultures(t_[0]) if siege_available(t_[0], c_)]
                        if cs_:
                            types_[t_[0]] = cs_
                if types_:                  # type tiré à égalité, puis culture à égalité
                    sc.siege_type = random.choice(sorted(types_))
                    sc.siege_culture = random.choice(types_[sc.siege_type])
                else:
                    sc.siege_type, sc.siege_culture = random.choice(SIEGE_RANDOM)
                sc.siege_dlevel = random.randint(1, next((x_[3] for x_ in SETTLEMENTS if x_[0] == sc.siege_type), 1))
                sc.siege_same = random.random() < 0.5
                sc.siege_dist = 0                  # toujours automatique : assaillants le plus loin possible (puis optimisés selon les armées)
                att_flags = [t == att_team for t in teams]
            lists, target, ok = build_armies_siege(pools, teams, self.udict, target, mu, upgrades, army_floor(vmax), att_flags,
                                                   sc.siege_type if siege else '', max_soldiers)
            order = list(range(len(chosen)))
            random.shuffle(order)
            for i in order:
                f = chosen[i]
                sc.armies.append(Army(faction=f, human=f in humans, team=team_of[f], units=lists[i] if i < len(lists) else [],
                                      gender=random.choice(['male', 'female']), age=33))
            sc.armies.sort(key=lambda a: a.team)
            if len({a.team for a in sc.armies}) >= MAX_ARMIES - 1:      # 7 ou 8 équipes : jamais d'humain en 7e ou 8e position
                nh_ = sum(1 for a in sc.armies if a.human)
                for a in sc.armies:
                    a.human = False
                for a in random.sample(sc.armies[:MAX_ARMIES - 2], min(nh_, MAX_ARMIES - 2)):
                    a.human = True
            tl = sorted({a.team for a in sc.armies})
            sc.team_roles = {str(t): random.choice(['defending', 'attacking']) for t in tl}
            if siege:
                sc.team_roles = {str(t): ('attacking' if t == att_team else 'defending') for t in tl}
                siege_clamp(sc, self.udict)
            sizes = [sum(1 for a in sc.armies if a.team == t) for t in tl]
            sc.name = random_scenario_name(sc.weather, label, sc.hour, sizes, sc.siege_type if siege else '')
            return sc, target, ok

        # ---------------------------------------------------------------- bibliothèque
        def fit_lib_columns(self, _e=None):
            """Toutes les colonnes de la bibliothèque tiennent dans la largeur disponible."""
            t = self.t_lib
            w = t.winfo_width() - 4
            if w < 150:
                return
            mins = {c: max(self.lib_min.get(c, 40) if c in ('name', 'type') else 0, 30) for c in self.lib_weights}
            tot = float(sum(self.lib_weights.values()))
            widths = {c: max(mins[c], int(w * wt / tot)) for c, wt in self.lib_weights.items()}
            extra = sum(widths.values()) - w
            for c in ('name', 'type', 'cls', 'cat'):          # trop large : on rogne les colonnes de texte, jamais les nombres
                if extra <= 0:
                    break
                cut = min(extra, max(0, widths[c] - mins[c]))
                widths[c] -= cut
                extra -= cut
            for c, wd in widths.items():
                t.column(c, width=wd, minwidth=mins[c], stretch=False)

        def refresh_library(self):
            t = self.t_lib
            t.delete(*t.get_children())
            q = self.v_search.get().strip().lower()
            ff = self.v_ffilter.get()
            fid = self.fac_from_label(ff) if ff and not ff.startswith('(') else None
            cat = self.v_cat.get()
            cls = self.v_cls.get()
            mode = self.v_libmode.get()
            aux_types = set()
            if fid and self.avail:
                pool = self.avail.units_for(fid, with_aux=(mode == self.LIB_MODES[2]),
                                            aux_only=(mode == self.LIB_MODES[1]))
                base_types = {u.type for u in self.avail.base.get(fid, [])}
                aux_types = {u.type for u in pool if u.type not in base_types}
            else:
                pool = self.units
            shown = 0
            for u in pool:
                if cat != '(toutes)' and u.category != cat:
                    continue
                if cat == '(toutes)' and u.category == 'ship':
                    continue
                if cls != '(toutes)' and u.cls != cls:
                    continue
                if q and q not in u.name.lower() and q not in u.type.lower():
                    continue
                t.insert('', 'end', iid=u.type, tags=(), values=('aux' if u.type in aux_types else '', ('\u2605 ' if u.is_general else '') + u.name, u.type,
                                                        u.category, u.cls, u.ls, u.cost))
                shown += 1
            note = ''
            if not fid:
                note = '  · choisissez une faction pour filtrer base / auxiliaire'
            self.lbl_lib.config(text='%d unités affichées  (\u2605 = bon général)%s' % (shown, note))
            self.update_lib_tags()

        def update_lib_tags(self):
            """Nom en rouge dans la bibliothèque : l'armée sélectionnée a déjà le maximum d'exemplaires au prix normal."""
            t = getattr(self, 't_lib', None)
            if t is None:
                return
            t.tag_configure('maxed', foreground='#c00000')
            a = self.cur_army()
            cnt = {}
            if a:
                for e in a.units:
                    cnt[e.type.lower()] = cnt.get(e.type.lower(), 0) + 1
            for iid in t.get_children(''):
                u = self.udict.get(iid.lower())
                full = bool(u and cnt.get(iid.lower(), 0) >= max(1, u.max_copies))
                t.item(iid, tags=('maxed',) if full else ())

        def sort_lib(self, col, numeric):
            last_col, rev = self._lib_sort
            rev = (not rev) if last_col == col else False
            self._lib_sort = (col, rev)
            items = [(self.t_lib.set(i, col), i) for i in self.t_lib.get_children('')]
            if numeric:
                items.sort(key=lambda x: float(x[0]) if x[0] not in ('', None) else 0, reverse=rev)
            else:
                items.sort(key=lambda x: str(x[0]).replace('\u2605 ', '').lower(), reverse=rev)
            for pos, (_, iid) in enumerate(items):
                self.t_lib.move(iid, '', pos)

        # ---------------------------------------------------------------- aperçus
        def schedule_preview(self):
            if self._preview_job:
                self.after_cancel(self._preview_job)
            self._preview_job = self.after(120, self._do_preview)

        def spawn_signature(self):
            sc = self.sc
            return (bool(self.v_siege.get()), bool(self.v_same.get()), self.v_stype.get(), self.v_scult.get(), self.v_sdlev.get(), self.v_sdist.get(),
                    tuple((a.faction, a.team, len(a.units), sum(e.ls for e in a.units)) for a in sc.armies))

        def auto_spawn(self):
            """Les spawns sont réoptimisés dès qu'une valeur liée change (unités, factions, équipes, siège, une zone par équipe)."""
            try:
                sig = self.spawn_signature()
            except (tk.TclError, AttributeError):
                return
            old = getattr(self, '_spawn_sig', None)
            self._spawn_sig = sig
            if old is None or old == sig:
                return                          # premier affichage / chargement d'un projet : on garde les valeurs enregistrées
            try:
                self.collect()
                optimize_zones(self.sc, self.udict)
                self.v_gap.set(str(int(self.sc.gap)))
                self.v_depth.set(str(int(self.sc.depth)))
                self.v_awidth.set(str(int(self.sc.army_width)))
            except Exception:
                pass

        def _do_preview(self):
            self._preview_job = None
            self.auto_spawn()
            self.draw_plan()
            self.update_preset_flag()
            if self.nb.index(self.nb.select()) == 2:
                self.refresh_text()

        def on_tab(self, _e=None):
            i = self.nb.index(self.nb.select())
            if i == 3:
                self.desc_reload(False)
            if i == 1:
                self.draw_plan()
            elif i == 2:
                self.refresh_text()

        # ---------------------------------------------------------------- descriptions
        def build_desc_tab(self, f):
            tb = ttk.Frame(f)
            tb.pack(fill='x')
            for txt, cmd, tip in (
                    ('Ajouter', self.desc_add, "Ajoute, à la suite du texte, les scénarios dont le dossier est à côté de l'éditeur "
                                               "et qui n'y figurent pas encore (titre avec espaces, météo, heure, joueurs et or). "
                                               "Écrit le fichier."),
                    ('Supprimer', self.desc_remove, "Enlève du texte les scénarios dont le dossier n'est plus à côté de l'éditeur "
                                                    "(seuls les blocs créés par l'éditeur sont concernés). Écrit le fichier."),
                    ('Écraser', self.desc_overwrite, "Écrit dans le fichier le texte tel qu'il est affiché ici (vos modifications "
                                                     "manuelles comprises)."),
                    ('Actualiser', lambda: self.desc_reload(True), "Recharge le fichier battle_descriptions.txt situé dans le dossier de l'éditeur.")):
                b = ttk.Button(tb, text=txt, command=cmd)
                b.pack(side='left', padx=(0, 4))
                Tooltip(b, tip)
            self.txt_desc = tk.Text(f, wrap='none', font=('Consolas', 9))
            ys = ttk.Scrollbar(f, orient='vertical', command=self.txt_desc.yview)
            xs = ttk.Scrollbar(f, orient='horizontal', command=self.txt_desc.xview)
            self.txt_desc.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
            xs.pack(side='bottom', fill='x')
            ys.pack(side='right', fill='y')
            self.txt_desc.pack(fill='both', expand=True)
            self.desc_loaded = False

        def desc_path(self):
            return os.path.join(here, DESC_FILE)

        def desc_read(self):
            try:
                return desc_decode(read_bytes(self.desc_path()))
            except OSError:
                return DESC_HEADER + '\r\n'

        def desc_reload(self, force):
            if self.desc_loaded and not force:
                return
            self.txt_desc.delete('1.0', 'end')
            self.txt_desc.insert('1.0', self.desc_read().replace('\r\n', '\n'))
            self.desc_loaded = True

        def desc_write(self, text, notify):
            try:
                with open(self.desc_path(), 'wb') as fh:
                    fh.write(desc_encode(text))
            except OSError as ex:
                messagebox.showerror('Erreur', "Écriture impossible : %s" % ex)
                return
            self.desc_reload(True)
            if notify:
                messagebox.showinfo('Descriptions', "Copiez %s dans le dossier mod/data/text." % DESC_FILE)

        def desc_register(self, sc, folder):
            """Ajoute (ou remplace) le bloc du scénario qui vient d'être créé dans battle_descriptions.txt."""
            text = self.txt_desc.get('1.0', 'end') if self.desc_loaded else self.desc_read()
            head, blocks = desc_split(text)
            blocks[folder] = desc_block_sc(folder, sc, self.factions, self.udict)
            self.desc_write(desc_join(head, blocks), False)

        def desc_add(self):
            head, blocks = desc_split(self.txt_desc.get('1.0', 'end'))
            have = {ln.split('}')[0].upper() for ln in head if ln.startswith('{')}
            for b in blocks.values():
                have |= {ln.split('}')[0].upper() for ln in b if ln.startswith('{')}
            for d in scenario_folders(here):
                if d in blocks or ('{%s_TITLE' % desc_key(d)) in have:
                    continue
                try:
                    with open(os.path.join(here, d, 'descr_battle.txt'), 'r', encoding='latin-1') as fh:
                        dt = fh.read()
                except OSError:
                    continue
                blocks[d] = desc_block(d, dt, self.factions, self.udict)
            self.desc_write(desc_join(head, blocks), True)

        def desc_remove(self):
            head, blocks = desc_split(self.txt_desc.get('1.0', 'end'))
            present = set(scenario_folders(here))
            blocks = {k: v for k, v in blocks.items() if k in present}
            self.desc_write(desc_join(head, blocks), False)

        def desc_overwrite(self):
            t = self.txt_desc.get('1.0', 'end').rstrip('\n').replace('\r\n', '\n').replace('\n', '\r\n')
            self.desc_write(t, True)

        def refresh_text(self):
            self.collect()
            try:
                layout, _ = compute_layout(self.sc, self.udict)
                text = generate_descr_battle(self.sc, self.udict, layout) if layout else '(aucune armée)'
            except Exception as ex:   # noqa
                text = 'Erreur : %s' % ex
            self.txt.delete('1.0', 'end')
            self.txt.insert('1.0', text.replace('\r\n', '\n'))

        def draw_plan(self):
            c = self.canvas
            c.delete('all')
            self.collect()
            layout, warns = compute_layout(self.sc, self.udict)
            self.lbl_warn.config(text='\n'.join('⚠ ' + w for w in warns))
            W, H = c.winfo_width(), c.winfo_height()
            if not layout or W < 50 or H < 50:
                return
            pts = [pt for L in layout.values() for pt in L['zone'] + [q for z, _m in L.get('extra', []) for q in z]]
            if self.sc.siege:
                pts += [(-SIEGE_MAP_LIMIT, -SIEGE_MAP_LIMIT), (SIEGE_MAP_LIMIT, SIEGE_MAP_LIMIT)]
            minx, maxx = min(p[0] for p in pts) - 40, max(p[0] for p in pts) + 40
            miny, maxy = min(p[1] for p in pts) - 40, max(p[1] for p in pts) + 40
            half = max(maxx - minx, maxy - miny) / 2.0
            cx, cy = (minx + maxx) / 2.0, (miny + maxy) / 2.0
            scale = min(W, H) / (2.0 * half) * 0.96

            def tp(x, y):
                return W / 2.0 + (x - cx) * scale, H / 2.0 - (y - cy) * scale

            if self.sc.siege:
                r0 = siege_def(self.sc)[5]
                x1, y1 = tp(-r0, r0)
                x2, y2 = tp(r0, -r0)
                c.create_polygon([v for p in siege_def_polygon(self.sc) for v in tp(*p)], fill='#d8d2c0', outline='#777', width=2)   # périmètre
                m1, m2 = tp(-SIEGE_MAP_LIMIT, SIEGE_MAP_LIMIT), tp(SIEGE_MAP_LIMIT, -SIEGE_MAP_LIMIT)
                c.create_rectangle(m1[0], m1[1], m2[0], m2[1], outline='#999', dash=(2, 4))
            rv = None if self.sc.siege else RIVER_LOCATIONS.get((self.sc.map_x, self.sc.map_y))
            if rv:              # fleuve central de la carte (Bridge / Crossing) : bande d'eau
                if rv == 'vertical':
                    q1, q2 = tp(-RIVER_HALF_WIDTH, cy + half), tp(RIVER_HALF_WIDTH, cy - half)
                else:
                    q1, q2 = tp(cx - half, RIVER_HALF_WIDTH), tp(cx + half, -RIVER_HALF_WIDTH)
                c.create_rectangle(q1[0], q1[1], q2[0], q2[1], fill='#8fbfe8', outline='')
            teams = sorted({a.team for a in self.sc.armies})
            labels = []
            for i, a in enumerate(self.sc.armies):
                L = layout[i]
                col = self.team_colors[teams.index(a.team) % len(self.team_colors)]
                c.create_polygon([v for p in L['zone'] for v in tp(*p)], outline=col, fill='', width=2, dash=(4, 3))
                for z2, _m in L.get('extra', []):
                    c.create_polygon([v for p in z2 for v in tp(*p)], outline=col, fill='', width=2, dash=(4, 3))
                for idx, (x, y, o, w) in enumerate(L['units']):
                    h = math.radians(o)
                    fx, fy = math.sin(h), math.cos(h)
                    rx, ry = math.cos(h), -math.sin(h)
                    hw, hd = max(w / 2.0, 2.5 / scale), max(5.0, 2.5 / scale)
                    quad = [(x + rx * hw + fx * hd, y + ry * hw + fy * hd), (x + rx * hw - fx * hd, y + ry * hw - fy * hd),
                            (x - rx * hw - fx * hd, y - ry * hw - fy * hd), (x - rx * hw + fx * hd, y - ry * hw + fy * hd)]
                    c.create_polygon([v for p in quad for v in tp(*p)], fill=col, outline='white')
                nm = '%s (%s)' % (self.factions.get(a.faction, a.faction), tr_value('Joueur' if a.human else 'IA'))
                if self.sc.siege:
                    nm = '%s · %s' % (tr_value(ROLES.get(self.sc.role_of(a.team), '')), nm)
                labels.append((i, nm, col, [q for p in [L['zone']] + [z2 for z2, _m in L.get('extra', [])] for q in p],
                               bool(self.sc.siege and self.sc.role_of(a.team) == 'attacking')))
            placed = []                                # légendes déjà posées (x, y, demi-largeur, demi-hauteur)
            fnt = ('Segoe UI', 9, 'bold')
            for i, nm, col, zpts, att in sorted(labels, key=lambda t: min(tp(*p)[1] for p in t[3])):
                sp = [tp(*p) for p in zpts]
                cyy = sum(p[1] for p in sp) / len(sp)
                south = att and cyy > H / 2.0 + 25          # assaillants au sud : légende sous leur zone (hors du fort)
                tx = (min(p[0] for p in sp) + max(p[0] for p in sp)) / 2.0      # centrée sur sa zone, au-dessus de celle-ci
                top = min(p[1] for p in sp)
                bw, bh = 6.4 * len(nm) / 2.0 + 5, 9.0
                tx = max(bw + 2, min(W - bw - 2, tx))
                ty = top - bh - 4
                if south:
                    ty = max(p[1] for p in sp) + bh + 4
                    for _k in range(80):
                        hit = next((p for p in placed if abs(p[0] - tx) < bw + p[2] and abs(p[1] - ty) < bh + p[3]), None)
                        if not hit:
                            break
                        ty = hit[1] + hit[3] + bh + 2
                    if ty > H - bh - 2:                # plus de place en bas : au-dessus de la zone
                        south = False
                        ty = top - bh - 4
                for _k in range(80 if not south else 0):   # remonte la légende tant qu'elle chevauche une autre
                    hit = next((p for p in placed if abs(p[0] - tx) < bw + p[2] and abs(p[1] - ty) < bh + p[3]), None)
                    if not hit:
                        break
                    ty = hit[1] - hit[3] - bh - 2
                if ty < bh + 2 and not south:          # plus de place en haut : sous la zone
                    ty = max(p[1] for p in sp) + bh + 4
                    for _k in range(80):
                        hit = next((p for p in placed if abs(p[0] - tx) < bw + p[2] and abs(p[1] - ty) < bh + p[3]), None)
                        if not hit:
                            break
                        ty = hit[1] + hit[3] + bh + 2
                placed.append((tx, ty, bw, bh))
                c.create_rectangle(tx - bw, ty - bh, tx + bw, ty + bh, fill='white', outline=col)
                c.create_text(tx, ty, text=nm, fill=col, font=fnt)
            c.create_text(8, 8, anchor='nw', fill='#555', text=tr('Plan (nord = haut)') + (tr('  Colonie : %s') % self.sc.siege_type if self.sc.siege else ''), font=('Segoe UI', 9))

        # ---------------------------------------------------------------- fichiers
        def import_battle(self):
            p = filedialog.askopenfilename(title='descr_battle.txt à importer',
                                           filetypes=[('descr_battle', '*.txt'), ('Tous', '*.*')])
            if not p:
                return
            try:
                self.sc = parse_descr_battle(read_text(p), self.factions)
            except OSError as ex:
                messagebox.showerror('Erreur', str(ex))
                return
            for a in self.sc.armies:
                for e in a.units:
                    u = self.udict.get(e.type.lower())
                    if u:
                        e.armour = min(e.armour, u.max_armour)
                a.units = a.units[:MAX_UNITS]
            self.after_load()
            messagebox.showinfo('Import', "Scénario importé. Les positions des unités sont recalculées automatiquement.")

        def after_load(self):
            self._spawn_sig = None
            self.preset_ref = None
            migrate_engines(self.sc, self.udict)
            self.sel = 0 if self.sc.armies else None
            self.push_settings()
            self.refresh_armies()
            self.refresh_units()
            self.schedule_preview()

        def build_output(self):
            self.collect()
            if self.sc.siege:                      # siège : spawn toujours optimisé
                optimize_zones(self.sc, self.udict)
            self.sort_armies()
            self.refresh_armies()
            errors, warnings = validate(self.sc, self.udict, self.avail, True, self.weather_values)
            if errors:
                messagebox.showerror('Scénario incomplet', '\n'.join('• ' + e for e in errors))
                return None
            layout, lw = compute_layout(self.sc, self.udict)
            warnings += lw
            if self.sc.siege and not self.campaign.is_clear(self.sc.map_x, self.sc.map_y):
                pass
            if self.sc.siege:
                inf = self.current_map_info() or {}
                if inf.get('locked'):
                    warnings.append("Siège : ce lieu du mod a une colonie fixe (sett_locked) : le fort ajouté risque de ne pas se charger ou de faire planter le jeu.")
            if warnings and not messagebox.askyesno('Avertissements', '\n'.join('• ' + w for w in warnings) +
                                                    '\n\nGénérer quand même ?'):
                return None
            return generate_descr_battle(self.sc, self.udict, layout)

        def generate(self):
            self.collect()
            base = self.sc.name
            if os.path.exists(os.path.join(here, folder_name(base))):
                mm = re.match(r'^(.*\S)\s+(\d+)$', base)
                stem, n = (mm.group(1), int(mm.group(2)) + 1) if mm else (base, 1)
                while os.path.exists(os.path.join(here, folder_name('%s %d' % (stem, n)))):
                    n += 1
                new = '%s %d' % (stem, n)
                self.v_name.set(new)
                self.collect()
                messagebox.showwarning('Nom déjà utilisé', "Un scénario « %s » existe déjà : le nouveau est nommé « %s » (l'ancien n'est pas modifié)." % (base, new))
            text = self.build_output()
            if text is None:
                return
            if sum(1 for a in self.sc.armies if a.human) == 1 and not getattr(self.sc, 'solo', False):
                if not messagebox.askyesno('Un seul joueur humain', "Attention : il n'y a qu'un seul emplacement pour joueur humain "
                                           "dans ce scénario (une seule armée « Joueur »).\n\nCréer quand même la carte ?"):
                    return
            tpl = self.v_tpl.get().strip().strip('"')
            snap = self.v_snap.get().strip().strip('"')
            if not snap:                            # « image du mod » la plus proche des coordonnées
                if self.data_dir:
                    snap = nearest_battlefield_pic(self.data_dir, self.sc.map_x, self.sc.map_y, self.map_info) or ''
            loading = self.v_loading.get().strip().strip('"')
            try:
                path, copied = write_descr_battle(self.sc, self.udict, here, text, tpl or None, True, snap or None, loading or None)
            except OSError as ex:
                messagebox.showerror('Erreur', 'Écriture impossible : %s' % ex)
                return
            try:
                self.desc_register(self.sc, os.path.basename(os.path.dirname(path)))
            except Exception as ex:     # noqa : la description ne doit jamais bloquer la création
                messagebox.showwarning('Description', "battle_descriptions.txt non mis à jour : %s" % ex)
            extra = ('\nFichiers créés : %s' % ', '.join(copied)) if copied else '\n(aucun map.wfc / snapshot copié)'
            messagebox.showinfo('Scénario généré',
                                "Dossier créé à côté de l'éditeur :\n%s%s\n\nCopiez ce dossier dans :\n"
                                "...\\mods\\<votre mod>\\data\\world\\maps\\battle\\\n"
                                "puis relancez le jeu." % (os.path.dirname(path), extra))

    app = App()
    if autorun:
        app.mainloop()
    return app


if __name__ == '__main__':
    run_gui()
