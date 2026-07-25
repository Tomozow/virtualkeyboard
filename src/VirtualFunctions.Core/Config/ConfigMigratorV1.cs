using System.Text.Json.Nodes;
using VirtualFunctions.Core.Models;

namespace VirtualFunctions.Core.Config;

/// <summary>Everything produced by a v1 → v2 migration.</summary>
public sealed record MigrationResult(AppSettings Settings, IReadOnlyList<Preset> Presets);

/// <summary>
/// One-time, read-only import of the Python v1 files (config.json + presets\*.json).
/// v1 sections that were dead code (hotkeys, triggerKeys, focusRestore, appearance)
/// are intentionally dropped. The configured delay is honored — v1 hard-coded 3000 ms
/// at runtime (old main.py:172) and ignored its own config; v2 does not.
/// </summary>
public static class ConfigMigratorV1
{
    /// <summary>Name given to the preset built from config.json's floatingWindow.buttons.</summary>
    public const string ImportedPresetName = "imported";

    private static readonly string[] ImageExtensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp"];

    /// <summary>
    /// Migrates v1 files found in <paramref name="v1Root"/>. Returns null when no v1 config exists.
    /// Never writes or deletes anything — callers persist the result.
    /// </summary>
    public static MigrationResult? Migrate(string v1Root)
    {
        string configPath = Path.Combine(v1Root, "config.json");
        if (!File.Exists(configPath))
        {
            return null;
        }

        JsonNode? v1Config = JsonNode.Parse(File.ReadAllText(configPath));
        AppSettings settings = MigrateSettings(v1Config);

        var presets = new List<Preset>();
        JsonNode? buttons = v1Config?["floatingWindow"]?["buttons"];
        if (buttons is JsonArray buttonArray && buttonArray.Count > 0)
        {
            presets.Add(BuildPresetFromButtons(buttonArray, v1Config, ImportedPresetName));
            settings.ActivePreset = ImportedPresetName;
        }

        string presetsDir = Path.Combine(v1Root, "presets");
        if (Directory.Exists(presetsDir))
        {
            foreach (string file in Directory.EnumerateFiles(presetsDir, "*.json").Order(StringComparer.OrdinalIgnoreCase))
            {
                Preset? preset = TryMigratePresetFile(file);
                if (preset is not null &&
                    !presets.Any(p => string.Equals(p.Name, preset.Name, StringComparison.OrdinalIgnoreCase)))
                {
                    presets.Add(preset);
                }
            }
        }

        return new MigrationResult(settings, presets);
    }

    public static AppSettings MigrateSettings(JsonNode? v1Config)
    {
        var settings = new AppSettings();
        JsonNode? fw = v1Config?["floatingWindow"];
        if (fw is null)
        {
            return settings;
        }

        settings.Window.X = fw["position"]?["x"]?.GetValue<double>() ?? settings.Window.X;
        settings.Window.Y = fw["position"]?["y"]?.GetValue<double>() ?? settings.Window.Y;
        settings.Window.LayoutDirection = ParseEnum(fw["layoutDirection"], LayoutDirection.Horizontal);
        settings.Window.DisplayMode = ParseEnum(fw["displayMode"], DisplayMode.Normal);
        settings.Window.Theme = fw["darkMode"]?.GetValue<bool>() is true ? ThemeMode.Dark : ThemeMode.Light;
        settings.Window.TooltipMode = ParseEnum(fw["tooltipMode"], TooltipMode.Key);
        settings.Window.ButtonsPerRow = fw["layout"]?["buttonsPerRow"]?.GetValue<int>() ?? settings.Window.ButtonsPerRow;
        settings.Window.IconSize = fw["layout"]?["iconSize"]?.GetValue<int>() ?? settings.Window.IconSize;

        settings.DelayInput.Enabled = fw["delayInputMode"]?.GetValue<bool>() ?? false;
        settings.DelayInput.DelayMs = fw["delayTime"]?.GetValue<int>()
            ?? v1Config?["keyDelay"]?["delayMs"]?.GetValue<int>()
            ?? settings.DelayInput.DelayMs;

        settings.Normalize();
        return settings;
    }

    public static ButtonDefinition MigrateButton(JsonNode button)
    {
        ArgumentNullException.ThrowIfNull(button);

        string icon = button["icon"]?.GetValue<string>() ?? string.Empty;
        string color = button["color"]?.GetValue<string>() ?? string.Empty;
        JsonNode? mods = button["modifiers"];

        KeyModifiers modifiers = KeyModifiers.None;
        if (mods?["ctrl"]?.GetValue<bool>() is true)
        {
            modifiers |= KeyModifiers.Ctrl;
        }

        if (mods?["shift"]?.GetValue<bool>() is true)
        {
            modifiers |= KeyModifiers.Shift;
        }

        if (mods?["alt"]?.GetValue<bool>() is true)
        {
            modifiers |= KeyModifiers.Alt;
        }

        if (mods?["win"]?.GetValue<bool>() is true)
        {
            modifiers |= KeyModifiers.Win;
        }

        return new ButtonDefinition
        {
            Key = button["key"]?.GetValue<string>() ?? string.Empty,
            Label = button["label"]?.GetValue<string>() ?? string.Empty,
            Icon = new ButtonIcon { Kind = InferIconKind(icon), Value = icon },
            Background = NormalizeColor(color),
            Toggle = new ToggleSettings
            {
                Enabled = button["toggleHighlight"]?.GetValue<bool>() ?? false,
                Color = button["highlightColor"]?.GetValue<string>() ?? "#d1d5db",
            },
            Modifiers = modifiers,
            Tooltip = button["description"]?.GetValue<string>() ?? string.Empty,
        };
    }

