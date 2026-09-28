# Snowy Gothic Fortress / Cathedral Castle - V2
# Denser, more layered silhouette based on the supplied concept art.
# Front ceremonial gate faces -Z.

stone = weighted_block({
    "stone_bricks": 0.66,
    "cracked_stone_bricks": 0.10,
    "andesite": 0.10,
    "tuff_bricks": 0.08,
    "polished_deepslate": 0.06,
})
trim = weighted_block({
    "stone_bricks": 0.74,
    "andesite": 0.16,
    "polished_deepslate": 0.10,
})
roof = weighted_block({
    "deepslate_tiles": 0.76,
    "deepslate_bricks": 0.14,
    "polished_deepslate": 0.10,
})


def warm_lancet(x, y, z, h=8, axis="z"):
    for yy in range(y, y + h - 2):
        set_block(x, yy, z, "orange_stained_glass")
    set_block(x, y + h - 2, z, "orange_stained_glass")
    if axis == "z":
        set_block(x - 1, y + h - 3, z, "stone_brick_stairs[facing=east,half=bottom,shape=straight]")
        set_block(x + 1, y + h - 3, z, "stone_brick_stairs[facing=west,half=bottom,shape=straight]")
        set_block(x, y + h - 1, z, "stone_brick_slab[type=bottom]")
        if h >= 7:
            set_block(x, y + 2, z, "orange_stained_glass")
    else:
        set_block(x, y + h - 3, z - 1, "stone_brick_stairs[facing=south,half=bottom,shape=straight]")
        set_block(x, y + h - 3, z + 1, "stone_brick_stairs[facing=north,half=bottom,shape=straight]")
        set_block(x, y + h - 1, z, "stone_brick_slab[type=bottom]")


def cross_finial(cx, y, cz):
    fill(cx, y, cz, cx, y + 4, cz, "gold_block")
    fill(cx - 1, y + 2, cz, cx + 1, y + 2, cz, "gold_block")


def snow_ring(cx, y, cz, r):
    for deg in range(0, 360, 18):
        a = math.radians(deg)
        set_block(cx + round(r * math.cos(a)), y, cz + round(r * math.sin(a)), "snow_block")


def battlements(x1, z1, x2, z2, y):
    for x in range(x1, x2 + 1, 3):
        fill(x, y, z1, x + 1, y + 2, z1, "stone_bricks")
        fill(x, y, z2, x + 1, y + 2, z2, "stone_bricks")
        set_block(x, y + 3, z1, "snow_block")
        set_block(x, y + 3, z2, "snow_block")
    for z in range(z1, z2 + 1, 3):
        fill(x1, y, z, x1, y + 2, z + 1, "stone_bricks")
        fill(x2, y, z, x2, y + 2, z + 1, "stone_bricks")
        set_block(x1, y + 3, z, "snow_block")
        set_block(x2, y + 3, z, "snow_block")


def round_tower(cx, cz, base_y, body_h, r, roof_h=15, tall=True):
    cylinder(cx, cz, base_y, body_h, r, stone, hollow=True)
    cylinder(cx, cz, base_y + body_h - 4, 3, r + 1, trim, hollow=True)

    # slit windows around the body
    step = 14 if tall else 12
    for yy in range(base_y + 10, base_y + body_h - 7, step):
        warm_lancet(cx, yy, cz - r, h=6, axis="z")
        warm_lancet(cx, yy, cz + r, h=5, axis="z")
        warm_lancet(cx - r, yy, cz, h=5, axis="x")
        warm_lancet(cx + r, yy, cz, h=5, axis="x")

    # corner-looking pinnacles around the crown
    for deg in range(0, 360, 45):
        a = math.radians(deg)
        px = cx + round((r + 1) * math.cos(a))
        pz = cz + round((r + 1) * math.sin(a))
        fill(px, base_y + body_h - 3, pz, px, base_y + body_h + 2, pz, "stone_brick_wall")
        set_block(px, base_y + body_h + 3, pz, "stone_brick_slab[type=bottom]")

    cone(cx, cz, base_y + body_h - 1, r + 2, roof_h, roof, hollow=False)
    snow_ring(cx, base_y + body_h, cz, r + 1)
    cross_finial(cx, base_y + body_h + roof_h - 2, cz)


