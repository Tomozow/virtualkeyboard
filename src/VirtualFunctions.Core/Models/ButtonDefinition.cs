namespace VirtualFunctions.Core.Models;

/// <summary>Icon shown on a keyboard button.</summary>
public sealed class ButtonIcon
{
    public IconKind Kind { get; set; } = IconKind.Text;

    /// <summary>Text/emoji literal, or an image file path when <see cref="Kind"/> is Image.</summary>
    public string Value { get; set; } = string.Empty;
}

/// <summary>Latch-on-click behaviour of a button.</summary>
public sealed class ToggleSettings
{
    public bool Enabled { get; set; }

    /// <summary>Highlight color (hex) while latched.</summary>
    public string Color { get; set; } = "#d1d5db";
}

/// <summary>One user-configured key button.</summary>
public sealed class ButtonDefinition
{
    /// <summary>Key name understood by KeyMap, e.g. "F13", "A", "変換", or a combo "Ctrl+C".</summary>
    public string Key { get; set; } = string.Empty;

    public string Label { get; set; } = string.Empty;

    public ButtonIcon Icon { get; set; } = new();

    /// <summary>Background color (hex) or null for the theme default.</summary>
    public string? Background { get; set; }

    public ToggleSettings Toggle { get; set; } = new();

    /// <summary>Modifiers held while sending <see cref="Key"/>.</summary>
    public KeyModifiers Modifiers { get; set; }

    public string Tooltip { get; set; } = string.Empty;
}