    public static Preset MigratePreset(JsonNode v1Preset, string fallbackName)
    {
        ArgumentNullException.ThrowIfNull(v1Preset);

        var preset = new Preset
        {
            Name = v1Preset["name"]?.GetValue<string>() is { Length: > 0 } name ? name : fallbackName,
            Description = v1Preset["description"]?.GetValue<string>() ?? string.Empty,
        };

        if (v1Preset["buttons"] is JsonArray buttons)
        {
            foreach (JsonNode? node in buttons)
            {
                if (node is not null)
                {
                    preset.Buttons.Add(MigrateButton(node));
                }
            }
        }

        JsonNode? settings = v1Preset["settings"];
        if (settings is not null)
        {
            preset.Layout.Direction = TryParseEnum<LayoutDirection>(settings["layoutDirection"]);
            preset.Layout.ButtonsPerRow = settings["buttonsPerRow"]?.GetValue<int>();
            preset.Layout.IconSize = settings["iconSize"]?.GetValue<int>();
        }

        preset.AppBinding = MigrateAppBinding(v1Preset["appBinding"]);
        return preset;
    }

    /// <summary>Handles both the v1 object form and the legacy plain-string form.</summary>
    public static AppBinding MigrateAppBinding(JsonNode? v1Binding)
    {
        if (v1Binding is JsonValue value && value.TryGetValue(out string? legacyPattern))
        {
            return new AppBinding
            {
                Enabled = !string.IsNullOrEmpty(legacyPattern),
                Pattern = legacyPattern ?? string.Empty,
            };
        }

        if (v1Binding is JsonObject obj)
        {
            return new AppBinding
            {
                Enabled = obj["enabled"]?.GetValue<bool>() ?? false,
                Pattern = obj["windowName"]?.GetValue<string>() ?? string.Empty,
                Target = obj["matchTarget"]?.GetValue<string>()?.ToUpperInvariant() switch
                {
                    "PROCESSNAME" => BindingTarget.ProcessName,
                    "CLASSNAME" => BindingTarget.ClassName,
                    _ => BindingTarget.WindowTitle,
                },
                Match = obj["matchType"]?.GetValue<string>()?.ToUpperInvariant() == "EXACT"
                    ? BindingMatch.Exact
                    : BindingMatch.Partial,
                Priority = obj["priority"]?.GetValue<int>() ?? 1,
            };
        }

        return new AppBinding();
    }

    internal static IconKind InferIconKind(string icon)
    {
        if (string.IsNullOrEmpty(icon))
        {
            return IconKind.Text;
        }

        if (icon.Contains('/', StringComparison.Ordinal) ||
            icon.Contains('\\', StringComparison.Ordinal) ||
            ImageExtensions.Any(ext => icon.EndsWith(ext, StringComparison.OrdinalIgnoreCase)))
        {
            return IconKind.Image;
        }

        foreach (System.Text.Rune rune in icon.EnumerateRunes())
        {
            if (rune.Value >= 0x1F000 || rune.Value is >= 0x2190 and <= 0x2BFF or 0xFE0F)
            {
                return IconKind.Emoji;
            }
        }

        return IconKind.Text;
    }

    internal static string? NormalizeColor(string color) =>
        string.IsNullOrWhiteSpace(color) || color.Equals("transparent", StringComparison.OrdinalIgnoreCase)
            ? null
            : color;

    private static Preset BuildPresetFromButtons(JsonArray buttons, JsonNode? v1Config, string name)
    {
        var preset = new Preset
        {
            Name = name,
            Description = "config.json (v1) から移行されたボタン",
        };

        foreach (JsonNode? node in buttons)
        {
            if (node is not null)
            {
                preset.Buttons.Add(MigrateButton(node));
            }
        }

        JsonNode? layout = v1Config?["floatingWindow"]?["layout"];
        preset.Layout.ButtonsPerRow = layout?["buttonsPerRow"]?.GetValue<int>();
        preset.Layout.IconSize = layout?["iconSize"]?.GetValue<int>();
        return preset;
    }

    private static Preset? TryMigratePresetFile(string path)
    {
        try
        {
            JsonNode? node = JsonNode.Parse(File.ReadAllText(path));
            return node is null ? null : MigratePreset(node, Path.GetFileNameWithoutExtension(path));
        }
        catch (System.Text.Json.JsonException)
        {
            return null;
        }
    }

    private static T ParseEnum<T>(JsonNode? node, T fallback) where T : struct, Enum
        => TryParseEnum<T>(node) ?? fallback;

    private static T? TryParseEnum<T>(JsonNode? node) where T : struct, Enum
    {
        string? text = node?.GetValue<string>();
        return text is not null && Enum.TryParse(text, ignoreCase: true, out T parsed) ? parsed : null;
    }
}
