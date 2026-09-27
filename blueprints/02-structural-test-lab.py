# GabCon BuildAI - Structural Validation Test Lab
#
# Purpose:
#   Compact paste-test covering the structural rules currently enforced by BuildAI.
#   Generate with the live server registry, then paste with WorldEdit.
#
# Coordinate convention:
#   x = west/east
#   y = up
#   z = north/south
#
# The colored floor pads separate test families visually.

# ---------------------------------------------------------------------------
# Base platform
# ---------------------------------------------------------------------------

floor(-16, -12, 16, 12, 0, "smooth_stone")

# Border
fill(-16, 0, -12, 16, 0, -12, "polished_deepslate")
fill(-16, 0, 12, 16, 0, 12, "polished_deepslate")
fill(-16, 0, -12, -16, 0, 12, "polished_deepslate")
fill(16, 0, -12, 16, 0, 12, "polished_deepslate")

# Test pads
floor(-15, -10, -9, -5, 0, "blue_concrete")       # Waystone
floor(-8, -10, -3, -5, 0, "red_concrete")         # Bed
floor(-2, -10, 5, -3, 0, "yellow_concrete")       # Vanilla pistons
floor(-15, -2, -9, 3, 0, "orange_concrete")       # Chain drive
floor(-7, -2, 5, 3, 0, "lime_concrete")           # Belts
floor(-15, 5, -9, 10, 0, "cyan_concrete")         # Gantry
floor(-7, 5, -2, 10, 0, "purple_concrete")        # Sticker
floor(0, 5, 14, 10, 0, "light_blue_concrete")     # Mechanical pistons

# ---------------------------------------------------------------------------
# 1) Waystone - generic half=lower/upper vertical pair
# ---------------------------------------------------------------------------

set_block(
    -12,
    1,
    -7,
    "waystones:waystone[facing=north,half=lower,origin=player,waterlogged=false]",
)
set_block(
    -12,
    2,
    -7,
    "waystones:waystone[facing=north,half=upper,origin=player,waterlogged=false]",
)

# ---------------------------------------------------------------------------
# 2) Bed - horizontal foot/head pair following facing=east
# ---------------------------------------------------------------------------

set_block(-7, 1, -7, "minecraft:red_bed[facing=east,occupied=false,part=foot]")
set_block(-6, 1, -7, "minecraft:red_bed[facing=east,occupied=false,part=head]")

# ---------------------------------------------------------------------------
# 3) Vanilla pistons - extended body + matching piston head
# ---------------------------------------------------------------------------

# Normal piston, facing east.
set_block(-1, 1, -8, "minecraft:redstone_block")
set_block(0, 1, -8, "minecraft:piston[extended=true,facing=east]")
set_block(1, 1, -8, "minecraft:piston_head[facing=east,short=false,type=normal]")

# Sticky piston, facing east.
set_block(-1, 1, -5, "minecraft:redstone_block")
set_block(0, 1, -5, "minecraft:sticky_piston[extended=true,facing=east]")
set_block(1, 1, -5, "minecraft:piston_head[facing=east,short=false,type=sticky]")

# ---------------------------------------------------------------------------
# 4) Create chain drive - START / MIDDLE / END along X
#    axis=y + axis_along_first=true resolves the chain connection axis to X.
# ---------------------------------------------------------------------------

set_block(
    -13,
    1,
    0,
    "create:adjustable_chain_gearshift[axis=y,axis_along_first=true,part=start,powered=false]",
)
set_block(
    -12,
    1,
    0,
    "create:encased_chain_drive[axis=y,axis_along_first=true,part=middle]",
)
set_block(
    -11,
    1,
    0,
    "create:encased_chain_drive[axis=y,axis_along_first=true,part=end]",
)

# ---------------------------------------------------------------------------
# 5) Create belts
# ---------------------------------------------------------------------------

# Horizontal START / MIDDLE / END.
set_block(
    -6,
    1,
    0,
    "create:belt[casing=false,facing=east,part=start,slope=horizontal,waterlogged=false]",
)
set_block(
    -5,
    1,
    0,
    "create:belt[casing=false,facing=east,part=middle,slope=horizontal,waterlogged=false]",
)
set_block(
    -4,
    1,
    0,
    "create:belt[casing=false,facing=east,part=end,slope=horizontal,waterlogged=false]",
)

# Upward belt. Each eastward segment rises by one block.
set_block(
    1,
    1,
    0,
    "create:belt[casing=false,facing=east,part=start,slope=upward,waterlogged=false]",
)
set_block(
    2,
    2,
    0,
    "create:belt[casing=false,facing=east,part=middle,slope=upward,waterlogged=false]",
)
set_block(
    3,
    3,
    0,
    "create:belt[casing=false,facing=east,part=end,slope=upward,waterlogged=false]",
)

# Visual supports below the raised belt segments.
set_block(2, 1, 0, "create:andesite_casing")
set_block(3, 1, 0, "create:andesite_casing")
set_block(3, 2, 0, "create:andesite_casing")

# ---------------------------------------------------------------------------
# 6) Create gantry shaft - START / MIDDLE / END facing east
# ---------------------------------------------------------------------------

set_block(-13, 1, 7, "create:gantry_shaft[facing=east,part=start,powered=false]")
set_block(-12, 1, 7, "create:gantry_shaft[facing=east,part=middle,powered=false]")
set_block(-11, 1, 7, "create:gantry_shaft[facing=east,part=end,powered=false]")

# ---------------------------------------------------------------------------
# 7) Create Sticker - extended is state-only, no companion block required
# ---------------------------------------------------------------------------

set_block(-5, 1, 7, "create:sticker[extended=true,facing=east,powered=true]")

# ---------------------------------------------------------------------------
# 8) Create mechanical pistons
#    Extended piston -> extension pole(s) -> matching head.
# ---------------------------------------------------------------------------

# Normal mechanical piston.
set_block(
    1,
    1,
    7,
    "create:mechanical_piston[axis_along_first=true,facing=east,state=extended]",
)
set_block(2, 1, 7, "create:piston_extension_pole[facing=east,waterlogged=false]")
set_block(
    3,
    1,
    7,
    "create:mechanical_piston_head[facing=east,type=normal,waterlogged=false]",
)

# Sticky mechanical piston.
set_block(
    7,
    1,
    7,
    "create:sticky_mechanical_piston[axis_along_first=true,facing=east,state=extended]",
)
set_block(8, 1, 7, "create:piston_extension_pole[facing=east,waterlogged=false]")
set_block(
    9,
    1,
    7,
    "create:mechanical_piston_head[facing=east,type=sticky,waterlogged=false]",
)

# Small marker columns so the two piston tests are easy to distinguish in the render.
set_block(1, 1, 9, "white_concrete")
set_block(7, 1, 9, "magenta_concrete")
