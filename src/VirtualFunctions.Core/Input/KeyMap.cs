using VirtualFunctions.Core.Models;

namespace VirtualFunctions.Core.Input;

/// <summary>A named key with its virtual-key code and send quirks.</summary>
public sealed record KeyDefinition(string Name, ushort Vk, KeySendOptions Flags);

/// <summary>
/// The single name↔VK table for the whole app.
/// Ported from the union of the two Python v1 tables
/// (services/keysender.py key_name_to_vk and services/win32_types.py FunctionKeyMap).
/// </summary>
public static class KeyMap
{
    // v1-compatible IME virtual keys (win32_types.py:27-32).
    private const ushort VkKana = 0x15;
    private const ushort VkKanji = 0x19;
    private const ushort VkConvert = 0x1C;
    private const ushort VkNonConvert = 0x1D;
    private const ushort VkImeOn = 0xF2;
    private const ushort VkImeOff = 0xF3;

    private static readonly KeyDefinition[] CanonicalKeys = BuildCanonicalKeys();
    private static readonly Dictionary<string, KeyDefinition> Lookup = BuildLookup();

    /// <summary>Canonical entries (one per key) for editor dropdowns.</summary>
    public static IReadOnlyList<KeyDefinition> AllKeys => CanonicalKeys;

    /// <summary>Resolves a single key name (canonical or alias, case-insensitive).</summary>
    public static bool TryResolveKey(string name, out KeyDefinition definition)
    {
        if (Lookup.TryGetValue(name.Trim(), out KeyDefinition? found))
        {
            definition = found;
            return true;
        }

        definition = null!;
        return false;
    }

    /// <summary>
    /// Parses a key spec such as "F13", "変換", or "Ctrl+Shift+C" into a stroke,
    /// merging any extra modifiers (from per-button settings).
    /// Returns null when the spec references an unknown key or modifier.
    /// </summary>
    public static KeyStroke? Parse(string keySpec, KeyModifiers modifiers = KeyModifiers.None)
    {
        if (string.IsNullOrWhiteSpace(keySpec))
        {
            return null;
        }

        string spec = keySpec.Trim();
        if (!spec.Contains('+', StringComparison.Ordinal) || spec == "+")
        {
            return TryResolveKey(spec, out KeyDefinition def)
                ? new KeyStroke(def.Vk, modifiers, def.Flags)
                : null;
        }

        string[] parts = spec.Split('+', StringSplitOptions.TrimEntries);
        if (parts.Length < 2 || parts.Any(string.IsNullOrEmpty))
        {
            return null;
        }

        KeyModifiers combined = modifiers;
        foreach (string part in parts[..^1])
        {
            KeyModifiers? mod = ParseModifier(part);
            if (mod is null)
            {
                return null;
            }

            combined |= mod.Value;
        }

        return TryResolveKey(parts[^1], out KeyDefinition mainDef)
            ? new KeyStroke(mainDef.Vk, combined, mainDef.Flags)
            : null;
    }

    /// <summary>Canonical name for a VK code (used by the key-capture editor); null when unmapped.</summary>
    public static string? NameFromVk(ushort vk)
    {
        foreach (KeyDefinition def in CanonicalKeys)
        {
            if (def.Vk == vk)
            {
                return def.Name;
            }
        }

        return null;
    }

    private static KeyModifiers? ParseModifier(string token) => token.ToUpperInvariant() switch
    {
        "CTRL" or "CONTROL" => KeyModifiers.Ctrl,
        "SHIFT" => KeyModifiers.Shift,
        "ALT" => KeyModifiers.Alt,
        "WIN" or "WINDOWS" => KeyModifiers.Win,
        _ => null,
    };