def square_turret(cx, cz, base_y, body_h, half_w=3, roof_h=9, axis="z"):
    x1, x2 = cx - half_w, cx + half_w
    z1, z2 = cz - half_w, cz + half_w
    walls(x1, z1, x2, z2, base_y, base_y + body_h, stone, thickness=1)
    battlements(x1, z1, x2, z2, base_y + body_h)
    gable_roof(x1 - 1, z1 - 1, x2 + 1, z2 + 1, base_y + body_h + 1, roof, ridge_axis=axis, overhang=1)
    warm_lancet(cx, base_y + 6, z1, h=5, axis="z")
    cross_finial(cx, base_y + body_h + roof_h - 2, cz)


def pointed_gate(z, half_w, bottom, spring, apex, depth=2):
    for d in range(depth):
        zz = z - d
        for t in range(3):
            hw = half_w + t
            line(-hw, bottom, zz, -hw, spring, zz, "stone_bricks")
            line(hw, bottom, zz, hw, spring, zz, "stone_bricks")
            line(-hw, spring, zz, 0, apex + t, zz, "stone_bricks")
            line(hw, spring, zz, 0, apex + t, zz, "stone_bricks")


def flying_buttress(x0, z0, x1, z1, y0, y1):
    fill(x0 - 1, y0, z0 - 1, x0 + 1, y0 + 9, z0 + 1, "stone_bricks")
    line(x0, y0 + 9, z0, x1, y1, z1, "stone_bricks")
    line(x0, y0 + 10, z0, x1, y1 + 1, z1, "stone_bricks")
    set_block(x1, y1 + 2, z1, "stone_brick_wall")


def arcade_bridge(x1, z1, x2, z2, y, posts=5):
    line(x1, y, z1, x2, y, z2, "stone_bricks")
    line(x1, y + 1, z1, x2, y + 1, z2, "stone_bricks")
    for i in range(posts + 1):
        t = i / posts
        px = round(x1 + (x2 - x1) * t)
        pz = round(z1 + (z2 - z1) * t)
        fill(px, y - 10, pz, px, y + 2, pz, "stone_brick_wall")
        if i < posts:
            mx = round(x1 + (x2 - x1) * ((i + 0.5) / posts))
            mz = round(z1 + (z2 - z1) * ((i + 0.5) / posts))
            line(px, y - 3, pz, mx, y - 7, mz, "stone_bricks")
    for i in range(1, posts):
        t = i / posts
        px = round(x1 + (x2 - x1) * t)
        pz = round(z1 + (z2 - z1) * t)
        set_block(px, y + 2, pz, "stone_brick_wall")


def tree(tx, tz, base_y=14, h=6):
    fill(tx, base_y, tz, tx, base_y + h, tz, "spruce_log")
    for yy, rr in [(base_y + h - 1, 3), (base_y + h + 1, 2), (base_y + h + 3, 1)]:
        for xx in range(tx - rr, tx + rr + 1):
            for zz in range(tz - rr, tz + rr + 1):
                if abs(xx - tx) + abs(zz - tz) <= rr + 1:
                    set_block(xx, yy, zz, "spruce_leaves")
                    if (xx + yy + zz) % 3 == 0:
                        set_block(xx, yy + 1, zz, "snow_block")


# ---------------------------------------------------------------------------
# Cliff / mountain pedestal
# ---------------------------------------------------------------------------
for level in range(8):
    y = level * 2
    floor(-72 + level * 4, -56 + level * 3, 72 - level * 4, 52 - level * 3, y, stone)

# rough front outcrops and side shelves
for x in range(-70, 71, 4):
    height = 4 + abs(x) % 8
    fill(x, 0, -54, x + 2, height, -50, "stone_bricks")
for z in range(-48, 41, 6):
    fill(-66, 0, z, -63, 5 + abs(z) % 6, z + 2, "stone_bricks")
    fill(63, 0, z, 66, 5 + abs(z) % 6, z + 2, "stone_bricks")

