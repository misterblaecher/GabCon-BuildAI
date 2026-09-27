# GabCon BuildAI - Arcane Industrial Portal Complex
# Reference: references/Forteresse steampunk aux portails magiques.png
# Three portals: cyan left/high, blue center/high, purple right/lower.

stone = weighted_block({
    "deepslate_bricks": 0.45,
    "stone_bricks": 0.28,
    "polished_deepslate": 0.12,
    "tuff_bricks": 0.10,
    "cracked_stone_bricks": 0.05,
})
CREATE_ANDESITE = "create:andesite_casing"
CREATE_BRASS = "create:brass_casing"
CREATE_COPPER = "create:copper_casing"


def lamp(x, y, z):
    set_block(x, y, z, "polished_blackstone")
    set_block(x, y + 1, z, "lantern[hanging=false]")


def portal_disc(cx, cy, z, r, energy, trim, accent):
    # Filled magical disc + heavy double ring, facing negative z.
    for dx in range(-r + 2, r - 1):
        for dy in range(-r + 2, r - 1):
            if dx * dx + dy * dy <= (r - 2) * (r - 2):
                block = energy
                if (dx + dy) % 9 == 0:
                    block = accent
                set_block(cx + dx, cy + dy, z, block)
    for degree in range(0, 360, 3):
        a = math.radians(degree)
        for rr, block in [(r, trim), (r + 2, "deepslate_bricks")]:
            x = cx + round(rr * math.cos(a))
            y = cy + round(rr * math.sin(a))
            set_block(x, y, z - 1, block)
            set_block(x, y, z + 1, block)
    # Mechanical cardinal clamps.
    for dx, dy in [(r + 3, 0), (-r - 3, 0), (0, r + 3), (0, -r - 3)]:
        fill(cx + dx - 1, cy + dy - 1, z - 2,
             cx + dx + 1, cy + dy + 1, z + 2, CREATE_COPPER)


def hall(cx, cz, w, d, y, h):
    x1, x2 = cx - w // 2, cx + w // 2
    z1, z2 = cz - d // 2, cz + d // 2
    floor(x1, z1, x2, z2, y, "stone_bricks")
    walls(x1, z1, x2, z2, y, y + h, stone, thickness=2)
    gable_roof(x1, z1, x2, z2, y + h + 1, "deepslate_tiles", ridge_axis="x", overhang=2)
    for xx in range(x1 + 3, x2 - 2, 6):
        set_block(xx, y + 6, z1, "orange_stained_glass")


# Terraced foundation.
floor(-52, -38, 52, 38, 0, stone)
floor(-48, -31, 48, 33, 8, stone)
floor(-45, -24, 45, 29, 16, stone)

# Lower industrial halls.
hall(-25, 9, 35, 28, 17, 25)
hall(17, 10, 38, 31, 17, 30)
hall(0, 28, 34, 18, 28, 33)

# Portal platforms at three elevations.
floor(-50, -36, -12, -18, 37, "stone_bricks")
floor(-18, -35, 24, -14, 45, "stone_bricks")
floor(20, -34, 50, -12, 26, "stone_bricks")

# Portal structural frames.
for cx, cy, r in [(-31, 58, 14), (3, 68, 17), (35, 45, 12)]:
    fill(cx - r - 5, cy - r - 7, -18, cx - r - 2, cy + r + 7, -13, stone)
    fill(cx + r + 2, cy - r - 7, -18, cx + r + 5, cy + r + 7, -13, stone)
    fill(cx - r - 5, cy - r - 7, -18, cx + r + 5, cy - r - 4, -13, stone)

portal_disc(-31, 58, -20, 14, "cyan_stained_glass", CREATE_COPPER, "sea_lantern")
portal_disc(3, 68, -20, 17, "blue_stained_glass", CREATE_BRASS, "sea_lantern")
portal_disc(35, 45, -20, 12, "purple_stained_glass", "crying_obsidian", "amethyst_block")

# Tall mechanical towers.
for cx, cz, y, h, r in [
    (-44, 12, 18, 65, 5),
    (-10, 25, 35, 68, 6),
    (24, 27, 38, 74, 5),
    (46, 12, 18, 58, 5),
]:
    cylinder(cx, cz, y, h, r, "deepslate_bricks", hollow=True)
    cylinder(cx, cz, y + h - 3, 4, r + 1, "stone_bricks", hollow=False)
    cone(cx, cz, y + h + 1, r + 1, 9, "oxidized_copper")
    set_block(cx, y + h + 10, cz, "sea_lantern")

# Bridges and multi-level stairs.
for y, x1, x2, z in [
    (39, -49, -12, -9),
    (48, -15, 24, -7),
    (31, 20, 49, -6),
    (61, -26, 11, 16),
    (72, -8, 31, 22),
]:
    fill(x1, y, z - 1, x2, y + 1, z + 1, "stone_bricks")
    for x in range(x1, x2 + 1, 4):
        set_block(x, y + 2, z - 1, "stone_brick_wall")
        set_block(x, y + 2, z + 1, "stone_brick_wall")

for step in range(14):
    fill(-20 + step, 25 + step, -9, -16 + step, 25 + step, -6, "stone_bricks")
for step in range(18):
    fill(20 - step, 29 + step, 4, 24 - step, 29 + step, 7, "stone_bricks")

# Controlled waterfalls between terraces.
for x, z, y1, y2 in [(-13, 18, 8, 38), (17, 19, 16, 48), (44, 7, 8, 34)]:
    fill(x - 1, y1, z, x + 1, y2, z + 1, "water[level=0]")
    fill(x - 3, y1, z + 2, x + 3, y1 + 1, z + 4, "stone_bricks")

# Mechanical machinery clusters.
for x, y, z in [
    (-46, 42, -12), (-38, 45, -12), (-19, 50, -10),
    (-9, 56, -9), (17, 56, -10), (27, 35, -8), (43, 34, -8),
    (-8, 82, 20), (23, 87, 22),
]:
    set_block(x, y, z, CREATE_ANDESITE)
    set_block(x + 1, y, z, CREATE_BRASS)
    set_block(x, y + 1, z, CREATE_COPPER)

# Cranes at both ends.
for px, direction in [(-49, 1), (49, -1)]:
    fill(px, 28, -28, px, 46, -28, "dark_oak_log")
    line(px, 46, -28, px + direction * 18, 46, -28, "dark_oak_log")
    line(px, 38, -28, px + direction * 16, 46, -28, "dark_oak_fence")
    hx = px + direction * 16
    fill(hx, 35, -28, hx, 45, -28, "chain")
    hollow_box(hx - 2, 32, -30, hx + 2, 35, -26, "spruce_planks")

# Purple crystal accents.
for x, y, z in [(29, 58, -16), (41, 59, -16), (-39, 76, -13), (11, 91, -13)]:
    fill(x, y, z, x, y + 6, z, "amethyst_block")
    set_block(x, y + 7, z, "purple_stained_glass")

# Supported warm lights.
for x, y, z in [
    (-47, 39, -31), (-25, 39, -31), (-11, 47, -30),
    (8, 47, -30), (27, 28, -30), (45, 28, -30),
    (-33, 64, 3), (4, 80, 5), (35, 57, 1),
]:
    lamp(x, y, z)
