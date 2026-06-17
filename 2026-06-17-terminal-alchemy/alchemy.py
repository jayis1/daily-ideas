#!/usr/bin/env python3
"""Terminal Alchemy — combine elements to discover new ones, right in your terminal."""

from __future__ import annotations
import json
import os
import sys
import textwrap
import shutil
from pathlib import Path

# ---------------------------------------------------------------------------
# Recipe database
# ---------------------------------------------------------------------------
# Format: (ingredient_a, ingredient_b) → result
# Order-independent: combine(a, b) == combine(b, a)
# We store each pair once (canonical order: sorted alphabetically).

RECIPES: dict[tuple[str, str], str] = {}

def _add(a: str, b: str, result: str) -> None:
    key = tuple(sorted((a, b)))
    if key not in RECIPES:
        RECIPES[key] = result

# ── Base elements ──
BASE = {"water", "fire", "earth", "air"}

# ── Tier 1: base + base ──
_add("water", "fire", "steam")
_add("water", "earth", "mud")
_add("water", "air", "mist")
_add("fire", "earth", "lava")
_add("fire", "air", "smoke")
_add("earth", "air", "dust")

# ── Tier 2: base + tier1 ──
_add("water", "steam", "pressure")
_add("water", "mud", "swamp")
_add("water", "mist", "fog")
_add("water", "lava", "obsidian")
_add("water", "dust", "clay")
_add("water", "smoke", "smog")
_add("fire", "steam", "engine")
_add("fire", "mud", "brick")
_add("fire", "smoke", "ash")
_add("fire", "lava", "magma")
_add("fire", "dust", "explosion")
_add("fire", "mist", "rainbow")
_add("fire", "clay", "pottery")
_add("earth", "steam", "geyser")
_add("earth", "mud", "quicksand")
_add("earth", "mist", "fog")  # duplicate result is fine
_add("earth", "lava", "volcano")
_add("earth", "dust", "sand")
_add("earth", "smoke", "smog")
_add("earth", "clay", "adobe")
_add("air", "steam", "cloud")
_add("air", "mud", "breeze")  # mud drying
_add("air", "mist", "rain")
_add("air", "lava", "stone")
_add("air", "smoke", "cloud")
_add("air", "dust", "storm")
_add("air", "clay", "sand")

# ── Tier 3: deeper combos ──
_add("steam", "steam", "pressure")
_add("steam", "cloud", "rain")
_add("steam", "stone", "geyser")
_add("steam", "engine", "train")
_add("cloud", "cloud", "storm")
_add("cloud", "rain", "storm")
_add("cloud", "fire", "lightning")
_add("cloud", "ice", "snow")
_add("rain", "earth", "plant")
_add("rain", "rain", "flood")
_add("rain", "fire", "rainbow")
_add("rain", "cold", "snow")
_add("rain", "sand", "quicksand")
_add("storm", "storm", "hurricane")
_add("storm", "water", "hurricane")
_add("storm", "lightning", "thunderstorm")
_add("lightning", "water", "life")
_add("lightning", "sand", "glass")
_add("lightning", "metal", "electricity")
_add("lightning", "tree", "charcoal")
_add("lava", "water", "obsidian")
_add("lava", "pressure", "volcano")
_add("mud", "fire", "brick")
_add("mud", "plant", "swamp")
_add("mud", "sand", "clay")
_add("pressure", "coal", "diamond")
_add("pressure", "stone", "diamond")
_add("pressure", "carbon", "diamond")
_add("pressure", "water", "ice")
_add("pressure", "steam", "engine")
_add("pressure", "pressure", "explosion")
_add("obsidian", "fire", "blade")
_add("obsidian", "pressure", "mirror")
_add("sand", "fire", "glass")
_add("sand", "glass", "lens")
_add("sand", "water", "quicksand")
_add("sand", "plant", "cactus")
_add("dust", "water", "clay")
_add("dust", "fire", "explosion")
_add("dust", "dust", "sand")
_add("dust", "wind", "storm")
_add("fog", "fog", "cloud")
_add("mist", "cold", "snow")
_add("mist", "mist", "fog")

# ── Organic / Life ──
_add("life", "water", "fish")
_add("life", "earth", "animal")
_add("life", "air", "bird")
_add("life", "fire", "phoenix")
_add("life", "plant", "tree")
_add("life", "mud", "bacteria")
_add("life", "swamp", "lizard")
_add("life", "life", "love")
_add("life", "lightning", "energy")
_add("life", "sand", "fossil")

# ── Plants / Nature ──
_add("plant", "fire", "ash")
_add("plant", "water", "flower")
_add("plant", "earth", "garden")
_add("plant", "plant", "forest")
_add("plant", "sun", "flower")
_add("plant", "stone", "moss")
_add("plant", "time", "tree")
_add("plant", "cold", "ice_plant")
_add("plant", "clay", "crop")
_add("plant", "lava", "volcanic_rock")
_add("flower", "flower", "garden")
_add("flower", "water", "perfume")
_add("flower", "bee", "honey")
_add("tree", "fire", "charcoal")
_add("tree", "axe", "wood")
_add("tree", "tree", "forest")
_add("tree", "water", "swamp")
_add("tree", "wind", "leaf")
_add("tree", "time", "fossil")
_add("forest", "fire", "wildfire")
_add("forest", "animal", "wolf")

