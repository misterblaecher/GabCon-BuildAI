# GabCon BuildAI - Central Lakeside Arcane Gateway
# Blueprint DSL for mcbuild.
#
# Coordinate convention:
#   x = left/right
#   y = up
#   z = front/back
# The public plaza is toward negative z. The portal faces the plaza.

stone = weighted_block({
    "stone_bricks": 0.68,
    "cracked_stone_bricks": 0.18,
    "mossy_stone_bricks": 0.06,
    "andesite": 0.08,
})
dark_stone = weighted_block({
    "deepslate_bricks": 0.58,
    "polished_deepslate": 0.22,
    "deepslate_tiles": 0.12,
    "cracked_deepslate_bricks": 0.08,
})
plaza_stone = weighted_block({
    "stone_bricks": 0.55,
    "andesite": 0.20,
    "polished_andesite": 0.15,
    "cracked_stone_bricks": 0.10,
})

# Confirmed against the GabCon 1.21.1 live registry and the modded-preview lab.
CREATE_ANDESITE = "create:andesite_casing"
CREATE_BRASS = "create:brass_casing"
CREATE_COPPER = "create:copper_casing"
TRADING_DEPOT = "trading_floor:trading_depot"


def pointed_arch_frame(z, half_width, bottom, spring, apex, thickness, block):
    """Layered pointed arch in the x/y plane at fixed z."""
    for t in range(thickness):
        hw = half_width + t
        y0 = bottom - t
        ys = spring + t // 2
        ya = apex + t
        line(-hw, y0, z, -hw, ys, z, block)
        line(hw, y0, z, hw, ys, z, block)
        line(-hw, ys, z, 0, ya, z, block)
        line(hw, ys, z, 0, ya, z, block)


def fill_pointed_opening(z1, z2, half_width, bottom, spring, apex, block):
    """Fill the inside of a pointed arch volume."""
    for y in range(bottom, spring + 1):
        fill(-half_width, y, z1, half_width, y, z2, block)
    height = max(1, apex - spring)
    for y in range(spring + 1, apex + 1):
        remaining = apex - y
        hw = int(round(half_width * remaining / height))
        fill(-hw, y, z1, hw, y, z2, block)


def carve_pointed_opening(z1, z2, half_width, bottom, spring, apex):
    for y in range(bottom, spring + 1):
        clear(-half_width, y, z1, half_width, y, z2)
    height = max(1, apex - spring)
    for y in range(spring + 1, apex + 1):
        remaining = apex - y
        hw = int(round(half_width * remaining / height))
        clear(-hw, y, z1, hw, y, z2)


def crystal_cluster(cx, cy, cz, scale=1):
    heights = [7, 5, 4, 3, 2]
    offsets = [(0, 0), (-2, 1), (2, 1), (-1, -2), (2, -1)]
    for i in range(len(heights)):
        ox, oz = offsets[i]
        h = heights[i] * scale
        x = cx + ox * scale
        z = cz + oz * scale
        fill(x, cy, z, x, cy + h - 1, z, "amethyst_block")
        if h >= 4:
            set_block(x, cy + h, z, "purple_stained_glass")
    set_block(cx, cy + 7 * scale + 1, cz, "sea_lantern")


def lantern_post(x, y, z, height=4, soul=False):
    block = "soul_lantern" if soul else "lantern"
    fill(x, y, z, x, y + height - 1, z, "polished_blackstone")
    set_block(x, y + height, z, block)


def planter(x1, z1, x2, z2, y):
    floor(x1, z1, x2, z2, y, "stone_bricks")
    walls(x1, z1, x2, z2, y, y + 1, "stone_bricks")
    if x2 - x1 >= 3 and z2 - z1 >= 3:
        fill(x1 + 1, y + 1, z1 + 1, x2 - 1, y + 1, z2 - 1, "dirt")
        for x in range(x1 + 1, x2):
            for z in range(z1 + 1, z2):
                if (x + z) % 3 == 0:
                    set_block(x, y + 2, z, "azalea_leaves")


