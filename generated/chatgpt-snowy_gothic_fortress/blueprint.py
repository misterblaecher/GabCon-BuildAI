# Snowy Gothic Fortress
# Reference-driven deterministic mcbuild DSL blueprint.
# Front entrance faces negative Z.
#
# Design goals:
# - a dense cathedral-castle silhouette with one dominant central spire
# - layered defensive walls and a monumental pointed gate
# - many steep dark roofs, pinnacles, flying buttresses, and warm lancet windows
# - stepped snowy rock base rather than a flat rectangular plinth

STONE = weighted_block(
    {
        "stone_bricks": 0.62,
        "cracked_stone_bricks": 0.12,
        "andesite": 0.09,
        "tuff_bricks": 0.08,
        "polished_andesite": 0.05,
        "polished_deepslate": 0.04,
    }
)
CLEAN = "stone_bricks"
TRIM = "polished_andesite"
DARK = "deepslate_tiles"
ROOF = "dark_oak_planks"
GLASS = "orange_stained_glass"
SNOW = "snow_block"


def gold_cross(x, y, z):
    set_block(x, y, z, "gold_block")
    set_block(x, y + 1, z, "gold_block")
    set_block(x, y + 2, z, "gold_block")
    set_block(x - 1, y + 1, z, "gold_block")
    set_block(x + 1, y + 1, z, "gold_block")


def lancet_front(cx, z, y0, width, height, glass=GLASS):
    # Pointed lancet cut directly into a Z-facing wall.
    half = width // 2
    shoulder = height - half - 1
    for dy in range(height):
        if dy < shoulder:
            hw = half
        else:
            hw = max(0, half - (dy - shoulder))
        for x in range(cx - hw, cx + hw + 1):
            set_block(x, y0 + dy, z, glass)

    # Stone frame and pointed crown.
    line(cx - half - 1, y0 - 1, z, cx - half - 1, y0 + shoulder, z, CLEAN)
    line(cx + half + 1, y0 - 1, z, cx + half + 1, y0 + shoulder, z, CLEAN)
    line(cx - half - 1, y0 + shoulder, z, cx, y0 + height + 1, z, CLEAN)
    line(cx + half + 1, y0 + shoulder, z, cx, y0 + height + 1, z, CLEAN)


def lancet_side(x, cz, y0, width, height, glass=GLASS):
    # Pointed lancet in an X-facing wall.
    half = width // 2
    shoulder = height - half - 1
    for dy in range(height):
        if dy < shoulder:
            hw = half
        else:
            hw = max(0, half - (dy - shoulder))
        for z in range(cz - hw, cz + hw + 1):
            set_block(x, y0 + dy, z, glass)

    line(x, y0 - 1, cz - half - 1, x, y0 + shoulder, cz - half - 1, CLEAN)
    line(x, y0 - 1, cz + half + 1, x, y0 + shoulder, cz + half + 1, CLEAN)
    line(x, y0 + shoulder, cz - half - 1, x, y0 + height + 1, cz, CLEAN)
    line(x, y0 + shoulder, cz + half + 1, x, y0 + height + 1, cz, CLEAN)


