package com.mcbuild.mod.command;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.logging.LogUtils;
import java.io.IOException;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import net.minecraft.SharedConstants;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;
import net.neoforged.fml.loading.FMLPaths;
import org.slf4j.Logger;

/**
 * Exports the block registry that is actually loaded by the running NeoForge server.
 *
 * <p>The resulting JSON is intended to be the source of truth for mcbuild profiles:
 * every block keeps its namespace, every state property lists its accepted values,
 * and {@code states} contains the concrete state combinations exposed by Minecraft.
 */
public final class RegistryExportCommand {
    private static final Logger LOGGER = LogUtils.getLogger();
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private static final String FILE_NAME = "server-block-registry.json";

    private RegistryExportCommand() {}

    public static void register(CommandDispatcher<CommandSourceStack> dispatcher) {
        dispatcher.register(
                Commands.literal("mcbuild")
                        .requires(source -> source.hasPermission(2))
                        .then(Commands.literal("registry")
                                .then(Commands.literal("export")
                                        .executes(ctx -> exportRegistry(ctx.getSource())))));
    }

    private static int exportRegistry(CommandSourceStack source) {
        try {
            ExportResult result = writeRegistry();
            source.sendSuccess(
                    () -> Component.literal(
                            "[mcbuild] Exported "
                                    + result.blockCount()
                                    + " blocks / "
                                    + result.stateCount()
                                    + " states to "
                                    + result.path().toAbsolutePath()),
                    false);
            return 1;
        } catch (Exception e) {
            LOGGER.error("Failed to export the Minecraft block registry", e);
            source.sendFailure(Component.literal("[mcbuild] Registry export failed: " + e.getMessage()));
            return 0;
        }
    }

    static ExportResult writeRegistry() throws IOException {
        JsonObject root = new JsonObject();
        root.addProperty("format_version", 1);
        root.addProperty("minecraft_version", SharedConstants.getCurrentVersion().getName());
        root.addProperty(
                "data_version",
                SharedConstants.getCurrentVersion().getDataVersion().getVersion());
        root.addProperty("generated_at", Instant.now().toString());

        JsonObject blocksJson = new JsonObject();
        Map<String, Integer> namespaceCounts = new TreeMap<>();
        int stateCount = 0;

        List<ResourceLocation> ids = new ArrayList<>(BuiltInRegistries.BLOCK.keySet());
        ids.sort(Comparator.comparing(ResourceLocation::toString));

        for (ResourceLocation id : ids) {
            Block block = BuiltInRegistries.BLOCK.get(id);
            JsonObject blockJson = new JsonObject();
            blockJson.addProperty("namespace", id.getNamespace());
            blockJson.addProperty("path", id.getPath());

            List<Property<?>> properties = new ArrayList<>(block.getStateDefinition().getProperties());
            properties.sort(Comparator.comparing(Property::getName));

            JsonObject propertiesJson = new JsonObject();
            for (Property<?> property : properties) {
                JsonArray valuesJson = new JsonArray();
                for (Object value : property.getPossibleValues()) {
                    valuesJson.add(propertyValueName(property, value));
                }
                propertiesJson.add(property.getName(), valuesJson);
            }
            blockJson.add("properties", propertiesJson);

            String defaultState = formatState(id, block.defaultBlockState(), properties);
            blockJson.addProperty("default_state", defaultState);

            List<String> states = new ArrayList<>();
            for (BlockState state : block.getStateDefinition().getPossibleStates()) {
                states.add(formatState(id, state, properties));
            }
            states.sort(String::compareTo);

            JsonArray statesJson = new JsonArray();
            states.forEach(statesJson::add);
            blockJson.add("states", statesJson);
            blockJson.addProperty("state_count", states.size());

            blocksJson.add(id.toString(), blockJson);
            namespaceCounts.merge(id.getNamespace(), 1, Integer::sum);
            stateCount += states.size();
        }

        JsonObject namespacesJson = new JsonObject();
        namespaceCounts.forEach((namespace, count) -> namespacesJson.addProperty(namespace, count));

        root.addProperty("block_count", ids.size());
        root.addProperty("state_count", stateCount);
        root.add("namespaces", namespacesJson);
        root.add("blocks", blocksJson);

        Path output = FMLPaths.CONFIGDIR.get().resolve("mcbuild").resolve(FILE_NAME);
        writeAtomically(output, root);
        return new ExportResult(output, ids.size(), stateCount);
    }

    private static String formatState(
            ResourceLocation id, BlockState state, List<Property<?>> properties) {
        if (properties.isEmpty()) {
            return id.toString();
        }

        StringBuilder out = new StringBuilder(id.toString()).append('[');
        for (int i = 0; i < properties.size(); i++) {
            if (i > 0) {
                out.append(',');
            }
            Property<?> property = properties.get(i);
            out.append(property.getName())
                    .append('=')
                    .append(statePropertyValueName(state, property));
        }
        return out.append(']').toString();
    }

    @SuppressWarnings({"rawtypes", "unchecked"})
    private static String propertyValueName(Property property, Object value) {
        return property.getName((Comparable) value);
    }

    @SuppressWarnings({"rawtypes", "unchecked"})
    private static String statePropertyValueName(BlockState state, Property property) {
        Comparable value = (Comparable) state.getValue(property);
        return property.getName(value);
    }

    private static void writeAtomically(Path output, JsonObject root) throws IOException {
        Files.createDirectories(output.getParent());
        Path temp = output.resolveSibling(output.getFileName() + ".tmp");

        try (Writer writer = Files.newBufferedWriter(temp, StandardCharsets.UTF_8)) {
            GSON.toJson(root, writer);
        }

        try {
            Files.move(
                    temp,
                    output,
                    StandardCopyOption.REPLACE_EXISTING,
                    StandardCopyOption.ATOMIC_MOVE);
        } catch (AtomicMoveNotSupportedException ignored) {
            Files.move(temp, output, StandardCopyOption.REPLACE_EXISTING);
        }
    }

    record ExportResult(Path path, int blockCount, int stateCount) {}
}
