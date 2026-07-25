using VirtualFunctions.Core.Config;
using VirtualFunctions.Core.Models;

namespace VirtualFunctions.Core.Tests;

/// <summary>
/// Operation-pattern tests for layout toggling. The reported bug: toggling did
/// nothing while a migrated v1 preset (which always carries a Direction override)
/// was active, because only the global setting was flipped.
/// </summary>
public class LayoutResolverTests
{
    private static Preset PresetWithoutOverride() => new() { Name = "plain" };

    private static Preset PresetWithOverride(LayoutDirection direction) => new()
    {
        Name = "migrated",
        Layout = new LayoutSettings { Direction = direction },
    };

    // Pattern 1: preset without override (v1 "imported") — global drives, toggle works.
    [Fact]
    public void Toggle_WithoutPresetOverride_FlipsGlobalAndEffective()
    {
        Preset preset = PresetWithoutOverride();
        var window = new WindowSettings { LayoutDirection = LayoutDirection.Horizontal };

        bool presetModified = LayoutResolver.ToggleDirection(preset, window);

        Assert.False(presetModified);
        Assert.Null(preset.Layout.Direction);
        Assert.Equal(LayoutDirection.Vertical, window.LayoutDirection);
        Assert.Equal(LayoutDirection.Vertical, LayoutResolver.EffectiveDirection(preset, window));
    }

    // Pattern 2 (the reported bug): migrated preset override equals global —
    // the effective direction MUST change on toggle.
    [Fact]
    public void Toggle_WithPresetOverride_FlipsEffectiveDirection()
    {
        Preset preset = PresetWithOverride(LayoutDirection.Horizontal);
        var window = new WindowSettings { LayoutDirection = LayoutDirection.Horizontal };

        bool presetModified = LayoutResolver.ToggleDirection(preset, window);

        Assert.True(presetModified);
        Assert.Equal(LayoutDirection.Vertical, preset.Layout.Direction);
        Assert.Equal(LayoutDirection.Vertical, LayoutResolver.EffectiveDirection(preset, window));
    }

    // Pattern 3 (the "sometimes" case): override and global disagree. Pre-fix, flipping
    // the global from Vertical to Horizontal changed nothing visibly (override won).
    [Fact]
    public void Toggle_WhenOverrideDisagreesWithGlobal_FlipsWhatUserSees()
    {
        Preset preset = PresetWithOverride(LayoutDirection.Horizontal);
        var window = new WindowSettings { LayoutDirection = LayoutDirection.Vertical };

        Assert.Equal(LayoutDirection.Horizontal, LayoutResolver.EffectiveDirection(preset, window));

        LayoutResolver.ToggleDirection(preset, window);

        Assert.Equal(LayoutDirection.Vertical, LayoutResolver.EffectiveDirection(preset, window));
        Assert.Equal(LayoutDirection.Vertical, window.LayoutDirection);
    }

    // Pattern 4: double toggle returns to the original effective direction.
    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public void Toggle_Twice_RoundTrips(bool withOverride)
    {
        Preset preset = withOverride ? PresetWithOverride(LayoutDirection.Horizontal) : PresetWithoutOverride();
        var window = new WindowSettings { LayoutDirection = LayoutDirection.Horizontal };

        LayoutResolver.ToggleDirection(preset, window);
        LayoutResolver.ToggleDirection(preset, window);

        Assert.Equal(LayoutDirection.Horizontal, LayoutResolver.EffectiveDirection(preset, window));
    }

    // Pattern 5: toggle then switch to another preset with its own override —
    // that preset's direction wins again (per-preset layout is by design).
    [Fact]
    public void SwitchingPresets_AfterToggle_UsesNewPresetOverride()
    {
        Preset first = PresetWithOverride(LayoutDirection.Horizontal);
        Preset second = PresetWithOverride(LayoutDirection.Vertical);
        var window = new WindowSettings { LayoutDirection = LayoutDirection.Horizontal };

        LayoutResolver.ToggleDirection(first, window);

        Assert.Equal(LayoutDirection.Vertical, LayoutResolver.EffectiveDirection(second, window));
        Assert.Equal(LayoutDirection.Vertical, LayoutResolver.EffectiveDirection(first, window));
    }

    // Pattern 6: regression against the real migrated fixtures — every v1 preset
    // file carries settings.layoutDirection, so the override is always present.
    [Fact]
    public void MigratedV1Presets_CarryDirectionOverride_AndToggleStillWorks()
    {
        string testDataRoot = Path.Combine(AppContext.BaseDirectory, "TestData");
        MigrationResult? result = ConfigMigratorV1.Migrate(testDataRoot);

        Assert.NotNull(result);
        Preset migrated = result.Presets.Single(p => p.Name == "default");
        Assert.NotNull(migrated.Layout.Direction); // this is what made the bug preset-specific

        var window = new WindowSettings { LayoutDirection = migrated.Layout.Direction!.Value };
        LayoutDirection before = LayoutResolver.EffectiveDirection(migrated, window);

        LayoutResolver.ToggleDirection(migrated, window);

        Assert.NotEqual(before, LayoutResolver.EffectiveDirection(migrated, window));
    }

    [Fact]
    public void EffectiveButtonsPerRowAndIconSize_PreferPresetOverride()
    {
        var preset = new Preset
        {
            Name = "p",
            Layout = new LayoutSettings { ButtonsPerRow = 4, IconSize = 24 },
        };
        var window = new WindowSettings { ButtonsPerRow = 6, IconSize = 38 };

        Assert.Equal(4, LayoutResolver.EffectiveButtonsPerRow(preset, window));
        Assert.Equal(24, LayoutResolver.EffectiveIconSize(preset, window));

        Assert.Equal(6, LayoutResolver.EffectiveButtonsPerRow(PresetWithoutOverride(), window));
        Assert.Equal(38, LayoutResolver.EffectiveIconSize(PresetWithoutOverride(), window));
    }
}
