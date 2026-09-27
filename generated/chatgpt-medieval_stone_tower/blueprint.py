# Small medieval stone watchtower.
# Authored for the deterministic ChatGPT -> DSL -> renderer workflow.

WALL = weighted_block(
    {
        "stone_bricks": 0.78,
        "cracked_stone_bricks": 0.14,
        "mossy_stone_bricks": 0.08,
    }
)

# Compact round stone shell: 9 blocks across, 10 blocks to the eaves.
cylinder(0, 0, 0, height=10, r=4, block=WALL, hollow=True)

# Circular timber floors inside the stone shell.
for y in (0, 5):
    for x in range(-3, 4):
        for z in range(-3, 4):
            if x * x + z * z <= 9:
                set_block(x, y, z, "spruce_planks")

# South-facing walkable doorway.
clear(-1, 1, -4, 1, 3, -4)
set_block(0, 0, -5, "stone_brick_stairs[facing=south,half=bottom,shape=straight]")

# Three narrow medieval arrow-slit openings.
clear(-4, 3, 0, -4, 4, 0)
clear(4, 3, 0, 4, 4, 0)
clear(0, 7, 4, 0, 8, 4)

# Interior staircase rising along the east side to the upper floor.
# The stair positions remain inside the radius-4 shell.
for i in range(5):
    set_block(
        2,
        1 + i,
        2 - i,
        "spruce_stairs[facing=north,half=bottom,shape=straight]",
    )

# Open the landing through the upper floor and add a small safety rail.
clear(1, 5, -2, 2, 5, -1)
set_block(1, 5, -2, "spruce_planks")
set_block(2, 6, -2, "spruce_fence")
set_block(2, 6, -1, "spruce_fence")

# A stone eave ring visually separates the body from the roof.
cylinder(0, 0, 9, height=1, r=4.5, block="stone_bricks", hollow=True)

# Tall coherent wooden cone, with a one-block overhang around the stone shell.
cone(0, 0, 10, r=5, height=5, block="spruce_planks", hollow=True)

# Timber roof finial.
set_block(0, 15, 0, "spruce_log")
set_block(0, 16, 0, "spruce_fence")
