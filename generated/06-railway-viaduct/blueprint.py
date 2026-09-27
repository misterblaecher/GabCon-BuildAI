# GabCon BuildAI - Gothic Industrial Railway Viaduct
# Reference: references/Viaduc ferroviaire gothique en pierre.png
# Long axis = x. Designed as five readable repeatable spans.

stone = weighted_block({
    "stone_bricks": 0.70,
    "cracked_stone_bricks": 0.14,
    "andesite": 0.08,
    "tuff_bricks": 0.05,
    "mossy_stone_bricks": 0.03,
})
CREATE_ANDESITE = "create:andesite_casing"
CREATE_BRASS = "create:brass_casing"


def lamp_post(x, y, z):
    fill(x, y, z, x, y + 3, z, "polished_blackstone")
    set_block(x, y + 4, z, "lantern[hanging=false]")


def pier(cx):
    # Massive stepped pier.
    fill(cx - 5, 0, -6, cx + 5, 4, 6, stone)
    fill(cx - 4, 5, -5, cx + 4, 14, 5, stone)
    fill(cx - 3, 15, -5, cx + 3, 37, 5, stone)
    for yy in (12, 24, 34):
        fill(cx - 4, yy, -6, cx + 4, yy + 1, 6, "stone_bricks")
    set_block(cx, 26, -6, CREATE_ANDESITE)
    set_block(cx, 26, 6, CREATE_ANDESITE)


def arch_face(left_pier, right_pier, z):
    # Pointed arch profile between neighboring piers.
    left = left_pier + 5
    right = right_pier - 5
    mid = (left + right) // 2
    for t in range(3):
        line(left + t, 17 - t, z, mid, 35 + t, z, "stone_bricks")
        line(right - t, 17 - t, z, mid, 35 + t, z, "stone_bricks")
    # Gothic secondary braces.
    line(left, 26, z, mid - 3, 37, z, "andesite")
    line(right, 26, z, mid + 3, 37, z, "andesite")


# Piers for five spans.
pier_positions = [-60, -36, -12, 12, 36, 60]
for p in pier_positions:
    pier(p)

# Arches on both faces and shallow masonry depth.
for i in range(len(pier_positions) - 1):
    a = pier_positions[i]
    b = pier_positions[i + 1]
    for z in (-6, -5, 5, 6):
        arch_face(a, b, z)
    # Upper spandrel band.
    fill(a + 5, 34, -6, b - 5, 39, -4, stone)
    fill(a + 5, 34, 4, b - 5, 39, 6, stone)

# Heavy railway deck.
fill(-64, 38, -7, 64, 41, 7, "stone_bricks")
fill(-64, 42, -6, 64, 42, 6, "smooth_stone")

# Rails and maintenance walkway.
for x in range(-62, 63):
    set_block(x, 43, -1, "rail")
    set_block(x, 43, 1, "rail")
for x in range(-64, 65):
    set_block(x, 43, -6, "stone_brick_wall")
    set_block(x, 43, 6, "stone_brick_wall")

# Lantern rhythm and Create-style maintenance nodes.
for x in range(-60, 61, 12):
    lamp_post(x, 43, -5)
    if x % 24 == 0:
        set_block(x, 42, 5, CREATE_BRASS)
        set_block(x, 43, 5, CREATE_ANDESITE)

# End gate towers.
for cx in (-62, 62):
    for side in (-1, 1):
        cz = side * 4
        cylinder(cx, cz, 39, 24, 4, stone, hollow=True)
        cone(cx, cz, 63, 5, 8, "deepslate_tiles")
        set_block(cx, 72, cz, "lantern[hanging=false]")
        set_block(cx, 71, cz, "polished_blackstone")

# Maintenance balconies on selected piers.
for cx in (-36, -12, 12, 36):
    fill(cx - 4, 20, -9, cx + 4, 21, -6, "spruce_planks")
    for x in range(cx - 4, cx + 5, 2):
        set_block(x, 22, -9, "dark_oak_fence")
    fill(cx, 18, -10, cx, 21, -10, "dark_oak_log")
    set_block(cx, 23, -9, "lantern[hanging=false]")

# Buttress feet on the outer faces.
for cx in pier_positions:
    line(cx - 3, 15, -6, cx - 7, 0, -10, "stone_bricks")
    line(cx + 3, 15, -6, cx + 7, 0, -10, "stone_bricks")
    line(cx - 3, 15, 6, cx - 7, 0, 10, "stone_bricks")
    line(cx + 3, 15, 6, cx + 7, 0, 10, "stone_bricks")
