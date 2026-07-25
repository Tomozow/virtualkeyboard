namespace VirtualFunctions.Core.Models;

/// <summary>
/// Resolves the strip layout from per-preset overrides and global settings,
/// and implements toggle semantics that always change what the user sees.
/// (A preset override must not silently swallow the context-menu toggle —
/// migrated v1 presets always carry a Direction override.)
/// </summary>
public static class LayoutResolver
{
    public static LayoutDirection EffectiveDirection(Preset preset, WindowSettings window)
    {
        ArgumentNullException.ThrowIfNull(preset);
        ArgumentNullException.ThrowIfNull(window);
        return preset.Layout.Direction ?? window.LayoutDirection;
    }

    public static int EffectiveButtonsPerRow(Preset preset, WindowSettings window)
    {
        ArgumentNullException.ThrowIfNull(preset);
        ArgumentNullException.ThrowIfNull(window);
        return preset.Layout.ButtonsPerRow ?? window.ButtonsPerRow;
    }

    public static int EffectiveIconSize(Preset preset, WindowSettings window)
    {
        ArgumentNullException.ThrowIfNull(preset);
        ArgumentNullException.ThrowIfNull(window);
        return preset.Layout.IconSize ?? window.IconSize;
    }

    /// <summary>
    /// Flips the direction the user currently sees. The global setting always follows;
    /// when the active preset carries its own Direction override, the override follows
    /// too (so the flip is visible no matter which source was winning).
    /// Returns true when the preset was modified and needs to be persisted.
    /// </summary>
    public static bool ToggleDirection(Preset preset, WindowSettings window)
    {
        LayoutDirection next = EffectiveDirection(preset, window) == LayoutDirection.Horizontal
            ? LayoutDirection.Vertical
            : LayoutDirection.Horizontal;

        window.LayoutDirection = next;
        if (preset.Layout.Direction is not null && preset.Layout.Direction != next)
        {
            preset.Layout.Direction = next;
            return true;
        }

        return false;
    }
}