# ── Cold / Ice ──
_add("cold", "water", "ice")
_add("cold", "air", "wind")
_add("cold", "fire", "energy")
_add("cold", "earth", "permafrost")
_add("cold", "rain", "snow")
_add("cold", "cloud", "snow")
_add("cold", "steam", "water")
_add("ice", "fire", "water")
_add("ice", "ice", "glacier")
_add("ice", "stone", "iceberg")
_add("ice", "pressure", "glacier")
_add("ice", "heat", "water")
_add("snow", "snow", "blizzard")
_add("snow", "fire", "water")
_add("snow", "wind", "blizzard")
_add("glacier", "fire", "flood")
_add("glacier", "pressure", "iceberg")

# ── Minerals / Crafted ──
_add("stone", "fire", "metal")
_add("stone", "stone", "wall")
_add("stone", "water", "sand")
_add("stone", "axe", "brick")
_add("stone", "pressure", "diamond")
_add("metal", "fire", "sword")
_add("metal", "metal", "alloy")
_add("metal", "water", "rust")
_add("metal", "hammer", "blade")
_add("metal", "electricity", "magnet")
_add("metal", "wood", "nail")
_add("glass", "sand", "lens")
_add("glass", "fire", "bottle")
_add("glass", "light", "prism")
_add("glass", "metal", "mirror")
_add("diamond", "axe", "gem")
_add("diamond", "metal", "jewelry")
_add("diamond", "tool", "gem")
_add("clay", "fire", "brick")
_add("clay", "water", "mud")
_add("clay", "pottery", "amphora")
_add("brick", "brick", "wall")
_add("brick", "wood", "house")
_add("adobe", "adobe", "house")

# ── Tools / Technology ──
_add("tool", "wood", "hammer")
_add("tool", "metal", "axe")
_add("tool", "stone", "axe")
_add("tool", "tool", "machine")
_add("tool", "plant", "scythe")
_add("tool", "fire", "torch")
_add("axe", "wood", "plank")
_add("axe", "stone", "brick")
_add("hammer", "stone", "tool")
_add("hammer", "metal", "blade")
_add("sword", "human", "warrior")
_add("sword", "lightning", "lightsaber")
_add("blade", "blade", "scissors")
_add("blade", "wood", "axe")
_add("engine", "metal", "machine")
_add("engine", "wheel", "car")
_add("engine", "train", "bullet_train")
_add("engine", "wood", "locomotive")
_add("electricity", "metal", "magnet")
_add("electricity", "glass", "lightbulb")
_add("electricity", "lightbulb", "lamp")
_add("electricity", "human", "cyborg")
_add("electricity", "machine", "computer")
_add("electricity", "computer", "ai")
_add("electricity", "lightning", "thunderstorm")
_add("wheel", "metal", "car")
_add("wheel", "wood", "cart")
_add("wheel", "wheel", "bicycle")
_add("car", "fire", "explosion")
_add("car", "road", "traffic")
_add("train", "metal", "bullet_train")
_add("machine", "machine", "factory")
_add("machine", "human", "robot")
_add("computer", "ai", "internet")
_add("computer", "human", "hacker")
_add("computer", "computer", "internet")
_add("robot", "human", "cyborg")
_add("robot", "ai", "overlord")

# ── Humans / Civilization ──
_add("animal", "animal", "pack")
_add("animal", "life", "human")
_add("animal", "time", "fossil")
_add("animal", "fire", "cooked_meat")
_add("animal", "human", "pet")
_add("animal", "wood", "beaver")
_add("bird", "fire", "phoenix")
_add("bird", "bird", "flock")
_add("bird", "tree", "nest")
_add("fish", "fish", "school")
_add("fish", "fire", "cooked_fish")
_add("fish", "human", "fisherman")
_add("human", "human", "village")
_add("human", "fire", "campfire")
_add("human", "water", "swimmer")
_add("human", "tool", "craftsman")
_add("human", "knowledge", "scientist")
_add("human", "metal", "warrior")
_add("human", "plant", "farmer")
_add("human", "love", "family")
_add("human", "house", "family")
_add("human", "book", "scholar")
_add("human", "computer", "hacker")
_add("human", "sword", "warrior")
_add("human", "pet", "companionship")
_add("village", "village", "city")
_add("city", "city", "civilization")
_add("city", "fire", "ruins")
_add("civilization", "civilization", "empire")
_add("civilization", "fire", "war")
_add("empire", "fire", "ruins")
_add("love", "human", "family")
_add("love", "love", "harmony")
_add("family", "family", "community")
_add("community", "community", "civilization")
_add("knowledge", "fire", "candle")
_add("knowledge", "human", "scientist")
_add("knowledge", "book", "library")
_add("knowledge", "stone", "rune")
_add("knowledge", "paper", "book")
_add("knowledge", "knowledge", "philosophy")

