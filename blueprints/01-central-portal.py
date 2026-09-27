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
    # 7 x 5 footprint
    floor(cx - 3, z - 2, cx + 3, z + 2, y, "spruce_planks")
    for x in (cx - 3, cx + 3):
        for zz in (z - 2, z + 2):
            fill(x, y + 1, zz, x, y + 4, zz, "dark_oak_log")
    fill(cx - 3, y + 4, z - 2, cx + 3, y + 4, z + 2, awning)
    fill(cx - 2, y + 1, z + 1, cx + 2, y + 2, z + 1, "barrel")
    set_block(cx - 3, y + 3, z, "lantern")
    set_block(cx + 3, y + 3, z, "lantern")


def tower(cx, cz, base_y, body_h, radius=5):
    cylinder(cx, cz, base_y, body_h, radius, dark_stone, hollow=True)
    floor(cx - radius, cz - radius, cx + radius, cz + radius, base_y, "stone_bricks")

    # Structural ribs
    for dx, dz in ((radius, 0), (-radius, 0), (0, radius), (0, -radius)):
        fill(cx + dx, base_y, cz + dz, cx + dx, base_y + body_h + 1, cz + dz, "polished_deepslate")

    # Warm lower windows and cyan upper windows
    for yy in (base_y + 9, base_y + 19, base_y + 28):
        set_block(cx - radius, yy, cz, "light_blue_stained_glass")
        set_block(cx + radius, yy, cz, "light_blue_stained_glass")
        set_block(cx, yy, cz - radius, "light_blue_stained_glass")

    # Collar and roof
    cylinder(cx, cz, base_y + body_h - 2, 3, radius + 1, "stone_bricks", hollow=False)
    cone(cx, cz, base_y + body_h + 1, radius + 1, 10, "oxidized_copper", hollow=False)
    fill(cx, base_y + body_h + 10, cz, cx, base_y + body_h + 13, cz, "polished_blackstone")
    set_block(cx, base_y + body_h + 14, cz, "sea_lantern")


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

