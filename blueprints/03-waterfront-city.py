# GabCon BuildAI - Central Waterfront Market District
# Reference: references/Port steampunk autour de la grande place centrale.png
# IMPORTANT: the central 95x80 insertion zone remains empty for module 01.

stone = weighted_block({
    "stone_bricks": 0.67,
    "cracked_stone_bricks": 0.13,
    "andesite": 0.10,
    "mossy_stone_bricks": 0.04,
    "tuff_bricks": 0.06,
})
CREATE_ANDESITE = "create:andesite_casing"
CREATE_BRASS = "create:brass_casing"
CREATE_COPPER = "create:copper_casing"
TRADING_DEPOT = "trading_floor:trading_depot"


def lamp_post(x, y, z, h=4):
    fill(x, y, z, x, y + h - 1, z, "polished_blackstone")
    set_block(x, y + h, z, "lantern[hanging=false]")


def town_house(cx, cz, w, d, floors_count, roof_axis="x", civic=False):
    x1, x2 = cx - w // 2, cx + w // 2
    z1, z2 = cz - d // 2, cz + d // 2
    base_y = 3
    floor(x1, z1, x2, z2, base_y, "stone_bricks")
    # Stone ground floor.
    walls(x1, z1, x2, z2, base_y, base_y + 5, stone, thickness=1)
    # Explicit two-block door. Doors are multi-block structures and must not be
    # filled as a rectangular volume, otherwise every placed cell defaults to half=lower.
    clear(cx, base_y + 1, z1, cx, base_y + 2, z1)
    set_block(cx, base_y + 1, z1, "dark_oak_door[half=lower]")
    set_block(cx, base_y + 2, z1, "dark_oak_door[half=upper]")

    top = base_y + 5
    for level in range(1, floors_count):
        y1 = base_y + level * 5
        y2 = y1 + 5
        walls(x1, z1, x2, z2, y1, y2, "spruce_planks", thickness=1)
        # Timber corner frame.
        for x in (x1, x2):
            for z in (z1, z2):
                fill(x, y1, z, x, y2, z, "dark_oak_log")
        for xx in range(x1 + 3, x2 - 2, 5):
            set_block(xx, y1 + 2, z1, "orange_stained_glass")
            set_block(xx, y1 + 3, z1, "orange_stained_glass")
        top = y2

    roof_block = "deepslate_tiles" if not civic else "oxidized_copper"
    gable_roof(x1, z1, x2, z2, top + 1, roof_block, ridge_axis=roof_axis, overhang=2)

    # Small steampunk trim.
    set_block(x1, base_y + 4, z1 - 1, CREATE_COPPER)
    set_block(x2, base_y + 4, z1 - 1, CREATE_ANDESITE)
    if civic:
        set_block(cx, top + 6, cz, CREATE_BRASS)


def market_stall(cx, z, awning):
    y = 3
    floor(cx - 3, z - 2, cx + 3, z + 2, y, "spruce_planks")
    for x in (cx - 3, cx + 3):
        for zz in (z - 2, z + 2):
            fill(x, y + 1, zz, x, y + 4, zz, "dark_oak_log")
    fill(cx - 3, y + 4, z - 2, cx + 3, y + 4, z + 2, awning)
    set_block(cx, y + 1, z, TRADING_DEPOT)
    set_block(cx - 3, y + 3, z, "lantern[hanging=true]")
    set_block(cx - 3, y + 4, z, "dark_oak_log")
    set_block(cx + 3, y + 3, z, "lantern[hanging=true]")
    set_block(cx + 3, y + 4, z, "dark_oak_log")


def dock(cx, length=16):
    floor(cx - 3, -80, cx + 3, -80 - length, 2, "spruce_planks")
    for z in range(-82, -80 - length - 1, -5):
        for x in (cx - 3, cx + 3):
            fill(x, -1, z, x, 2, z, "dark_oak_log")
    for z in range(-83, -80 - length, -5):
        lamp_post(cx - 2, 3, z, 2)


# ---------------------------------------------------------------------------
# Streets and plaza ring. The central slot x=-48..48, z=-40..40 stays empty.
# ---------------------------------------------------------------------------

# Waterfront band.
floor(-108, -79, 108, -45, 2, stone)
# Left and right urban bands.
floor(-108, -44, -51, 43, 2, stone)
floor(51, -44, 108, 43, 2, stone)
# Rear civic band.
floor(-108, 42, 108, 77, 2, stone)

