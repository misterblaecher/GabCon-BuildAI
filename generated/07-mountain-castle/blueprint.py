# GabCon BuildAI - Snowy Gothic Mountain Castle
# Reference: references/Forteresse gothique enneigée en blocs.png
# Front gate faces negative z.

stone = weighted_block({
    "stone_bricks": 0.68,
    "cracked_stone_bricks": 0.12,
    "andesite": 0.10,
    "polished_deepslate": 0.05,
    "tuff_bricks": 0.05,
})
CREATE_BRASS = "create:brass_casing"


def warm_window(x, y, z):
    set_block(x, y, z, "orange_stained_glass")
    set_block(x, y + 1, z, "orange_stained_glass")


def tower(cx, cz, base_y, body_h, r, roof_h=14):
    cylinder(cx, cz, base_y, body_h, r, stone, hollow=True)
    cylinder(cx, cz, base_y + body_h - 3, 4, r + 1, "stone_bricks", hollow=False)
    for yy in range(base_y + 10, base_y + body_h - 5, 15):
        set_block(cx, yy, cz - r, "orange_stained_glass")
        set_block(cx, yy + 1, cz - r, "orange_stained_glass")
    cone(cx, cz, base_y + body_h + 1, r + 1, roof_h, "deepslate_tiles", hollow=False)
    # Snow accents on roof shoulders.
    for degree in range(0, 360, 30):
        a = math.radians(degree)
        set_block(cx + round((r + 1) * math.cos(a)),
                  base_y + body_h + 2,
                  cz + round((r + 1) * math.sin(a)),
                  "snow_block")


def pointed_gate(z, half_w, bottom, spring, apex):
    for t in range(3):
        hw = half_w + t
        line(-hw, bottom - t, z, -hw, spring, z, "stone_bricks")
        line(hw, bottom - t, z, hw, spring, z, "stone_bricks")
        line(-hw, spring, z, 0, apex + t, z, "stone_bricks")
        line(hw, spring, z, 0, apex + t, z, "stone_bricks")


# Compact snowy summit foundation.
for level in range(6):
    floor(-64 + level * 4, -47 + level * 3, 64 - level * 4, 47 - level * 3, level * 2, stone)
floor(-58, -40, 58, 42, 12, "snow_block")

# Outer defensive wall.
walls(-56, -39, 56, 39, 12, 27, stone, thickness=2)

# Front gatehouse.
walls(-18, -42, 18, -27, 12, 40, stone, thickness=2)
clear(-6, 13, -43, 6, 29, -27)
pointed_gate(-43, 7, 12, 27, 39)
for step in range(9):
    fill(-8, 12 + step, -51 + step, 8, 12 + step, -50 + step, "stone_bricks")

# Central palace.
walls(-30, -18, 30, 22, 14, 62, stone, thickness=2)
gable_roof(-30, -18, 30, 22, 63, "deepslate_tiles", ridge_axis="z", overhang=2)
for x in range(-24, 25, 8):
    warm_window(x, 35, -19)
    warm_window(x, 48, -19)

# Dominant central tower and spire.
tower(0, 5, 44, 78, 11, roof_h=18)
for yy in (68, 83, 98, 113):
    fill(-3, yy, -7, 3, yy + 7, -7, "orange_stained_glass")
set_block(0, 141, 5, CREATE_BRASS)

# Eight secondary towers.
secondary = [
    (-44, -25, 14, 62, 7, 14),
    (44, -25, 14, 62, 7, 14),
    (-50, 18, 14, 74, 7, 15),
    (50, 18, 14, 68, 7, 14),
    (-27, 31, 14, 82, 7, 16),
    (28, 31, 14, 76, 7, 15),
    (-24, -5, 28, 64, 6, 13),
    (25, -2, 28, 58, 6, 13),
]
for spec in secondary:
    tower(*spec)

# Inner courtyard wings.
for cx, cz, w, d, h in [
    (-30, 8, 25, 24, 34),
    (31, 10, 24, 23, 32),
    (-15, 29, 20, 18, 30),
    (14, 30, 20, 18, 28),
]:
    x1, x2 = cx - w // 2, cx + w // 2
    z1, z2 = cz - d // 2, cz + d // 2
    walls(x1, z1, x2, z2, 14, 14 + h, stone, thickness=1)
    gable_roof(x1, z1, x2, z2, 15 + h, "deepslate_tiles", ridge_axis="x", overhang=1)
    warm_window(cx, 28, z1)

# Bridges between towers.
for y, x1, z1, x2, z2 in [
    (54, -44, -25, -24, -5),
    (54, 44, -25, 25, -2),
    (67, -50, 18, -27, 31),
    (65, 50, 18, 28, 31),
    (75, -24, -5, 0, 5),
    (72, 25, -2, 0, 5),
]:
    line(x1, y, z1, x2, y, z2, "stone_bricks")
    line(x1, y + 1, z1, x2, y + 1, z2, "stone_bricks")

# Flying buttresses around the central palace.
for x in (-30, -20, 20, 30):
    line(x, 48, -18, x + (-8 if x < 0 else 8), 28, -27, "stone_bricks")
    line(x, 50, 22, x + (-8 if x < 0 else 8), 30, 32, "stone_bricks")

# Courtyard snow, paths and warm supported lamps.
floor(-22, -30, 22, -21, 13, "snow_block")
for x in range(-18, 19, 9):
    set_block(x, 14, -25, "polished_blackstone")
    set_block(x, 15, -25, "lantern[hanging=false]")

# Snow caps on selected wall ledges.
for x in range(-55, 56, 4):
    set_block(x, 28, -39, "snow_block")
    set_block(x, 28, 39, "snow_block")