# ── Crafted items ──
_add("wood", "fire", "charcoal")
_add("wood", "water", "boat")
_add("wood", "wood", "wall")
_add("wood", "stone", "house")
_add("wood", "rope", "bridge")
_add("wood", "tool", "wheel")
_add("wood", "axe", "plank")
_add("wood", "metal", "nail")
_add("wood", "plank", "furniture")
_add("charcoal", "pressure", "diamond")
_add("charcoal", "charcoal", "coal")
_add("coal", "fire", "energy")
_add("coal", "pressure", "diamond")
_add("plank", "plank", "wall")
_add("plank", "nail", "furniture")
_add("paper", "knowledge", "book")
_add("paper", "paper", "book")
_add("paper", "wood", "cardboard")
_add("book", "book", "library")
_add("bottle", "water", "potion")
_add("bottle", "fire", "lamp")
_add("bottle", "glass", "vase")
_add("rope", "wood", "bridge")
_add("rope", "rope", "net")
_add("net", "fish", "fisherman")
_add("mirror", "light", "prism")
_add("mirror", "mirror", "infinity")
_add("mirror", "human", "doppelganger")
_add("perfume", "love", "potion")
_add("potion", "human", "wizard")
_add("potion", "animal", "monster")
_add("wizard", "fire", "dragon")
_add("wizard", "lightning", "storm")
_add("wizard", "knowledge", "sorcerer")
_add("wizard", "wizard", "guild")
_add("dragon", "water", "steam")
_add("dragon", "fire", "inferno")
_add("dragon", "gold", "hoard")
_add("monster", "human", "hero")
_add("hero", "dragon", "legend")
_add("hero", "sword", "paladin")

# ── Light / Heat / Cosmic ──
_add("fire", "fire", "heat")
_add("fire", "heat", "sun")
_add("heat", "water", "steam")
_add("heat", "cold", "energy")
_add("heat", "stone", "lava")
_add("light", "glass", "prism")
_add("light", "water", "rainbow")
_add("light", "plant", "photosynthesis")
_add("light", "darkness", "twilight")
_add("light", "light", "star")
_add("darkness", "darkness", "void")
_add("darkness", "light", "twilight")
_add("darkness", "fire", "candle")
_add("sun", "water", "rainbow")
_add("sun", "plant", "flower")
_add("sun", "ice", "water")
_add("sun", "earth", "desert")
_add("sun", "moon", "eclipse")
_add("star", "star", "constellation")
_add("star", "water", "ocean")
_add("star", "darkness", "galaxy")
_add("constellation", "knowledge", "astronomy")
_add("galaxy", "galaxy", "universe")
_add("universe", "life", "everything")
_add("everything", "everything", "everything")
_add("moon", "water", "tide")
_add("moon", "sun", "eclipse")
_add("moon", "stone", "meteor")
_add("moon", "wolf", "howl")
_add("tide", "wind", "wave")
_add("wave", "wave", "tsunami")
_add("tsunami", "city", "disaster")
_add("meteor", "earth", "crater")
_add("meteor", "fire", "meteorite")
_add("volcano", "water", "island")
_add("island", "island", "archipelago")
_add("ocean", "ocean", "tsunami")
_add("desert", "water", "oasis")
_add("desert", "wind", "sandstorm")

# ── Derived from base combos that fill gaps ──
_add("wind", "water", "wave")
_add("wind", "fire", "smoke")
_add("wind", "sand", "sandstorm")
_add("wind", "leaf", "dandelion")
_add("energy", "energy", "explosion")
_add("energy", "metal", "magnet")
_add("energy", "glass", "lightbulb")
_add("energy", "plant", "biofuel")
_add("bacteria", "water", "plankton")
_add("bacteria", "time", "evolution")
_add("evolution", "life", "human")
_add("evolution", "fish", "amphibian")
_add("evolution", "lizard", "dinosaur")
_add("dinosaur", "meteor", "fossil")
_add("dinosaur", "dinosaur", "extinction")
_add("extinction", "earth", "fossil")
_add("fossil", "fire", "coal")
_add("fossil", "pressure", "oil")
_add("oil", "fire", "energy")
_add("oil", "pressure", "plastic")
_add("plastic", "metal", "gadget")
_add("gadget", "electricity", "phone")
_add("phone", "internet", "social_media")
_add("social_media", "human", "influencer")

# ── Some fun wildcards ──
_add("time", "flower", "seed")
_add("time", "seed", "tree")
_add("time", "human", "elder")
_add("time", "animal", "fossil")
_add("time", "stone", "sand")
_add("time", "mountain", "sand")
_add("time", "river", "canyon")
_add("mountain", "mountain", "mountain_range")
_add("mountain", "cloud", "rain")
_add("mountain", "fire", "volcano")
_add("mountain", "snow", "glacier")
_add("mountain", "stone", "cave")
_add("cave", "water", "lake")
_add("cave", "light", "crystal")
_add("crystal", "light", "prism")
_add("crystal", "crystal", "gem")
_add("gem", "metal", "jewelry")
_add("jewelry", "love", "ring")
_add("ring", "human", "marriage")
_add("lake", "fish", "pond")
_add("river", "fish", "salmon")
_add("river", "mountain", "waterfall")
_add("waterfall", "light", "rainbow")

# ── Food / Drink ──
_add("water", "flower", "tea")
_add("heat", "water", "soup")
_add("fire", "wheat", "bread")
_add("fire", "meat", "steak")
_add("wheat", "water", "dough")
_add("dough", "fire", "bread")
_add("crop", "water", "wheat")
_add("crop", "fire", "bread")
_add("bread", "meat", "sandwich")
_add("honey", "water", "mead")
_add("tea", "sugar", "sweet_tea")
_add("water", "sugar", "soda")
_add("plant", "sugar", "candy")
_add("flower", "bee", "honey")

# ── Misc fill ──
_add("sand", "heat", "glass")
_add("sugar", "energy", "hyperactivity")
_add("gold", "fire", "jewelry")
_add("gold", "human", "wealth")
_add("gold", "gold", "wealth")
_add("wealth", "human", "king")
_add("king", "village", "kingdom")
_add("kingdom", "kingdom", "war")
_add("war", "sword", "battle")
_add("battle", "hero", "victory")
_add("victory", "human", "peace")
_add("peace", "peace", "harmony")
_add("harmony", "life", "utopia")

