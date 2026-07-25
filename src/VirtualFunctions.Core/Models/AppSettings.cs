namespace VirtualFunctions.Core.Models;

public sealed class WindowSettings
{
    public double X { get; set; } = 100;
    public double Y { get; set; } = 100;
    public LayoutDirection LayoutDirection { get; set; } = LayoutDirection.Horizontal;
    public DisplayMode DisplayMode { get; set; } = DisplayMode.Normal;
    public ThemeMode Theme { get; set; } = ThemeMode.Light;
    public double Opacity { get; set; } = 0.85;
    public int ButtonsPerRow { get; set; } = 6;
    public int IconSize { get; set; } = 38;
    public TooltipMode TooltipMode { get; set; } = TooltipMode.Key;
}

public sealed class DelayInputSettings
{
    public bool Enabled { get; set; }

    /// <summary>Countdown before the key fires. Clamped to 500–30000 ms on load.</summary>
    public int DelayMs { get; set; } = 1000;
}

/// <summary>Root of settings.json (schema v2).</summary>
public sealed class AppSettings
{
    public const int CurrentSchemaVersion = 2;
    public const int MinDelayMs = 500;
    public const int MaxDelayMs = 30000;

    public int SchemaVersion { get; set; } = CurrentSchemaVersion;

    public WindowSettings Window { get; set; } = new();

    public DelayInputSettings DelayInput { get; set; } = new();

    /// <summary>Name of the preset whose buttons are shown.</summary>
    public string ActivePreset { get; set; } = "default";

    /// <summary>Global switch for foreground-window preset auto-switching.</summary>
    public bool AppBindingEnabled { get; set; } = true;

    public void Normalize()
    {
        DelayInput.DelayMs = Math.Clamp(DelayInput.DelayMs, MinDelayMs, MaxDelayMs);
        Window.Opacity = Math.Clamp(Window.Opacity, 0.2, 1.0);
        Window.ButtonsPerRow = Math.Clamp(Window.ButtonsPerRow, 1, 24);
        Window.IconSize = Math.Clamp(Window.IconSize, 16, 128);
        if (string.IsNullOrWhiteSpace(ActivePreset))
        {
            ActivePreset = "default";
        }
    }
}