floor(-60, -44, 60, 44, 14, "snow_block")

# cut approach stairs into the plinth
for step in range(12):
    fill(-10 + step // 3, 14 + step, -60 + step, 10 - step // 3, 14 + step, -58 + step, "stone_bricks")


# ---------------------------------------------------------------------------
# Outer curtain wall and perimeter towers
# ---------------------------------------------------------------------------
walls(-58, -42, 58, 42, 14, 34, stone, thickness=2)
battlements(-58, -42, 58, 42, 34)

# outer corner towers
round_tower(-53, -36, 14, 58, 8, roof_h=16, tall=True)
round_tower(53, -36, 14, 56, 8, roof_h=15, tall=True)
round_tower(-54, 32, 14, 70, 7, roof_h=17, tall=True)
round_tower(54, 31, 14, 66, 7, roof_h=16, tall=True)

# extra slender front-side towers
round_tower(-28, -32, 15, 50, 5, roof_h=14, tall=False)
round_tower(28, -32, 15, 48, 5, roof_h=13, tall=False)
round_tower(-18, 35, 15, 44, 4, roof_h=12, tall=False)
round_tower(18, 35, 15, 42, 4, roof_h=12, tall=False)


# ---------------------------------------------------------------------------
# Front gatehouse and lower forebuildings
# ---------------------------------------------------------------------------
walls(-20, -45, 20, -25, 14, 44, stone, thickness=2)
clear(-7, 15, -46, 7, 31, -24)
pointed_gate(-45, 7, 14, 29, 42, depth=3)

# flanking turrets around the gate
square_turret(-16, -30, 18, 18, half_w=3, roof_h=8, axis="x")
square_turret(16, -30, 18, 18, half_w=3, roof_h=8, axis="x")
square_turret(-8, -18, 16, 14, half_w=2, roof_h=7, axis="z")
square_turret(8, -18, 16, 14, half_w=2, roof_h=7, axis="z")

# banner strips near the portal
for x in (-10, 10):
    fill(x, 18, -24, x, 30, -24, "blue_wool")
    fill(x, 20, -24, x, 28, -24, "white_wool")


# ---------------------------------------------------------------------------
# Main cathedral-palace volume
# ---------------------------------------------------------------------------
walls(-32, -20, 32, 24, 16, 70, stone, thickness=2)
gable_roof(-33, -21, 33, 25, 71, roof, ridge_axis="z", overhang=2)

# tall front nave / grand facade
walls(-12, -28, 12, -16, 16, 61, trim, thickness=2)
pointed_gate(-28, 8, 16, 39, 57, depth=2)
for x in (-5, 0, 5):
    warm_lancet(x, 28, -29, h=18, axis="z")

# side aisle chapels on the front
for cx in (-22, 22):
    walls(cx - 7, -15, cx + 7, -2, 16, 38, stone, thickness=1)
    gable_roof(cx - 8, -16, cx + 8, -1, 39, roof, ridge_axis="x", overhang=1)
    square_turret(cx - 8, -10, 18, 14, half_w=2, roof_h=6, axis="z")
    square_turret(cx + 8, -10, 18, 14, half_w=2, roof_h=6, axis="z")
    warm_lancet(cx, 24, -16, h=10, axis="z")

# main palace windows front and sides
for x in range(-26, 27, 8):
    warm_lancet(x, 34, -21, h=10, axis="z")
    warm_lancet(x, 50, -21, h=9, axis="z")
for z in range(-10, 21, 8):
    warm_lancet(-33, 34, z, h=8, axis="x")
    warm_lancet(33, 34, z, h=8, axis="x")

# snow on palace roof ledges
for x in range(-32, 33, 3):
    set_block(x, 71, -20, "snow_block")
    set_block(x, 71, 24, "snow_block")


# ---------------------------------------------------------------------------
# Central giant spire and clustered towers around it
# ---------------------------------------------------------------------------
round_tower(0, 5, 46, 82, 11, roof_h=22, tall=True)
for x in (-3, 0, 3):
    warm_lancet(x, 72, -7, h=20, axis="z")
    warm_lancet(x, 95, -6, h=12, axis="z")

# clustered attendants around the spire
round_tower(-12, 2, 42, 50, 4, roof_h=12, tall=False)
round_tower(12, 2, 42, 50, 4, roof_h=12, tall=False)
round_tower(-10, 18, 38, 43, 3, roof_h=10, tall=False)
round_tower(10, 18, 38, 43, 3, roof_h=10, tall=False)


# ---------------------------------------------------------------------------
# Secondary towers and crowded inner wings to match the concept silhouette
# ---------------------------------------------------------------------------
secondary = [
    (-47, -25, 16, 60, 7, 16),
    (47, -25, 16, 58, 7, 15),
    (-28, 31, 16, 78, 7, 17),
    (29, 31, 16, 74, 7, 16),
    (-24, -2, 29, 60, 6, 14),
    (25, -1, 29, 58, 6, 14),
    (-40, 8, 16, 43, 5, 12),
    (40, 10, 16, 41, 5, 12),
    (-12, 30, 16, 38, 4, 10),
    (12, 31, 16, 36, 4, 10),
]
for spec in secondary:
    round_tower(*spec)

wings = [
    (-33, 8, 24, 28, 36, "x"),
    (33, 10, 24, 27, 35, "x"),
    (-16, 30, 18, 18, 30, "z"),
    (16, 31, 18, 18, 29, "z"),
    (-36, -13, 16, 20, 26, "z"),
    (36, -12, 16, 18, 24, "z"),
    (-2, 27, 18, 12, 26, "x"),
]
for cx, cz, w, d, h, ridge in wings:
    x1, x2 = cx - w // 2, cx + w // 2
    z1, z2 = cz - d // 2, cz + d // 2
    walls(x1, z1, x2, z2, 16, 16 + h, stone, thickness=1)
    gable_roof(x1, z1, x2, z2, 17 + h, roof, ridge_axis=ridge, overhang=1)
    warm_lancet(cx, 27, z1, h=8, axis="z")
    square_turret(x1, cz, 17, 12, half_w=2, roof_h=6, axis="z")
    square_turret(x2, cz, 17, 12, half_w=2, roof_h=6, axis="z")


# ---------------------------------------------------------------------------
# Buttresses, elevated bridges, arcades
# ---------------------------------------------------------------------------
for x in (-28, -20, 20, 28):
    flying_buttress(x - 10 if x < 0 else x + 10, -28, x, -18, 24, 51)
    flying_buttress(x - 10 if x < 0 else x + 10, 34, x, 24, 25, 53)

arcade_bridge(-53, -24, -26, -3, 56, posts=4)
arcade_bridge(53, -24, 26, -2, 55, posts=4)
arcade_bridge(-54, 20, -29, 31, 69, posts=4)
arcade_bridge(54, 19, 30, 31, 67, posts=4)
arcade_bridge(-23, -1, 0, 5, 76, posts=4)
arcade_bridge(24, 0, 0, 5, 74, posts=4)


# ---------------------------------------------------------------------------
# Courtyard details, lamps, trees, snow accents
# ---------------------------------------------------------------------------
floor(-24, -32, 24, -22, 15, "snow_block")
floor(-20, 23, 20, 38, 15, "snow_block")

for x in range(-18, 19, 9):
    set_block(x, 15, -25, "polished_blackstone")
    set_block(x, 16, -25, "lantern")

for pos in [(-41, -18, 7), (41, -18, 7), (-40, 29, 8), (40, 30, 8), (-14, -35, 6), (15, -35, 6), (-28, 15, 5), (29, 17, 5)]:
    tree(*pos)

# snow ledges on the curtain wall top
for x in range(-58, 59, 3):
    set_block(x, 37, -42, "snow_block")
    set_block(x, 37, 42, "snow_block")
for z in range(-41, 42, 3):
    set_block(-58, 37, z, "snow_block")
    set_block(58, 37, z, "snow_block")