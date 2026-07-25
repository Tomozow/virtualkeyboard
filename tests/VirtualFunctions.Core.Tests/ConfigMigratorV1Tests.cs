using System.Text.Json.Nodes;
using VirtualFunctions.Core.Config;
using VirtualFunctions.Core.Models;

namespace VirtualFunctions.Core.Tests;

public class ConfigMigratorV1Tests
{
    private static readonly string TestDataRoot = Path.Combine(AppContext.BaseDirectory, "TestData");

    [Fact]
    public void Migrate_RealV1Config_MapsSettings()
    {
        MigrationResult? result = ConfigMigratorV1.Migrate(TestDataRoot);

        Assert.NotNull(result);
        AppSettings settings = result.Settings;
        Assert.Equal(1572, settings.Window.X);
        Assert.Equal(1168, settings.Window.Y);
        Assert.Equal(LayoutDirection.Horizontal, settings.Window.LayoutDirection);
        Assert.Equal(DisplayMode.Mini, settings.Window.DisplayMode);
        Assert.Equal(ThemeMode.Light, settings.Window.Theme);
        Assert.Equal(TooltipMode.Key, settings.Window.TooltipMode);
        Assert.Equal(6, settings.Window.ButtonsPerRow);
        Assert.Equal(38, settings.Window.IconSize);
        Assert.False(settings.DelayInput.Enabled);
        // v1 configured 1000 ms; the Python runtime ignored it (hard-coded 3000) — v2 honors it.
        Assert.Equal(1000, settings.DelayInput.DelayMs);
        Assert.Equal(ConfigMigratorV1.ImportedPresetName, settings.ActivePreset);
    }

    [Fact]
    public void Migrate_RealV1Config_ProducesImportedAndFilePresets()
    {
        MigrationResult? result = ConfigMigratorV1.Migrate(TestDataRoot);

        Assert.NotNull(result);
        Assert.Contains(result.Presets, p => p.Name == ConfigMigratorV1.ImportedPresetName);
        Assert.Contains(result.Presets, p => p.Name == "default");
        Assert.Contains(result.Presets, p => p.Name == "sample");

        Preset imported = result.Presets.Single(p => p.Name == ConfigMigratorV1.ImportedPresetName);
        Assert.Equal(12, imported.Buttons.Count);
        Assert.Equal("F13", imported.Buttons[0].Key);
        Assert.Equal("F24", imported.Buttons[^1].Key);
    }

    [Fact]
    public void Migrate_MissingConfig_ReturnsNull()
    {
        string emptyDir = Path.Combine(Path.GetTempPath(), Path.GetRandomFileName());
        Directory.CreateDirectory(emptyDir);
        try
        {
            Assert.Null(ConfigMigratorV1.Migrate(emptyDir));
        }
        finally
        {
            Directory.Delete(emptyDir);
        }
    }

    [Fact]
    public void MigrateButton_MapsColorsModifiersAndToggle()
    {
        JsonNode button = JsonNode.Parse("""
            {
              "key": "C",
              "label": "コピー",
              "icon": "📋",
              "color": "transparent",
              "toggleHighlight": true,
              "highlightColor": "#ff0000",
              "modifiers": { "ctrl": true, "shift": false, "alt": true, "win": false },
              "description": "コピーする"
            }
            """)!;

        ButtonDefinition result = ConfigMigratorV1.MigrateButton(button);

        Assert.Equal("C", result.Key);
        Assert.Equal("コピー", result.Label);
        Assert.Equal(IconKind.Emoji, result.Icon.Kind);
        Assert.Null(result.Background);
        Assert.True(result.Toggle.Enabled);
        Assert.Equal("#ff0000", result.Toggle.Color);
        Assert.Equal(KeyModifiers.Ctrl | KeyModifiers.Alt, result.Modifiers);
        Assert.Equal("コピーする", result.Tooltip);
    }

    [Theory]
    [InlineData("F13", IconKind.Text)]
    [InlineData("変換", IconKind.Text)]
    [InlineData("📋", IconKind.Emoji)]
    [InlineData("⏱️", IconKind.Emoji)]
    [InlineData("C:/icons/foo.png", IconKind.Image)]
    [InlineData("icons\\foo.ico", IconKind.Image)]
    [InlineData("", IconKind.Text)]
    public void InferIconKind_ClassifiesCorrectly(string icon, IconKind expected)
        => Assert.Equal(expected, ConfigMigratorV1.InferIconKind(icon));

    [Fact]
    public void MigrateAppBinding_ObjectForm_MapsAllFields()
    {
        JsonNode binding = JsonNode.Parse("""
            { "enabled": true, "windowName": "notepad", "matchTarget": "processName",
              "matchType": "exact", "priority": 5 }
            """)!;

        AppBinding result = ConfigMigratorV1.MigrateAppBinding(binding);

        Assert.True(result.Enabled);
        Assert.Equal("notepad", result.Pattern);
        Assert.Equal(BindingTarget.ProcessName, result.Target);
        Assert.Equal(BindingMatch.Exact, result.Match);
        Assert.Equal(5, result.Priority);
    }

    [Fact]
    public void MigrateAppBinding_LegacyStringForm_EnablesPartialTitleMatch()
    {
        JsonNode binding = JsonNode.Parse("\"Chrome\"")!;

        AppBinding result = ConfigMigratorV1.MigrateAppBinding(binding);

        Assert.True(result.Enabled);
        Assert.Equal("Chrome", result.Pattern);
        Assert.Equal(BindingTarget.WindowTitle, result.Target);
        Assert.Equal(BindingMatch.Partial, result.Match);
    }

    [Fact]
    public void MigrateAppBinding_Null_ReturnsDisabled()
    {
        AppBinding result = ConfigMigratorV1.MigrateAppBinding(null);
        Assert.False(result.Enabled);
    }
}
