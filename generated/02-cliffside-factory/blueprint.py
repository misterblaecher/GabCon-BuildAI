# GabCon BuildAI - Great Cliffside Waterwheel Factory
# Reference: references/Forteresse industrielle steampunk en voxel.png
# Local origin: module center. Lake-facing facade is toward negative z.

stone = weighted_block({
    "stone_bricks": 0.62,
    "cracked_stone_bricks": 0.16,
    "andesite": 0.12,
    "mossy_stone_bricks": 0.04,
    "tuff_bricks": 0.06,
})
dark = weighted_block({
    "deepslate_bricks": 0.58,
    "polished_deepslate": 0.22,
    "deepslate_tiles": 0.12,
    "cracked_deepslate_bricks": 0.08,
})

CREATE_ANDESITE = "create:andesite_casing"
CREATE_BRASS = "create:brass_casing"
CREATE_COPPER = "create:copper_casing"


def floor_lamp(x, y, z):
    set_block(x, y, z, "polished_blackstone")
    set_block(x, y + 1, z, "lantern[hanging=false]")


def industrial_hall(cx, cz, w, d, y, h, roof_axis="x"):
    x1, x2 = cx - w // 2, cx + w // 2
    z1, z2 = cz - d // 2, cz + d // 2
    floor(x1, z1, x2, z2, y, "stone_bricks")
    walls(x1, z1, x2, z2, y, y + h, stone, thickness=2)
    gable_roof(x1, z1, x2, z2, y + h + 1, "deepslate_tiles", ridge_axis=roof_axis, overhang=2)
    for xx in range(x1 + 4, x2 - 3, 6):
        fill(xx, y + 5, z1, xx + 2, y + h - 4, z1, "orange_stained_glass")
        set_block(xx + 1, y + 6, z1 + 1, "glowstone")
    for xx in range(x1 + 3, x2 - 2, 8):
        set_block(xx, y + 2, z1 - 1, CREATE_ANDESITE)


def wheel(cx, cy, z, r):
    # Water wheel in the x/y plane, facing the lake.
    for depth in range(3):
        zz = z + depth
        for degree in range(0, 360, 4):
            a = math.radians(degree)
            x = cx + round(r * math.cos(a))
            y = cy + round(r * math.sin(a))
            set_block(x, y, zz, "dark_oak_planks")
            if degree % 12 == 0:
                x2 = cx + round((r - 2) * math.cos(a))
                y2 = cy + round((r - 2) * math.sin(a))
                set_block(x2, y2, zz, "spruce_planks")
    for degree in range(0, 360, 45):
        a = math.radians(degree)
        line(cx, cy, z + 1,
             cx + round((r - 2) * math.cos(a)),
             cy + round((r - 2) * math.sin(a)),
             z + 1, "dark_oak_log")
    cylinder(cx, z + 1, cy - 2, 5, 3, CREATE_COPPER, hollow=False)
    set_block(cx, cy, z - 1, CREATE_BRASS)


def chimney(cx, cz, y, h, r=2):
    cylinder(cx, cz, y, h, r, "deepslate_bricks", hollow=True)
    for yy in range(y + 8, y + h, 12):
        cylinder(cx, cz, yy, 2, r + 1, "cut_copper", hollow=True)
    cylinder(cx, cz, y + h - 2, 3, r + 1, "polished_blackstone_bricks", hollow=True)


def crane(px, py, pz, direction=1, length=20):
    fill(px - 1, py, pz - 1, px + 1, py + 18, pz + 1, "dark_oak_log")
    line(px, py + 18, pz, px + direction * length, py + 18, pz, "dark_oak_log")
    line(px, py + 17, pz + 1, px + direction * length, py + 17, pz + 1, "spruce_planks")
    line(px, py + 10, pz, px + direction * (length - 2), py + 18, pz, "dark_oak_fence")
    hook_x = px + direction * (length - 2)
    fill(hook_x, py + 8, pz, hook_x, py + 17, pz, "chain")
    hollow_box(hook_x - 2, py + 5, pz - 2, hook_x + 2, py + 8, pz + 2, "spruce_planks")
    set_block(px, py + 15, pz - 1, CREATE_BRASS)


# ---------------------------------------------------------------------------
# Foundation and terraced factory massing
# ---------------------------------------------------------------------------