def market_stall(cx, y, z, awning):
    # 7 x 5 footprint, with a real GabCon trading depot as the center counter.
    floor(cx - 3, z - 2, cx + 3, z + 2, y, "spruce_planks")
    for x in (cx - 3, cx + 3):
        for zz in (z - 2, z + 2):
            fill(x, y + 1, zz, x, y + 4, zz, "dark_oak_log")
    fill(cx - 3, y + 4, z - 2, cx + 3, y + 4, z + 2, awning)
    fill(cx - 2, y + 1, z + 1, cx + 2, y + 1, z + 1, "barrel")
    set_block(cx, y + 1, z, TRADING_DEPOT)
    set_block(cx - 3, y + 3, z, "lantern")
    set_block(cx + 3, y + 3, z, "lantern")


def tower(cx, cz, base_y, body_h, radius=5):
    cylinder(cx, cz, base_y, body_h, radius, dark_stone, hollow=True)
    floor(cx - radius, cz - radius, cx + radius, cz + radius, base_y, "stone_bricks")

    # Strong vertical ribs with mechanical Create casing nodes.
    for dx, dz in ((radius, 0), (-radius, 0), (0, radius), (0, -radius)):
        fill(cx + dx, base_y, cz + dz, cx + dx, base_y + body_h + 4, cz + dz, "polished_deepslate")
        for yy in (base_y + 8, base_y + 19, base_y + 30):
            set_block(cx + dx, yy, cz + dz, CREATE_ANDESITE)

    # Window bands.
    for yy in (base_y + 10, base_y + 20, base_y + 31):
        set_block(cx - radius, yy, cz, "light_blue_stained_glass")
        set_block(cx + radius, yy, cz, "light_blue_stained_glass")
        set_block(cx, yy, cz - radius, "light_blue_stained_glass")

    # Open crystal belfry.
    chamber_y = base_y + body_h - 10
    clear(cx - 2, chamber_y, cz - 2, cx + 2, base_y + body_h + 2, cz + 2)
    for yy in range(chamber_y, base_y + body_h + 3):
        set_block(cx - radius, yy, cz, CREATE_COPPER)
        set_block(cx + radius, yy, cz, CREATE_COPPER)
    crystal_cluster(cx, chamber_y + 1, cz, 1)

    # Heavy collar, brass mechanical ring and oxidized copper spire.
    cylinder(cx, cz, base_y + body_h - 2, 3, radius + 1, "stone_bricks", hollow=False)
    for x in range(cx - radius, cx + radius + 1):
        set_block(x, base_y + body_h + 1, cz - radius - 1, CREATE_BRASS)
    cone(cx, cz, base_y + body_h + 2, radius + 1, 11, "oxidized_copper", hollow=False)
    fill(cx, base_y + body_h + 13, cz, cx, base_y + body_h + 17, cz, "polished_blackstone")
    set_block(cx, base_y + body_h + 18, cz, "sea_lantern")


# ---------------------------------------------------------------------------
# 1) Plaza and approach
# ---------------------------------------------------------------------------

# Main plaza plate
floor(-43, -38, 43, -7, 0, plaza_stone)
fill(-43, -1, -38, 43, -1, -7, "stone_bricks")

# Outer low retaining wall
walls(-43, -38, 43, -7, 0, 2, "stone_bricks")
clear(-8, 1, -38, 8, 2, -38)

# Front ceremonial stairs from y=0 to y=4
for step in range(5):
    y = step
    z1 = -38 + step * 2
    z2 = -37 + step * 2
    fill(-12, y, z1, 12, y, z2, "stone_bricks")

# Upper plaza terrace
floor(-34, -7, 34, 4, 4, plaza_stone)
fill(-34, 0, -7, 34, 3, 4, "stone_bricks")