# Derived
_add("wall", "wall", "room")
_add("room", "furniture", "house")
_add("house", "human", "family")
_add("house", "house", "village")
_add("road", "car", "traffic")
_add("road", "road", "highway")
_add("bridge", "water", "crossing")
_add("boat", "wind", "sailboat")
_add("boat", "engine", "ship")
_add("sailboat", "ocean", "voyage")

# Need to define some things that were referenced but not created
_add("cold", "cold", "ice")
_add("cold", "heat", "energy")
_add("cold", "fire", "steam")  # fire melts cold
_add("wind", "wind", "tornado")
_add("tornado", "water", "hurricane")
_add("tornado", "tornado", "storm")

_add("light", "fire", "candle")
_add("darkness", "air", "night")
_add("night", "star", "constellation")
_add("night", "moon", "midnight")

_add("swamp", "plant", "moss")
_add("swamp", "life", "lizard")

_add("lizard", "fire", "dragon")
_add("lizard", "evolution", "dinosaur")

_add("influencer", "internet", "meme")
_add("meme", "meme", "viral")
_add("viral", "internet", "trend")

# ── Bridge recipes: connect unreachable elements to reachable ones ──
# These use reachable ingredients to produce key unlocking elements
_add("air", "energy", "cold")              # adiabatic expansion
_add("air", "cold", "wind")                # wind from cold air
_add("smoke", "mist", "darkness")          # darkness from obscuring
_add("air", "darkness", "night")           # night falls
_add("fire", "fire", "heat")               # fire creates heat
_add("energy", "fire", "light")             # energy + fire = light
_add("cloud", "night", "moon")             # moon in night sky
_add("stone", "obsidian", "mountain")      # mountains from volcanic rock
_add("water", "mountain", "river")         # rivers from mountains
_add("mountain", "stone", "cave")          # caves in mountains
_add("cave", "water", "lake")              # lakes in caves
_add("lake", "lake", "ocean")              # oceans from many lakes
_add("light", "light", "star")             # stars from light
_add("star", "star", "constellation")      # constellations from stars
_add("star", "darkness", "galaxy")         # galaxies from stars in dark
_add("galaxy", "galaxy", "universe")       # universe from galaxies
_add("sun", "darkness", "time")            # time from day/night cycle
_add("flower", "time", "seed")             # seeds from flowers over time
_add("tree", "wind", "leaf")               # leaves blown from trees
_add("flower", "heat", "sugar")            # sugar from flowers + heat
_add("water", "seed", "tea")               # tea from water + seeds
_add("plant", "wind", "vine")              # vines grow in wind
_add("animal", "axe", "meat")              # hunting
_add("flower", "animal", "bee")            # bees pollinate flowers
_add("charcoal", "heat", "carbon")         # carbon from charcoal
_add("sun", "charcoal", "gold")            # alchemy: sun transforms
_add("book", "light", "knowledge")         # illumination brings knowledge
_add("metal", "wood", "hammer")             # hammer from metal + wood
_add("hammer", "stone", "tool")             # tools from hammering stone
_add("metal", "wood", "axe")                # axe from metal + wood (same as hammer, but _add skips dupes)
_add("axe", "tree", "wood")                 # chopping trees gives wood
_add("axe", "stone", "brick")               # axes work stone
_add("plank", "tool", "wheel")              # wheel from planks + tools
_add("wood", "pressure", "paper")           # paper from wood pulp
_add("paper", "paper", "book")              # books from paper
_add("knowledge", "knowledge", "philosophy")
_add("knowledge", "human", "scientist")
_add("knowledge", "book", "library")
_add("knowledge", "stone", "rune")
_add("stone", "charcoal", "road")           # roads from stone + charcoal
_add("plant", "plant", "rope")              # rope from plant fibers
_add("rope", "wood", "bridge")              # bridges from rope + wood
_add("rope", "rope", "net")                 # nets from rope
_add("moon", "water", "tide")               # tides from moon
_add("moon", "wolf", "howl")                # wolves howl at moon
_add("light", "glass", "prism")              # prisms split light
_add("light", "darkness", "twilight")        # twilight at the boundary
_add("moon", "sun", "eclipse")              # eclipses
_add("night", "star", "constellation")      # constellations at night
_add("cold", "earth", "permafrost")          # permafrost
_add("cold", "water", "ice")                 # ice from cold water
_add("cold", "cloud", "snow")                # snow from cold clouds
_add("cold", "rain", "snow")                 # snow from cold rain
_add("ice", "ice", "glacier")                # glaciers from ice
_add("ice", "pressure", "glacier")           # glaciers from pressure
_add("ice", "stone", "iceberg")              # icebergs
_add("snow", "snow", "blizzard")             # blizzards
_add("snow", "wind", "blizzard")             # blizzards
_add("wind", "sand", "sandstorm")            # sandstorms
_add("wind", "water", "wave")               # waves from wind
_add("wave", "wave", "tsunami")              # tsunamis
_add("wind", "wind", "tornado")              # tornadoes
_add("tornado", "water", "hurricane")        # hurricanes
_add("wood", "water", "boat")                # boats from wood
_add("wood", "fire", "charcoal")             # charcoal from wood
_add("wood", "axe", "plank")                 # planks from wood
_add("wood", "metal", "nail")                # nails
_add("plank", "nail", "furniture")           # furniture
_add("plank", "plank", "wall")               # walls from planks
_add("plank", "brick", "house")              # houses from planks + bricks
_add("charcoal", "charcoal", "coal")         # coal from charcoal
_add("coal", "pressure", "diamond")          # diamonds from coal
_add("stone", "pressure", "diamond")         # diamonds from stone (dupe, skipped)
_add("charcoal", "water", "paper")            # paper from charcoal (dupe, skipped)
_add("charcoal", "fire", "carbon")            # carbon from charcoal + fire
_add("meat", "fire", "steak")                 # cooking meat
_add("meat", "bread", "sandwich")             # sandwiches
_add("bread", "meat", "sandwich")             # dupe, skipped
_add("flower", "bee", "honey")                # honey from bees
_add("honey", "water", "mead")                # mead from honey
_add("book", "human", "knowledge")            # books + humans = knowledge (dupe, skipped)
_add("book", "human", "scholar")              # scholars read books
_add("scholar", "book", "knowledge")          # scholars produce knowledge
_add("paper", "knowledge", "book")            # knowledge written on paper (dupe, skipped)
_add("paper", "wood", "cardboard")            # cardboard from paper + wood
_add("cave", "light", "crystal")              # crystals in caves
_add("crystal", "crystal", "gem")             # gems from crystals
_add("gem", "metal", "jewelry")               # jewelry from gems
_add("gold", "fire", "jewelry")               # gold jewelry (dupe, skipped)
_add("gold", "human", "wealth")               # gold brings wealth
_add("gold", "gold", "wealth")                # wealth from gold
_add("wealth", "human", "king")               # kings from wealth
_add("king", "village", "kingdom")            # kingdoms
_add("kingdom", "kingdom", "war")             # war between kingdoms
_add("war", "sword", "battle")                # battles
_add("battle", "hero", "victory")             # victory
_add("victory", "human", "peace")             # peace after victory
_add("peace", "peace", "harmony")             # harmony
_add("harmony", "life", "utopia")             # utopia
_add("light", "plant", "photosynthesis")      # photosynthesis
_add("light", "water", "rainbow")             # rainbows from light
_add("darkness", "darkness", "void")           # void
_add("darkness", "fire", "candle")             # candles pierce darkness
_add("darkness", "human", "fear")              # fear in darkness
_add("fear", "human", "courage")              # courage overcomes fear
_add("courage", "sword", "paladin")           # paladins from courage
_add("paladin", "dragon", "legend")           # legends from paladins vs dragons
_add("diamond", "axe", "gem")                 # gems from cutting diamonds
_add("diamond", "tool", "gem")                # dupe, skipped
_add("animal", "evolution", "dinosaur")       # dinosaurs evolve
_add("dinosaur", "meteor", "fossil")          # fossils from extinction
_add("dinosaur", "dinosaur", "extinction")   # extinction
_add("extinction", "earth", "fossil")         # fossils from extinction
_add("bacteria", "time", "evolution")         # evolution over time
_add("evolution", "life", "human")             # humans from evolution (dupe, skipped)
_add("evolution", "fish", "amphibian")        # amphibians evolve from fish
_add("evolution", "lizard", "dinosaur")       # dinosaurs evolve (dupe, skipped)
_add("meteor", "earth", "crater")              # craters from meteors
_add("meteor", "fire", "meteorite")            # meteorites
_add("volcano", "water", "island")             # islands from volcanoes
_add("island", "island", "archipelago")        # archipelagos
_add("desert", "water", "oasis")               # oases in deserts
_add("desert", "wind", "sandstorm")            # dupe, skipped
_add("sandstorm", "wind", "tornado")           # dupe, skipped
_add("plant", "cold", "ice_plant")            # ice plants
_add("plant", "time", "tree")                  # trees grow over time (dupe, skipped)
_add("seed", "time", "tree")                   # seeds grow into trees
_add("seed", "water", "plant")                 # seeds sprout into plants
_add("seed", "earth", "crop")                  # crops from seeds
_add("seed", "heat", "sprout")                 # sprouting seeds
_add("seed", "seed", "garden")                 # gardens from many seeds
_add("crop", "water", "wheat")                 # wheat from crops
_add("crop", "heat", "wheat")                  # dupe, skipped
_add("crop", "fire", "bread")                  # dupe, skipped
_add("wheat", "water", "dough")                # dough from wheat + water
_add("dough", "fire", "bread")                 # bread from dough
_add("dough", "heat", "bread")                 # dupe, skipped
_add("sugar", "water", "soda")                 # soda from sugar
_add("sugar", "plant", "candy")                # candy from sugar
_add("sugar", "energy", "hyperactivity")       # sugar rush
_add("tea", "sugar", "sweet_tea")              # sweet tea
_add("tea", "heat", "sweet_tea")               # dupe, skipped
_add("cold", "heat", "energy")                 # energy from temperature difference (dupe, skipped)
_add("cold", "fire", "steam")                  # cold meets fire = steam (dupe, skipped)
_add("cold", "plant", "ice_plant")             # dupe, skipped
_add("animal", "time", "fossil")               # fossils from ancient animals
_add("animal", "pet", "companionship")         # companionship
_add("ocean", "moon", "tide")                  # dupe, skipped
_add("ocean", "wind", "wave")                  # dupe, skipped
_add("ocean", "ocean", "tsunami")              # tsunamis
_add("ocean", "fish", "whale")                  # whales in the ocean
_add("ocean", "boat", "voyage")                 # voyages across oceans
_add("ocean", "sailboat", "voyage")            # dupe, skipped
_add("river", "fish", "salmon")                 # salmon in rivers
_add("river", "mountain", "waterfall")          # waterfalls
_add("lake", "fish", "pond")                    # ponds
_add("mountain", "snow", "glacier")             # glaciers on mountains
_add("mountain", "fire", "volcano")              # volcanoes from mountains
_add("mountain", "cloud", "rain")                # rain from mountains
_add("mountain", "mountain", "mountain_range")   # mountain ranges
_add("mountain_range", "mountain_range", "continent")  # continents
_add("cold", "rain", "snow")                     # dupe, skipped
_add("cold", "air", "wind")                      # dupe, skipped
_add("darkness", "fire", "candle")                # dupe, skipped
_add("night", "moon", "midnight")                 # midnight
_add("moon", "stone", "meteor")                   # meteors from the moon
_add("cave", "water", "lake")                     # dupe, skipped
_add("star", "darkness", "galaxy")                # dupe, skipped
_add("constellation", "knowledge", "astronomy")   # astronomy
_add("universe", "life", "everything")             # everything
_add("light", "darkness", "twilight")              # dupe, skipped
_add("moon", "moon", "month")                      # months from moon cycles
_add("time", "time", "eternity")                    # eternity
_add("eternity", "universe", "everything")           # dupe, skipped
_add("time", "stone", "sand")                        # stones become sand over time (dupe, skipped)
_add("time", "flower", "seed")                       # dupe, skipped
_add("time", "seed", "tree")                          # dupe, skipped
_add("time", "human", "elder")                        # elders
_add("time", "animal", "fossil")                      # dupe, skipped
_add("time", "mountain", "canyon")                     # canyons form over time
_add("time", "river", "canyon")                        # canyons from rivers
_add("time", "bacteria", "evolution")                  # dupe, skipped
_add("elder", "knowledge", "wisdom")                    # wisdom from elders
_add("wisdom", "wisdom", "philosophy")                  # dupe, skipped
_add("canyon", "water", "lake")                          # dupe, skipped