# Grand main staircase to portal terrace
for step in range(8):
    y = 4 + step
    z1 = -7 + step
    fill(-13 + step // 3, y, z1, 13 - step // 3, y, z1 + 1, "stone_bricks")

# Portal terrace
floor(-31, 1, 31, 13, 12, plaza_stone)
fill(-31, 4, 1, 31, 11, 13, stone)

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
# 2) Main cathedral massing
# ---------------------------------------------------------------------------

# Central hall
walls(-23, 10, 23, 30, 12, 61, stone, thickness=2)
floor(-23, 10, 23, 30, 12, "stone_bricks")
floor(-21, 12, 21, 28, 59, "deepslate_bricks")
gable_roof(-23, 10, 23, 30, 61, "deepslate_tiles", ridge_axis="z", overhang=2)

# Side wings
for side in (-1, 1):
    x1 = 23 * side
    x2 = 40 * side
    xa, xb = sorted((x1, x2))
    walls(xa, 9, xb, 28, 12, 34, stone, thickness=2)
    floor(xa, 9, xb, 28, 12, "stone_bricks")
    gable_roof(xa, 8, xb, 29, 35, "deepslate_tiles", ridge_axis="x", overhang=1)

# Main opening: carve through front wall and a few blocks inside
carve_pointed_opening(8, 15, 11, 14, 38, 59)

# Deep portal cavity
fill_pointed_opening(14, 17, 10, 14, 37, 57, "blue_stained_glass")
fill_pointed_opening(12, 13, 9, 15, 37, 56, "light_blue_stained_glass")
fill_pointed_opening(10, 11, 8, 16, 36, 54, "cyan_stained_glass")

# Hollow some of the center so the glow reads as depth
carve_pointed_opening(18, 25, 8, 16, 35, 52)

# Central energy column and glyph
fill(-1, 18, 15, 1, 48, 15, "sea_lantern")
for yy in (24, 31, 38, 45):
    fill(-5, yy, 15, 5, yy, 15, "light_blue_stained_glass")
    set_block(0, yy, 14, "sea_lantern")
for yy in range(20, 50, 4):
    set_block(-4, yy, 14, "prismarine_bricks")
    set_block(4, yy, 14, "prismarine_bricks")

# Layered portal frames
pointed_arch_frame(8, 14, 13, 39, 65, 3, "stone_bricks")
pointed_arch_frame(7, 12, 14, 38, 62, 2, "polished_deepslate")
pointed_arch_frame(6, 10, 15, 37, 58, 2, "prismarine_bricks")
pointed_arch_frame(5, 9, 16, 36, 55, 1, "sea_lantern")

# Deep buttresses framing the portal
for x in (-19, -16, 16, 19):
    fill(x, 12, 7, x, 58, 12, dark_stone)
    for yy in (20, 32, 44):
        fill(x - 1, yy, 6, x + 1, yy + 2, 12, "stone_bricks")
    set_block(x, 60, 9, "sea_lantern")

# Upper facade ribs and gothic crown
line(-23, 47, 8, 0, 76, 8, "stone_bricks")
line(23, 47, 8, 0, 76, 8, "stone_bricks")
line(-20, 48, 7, 0, 73, 7, "polished_deepslate")
line(20, 48, 7, 0, 73, 7, "polished_deepslate")

# Cyan vertical facade accents
for x in (-18, -13, 13, 18):
    fill(x, 27, 8, x, 54, 8, "cyan_stained_glass")
    for yy in range(29, 54, 7):
        set_block(x, yy, 7, "sea_lantern")

# High central crystal crown
crystal_cluster(0, 76, 11, 1)


# ---------------------------------------------------------------------------
# 3) Towers, side chapels and flying connections
# ---------------------------------------------------------------------------

# Main outer towers
tower(-34, 16, 12, 41, radius=6)
tower(34, 16, 12, 41, radius=6)

# Purple crystal chambers in outer towers
for cx in (-34, 34):
    clear(cx - 2, 28, 10, cx + 2, 44, 22)
    fill(cx - 2, 28, 15, cx + 2, 44, 17, "purple_stained_glass")
    crystal_cluster(cx, 30, 16, 1)
    with translate(cx, 0, 0):
        pointed_arch_frame(10, 4, 27, 39, 48, 1, "stone_bricks")

# Inner rear turrets
for cx in (-25, 25):
    cylinder(cx, 24, 30, 34, 4, "deepslate_bricks", hollow=True)
    cone(cx, 24, 64, 5, 9, "oxidized_copper")
    fill(cx, 73, 24, cx, 77, 24, "polished_blackstone")
    set_block(cx, 78, 24, "sea_lantern")

# Front lower corner towers
for cx in (-40, 40):
    cylinder(cx, 2, 5, 25, 3, stone, hollow=True)
    cone(cx, 2, 30, 4, 7, "oxidized_copper")
    set_block(cx, 38, 2, "sea_lantern")

# Side chapel arches / entries
for side in (-1, 1):
    cx = 27 * side
    # local gothic entry
    for t in range(2):
        hw = 5 + t
        line(cx - hw, 13, 7, cx - hw, 23, 7, "stone_bricks")
        line(cx + hw, 13, 7, cx + hw, 23, 7, "stone_bricks")
        line(cx - hw, 23, 7, cx, 30 + t, 7, "stone_bricks")
        line(cx + hw, 23, 7, cx, 30 + t, 7, "stone_bricks")
    clear(cx - 3, 13, 8, cx + 3, 23, 12)
    set_block(cx, 17, 8, "lantern")

# Flying buttress-like connectors from center to towers
for side in (-1, 1):
    sx = 20 * side
    tx = 31 * side
    line(sx, 42, 12, tx, 49, 14, "stone_bricks")
    line(sx, 39, 13, tx, 46, 15, "polished_deepslate")
    line(sx, 33, 15, tx, 37, 16, "stone_bricks")

# Upper bridges
for side in (-1, 1):
    x1, x2 = sorted((22 * side, 30 * side))
    fill(x1, 51, 20, x2, 52, 22, "deepslate_bricks")
    for x in range(x1, x2 + 1):
        if x % 2 == 0:
            set_block(x, 53, 20, "stone_brick_wall")


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

# Final cyan highlights at tower and portal tips
for x, y, z in [
    (0, 87, 11),
    (-34, 67, 16),
    (34, 67, 16),
    (-25, 79, 24),
    (25, 79, 24),
]:
    set_block(x, y, z, "sea_lantern")
