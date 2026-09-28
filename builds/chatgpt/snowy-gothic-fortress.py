# Snowy Gothic Fortress / cathedral-castle
# Authored from the reference image supplied in ChatGPT.
# Front ceremonial gate faces -Z.  y is up.

stone = weighted_block({
    "stone_bricks": 0.72,
    "cracked_stone_bricks": 0.10,
    "andesite": 0.08,
    "tuff_bricks": 0.06,
    "polished_deepslate": 0.04,
})
roof = weighted_block({
    "deepslate_tiles": 0.80,
    "polished_deepslate": 0.12,
    "deepslate_bricks": 0.08,
})


def lancet(x, y, z, h=8, axis="z"):
    """Tall warm gothic window with a pointed cap."""
    if axis == "z":
        for yy in range(y, y + h - 2):
            set_block(x, yy, z, "orange_stained_glass")
        set_block(x, y + h - 2, z, "orange_stained_glass")
        set_block(x - 1, y + h - 3, z, "stone_bricks")
        set_block(x + 1, y + h - 3, z, "stone_bricks")
        set_block(x, y + h - 1, z, "stone_bricks")
    else:
        for yy in range(y, y + h - 2):
            set_block(x, yy, z, "orange_stained_glass")
        set_block(x, y + h - 2, z, "orange_stained_glass")
        set_block(x, y + h - 3, z - 1, "stone_bricks")
        set_block(x, y + h - 3, z + 1, "stone_bricks")
        set_block(x, y + h - 1, z, "stone_bricks")


def cross_finial(cx, y, cz):
    fill(cx, y, cz, cx, y + 5, cz, "gold_block")
    fill(cx - 2, y + 3, cz, cx + 2, y + 3, cz, "gold_block")


def tower(cx, cz, base_y, body_h, r, roof_h=15, windows=True):
    cylinder(cx, cz, base_y, body_h, r, stone, hollow=True)

    # projecting crown / corbel band
    cylinder(cx, cz, base_y + body_h - 5, 3, r + 1, "stone_bricks", hollow=True)
    for deg in range(0, 360, 45):
        a = math.radians(deg)
        bx = cx + round((r + 1) * math.cos(a))
        bz = cz + round((r + 1) * math.sin(a))
        fill(bx, base_y + body_h - 4, bz, bx, base_y + body_h, bz, "stone_bricks")

    if windows:
        for yy in range(base_y + 12, base_y + body_h - 8, 16):
            lancet(cx, yy, cz - r, h=6, axis="z")
            lancet(cx - r, yy, cz, h=6, axis="x")

    cone(cx, cz, base_y + body_h - 1, r + 2, roof_h, roof, hollow=False)

    # snowy shoulders
    sy = base_y + body_h
    for deg in range(0, 360, 20):
        a = math.radians(deg)
        set_block(cx + round((r + 1) * math.cos(a)), sy,
                  cz + round((r + 1) * math.sin(a)), "snow_block")

    cross_finial(cx, base_y + body_h + roof_h - 1, cz)


def pointed_arch(z, half_w, bottom, spring, apex, thickness=2):
    for t in range(thickness):
        w = half_w + t
        line(-w, bottom, z - t, -w, spring, z - t, "stone_bricks")
        line(w, bottom, z - t, w, spring, z - t, "stone_bricks")
        line(-w, spring, z - t, 0, apex, z - t, "stone_bricks")
        line(w, spring, z - t, 0, apex, z - t, "stone_bricks")


def buttress(x, z, inward_x, inward_z, y0, y1):
    # stepped base plus flying diagonal
    fill(x - 1, y0, z - 1, x + 1, y0 + 9, z + 1, "stone_bricks")
    line(x, y0 + 9, z, inward_x, y1, inward_z, "stone_bricks")
    line(x, y0 + 10, z, inward_x, y1 + 1, inward_z, "stone_bricks")


# ---------------------------------------------------------------------------
# Snowy mountain plinth: irregular stepped cliff, wider at the front.
# ---------------------------------------------------------------------------
for level in range(7):
    y = level * 2
    inset_x = level * 4
    inset_z = level * 3
    floor(-68 + inset_x, -52 + inset_z, 68 - inset_x, 50 - inset_z, y, stone)