# ── Breaking circular dependency for tools ──
_add("human", "stone", "tool")              # humans craft tools from stone
_add("human", "tree", "wood")               # humans harvest wood
_add("tool", "metal", "hammer")             # hammer from tool + metal
_add("tool", "stone", "axe")                # axe from tool + stone
_add("axe", "tree", "plank")                 # planks from chopping (dupe, skipped)

# ---------------------------------------------------------------------------
# Discover all possible element names (for completeness tracking)
# Only count elements that are actually reachable from base elements
# ---------------------------------------------------------------------------
_all_recipe_elements: set[str] = set(BASE)
for key, val in RECIPES.items():
    _all_recipe_elements.add(key[0])
    _all_recipe_elements.add(key[1])
    _all_recipe_elements.add(val)

# Compute reachability from base elements
def _compute_reachable() -> set[str]:
    reachable = set(BASE)
    changed = True
    while changed:
        changed = False
        for (a, b), result in RECIPES.items():
            if a in reachable and b in reachable and result not in reachable:
                reachable.add(result)
                changed = True
    return reachable

REACHABLE_ELEMENTS = _compute_reachable()
ALL_ELEMENTS = REACHABLE_ELEMENTS
TOTAL_ELEMENTS = len(ALL_ELEMENTS)

# ---------------------------------------------------------------------------
# Save data helpers
# ---------------------------------------------------------------------------
SAVE_DIR = Path.home() / ".config" / "terminal-alchemy"
SAVE_FILE = SAVE_DIR / "save.json"