    private static KeyDefinition[] BuildCanonicalKeys()
    {
        var keys = new List<KeyDefinition>();

        // F1–F24 (win32_types.py FUNCTION_KEYS). F13+ have no scan code → VK only.
        for (int i = 1; i <= 24; i++)
        {
            KeySendOptions flags = i >= 13 ? KeySendOptions.VkOnly : KeySendOptions.None;
            keys.Add(new KeyDefinition($"F{i}", (ushort)(0x70 + i - 1), flags));
        }

        // Digits and letters.
        for (char c = '0'; c <= '9'; c++)
        {
            keys.Add(new KeyDefinition(c.ToString(), c, KeySendOptions.None));
        }

        for (char c = 'A'; c <= 'Z'; c++)
        {
            keys.Add(new KeyDefinition(c.ToString(), c, KeySendOptions.None));
        }

        // Special keys (keysender.py:397-404).
        keys.AddRange(
        [
            new KeyDefinition("Space", 0x20, KeySendOptions.None),
            new KeyDefinition("Enter", 0x0D, KeySendOptions.None),
            new KeyDefinition("Backspace", 0x08, KeySendOptions.None),
            new KeyDefinition("Delete", 0x2E, KeySendOptions.Extended),
            new KeyDefinition("Tab", 0x09, KeySendOptions.None),
            new KeyDefinition("Escape", 0x1B, KeySendOptions.None),
            new KeyDefinition("Insert", 0x2D, KeySendOptions.Extended),
            new KeyDefinition("Home", 0x24, KeySendOptions.Extended),
            new KeyDefinition("End", 0x23, KeySendOptions.Extended),
            new KeyDefinition("PageUp", 0x21, KeySendOptions.Extended),
            new KeyDefinition("PageDown", 0x22, KeySendOptions.Extended),
            new KeyDefinition("Up", 0x26, KeySendOptions.Extended),
            new KeyDefinition("Down", 0x28, KeySendOptions.Extended),
            new KeyDefinition("Left", 0x25, KeySendOptions.Extended),
            new KeyDefinition("Right", 0x27, KeySendOptions.Extended),
            new KeyDefinition("Shift", 0x10, KeySendOptions.None),
            new KeyDefinition("Ctrl", 0x11, KeySendOptions.None),
            new KeyDefinition("Alt", 0x12, KeySendOptions.None),
            new KeyDefinition("Win", 0x5B, KeySendOptions.Extended),
            new KeyDefinition("CapsLock", 0x14, KeySendOptions.None),
            new KeyDefinition("NumLock", 0x90, KeySendOptions.Extended),
            new KeyDefinition("ScrollLock", 0x91, KeySendOptions.None),
            new KeyDefinition("PrintScreen", 0x2C, KeySendOptions.Extended),
            new KeyDefinition("Pause", 0x13, KeySendOptions.None),

            // Symbol keys (keysender.py:407-409).
            new KeyDefinition("Semicolon", 0xBA, KeySendOptions.None),
            new KeyDefinition("Equal", 0xBB, KeySendOptions.None),
            new KeyDefinition("Comma", 0xBC, KeySendOptions.None),
            new KeyDefinition("Minus", 0xBD, KeySendOptions.None),
            new KeyDefinition("Period", 0xBE, KeySendOptions.None),
            new KeyDefinition("Slash", 0xBF, KeySendOptions.None),
            new KeyDefinition("Grave", 0xC0, KeySendOptions.None),
            new KeyDefinition("LeftBracket", 0xDB, KeySendOptions.None),
            new KeyDefinition("Backslash", 0xDC, KeySendOptions.None),
            new KeyDefinition("RightBracket", 0xDD, KeySendOptions.None),
            new KeyDefinition("Quote", 0xDE, KeySendOptions.None),

            // Japanese IME keys — v1 sends these VK-only (win32_types.py:116-128).
            new KeyDefinition("Kana", VkKana, KeySendOptions.VkOnly),
            new KeyDefinition("Kanji", VkKanji, KeySendOptions.VkOnly),
            new KeyDefinition("Convert", VkConvert, KeySendOptions.VkOnly),
            new KeyDefinition("NonConvert", VkNonConvert, KeySendOptions.VkOnly),
            new KeyDefinition("IME_ON", VkImeOn, KeySendOptions.VkOnly),
            new KeyDefinition("IME_OFF", VkImeOff, KeySendOptions.VkOnly),
        ]);

        return [.. keys];
    }

    private static Dictionary<string, KeyDefinition> BuildLookup()
    {
        var map = new Dictionary<string, KeyDefinition>(StringComparer.OrdinalIgnoreCase);
        foreach (KeyDefinition def in CanonicalKeys)
        {
            map[def.Name] = def;
        }

        // Aliases accepted by v1 configs (keysender.py:412-417).
        AddAlias(map, "かな", "Kana");
        AddAlias(map, "Hankaku", "Kanji");
        AddAlias(map, "Zenkaku", "Kanji");
        AddAlias(map, "Hankaku/Zenkaku", "Kanji");
        AddAlias(map, "半角/全角", "Kanji");
        AddAlias(map, "半角全角", "Kanji");
        AddAlias(map, "Henkan", "Convert");
        AddAlias(map, "変換", "Convert");
        AddAlias(map, "Muhenkan", "NonConvert");
        AddAlias(map, "無変換", "NonConvert");
        AddAlias(map, "Esc", "Escape");
        AddAlias(map, "Return", "Enter");
        AddAlias(map, "PgUp", "PageUp");
        AddAlias(map, "PgDn", "PageDown");
        return map;
    }

    private static void AddAlias(Dictionary<string, KeyDefinition> map, string alias, string canonical)
        => map[alias] = map[canonical];
}