# broken ledges around the silhouette
for x in range(-68, 69, 5):
    if (x // 5) % 3 != 0:
        fill(x, 0, -50, x + 2, 5 + abs(x) % 5, -47, "stone_bricks")
for x in range(-62, 63, 6):
    set_block(x, 13, -42, "snow_block")
    set_block(x, 13, 42, "snow_block")

floor(-56, -40, 56, 42, 13, "snow_block")


# ---------------------------------------------------------------------------
# Outer curtain wall and front gate.
# ---------------------------------------------------------------------------
walls(-56, -40, 56, 40, 13, 31, stone, thickness=2)

# crenellations
for x in range(-56, 57, 4):
    fill(x, 31, -40, x + 1, 34, -39, "stone_bricks")
    fill(x, 31, 39, x + 1, 34, 40, "stone_bricks")
for z in range(-36, 37, 4):
    fill(-56, 31, z, -55, 34, z + 1, "stone_bricks")
    fill(55, 31, z, 56, 34, z + 1, "stone_bricks")

# gatehouse mass
walls(-18, -43, 18, -25, 13, 45, stone, thickness=2)
clear(-6, 14, -44, 6, 31, -24)
pointed_arch(-44, 7, 13, 29, 42, thickness=3)

# grand stair
for step in range(11):
    fill(-9 + step // 3, 13 + step, -55 + step,
         9 - step // 3, 13 + step, -53 + step, "stone_bricks")

# gatehouse pinnacles
for x in (-15, 15):
    tower(x, -34, 28, 30, 4, roof_h=10, windows=False)


# ---------------------------------------------------------------------------
# Main cathedral-palace and dominant central spire.
# ---------------------------------------------------------------------------
walls(-31, -19, 31, 24, 16, 67, stone, thickness=2)
gable_roof(-32, -20, 32, 25, 68, roof, ridge_axis="z", overhang=2)

# front central gothic projection
walls(-11, -27, 11, -17, 16, 58, "stone_bricks", thickness=2)
for x in (-5, 0, 5):
    lancet(x, 29, -28, h=16, axis="z")

# repeated palace windows
for x in range(-25, 26, 10):
    lancet(x, 35, -20, h=10, axis="z")
    lancet(x, 51, -20, h=9, axis="z")
for z in range(-10, 19, 9):
    lancet(-32, 34, z, h=8, axis="x")
    lancet(32, 34, z, h=8, axis="x")

# central tower: large vertical emphasis
tower(0, 5, 47, 76, 11, roof_h=20)
# giant glowing lancets on its front
for x in (-3, 0, 3):
    lancet(x, 72, -7, h=18, axis="z")
lancet(0, 98, -7, h=14, axis="z")


# ---------------------------------------------------------------------------
# Dense forest of secondary towers, deliberately varied in height.
# ---------------------------------------------------------------------------
secondary = [
    (-47, -27, 15, 60, 7, 15),
    (47, -27, 15, 58, 7, 14),
    (-51, 18, 15, 69, 7, 16),
    (51, 18, 15, 66, 7, 15),
    (-28, 32, 15, 79, 7, 17),
    (29, 32, 15, 73, 7, 16),
    (-24, -2, 30, 59, 6, 14),
    (25, 0, 30, 56, 6, 13),
    (-15, 18, 38, 53, 5, 12),
    (16, 20, 38, 49, 5, 12),
]
for spec in secondary:
    tower(*spec)


# ---------------------------------------------------------------------------
# Inner wings and chapels create the layered, crowded gothic silhouette.
# ---------------------------------------------------------------------------
wings = [
    (-32, 7, 24, 26, 35, "x"),
    (32, 9, 23, 25, 34, "x"),
    (-17, 30, 20, 17, 31, "z"),
    (17, 31, 20, 17, 30, "z"),
    (-35, -14, 16, 18, 26, "z"),
    (36, -12, 16, 18, 24, "z"),
]
for cx, cz, w, d, h, ridge in wings:
    x1, x2 = cx - w // 2, cx + w // 2
    z1, z2 = cz - d // 2, cz + d // 2
    walls(x1, z1, x2, z2, 15, 15 + h, stone, thickness=1)
    gable_roof(x1, z1, x2, z2, 16 + h, roof, ridge_axis=ridge, overhang=1)
    lancet(cx, 28, z1 - 1, h=8, axis="z")


# ---------------------------------------------------------------------------
# Flying buttresses and high bridges.
# ---------------------------------------------------------------------------
for x in (-30, -20, 20, 30):
    buttress(x + (-9 if x < 0 else 9), -27, x, -18, 24, 50)
    buttress(x + (-9 if x < 0 else 9), 32, x, 23, 25, 52)

bridges = [
    (55, -47, -27, -24, -2),
    (55, 47, -27, 25, 0),
    (67, -51, 18, -28, 32),
    (66, 51, 18, 29, 32),
    (76, -24, -2, 0, 5),
    (73, 25, 0, 0, 5),
]
for y, x1, z1, x2, z2 in bridges:
    line(x1, y, z1, x2, y, z2, "stone_bricks")
    line(x1, y + 1, z1, x2, y + 1, z2, "stone_bricks")
    # simple rail rhythm
    for i in range(1, 5):
        t = i / 5
        px = round(x1 + (x2 - x1) * t)
        pz = round(z1 + (z2 - z1) * t)
        set_block(px, y + 2, pz, "cobblestone_wall")


# ---------------------------------------------------------------------------
# Courtyards, trees, snow and warm lights.
# ---------------------------------------------------------------------------
floor(-24, -31, 24, -22, 14, "snow_block")
floor(-20, 25, 20, 38, 14, "snow_block")

for x in range(-18, 19, 9):
    set_block(x, 15, -25, "polished_blackstone")
    set_block(x, 16, -25, "lantern")

# compact spruce trees on terraces
for tx, tz, th in [
    (-38, -18, 7), (38, -18, 6), (-42, 29, 8), (41, 30, 7),
    (-17, -35, 6), (18, -34, 6), (-31, 17, 5), (34, 20, 5),
]:
    fill(tx, 14, tz, tx, 14 + th, tz, "spruce_log")
    for yy, rr in [(14 + th - 1, 3), (14 + th + 1, 2), (14 + th + 3, 1)]:
        for xx in range(tx - rr, tx + rr + 1):
            for zz in range(tz - rr, tz + rr + 1):
                if abs(xx - tx) + abs(zz - tz) <= rr + 1:
                    set_block(xx, yy, zz, "spruce_leaves")
                    if (xx + zz + yy) % 3 == 0:
                        set_block(xx, yy + 1, zz, "snow_block")

# snow caps on major ledges
for x in range(-55, 56, 3):
    set_block(x, 35, -40, "snow_block")
    set_block(x, 35, 40, "snow_block")
for z in range(-39, 40, 4):
    set_block(-56, 35, z, "snow_block")
    set_block(56, 35, z, "snow_block")