def load_save() -> dict:
    if SAVE_FILE.exists():
        try:
            data = json.loads(SAVE_FILE.read_text())
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_progress(discovered: set[str], *, merge: bool = True) -> None:
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    data = load_save()
    if merge:
        existing = set(data.get("discovered", []))
        existing |= discovered
        data["discovered"] = sorted(existing)
    else:
        data["discovered"] = sorted(discovered)
    SAVE_FILE.write_text(json.dumps(data, indent=2))


def load_discovered() -> set[str]:
    data = load_save()
    return set(data.get("discovered", list(BASE)))


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------
def terminal_width() -> int:
    try:
        return shutil.get_terminal_size((80, 24)).columns
    except Exception:
        return 80


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def box_print(text: str, width: int = 60, style: str = "double") -> str:
    """Return a box-drawing framed text."""
    if style == "double":
        tl, tr, bl, br, h, v = "╔", "╗", "╚", "╝", "═", "║"
    else:
        tl, tr, bl, br, h, v = "┌", "┐", "└", "┘", "─", "│"
    lines = text.split("\n")
    max_len = max(len(line) for line in lines) if lines else 0
    w = max(max_len + 2, width)
    result = [tl + h * w + tr]
    for line in lines:
        result.append(v + f" {line:<{w-2}}" + v)
    result.append(bl + h * w + br)
    return "\n".join(result)


