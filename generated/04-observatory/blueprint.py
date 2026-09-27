# GabCon BuildAI - Steampunk Mountain Observatory
# Reference: references/Observatoire steampunk sur falaise.png
# Telescope points toward positive x and upward.

stone = weighted_block({
    "stone_bricks": 0.65,
    "andesite": 0.12,
    "cracked_stone_bricks": 0.12,
    "tuff_bricks": 0.07,
    "mossy_stone_bricks": 0.04,
})
CREATE_ANDESITE = "create:andesite_casing"
CREATE_BRASS = "create:brass_casing"
CREATE_COPPER = "create:copper_casing"


def lamp(x, y, z):
    set_block(x, y, z, "polished_blackstone")
    set_block(x, y + 1, z, "lantern[hanging=false]")


def ring_xy(cx, cy, z, r, block, step=5):
    for degree in range(0, 360, step):
        a = math.radians(degree)
        set_block(cx + round(r * math.cos(a)), cy + round(r * math.sin(a)), z, block)


def telescope_barrel(x1, y1, z1, x2, y2, z2):
    dx, dy, dz = x2 - x1, y2 - y1, z2 - z1
    steps = max(abs(dx), abs(dy), abs(dz))
    for i in range(0, steps + 1, 2):
        t = i / steps
        x = round(x1 + dx * t)
        y = round(y1 + dy * t)
        z = round(z1 + dz * t)
        sphere(x, y, z, 3, "deepslate_bricks", hollow=False)
        if i % 8 == 0:
            sphere(x, y, z, 4, "cut_copper", hollow=False)
            sphere(x, y, z, 3, "deepslate_bricks", hollow=False)


# Compact summit foundation.
for level in range(5):
    floor(-34 + level * 3, -27 + level * 2, 34 - level * 3, 29 - level * 2, level * 2, stone)

# Main tower.
cylinder(-8, 0, 8, 45, 12, stone, hollow=True)
cylinder(-8, 0, 49, 4, 14, "stone_bricks", hollow=False)
for yy in (18, 28, 38):
    for x, z in [(-20, 0), (4, 0), (-8, -12), (-8, 12)]:
        set_block(x, yy, z, "orange_stained_glass")
        set_block(x, yy + 1, z, "orange_stained_glass")

# Gallery around dome base.
cylinder(-8, 0, 50, 3, 16, "stone_bricks", hollow=True)
for degree in range(0, 360, 15):
    a = math.radians(degree)
    x = -8 + round(16 * math.cos(a))
    z = round(16 * math.sin(a))
    set_block(x, 53, z, "dark_oak_fence")

# Copper observation dome.
dome(-8, 53, 0, 14, "oxidized_copper", hollow=True)
for degree in range(0, 360, 30):
    a = math.radians(degree)
    line(-8, 53, 0,
         -8 + round(14 * math.cos(a)), 58, round(14 * math.sin(a)),
         "cut_copper")

# Telescope support mount.
cylinder(4, 2, 48, 18, 5, stone, hollow=False)
ring_xy(7, 64, 2, 9, CREATE_BRASS, step=6)
for degree in range(0, 360, 45):
    a = math.radians(degree)
    line(7, 64, 2,
         7 + round(8 * math.cos(a)),
         64 + round(8 * math.sin(a)),
         2, "dark_oak_log")
set_block(7, 64, 1, CREATE_COPPER)

# Telescope body from dome toward the sky.
telescope_barrel(1, 64, 0, 42, 82, 5)
# Lens housing and cool glass.
sphere(44, 83, 5, 5, "cut_copper", hollow=False)
sphere(45, 83, 5, 4, "light_blue_stained_glass", hollow=False)
set_block(46, 83, 5, "sea_lantern")

# Rear counterweight.
line(4, 62, 1, -5, 55, 1, "dark_oak_log")
sphere(-7, 53, 1, 4, CREATE_BRASS, hollow=False)

# Lower laboratories.
for cx, cz, w, d, h in [
    (13, 11, 25, 18, 16),
    (17, -12, 20, 17, 14),
    (-23, 12, 18, 16, 15),
]:
    x1, x2 = cx - w // 2, cx + w // 2
    z1, z2 = cz - d // 2, cz + d // 2
    floor(x1, z1, x2, z2, 10, "stone_bricks")
    walls(x1, z1, x2, z2, 10, 10 + h, stone, thickness=1)
    gable_roof(x1, z1, x2, z2, 11 + h, "deepslate_tiles", ridge_axis="x", overhang=1)
    for xx in range(x1 + 3, x2 - 2, 6):
        set_block(xx, 17, z1, "orange_stained_glass")

# Side towers and bridge arches.
for cx, cz in [(-28, -13), (27, 18)]:
    cylinder(cx, cz, 10, 30, 4, "deepslate_bricks", hollow=True)
    cone(cx, cz, 40, 5, 8, "oxidized_copper")
    set_block(cx, 49, cz, "sea_lantern")

fill(-27, 31, -13, -20, 33, -4, "stone_bricks")
fill(19, 29, 10, 27, 31, 18, "stone_bricks")

# Mechanical observatory trim.
for x, y, z in [
    (-20, 25, -2), (4, 25, -2), (-18, 38, 3), (3, 38, 3),
    (9, 57, 7), (13, 61, 6), (20, 69, 6), (29, 75, 6),
]:
    set_block(x, y, z, CREATE_ANDESITE)
    set_block(x, y + 1, z, CREATE_COPPER)

# Supported warm lights.
for x, y, z in [
    (-26, 12, -18), (-17, 12, -21), (8, 12, -20), (25, 12, -15),
    (-24, 12, 19), (-3, 12, 22), (20, 12, 22),
]:
    lamp(x, y, z)