# Compact stepped cliff foundation.
for level in range(6):
    inset = level * 4
    floor(-72 + inset, -16 + inset // 2, 72 - inset, 43 - inset, level * 2, stone)

# Waterfront quay.
floor(-72, -43, 72, -29, 4, "stone_bricks")
for x in range(-68, 69, 10):
    fill(x, 0, -42, x + 2, 4, -38, "stone_bricks")
    floor_lamp(x + 1, 5, -36)

# Main industrial halls, deliberately asymmetrical like the reference.
industrial_hall(-35, -4, 48, 34, 12, 38, "x")
industrial_hall(18, 1, 52, 38, 16, 44, "x")
industrial_hall(47, 16, 34, 28, 28, 40, "z")
industrial_hall(-5, 25, 45, 25, 42, 34, "x")
industrial_hall(-45, 24, 30, 24, 38, 34, "z")

# Tall machinery towers.
for cx, cz, y, h, r in [
    (-58, 12, 20, 58, 6),
    (-18, 30, 48, 52, 5),
    (33, 29, 42, 65, 6),
    (58, 29, 38, 48, 5),
]:
    cylinder(cx, cz, y, h, r, dark, hollow=True)
    cylinder(cx, cz, y + h - 3, 4, r + 1, "stone_bricks", hollow=False)
    cone(cx, cz, y + h + 1, r + 1, 9, "oxidized_copper")
    set_block(cx, y + h + 10, cz, "sea_lantern")

# Giant water wheels at the front.
wheel(-45, 24, -40, 15)
wheel(-14, 27, -40, 14)
wheel(20, 23, -40, 11)
wheel(48, 18, -40, 8)

# Axle supports.
for cx, cy, r in [(-45, 24, 15), (-14, 27, 14), (20, 23, 11), (48, 18, 8)]:
    fill(cx - 3, 4, -36, cx + 3, cy - 1, -32, stone)
    set_block(cx, cy, -36, CREATE_COPPER)
    set_block(cx, cy, -35, CREATE_BRASS)

# Controlled water channels and falls feeding wheels.
for x, top_y, wheel_y in [(-45, 48, 39), (-14, 52, 41), (20, 43, 34), (48, 34, 27)]:
    walls(x - 3, -31, x + 3, -27, top_y - 2, top_y, "stone_bricks")
    fill(x - 1, wheel_y, -32, x + 1, top_y, -30, "water[level=0]")

# ---------------------------------------------------------------------------
# Chimneys, bridges, stairs and machinery
# ---------------------------------------------------------------------------

for args in [
    (-61, 3, 45, 51, 2),
    (-48, 18, 55, 43, 2),
    (-29, 13, 48, 58, 2),
    (-4, 10, 55, 49, 2),
    (16, 21, 65, 53, 2),
    (38, 8, 61, 44, 2),
    (52, 20, 68, 42, 2),
    (62, 31, 55, 49, 2),
]:
    chimney(*args)

# Catwalk network.
for y, x1, x2, z in [
    (38, -67, -25, -18),
    (44, -24, 24, -15),
    (52, 12, 63, 7),
    (65, -38, 14, 22),
    (78, -20, 42, 31),
]:
    fill(x1, y, z - 1, x2, y + 1, z + 1, "spruce_planks")
    for x in range(x1, x2 + 1, 4):
        set_block(x, y + 2, z - 1, "dark_oak_fence")
        set_block(x, y + 2, z + 1, "dark_oak_fence")

# External stair runs.
for step in range(18):
    fill(48 - step, 22 + step, 24, 53 - step, 22 + step, 27, "stone_bricks")
for step in range(14):
    fill(-57 + step, 32 + step, 17, -53 + step, 32 + step, 20, "stone_bricks")

# Create-style machinery galleries.
for x, y, z in [
    (-52, 41, -15), (-39, 44, -15), (-25, 46, -15),
    (4, 55, -9), (19, 55, -9), (34, 59, -5),
    (45, 70, 16), (31, 82, 28),
]:
    set_block(x, y, z, CREATE_ANDESITE)
    set_block(x, y + 1, z, CREATE_COPPER)
    set_block(x + 1, y, z, CREATE_BRASS)

# Cyan energy column from the visual reference.
cylinder(28, 13, 52, 46, 4, "cyan_stained_glass", hollow=True)
for yy in range(55, 98, 6):
    set_block(28, yy, 13, "sea_lantern")
    set_block(24, yy, 13, CREATE_COPPER)
    set_block(32, yy, 13, CREATE_COPPER)

# Three cranes.
crane(-67, 11, -31, direction=1, length=24)
crane(58, 58, 26, direction=1, length=19)
crane(8, 70, 33, direction=-1, length=18)

# Warm lamps with physical support.
for x, y, z in [
    (-64, 18, -22), (-54, 31, -22), (-34, 28, -22),
    (-8, 34, -22), (15, 38, -22), (38, 31, -22), (61, 28, -22),
    (-45, 61, 8), (-18, 75, 23), (33, 74, 16), (56, 62, 24),
]:
    floor_lamp(x, y, z)