def format_discovered(discovered: set[str], cols: int | None = None) -> str:
    """Format discovered elements in columns with colors."""
    items = sorted(discovered)
    if not items:
        return "  (none yet)"
    
    max_len = max(len(e) for e in items) + 2
    if cols is None:
        cols = max(1, terminal_width() // max_len)
    
    lines = []
    row = []
    for item in items:
        if item in BASE:
            styled = f"\033[1;33m{item}\033[0m"
        elif item in discovered and item not in BASE:
            styled = f"\033[36m{item}\033[0m"
        else:
            styled = item
        row.append(styled)
        if len(row) == cols:
            lines.append("  ".join(f"{r:<{max_len}}" for r in row))
            row = []
    if row:
        lines.append("  ".join(f"{r:<{max_len}}" for r in row))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Hint system
# ---------------------------------------------------------------------------
def get_hints(discovered: set[str]) -> list[str]:
    """Find recipes where the player has one ingredient but not the other or result."""
    hints = []
    for (a, b), result in RECIPES.items():
        if result in discovered:
            continue
        # If player has one ingredient, hint about the other
        if a in discovered and b not in discovered:
            # Don't reveal the exact missing ingredient; just the one they have
            hints.append(f"  Try combining '{a}' with something new...")
        elif b in discovered and a not in discovered:
            hints.append(f"  Try combining '{a.split()[0] if ' ' in a else a}' with something new...")
    return hints[:5]


# ---------------------------------------------------------------------------
# Main game
# ---------------------------------------------------------------------------
BANNER = r"""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║              🧪  T E R M I N A L  A L C H E M Y  🧪     ║
║                                                          ║
║        Combine elements to discover new ones!            ║
║        Start with: water, fire, earth, air               ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
Commands:
  combine <a> <b>   — Combine two elements (shortcut: just type 'a + b')
  list              — Show all discovered elements
  hint              — Get a hint
  new               — Show newly discovered elements
  search <term>     — Search discovered elements
  stats             — Show progress statistics
  reset             — Reset all progress (with confirmation)
  help              — Show this help
  quit / exit       — Save and exit

Tip: You can also just type two element names separated by '+'
     e.g. 'water + fire' or 'water fire'
"""


def combine(a: str, b: str, discovered: set[str]) -> str | None:
    """Try to combine two elements. Returns result or None."""
    key = tuple(sorted((a, b)))
    return RECIPES.get(key)


def interactive_mode() -> None:
    discovered = load_discovered()
    just_discovered: set[str] = set()
    
    clear_screen()
    print(BANNER)
    
    if len(discovered) > 4:
        print(f"\033[32mWelcome back! You've discovered {len(discovered)}/{TOTAL_ELEMENTS} elements.\033[0m")
    else:
        print("\033[33mYou start with the four basic elements: water, fire, earth, air\033[0m")
        print("Combine them to discover new elements!\n")
        discovered = set(BASE)
    
    print("\nType \033[1mhelp\033[0m for commands, or just type combinations like \033[1mwater + fire\033[0m\n")
    
    while True:
        try:
            raw = input("\033[1;35m⚗️ > \033[0m").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\033[33mSaving progress... Goodbye!\033[0m")
            save_progress(discovered)
            break
        
        if not raw:
            continue
        
        raw_lower = raw.lower()
        
        # ── Commands ──
        if raw_lower in ("quit", "exit", "q"):
            print("\033[33mSaving progress... Goodbye!\033[0m")
            save_progress(discovered)
            break
        
        if raw_lower == "help" or raw_lower == "?":
            print(HELP_TEXT)
            continue
        
        if raw_lower == "list":
            print(f"\n\033[1mDiscovered Elements ({len(discovered)}/{TOTAL_ELEMENTS}):\033[0m")
            print(format_discovered(discovered))
            print()
            continue
        
        if raw_lower == "hint":
            hints = get_hints(discovered)
            if hints:
                print("\n\033[33m💡 Hints:\033[0m")
                for h in hints:
                    print(h)
            else:
                # Find completely undiscoverable recipes (need new base combos)
                undiscovered_recipes = [(a, b, r) for (a, b), r in RECIPES.items()
                                        if r not in discovered]
                if undiscovered_recipes:
                    a, b, r = undiscovered_recipes[0]
                    print(f"\n\033[33m💡 You have {len(discovered)}/{TOTAL_ELEMENTS} elements. Try combining things you haven't tried yet!\033[0m")
                else:
                    print("\n\033[32m🎉 You've discovered everything!\033[0m")
            print()
            continue
        
        if raw_lower == "new":
            if just_discovered:
                print(f"\n\033[32mRecently discovered:\033[0m")
                for e in sorted(just_discovered):
                    print(f"  ✨ {e}")
            else:
                print("\n  No new discoveries yet in this session.")
            print()
            continue
        
        if raw_lower == "stats":
            pct = len(discovered) / TOTAL_ELEMENTS * 100
            bar_len = 30
            filled = int(bar_len * pct / 100)
            bar = "█" * filled + "░" * (bar_len - filled)
            print(f"\n\033[1mAlchemy Progress:\033[0m")
            print(f"  [{bar}] {pct:.1f}%")
            print(f"  Discovered: {len(discovered)}/{TOTAL_ELEMENTS}")
            
            # Count by tier
            tiers = {"Base": 0, "Tier 1": 0, "Tier 2+": 0}
            for e in discovered:
                if e in BASE:
                    tiers["Base"] += 1
                else:
                    # Check if it's a tier-1 result
                    is_tier1 = False
                    for (a, b), r in RECIPES.items():
                        if r == e and a in BASE and b in BASE:
                            is_tier1 = True
                            break
                    if is_tier1:
                        tiers["Tier 1"] += 1
                    else:
                        tiers["Tier 2+"] += 1
            
            print(f"  Base elements: {tiers['Base']}/4")
            print(f"  Tier 1 combos: {tiers['Tier 1']}")
            print(f"  Advanced:       {tiers['Tier 2+']}")
            print()
            continue
        
        if raw_lower.startswith("search "):
            term = raw_lower[7:].strip()
            matches = sorted(e for e in discovered if term in e)
            if matches:
                print(f"\n\033[1mMatches for '{term}':\033[0m")
                for m in matches:
                    print(f"  • {m}")
            else:
                print(f"\n  No discovered elements matching '{term}'.")
            print()
            continue
        
        if raw_lower == "reset":
            confirm = input("\033[1;31m⚠️  Reset ALL progress? Type 'yes' to confirm: \033[0m").strip().lower()
            if confirm == "yes":
                discovered = set(BASE)
                just_discovered.clear()
                save_progress(discovered, merge=False)
                print("\033[31mProgress reset! Starting fresh with base elements.\033[0m")
            else:
                print("Reset cancelled.")
            continue
        
        # ── Parse combination ──
        # Accept: "a + b", "a+b", "a b", "combine a b"
        parts = raw_lower.replace("combine", "").strip()
        
        # Split by +
        if "+" in parts:
            ingredients = [p.strip() for p in parts.split("+") if p.strip()]
        else:
            # Try splitting by whitespace (take first two words)
            ingredients = parts.split()[:2]
        
        if len(ingredients) < 2:
            print("\033[31mPlease specify two elements to combine. Example: water + fire\033[0m")
            continue
        
        a, b = ingredients[0], ingredients[1]
        
        # Check if elements are discovered
        if a not in discovered:
            print(f"\033[31m❌ You haven't discovered '{a}' yet!\033[0m")
            continue
        if b not in discovered:
            print(f"\033[31m❌ You haven't discovered '{b}' yet!\033[0m")
            continue
        
        result = combine(a, b, discovered)
        
        if result is None:
            print(f"\033[33m💨 {a} + {b} = ... nothing happened.\033[0m")
            continue
        
        if result in discovered:
            print(f"\033[36m{a} + {b} = {result}\033[0m (already discovered)")
        else:
            discovered.add(result)
            just_discovered.add(result)
            save_progress(discovered)
            print(f"\n{'✨' * 3} \033[1;32mNEW DISCOVERY!\033[0m {'✨' * 3}")
            print(f"\033[1;36m{a} + {b} = {result}\033[0m")
            
            pct = len(discovered) / TOTAL_ELEMENTS * 100
            print(f"\033[2mProgress: {len(discovered)}/{TOTAL_ELEMENTS} ({pct:.1f}%)\033[0m")
            
            if len(discovered) == TOTAL_ELEMENTS:
                print("\n\033[1;33m" + "=" * 50)
                print("🎉🏆 CONGRATULATIONS! 🏆🎉")
                print("You've discovered ALL elements!")
                print("=" * 50 + "\033[0m")
    
    save_progress(discovered)


# ---------------------------------------------------------------------------
# Non-interactive mode (for scripting / batch combinations)
# ---------------------------------------------------------------------------
def batch_combine(pairs: list[tuple[str, str]]) -> None:
    """Combine pairs and print results, starting from saved progress."""
    discovered = load_discovered()
    if not discovered:
        discovered = set(BASE)
    
    for a, b in pairs:
        a, b = a.lower(), b.lower()
        if a not in discovered:
            print(f"❌ Unknown element: {a}")
            continue
        if b not in discovered:
            print(f"❌ Unknown element: {b}")
            continue
        result = combine(a, b, discovered)
        if result is None:
            print(f"💨 {a} + {b} = nothing")
        else:
            new = result not in discovered
            discovered.add(result)
            # Make result available for future combines in this session
            marker = " ✨ NEW!" if new else ""
            print(f"🧪 {a} + {b} = {result}{marker}")
    
    save_progress(discovered)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Terminal Alchemy — combine elements to discover new ones!"
    )
    parser.add_argument("--combine", nargs=2, action="append", metavar=("A", "B"),
                        help="Combine two elements non-interactively")
    parser.add_argument("--list", action="store_true", help="List discovered elements")
    parser.add_argument("--stats", action="store_true", help="Show progress stats")
    parser.add_argument("--hint", action="store_true", help="Show a hint")
    parser.add_argument("--reset", action="store_true", help="Reset all progress")
    parser.add_argument("--all-elements", action="store_true", help="List all possible elements (spoilers!)")
    parser.add_argument("--version", action="version", version="Terminal Alchemy 1.0.0")
    args = parser.parse_args()
    
    if args.all_elements:
        print(f"All {TOTAL_ELEMENTS} elements:\n")
        for e in sorted(ALL_ELEMENTS):
            marker = " 🟡" if e in BASE else ""
            print(f"  {e}{marker}")
        return
    
    if args.reset:
        save_progress(set(BASE), merge=False)
        print("Progress reset! You now have only the four base elements.")
        return
    
    if args.stats:
        discovered = load_discovered()
        pct = len(discovered) / TOTAL_ELEMENTS * 100
        print(f"Discovered: {len(discovered)}/{TOTAL_ELEMENTS} ({pct:.1f}%)")
        return
    
    if args.list:
        discovered = load_discovered()
        if discovered:
            for e in sorted(discovered):
                print(f"  {e}")
        else:
            print("No elements discovered yet. Start with: water, fire, earth, air")
        return
    
    if args.hint:
        discovered = load_discovered()
        hints = get_hints(discovered)
        if hints:
            for h in hints[:3]:
                print(h)
        else:
            print("No hints available — you may have discovered everything!")
        return
    
    if args.combine:
        batch_combine(args.combine)
        return
    
    # Default: interactive mode
    interactive_mode()


if __name__ == "__main__":
    main()