# Quay wall and water stairs.
fill(-108, -2, -80, 108, 2, -76, "stone_bricks")
for x in (-82, -42, 0, 42, 82):
    for step in range(4):
        fill(x - 4, 2 - step, -79 - step, x + 4, 2 - step, -80 - step, "stone_bricks")

# Portal-slot framing only, never inside the 95x80 reserved rectangle.
for x in range(-50, 51, 5):
    if x <= -48 or x >= 48:
        lamp_post(x, 3, -42, 3)
for z in range(-35, 36, 10):
    lamp_post(-50, 3, z, 3)
    lamp_post(50, 3, z, 3)

# ---------------------------------------------------------------------------
# 20 buildings around the insertion zone
# ---------------------------------------------------------------------------

houses = [
    (-92, -55, 22, 18, 3, "x", False),
    (-65, -56, 24, 19, 3, "z", False),
    (-32, -59, 24, 18, 2, "x", False),
    (34, -58, 24, 19, 3, "x", False),
    (66, -57, 22, 18, 2, "z", False),
    (94, -54, 24, 20, 3, "x", False),
    (-92, -22, 22, 22, 3, "z", False),
    (-70, 7, 25, 22, 4, "x", True),
    (-91, 30, 22, 20, 3, "z", False),
    (91, -22, 22, 22, 3, "z", False),
    (70, 8, 25, 22, 4, "x", True),
    (91, 30, 22, 20, 3, "z", False),
    (-93, 58, 23, 22, 3, "x", False),
    (-67, 60, 24, 22, 3, "z", False),
    (-36, 61, 24, 22, 4, "x", True),
    (0, 63, 30, 24, 5, "x", True),
    (36, 61, 24, 22, 4, "x", True),
    (67, 60, 24, 22, 3, "z", False),
    (93, 58, 23, 22, 3, "x", False),
    (0, -62, 28, 19, 3, "x", True),
]
for spec in houses:
    town_house(*spec)

# Central rear clock / guild tower.
walls(-10, 53, 10, 74, 3, 35, stone, thickness=2)
gable_roof(-10, 53, 10, 74, 36, "oxidized_copper", ridge_axis="x", overhang=2)
fill(-2, 24, 52, 2, 30, 52, "orange_stained_glass")
set_block(0, 32, 52, CREATE_BRASS)

# Market clusters outside the portal slot.
for cx, z, awning in [
    (-95, -35, "blue_wool"),
    (-86, -35, "white_wool"),
    (-67, -35, "orange_wool"),
    (67, -35, "cyan_wool"),
    (86, -35, "red_wool"),
    (95, -35, "white_wool"),
    (-77, 37, "cyan_wool"),
    (-62, 37, "orange_wool"),
    (62, 37, "blue_wool"),
    (77, 37, "red_wool"),
]:
    market_stall(cx, z, awning)

# Waterfront docks.
for cx, length in [(-92, 13), (-64, 18), (-28, 15), (24, 19), (58, 14), (91, 18)]:
    dock(cx, length)

# Two small harbor cranes.
for px, direction in [(-105, 1), (105, -1)]:
    fill(px, 3, -68, px, 17, -68, "dark_oak_log")
    line(px, 17, -68, px + direction * 16, 17, -68, "dark_oak_log")
    line(px, 10, -68, px + direction * 14, 17, -68, "dark_oak_fence")
    hx = px + direction * 14
    fill(hx, 8, -68, hx, 16, -68, "chain")
    hollow_box(hx - 2, 5, -70, hx + 2, 8, -66, "spruce_planks")

# Streetscape trees around the ring, never inside the insertion zone.
for x, z in [
    (-48, -48), (48, -48), (-50, -20), (50, -20),
    (-50, 15), (50, 15), (-44, 45), (44, 45),
    (-18, 47), (18, 47), (-98, -5), (98, -5),
]:
    fill(x, 3, z, x, 8, z, "dark_oak_log")
    sphere(x, 10, z, 3, "azalea_leaves", hollow=False)

# Warm supported lighting along roads and waterfront.
for x in range(-104, 105, 13):
    lamp_post(x, 3, -73, 4)
for x in (-103, -80, -56, 56, 80, 103):
    for z in (-38, -10, 18, 39):
        lamp_post(x, 3, z, 4)
for x in range(-98, 99, 14):
    lamp_post(x, 3, 46, 4)