def steep_square_roof(cx, cz, y, width, height, block=ROOF):
    # Layered stepped roof with a deliberately steep Gothic pitch.
    half = width // 2
    for dy in range(height):
        inset = min(half - 1, (dy * half) // max(1, height - 1))
        r = max(1, half - inset)
        yy = y + dy
        for x in range(cx - r, cx + r + 1):
            set_block(x, yy, cz - r, block)
            set_block(x, yy, cz + r, block)
        for z in range(cz - r + 1, cz + r):
            set_block(cx - r, yy, z, block)
            set_block(cx + r, yy, z, block)

    # Apply snow last so it remains visible as broken white bands on the roof.
    for dy in (0, 3, 7):
        if dy >= height:
            continue
        inset = min(half - 1, (dy * half) // max(1, height - 1))
        r = max(1, half - inset)
        yy = y + dy + 1
        for x in range(cx - r, cx + r + 1, 2):
            set_block(x, yy, cz - r, SNOW)
            set_block(x, yy, cz + r, SNOW)
        for z in range(cz - r + 1, cz + r, 2):
            set_block(cx - r, yy, z, SNOW)
            set_block(cx + r, yy, z, SNOW)

    set_block(cx, y + height, cz, DARK)
    set_block(cx, y + height + 1, cz, DARK)


def square_tower(cx, cz, base_y, width, body_h, roof_h, window_levels=(18, 34), finial=True):
    half = width // 2
    x1, x2 = cx - half, cx + half
    z1, z2 = cz - half, cz + half
    top = base_y + body_h

    walls(x1, z1, x2, z2, base_y, top, STONE, thickness=2)
    floor(x1, z1, x2, z2, base_y, STONE)
    floor(x1, z1, x2, z2, top, CLEAN)

    # Strong vertical corner buttresses.
    for bx in (x1 - 1, x2):
        for bz in (z1 - 1, z2):
            fill(bx, base_y, bz, bx + 1, top - 5, bz + 1, CLEAN)
            set_block(bx, top - 4, bz, TRIM)
            set_block(bx + 1, top - 4, bz + 1, TRIM)

    # Decorative belt courses.
    for yy in (base_y + body_h // 3, base_y + (2 * body_h) // 3):
        frame(x1 - 1, yy, z1 - 1, x2 + 1, yy + 1, z2 + 1, TRIM)

    for offset in window_levels:
        if offset < body_h - 8:
            lancet_front(cx, z1 - 1, base_y + offset, 2, 7)
            lancet_front(cx, z2 + 1, base_y + offset, 2, 7)
            lancet_side(x1 - 1, cz, base_y + offset, 2, 7)
            lancet_side(x2 + 1, cz, base_y + offset, 2, 7)

    # Eave band and steep roof.
    frame(x1 - 2, top - 2, z1 - 2, x2 + 2, top, z2 + 2, CLEAN)
    steep_square_roof(cx, cz, top + 1, width + 5, roof_h, ROOF)

    if finial:
        gold_cross(cx, top + roof_h + 2, cz)


def pinnacle(cx, cz, base_y, shaft_h=18, width=5, roof_h=9):
    half = width // 2
    walls(cx - half, cz - half, cx + half, cz + half, base_y, base_y + shaft_h, CLEAN)
    for yy in range(base_y + 5, base_y + shaft_h - 3, 8):
        lancet_front(cx, cz - half - 1, yy, 1, 4, "orange_stained_glass")
    steep_square_roof(cx, cz, base_y + shaft_h + 1, width + 2, roof_h, DARK)
    set_block(cx, base_y + shaft_h + roof_h + 3, cz, "gold_block")


def flying_buttress(x_wall, z_wall, y_wall, x_pier, z_pier, y_pier):
    # Two ribs, one above the other, plus a solid outer pier.
    line(x_wall, y_wall, z_wall, x_pier, y_pier + 12, z_pier, CLEAN)
    line(x_wall, y_wall - 5, z_wall, x_pier, y_pier + 6, z_pier, CLEAN)
    fill(x_pier - 1, y_pier, z_pier - 1, x_pier + 1, y_pier + 18, z_pier + 1, CLEAN)
    pinnacle(x_pier, z_pier, y_pier + 14, shaft_h=8, width=3, roof_h=5)


# ---------------------------------------------------------------------------
# 1. Stepped mountain / snowy foundation
# ---------------------------------------------------------------------------

terraces = [
    (74, 58, 0),
    (62, 49, 6),
    (54, 42, 12),
]
for hx, hz, y in terraces:
    # Concentric cliff rings.  Avoid stacking huge solid plates: the renderer
    # works on exposed voxels and the rings preserve the stepped mountain shape
    # at a fraction of the surface budget.
    walls(-hx, -hz, hx, hz, y, y + 3, STONE, thickness=2)
    # Broken snowy cornice on the exposed ledge.
    for x in range(-hx + 2, hx - 1, 3):
        set_block(x, y + 4, -hz, SNOW)
        set_block(x, y + 4, hz, SNOW)
    for z in range(-hz + 2, hz - 1, 3):
        set_block(-hx, y + 4, z, SNOW)
        set_block(hx, y + 4, z, SNOW)

# Irregular cliff buttresses on the visible front and side edges.
for x in range(-66, 67, 11):
    h = 4 + (abs(x) * 3) % 7
    fill(x - 2, 0, -60, x + 2, h, -54, STONE)
for z in range(-48, 49, 13):
    fill(-72, 0, z - 3, -66, 5 + (abs(z) % 6), z + 3, STONE)
    fill(66, 0, z - 3, 72, 4 + ((abs(z) + 2) % 7), z + 3, STONE)

# Snow shelf on the summit and broken snow shelves down the cliff.
floor(-52, -39, 52, 39, 13, SNOW)
for x in range(-70, 71, 8):
    set_block(x, 3 + (abs(x) % 5), -58 + (abs(x) % 4), SNOW)
    set_block(x, 6 + (abs(x) % 4), 54 - (abs(x) % 5), SNOW)
for z in range(-50, 51, 8):
    set_block(-68 + (abs(z) % 4), 4 + (abs(z) % 4), z, SNOW)
    set_block(68 - (abs(z) % 5), 5 + (abs(z) % 3), z, SNOW)


# ---------------------------------------------------------------------------
# 2. Outer enceinte and monumental gate
# ---------------------------------------------------------------------------

walls(-52, -39, 52, 39, 14, 34, STONE, thickness=2)
for x in range(-50, 51, 5):
    set_block(x, 35, -39, CLEAN)
    set_block(x, 35, 39, CLEAN)
    if x % 10 == 0:
        set_block(x, 36, -39, SNOW)
        set_block(x, 36, 39, SNOW)
for z in range(-35, 36, 5):
    set_block(-52, 35, z, CLEAN)
    set_block(52, 35, z, CLEAN)

# Front gatehouse mass.
walls(-18, -43, 18, -28, 14, 52, STONE, thickness=2)
frame(-19, 45, -44, 19, 49, -27, CLEAN)

# Main pointed entrance opening and deep passage.
clear(-7, 15, -44, 7, 33, -27)
for z in range(-44, -26):
    line(-8, 14, z, -8, 31, z, CLEAN)
    line(8, 14, z, 8, 31, z, CLEAN)
    line(-8, 31, z, 0, 43, z, CLEAN)
    line(8, 31, z, 0, 43, z, CLEAN)

# Heavy stair approach.
for step in range(11):
    floor(-10 + step // 4, -55 + step, 10 - step // 4, -54 + step, 3 + step, CLEAN)

# Gatehouse towers.
square_tower(-15, -36, 14, 11, 48, 16, window_levels=(14, 28), finial=True)
square_tower(15, -36, 14, 11, 46, 15, window_levels=(14, 28), finial=True)

# Monumental dark gate leaf on the facade; the tunnel remains carved behind it.
for yy in range(16, 32):
    hw = 6 if yy < 27 else max(1, 6 - (yy - 27))
    for xx in range(-hw, hw + 1):
        set_block(xx, yy, -44, "dark_oak_planks")
for yy in (20, 25):
    line(-5, yy, -45, 5, yy, -45, "polished_blackstone")
set_block(-4, 22, -45, "lantern[hanging=false]")
set_block(4, 22, -45, "lantern[hanging=false]")

# Gatehouse upper chapel window.
lancet_front(0, -44, 35, 5, 13, "orange_stained_glass")


# ---------------------------------------------------------------------------
# 3. Dense cathedral / palace core
# ---------------------------------------------------------------------------

# Main nave.
walls(-29, -22, 29, 23, 16, 72, STONE, thickness=2)
floor(-29, -22, 29, 23, 16, STONE)
gable_roof(-31, -24, 31, 25, 73, ROOF, ridge_axis="z", overhang=2)

# Side aisles create the stepped cathedral profile.
walls(-41, -16, -29, 20, 18, 55, STONE, thickness=2)
walls(29, -16, 41, 20, 18, 55, STONE, thickness=2)
gable_roof(-43, -18, -28, 22, 56, DARK, ridge_axis="z", overhang=1)
gable_roof(28, -18, 43, 22, 56, DARK, ridge_axis="z", overhang=1)

# Large warm nave windows.
for x in (-20, -10, 0, 10, 20):
    lancet_front(x, -23, 34, 3, 12)
for z in (-8, 5, 17):
    lancet_side(-42, z, 31, 2, 10)
    lancet_side(42, z, 31, 2, 10)

# Front transept/chancel volume and rose-like clustered glass.
walls(-18, -31, 18, -20, 18, 66, STONE, thickness=2)
gable_roof(-20, -33, 20, -18, 67, ROOF, ridge_axis="x", overhang=2)
lancet_front(0, -32, 33, 6, 18)
lancet_front(-10, -32, 38, 2, 10)
lancet_front(10, -32, 38, 2, 10)


# ---------------------------------------------------------------------------
# 4. Dominant central tower, giant stained glass, and spire
# ---------------------------------------------------------------------------

# First stage.
walls(-14, -8, 14, 15, 50, 104, STONE, thickness=3)
frame(-15, 72, -9, 15, 76, 16, CLEAN)
frame(-15, 94, -9, 15, 98, 16, CLEAN)

# Monumental front lancet.
lancet_front(0, -9, 64, 7, 29, "orange_stained_glass")
# Secondary high lancets on all faces.
lancet_front(0, 16, 80, 4, 17, "orange_stained_glass")
lancet_side(-15, 3, 78, 4, 17)
lancet_side(15, 3, 78, 4, 17)

# Narrower upper belfry.
walls(-11, -5, 11, 12, 105, 132, STONE, thickness=2)
for cx in (-6, 0, 6):
    lancet_front(cx, -6, 110, 2, 12, "orange_stained_glass")
lancet_side(-12, 3, 111, 3, 12, "orange_stained_glass")
lancet_side(12, 3, 111, 3, 12, "orange_stained_glass")

# Crown stage and very tall spire.
walls(-9, -3, 9, 10, 133, 145, CLEAN, thickness=2)
frame(-11, 140, -5, 11, 145, 12, TRIM)
steep_square_roof(0, 3, 146, 21, 42, ROOF)
gold_cross(0, 191, 3)

# Four corner pinnacles wrapping the central tower.
for px, pz in [(-15, -7), (15, -7), (-15, 14), (15, 14)]:
    pinnacle(px, pz, 104, shaft_h=30, width=6, roof_h=13)


# ---------------------------------------------------------------------------
# 5. Secondary skyline towers — varied heights like the reference
# ---------------------------------------------------------------------------

tower_specs = [
    (-46, -24, 14, 13, 64, 18, (18, 38)),
    (46, -24, 14, 12, 67, 18, (20, 40)),
    (-50, 11, 14, 12, 82, 20, (20, 45, 63)),
    (50, 10, 14, 11, 73, 18, (18, 40, 57)),
    (-32, 29, 16, 13, 92, 21, (24, 50, 72)),
    (30, 30, 16, 12, 84, 20, (22, 46, 65)),
    (-27, -4, 31, 10, 72, 18, (18, 39, 56)),
    (28, -1, 31, 10, 66, 17, (18, 38, 52)),
]
for spec in tower_specs:
    square_tower(*spec, finial=True)


# Additional thin sanctum spires tightly packed around the central keep.
# These create the dense crown of secondary needles visible in the reference.
inner_spires = [
    (-20, 8, 50, 7, 72, 17),
    (20, 8, 50, 7, 70, 17),
    (-11, 22, 48, 7, 66, 16),
    (11, 22, 48, 7, 63, 15),
    (-22, -10, 42, 7, 58, 15),
    (22, -10, 42, 7, 56, 14),
]
for cx, cz, by, w, bh, rh in inner_spires:
    square_tower(cx, cz, by, w, bh, rh, window_levels=(18, 38), finial=True)

# Two isolated edge towers extend the skyline beyond the main enceinte.
square_tower(-59, -2, 12, 9, 68, 18, window_levels=(18, 40), finial=True)
square_tower(59, 6, 12, 9, 73, 19, window_levels=(20, 43), finial=True)
line(-59, 46, -2, -52, 42, -2, CLEAN)
line(59, 49, 6, 52, 44, 6, CLEAN)


# ---------------------------------------------------------------------------
# 6. Lower chapel clusters and dense roofscape
# ---------------------------------------------------------------------------

chapels = [
    (-37, -5, 15, 15, 18, 32),
    (37, -3, 16, 15, 18, 34),
    (-21, 25, 19, 17, 18, 36),
    (19, 26, 18, 16, 18, 34),
    (-11, -28, 12, 11, 18, 28),
    (11, -28, 12, 11, 18, 27),
]
for cx, cz, w, d, y, h in chapels:
    x1, x2 = cx - w // 2, cx + w // 2
    z1, z2 = cz - d // 2, cz + d // 2
    walls(x1, z1, x2, z2, y, y + h, STONE, thickness=1)
    gable_roof(x1 - 1, z1 - 1, x2 + 1, z2 + 1, y + h + 1, ROOF, ridge_axis="x", overhang=1)
    lancet_front(cx, z1 - 1, y + 10, 2, 8)


# ---------------------------------------------------------------------------
# 7. Flying buttresses and elevated bridges
# ---------------------------------------------------------------------------

for z in (-14, 0, 14):
    flying_buttress(-29, z, 62, -45, z, 20)
    flying_buttress(29, z, 62, 45, z, 20)

# Rear buttresses around the central tower.
for x in (-10, 10):
    flying_buttress(x, 15, 98, x, 31, 32)

# Stone bridges between major masses.
bridges = [
    (-46, -24, -27, -4, 52),
    (46, -24, 28, -1, 54),
    (-50, 11, -32, 29, 68),
    (50, 10, 30, 30, 66),
    (-27, -4, -14, 3, 80),
    (28, -1, 14, 3, 78),
]
for x1, z1, x2, z2, y in bridges:
    line(x1, y, z1, x2, y, z2, CLEAN)
    line(x1, y + 1, z1, x2, y + 1, z2, CLEAN)
    line(x1, y + 2, z1, x2, y + 2, z2, "stone_brick_wall")


# ---------------------------------------------------------------------------
# 8. Snow, courtyard detail, and warm light rhythm
# ---------------------------------------------------------------------------

# Snowy terraces inside the enceinte.
floor(-22, -38, 22, -33, 15, SNOW)
floor(-48, 24, -34, 36, 15, SNOW)
floor(34, 24, 48, 36, 15, SNOW)

# Snow caps on buttresses and parapets.
for x in range(-50, 51, 4):
    if x < -19 or x > 19:
        set_block(x, 35, -38, SNOW)
for z in range(-35, 36, 4):
    set_block(-51, 35, z, SNOW)
    set_block(51, 35, z, SNOW)

# Warm lamps on the approach and courtyard.
for x in (-18, -9, 0, 9, 18):
    set_block(x, 15, -34, CLEAN)
    set_block(x, 16, -34, "lantern[hanging=false]")
for x, z in [(-34, -20), (34, -20), (-42, 20), (42, 20), (-20, 18), (20, 18)]:
    set_block(x, 17, z, CLEAN)
    set_block(x, 18, z, "lantern[hanging=false]")

# Small dark evergreen silhouettes to break up the snow near the walls.
def pine(cx, cz, y, h):
    fill(cx, y, cz, cx, y + h, cz, "spruce_log")
    for yy in range(y + 2, y + h + 1, 3):
        r = max(1, (h - (yy - y)) // 4)
        for x in range(cx - r, cx + r + 1):
            for z in range(cz - r, cz + r + 1):
                if abs(x - cx) + abs(z - cz) <= r + 1:
                    set_block(x, yy, z, "spruce_leaves")
        set_block(cx, yy + 1, cz, SNOW)

for px, pz, ph in [
    (-45, -34, 8), (-34, -35, 10), (36, -34, 9), (45, -31, 11),
    (-48, 31, 8), (-40, 34, 9), (40, 33, 8), (47, 30, 10),
]:
    pine(px, pz, 15, ph)