# Grand main staircase to portal terrace: broader, more monumental and closer
# to the schematic concept art.
for step in range(10):
    y = 4 + step
    z1 = -8 + step
    fill(-16 + step // 2, y, z1, 16 - step // 2, y, z1 + 1, "stone_bricks")

# Side flanking stairs.
for step in range(6):
    y = 4 + step
    z1 = -6 + step
    fill(-27, y, z1, -19, y, z1 + 1, "stone_bricks")
    fill(19, y, z1, 27, y, z1 + 1, "stone_bricks")

# Portal terrace.
floor(-34, 1, 34, 17, 14, plaza_stone)
fill(-34, 4, 1, 34, 13, 17, stone)

# Side terraces for markets
floor(-43, -29, -19, -8, 2, plaza_stone)
floor(19, -29, 43, -8, 2, plaza_stone)

# Terrace trims
fill(-43, 2, -8, -19, 3, -8, "stone_bricks")
fill(19, 2, -8, 43, 3, -8, "stone_bricks")
fill(-34, 4, -7, 34, 5, -7, "stone_bricks")

# Central plaza mosaic
for r, block in ((7, "deepslate_tiles"), (5, "oxidized_copper"), (3, "prismarine_bricks")):
    for i in range(8):
        a = 2 * math.pi * i / 8
        x = round(r * math.cos(a))
        z = -18 + round(r * math.sin(a))
        set_block(x, 1, z, block)
set_block(0, 1, -18, "sea_lantern")

# Planters and trees
for args in [
    (-35, -25, -29, -19, 2),
    (29, -25, 35, -19, 2),
    (-33, -14, -27, -9, 2),
    (27, -14, 33, -9, 2),
    (-22, -4, -17, 1, 4),
    (17, -4, 22, 1, 4),
]:
    planter(*args)

# Stylized plaza trees
for x, z, y in [(-32, -22, 4), (32, -22, 4), (-29, -11, 4), (29, -11, 4)]:
    fill(x, y, z, x, y + 5, z, "dark_oak_log")
    sphere(x, y + 7, z, 3, "azalea_leaves", hollow=False)

# Lantern rows
for x in (-36, -26, -16, 16, 26, 36):
    lantern_post(x, 3, -32, 4)
for x in (-26, -18, 18, 26):
    lantern_post(x, 5, -5, 4)
for x in (-17, -10, 10, 17):
    lantern_post(x, 12, 3, 3, soul=(abs(x) == 10))

# Market stalls from concept art
market_stall(-32, 3, -16, "blue_wool")
market_stall(-24, 3, -16, "white_wool")
market_stall(25, 3, -16, "red_wool")
market_stall(34, 3, -16, "orange_wool")


# ---------------------------------------------------------------------------
# 2) Main cathedral massing - V2 server palette
# ---------------------------------------------------------------------------

# Taller and deeper central hall.
walls(-25, 10, 25, 36, 14, 69, stone, thickness=2)
floor(-25, 10, 25, 36, 14, "stone_bricks")
gable_roof(-25, 10, 25, 36, 69, "deepslate_tiles", ridge_axis="z", overhang=2)

# Rear upper mass creates a cathedral silhouette instead of a flat wall.
walls(-15, 31, 15, 46, 22, 58, dark_stone, thickness=2)
floor(-15, 31, 15, 46, 22, "deepslate_bricks")
gable_roof(-15, 31, 15, 46, 58, "deepslate_tiles", ridge_axis="z", overhang=1)

# Side wings.
for side in (-1, 1):
    xa, xb = sorted((25 * side, 43 * side))
    walls(xa, 9, xb, 31, 14, 39, stone, thickness=2)
    floor(xa, 9, xb, 31, 14, "stone_bricks")
    gable_roof(xa, 8, xb, 32, 40, "deepslate_tiles", ridge_axis="x", overhang=1)

# Main opening.
carve_pointed_opening(8, 18, 12, 16, 42, 67)

# Portal depth layers. The Create casings make the frame read as arcane machinery
# rather than a purely vanilla stained-glass wall.
fill_pointed_opening(16, 19, 11, 16, 41, 64, "blue_stained_glass")
fill_pointed_opening(14, 15, 10, 17, 40, 62, "light_blue_stained_glass")
fill_pointed_opening(12, 13, 9, 18, 39, 59, "cyan_stained_glass")
fill_pointed_opening(20, 21, 8, 19, 38, 56, "cyan_stained_glass_pane")
carve_pointed_opening(22, 28, 7, 20, 37, 54)

# Energy spine.
fill(-1, 20, 16, 1, 53, 16, "sea_lantern")
for yy in (26, 33, 40, 47):
    fill(-5, yy, 16, 5, yy, 16, "light_blue_stained_glass")
    set_block(0, yy, 15, "sea_lantern")
for yy in range(22, 53, 4):
    set_block(-4, yy, 15, "prismarine_bricks")
    set_block(4, yy, 15, "prismarine_bricks")

# Layered gothic/mechanical arch.
pointed_arch_frame(8, 16, 15, 43, 73, 3, "stone_bricks")
pointed_arch_frame(7, 14, 16, 42, 70, 2, "polished_deepslate")
pointed_arch_frame(6, 12, 17, 41, 66, 2, CREATE_COPPER)
pointed_arch_frame(5, 10, 18, 40, 62, 1, CREATE_BRASS)
pointed_arch_frame(4, 9, 19, 39, 59, 1, "sea_lantern")

# Mechanical portal pylons and buttresses.
for x in (-21, -17, 17, 21):
    fill(x, 14, 7, x, 63, 13, dark_stone)
    for yy in (22, 35, 48, 59):
        fill(x - 1, yy, 6, x + 1, yy + 2, 13, "stone_bricks")
        set_block(x, yy + 1, 5, CREATE_ANDESITE)
    set_block(x, 65, 9, CREATE_COPPER)

# Inner machinery columns.
for x in (-10, 10):
    fill(x, 17, 8, x, 64, 11, "polished_deepslate")
    for yy in range(23, 64, 8):
        set_block(x, yy, 7, CREATE_BRASS)
        set_block(x, yy + 1, 7, "cyan_stained_glass")

# High facade ribs and crown.
line(-25, 51, 8, 0, 82, 8, "stone_bricks")
line(25, 51, 8, 0, 82, 8, "stone_bricks")
line(-22, 52, 7, 0, 78, 7, "polished_deepslate")
line(22, 52, 7, 0, 78, 7, "polished_deepslate")

# Create casing crown nodes.
for x in (-16, -8, 0, 8, 16):
    set_block(x, 67 + (8 - abs(x)) // 4, 7, CREATE_COPPER)

# Cyan vertical facade accents.
for x in (-19, -14, 14, 19):
    fill(x, 29, 8, x, 56, 8, "cyan_stained_glass")
    for yy in range(31, 56, 7):
        set_block(x, yy, 7, "sea_lantern")

# High crystal crown.
crystal_cluster(0, 82, 11, 1)


# ---------------------------------------------------------------------------
# 3) Towers, side chapels and flying connections - V2
# ---------------------------------------------------------------------------

# Dominant outer crystal towers.
tower(-36, 18, 14, 47, radius=6)
tower(36, 18, 14, 47, radius=6)

# Rear inner turrets.
for cx in (-26, 26):
    cylinder(cx, 26, 33, 38, 4, "deepslate_bricks", hollow=True)
    for yy in (42, 54, 65):
        set_block(cx, yy, 22, CREATE_ANDESITE)
    cone(cx, 26, 71, 5, 10, "oxidized_copper")
    fill(cx, 81, 26, cx, 85, 26, "polished_blackstone")
    set_block(cx, 86, 26, "sea_lantern")

# Front lower corner pylons.
for cx in (-43, 43):
    cylinder(cx, 3, 6, 30, 3, stone, hollow=True)
    set_block(cx, 18, 0, CREATE_BRASS)
    cone(cx, 3, 36, 4, 8, "oxidized_copper")
    set_block(cx, 45, 3, "sea_lantern")

# Side chapel masses beneath the towers.
for side in (-1, 1):
    xa, xb = sorted((19 * side, 36 * side))
    walls(xa, 6, xb, 22, 14, 31, stone, thickness=2)
    floor(xa, 6, xb, 22, 14, "stone_bricks")
    gable_roof(xa, 6, xb, 23, 32, "deepslate_tiles", ridge_axis="x", overhang=1)

# Large side chapel entries.
for side in (-1, 1):
    cx = 28 * side
    for t in range(2):
        hw = 5 + t
        line(cx - hw, 15, 7, cx - hw, 26, 7, "stone_bricks")
        line(cx + hw, 15, 7, cx + hw, 26, 7, "stone_bricks")
        line(cx - hw, 26, 7, cx, 34 + t, 7, "stone_bricks")
        line(cx + hw, 26, 7, cx, 34 + t, 7, "stone_bricks")
    clear(cx - 3, 15, 8, cx + 3, 26, 12)
    set_block(cx, 20, 8, "lantern")
    set_block(cx - 5, 25, 6, CREATE_COPPER)
    set_block(cx + 5, 25, 6, CREATE_COPPER)

# Flying buttresses with Create casing joints.
for side in (-1, 1):
    sx = 20 * side
    tx = 33 * side
    line(sx, 47, 12, tx, 56, 15, "stone_bricks")
    line(sx, 43, 13, tx, 52, 16, "polished_deepslate")
    line(sx, 38, 15, tx, 43, 17, "stone_bricks")
    set_block(tx, 56, 15, CREATE_ANDESITE)
    set_block(tx, 52, 16, CREATE_BRASS)

# Upper bridges.
for side in (-1, 1):
    x1, x2 = sorted((23 * side, 32 * side))
    fill(x1, 57, 20, x2, 58, 23, "deepslate_bricks")
    for x in range(x1, x2 + 1):
        if x % 2 == 0:
            set_block(x, 59, 20, "stone_brick_wall")
            set_block(x, 59, 23, "stone_brick_wall")

# Small mechanical galleries in front of the outer towers.
for cx in (-36, 36):
    fill(cx - 4, 24, 7, cx + 4, 24, 9, CREATE_ANDESITE)
    set_block(cx - 3, 25, 8, CREATE_BRASS)
    set_block(cx + 3, 25, 8, CREATE_BRASS)


# ---------------------------------------------------------------------------
# 4) Detail pass: lamps, banners, vegetation, copper and trim
# ---------------------------------------------------------------------------

# Large vertical teal banners
for x in (-20, 20):
    fill(x, 29, 6, x, 43, 6, "cyan_wool")
    set_block(x, 28, 6, "oxidized_copper")
    set_block(x, 44, 6, "oxidized_copper")

# Hanging lamps around portal
for x in (-15, -11, 11, 15):
    fill(x, 33, 4, x, 40, 4, "chain")
    set_block(x, 32, 4, "soul_lantern")

# Warm facade lights
for x in (-39, -31, -24, -18, 18, 24, 31, 39):
    for y in (15, 22):
        set_block(x, y, 6, "lantern")

# Stone railings around upper terrace
for x in range(-31, 32):
    if x < -14 or x > 14:
        set_block(x, 13, 1, "stone_brick_wall")
for z in range(2, 14):
    set_block(-31, 13, z, "stone_brick_wall")
    set_block(31, 13, z, "stone_brick_wall")

# Copper trim around portal shoulder
for x in range(-17, 18, 2):
    set_block(x, 42, 7, "oxidized_copper")

# Small crystals on side terraces and facade
for x, y, z in [(-20, 35, 7), (20, 35, 7), (-28, 28, 8), (28, 28, 8)]:
    crystal_cluster(x, y, z, 1)

# Portal-side planters
planter(-17, 1, -13, 5, 12)
planter(13, 1, 17, 5, 12)

# Benches on plaza
for cx in (-20, 20):
    fill(cx - 3, 2, -27, cx + 3, 2, -27, "dark_oak_slab[type=top]")
    set_block(cx - 3, 1, -27, "dark_oak_fence")
    set_block(cx + 3, 1, -27, "dark_oak_fence")

# Minor weathering near base, kept away from the portal glass
scatter(-40, 10, 8, -23, 25, 30, "mossy_stone_bricks", density=0.025)
scatter(23, 10, 8, 40, 25, 30, "mossy_stone_bricks", density=0.025)

# Create-powered portal machinery at the upper terrace.
for x in (-23, -18, 18, 23):
    set_block(x, 15, 3, CREATE_ANDESITE)
    set_block(x, 16, 3, CREATE_COPPER)
for x in (-12, -6, 6, 12):
    set_block(x, 15, 2, CREATE_BRASS)

# Final cyan highlights at tower and portal tips.
for x, y, z in [
    (0, 93, 11),
    (-36, 79, 18),
    (36, 79, 18),
    (-26, 86, 26),
    (26, 86, 26),
]:
    set_block(x, y, z, "sea_lantern")
