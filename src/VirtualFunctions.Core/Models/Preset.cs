namespace VirtualFunctions.Core.Models;

/// <summary>Automatic preset activation rule based on the foreground window.</summary>
public sealed class AppBinding
{
    public bool Enabled { get; set; }

    /// <summary>Substring or exact string to match against the selected target.</summary>
    public string Pattern { get; set; } = string.Empty;

    public BindingTarget Target { get; set; } = BindingTarget.WindowTitle;

    public BindingMatch Match { get; set; } = BindingMatch.Partial;

    /// <summary>Higher wins when several presets match.</summary>
    public int Priority { get; set; } = 1;
}

/// <summary>Per-preset layout overrides; null members fall back to global settings.</summary>
public sealed class LayoutSettings
{
    public LayoutDirection? Direction { get; set; }
    public int? ButtonsPerRow { get; set; }
    public int? IconSize { get; set; }
}

/// <summary>A named set of buttons with optional layout and app-binding rule.</summary>
public sealed class Preset
{
    public int SchemaVersion { get; set; } = 2;

    public string Name { get; set; } = string.Empty;

    public string Description { get; set; } = string.Empty;

    public List<ButtonDefinition> Buttons { get; set; } = [];

    public LayoutSettings Layout { get; set; } = new();

    public AppBinding AppBinding { get; set; } = new();

    public DateTimeOffset Created { get; set; } = DateTimeOffset.Now;

    public DateTimeOffset Modified { get; set; } = DateTimeOffset.Now;
}
