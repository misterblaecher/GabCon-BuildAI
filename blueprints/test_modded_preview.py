floor(0, 0, 8, 8, 0, "create:andesite_casing")

fill(1, 1, 1, 1, 3, 1, "create:brass_casing")
fill(3, 1, 1, 3, 3, 1, "create:copper_casing")
fill(5, 1, 1, 5, 3, 1, "minecraft:stone_bricks")

set_block(
    2, 1, 4,
    "waystones:waystone[facing=north,half=lower,origin=player,waterlogged=false]"
)
set_block(
    2, 2, 4,
    "waystones:waystone[facing=north,half=upper,origin=player,waterlogged=false]"
)
set_block(4, 1, 4, "trading_floor:trading_depot")
set_block(6, 1, 4, "create:andesite_casing")

fill(0, 1, 0, 8, 1, 0, "minecraft:glass")