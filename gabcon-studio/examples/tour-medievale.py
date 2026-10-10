# Blueprint de démonstration : petite tour médiévale (mcbuild DSL)
fill(-7, 0, -7, 7, 0, 7, "cobblestone")
cylinder(0, 0, 1, 17, 5, "stone_bricks", hollow=True)
for y in range(1, 17):
    for x, z in [(-4, -4), (-4, 4), (4, -4), (4, 4)]:
        set_block(x, y, z, "polished_andesite")
fill(-1, 1, -5, 1, 3, -5, "air")
for y in [7, 12]:
    for x, z in [(0, -5), (0, 5), (-5, 0), (5, 0)]:
        set_block(x, y, z, "glass_pane")
cylinder(0, 0, 18, 1, 7, "spruce_planks")
cylinder(0, 0, 19, 1, 6, "spruce_planks")
cylinder(0, 0, 20, 1, 5, "spruce_planks")
cylinder(0, 0, 21, 1, 4, "dark_oak_planks")
cylinder(0, 0, 22, 1, 3, "dark_oak_planks")
cylinder(0, 0, 23, 1, 2, "dark_oak_planks")
set_block(0, 24, 0, "lightning_rod")
