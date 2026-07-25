using System.Text.Json;
using VirtualFunctions.Core.Config;
using VirtualFunctions.Core.Models;

namespace VirtualFunctions.Core.Tests;

public sealed class AtomicJsonFileTests : IDisposable
{
    private readonly string _dir = Path.Combine(Path.GetTempPath(), Path.GetRandomFileName());

    public AtomicJsonFileTests()
    {
        Directory.CreateDirectory(_dir);
    }

    public void Dispose() => Directory.Delete(_dir, recursive: true);

    [Fact]
    public void WriteThenRead_RoundTrips()
    {
        string path = Path.Combine(_dir, "settings.json");
        var settings = new AppSettings();
        settings.Window.X = 42;
        settings.ActivePreset = "テスト";

        AtomicJsonFile.Write(path, settings, ConfigJsonContext.Default.AppSettings);
        AppSettings? loaded = AtomicJsonFile.Read(path, ConfigJsonContext.Default.AppSettings);

        Assert.NotNull(loaded);
        Assert.Equal(42, loaded.Window.X);
        Assert.Equal("テスト", loaded.ActivePreset);
        Assert.False(File.Exists(path + ".tmp"));
    }

    [Fact]
    public void SecondWrite_KeepsBackupOfPreviousVersion()
    {
        string path = Path.Combine(_dir, "settings.json");
        var first = new AppSettings { ActivePreset = "first" };
        var second = new AppSettings { ActivePreset = "second" };

        AtomicJsonFile.Write(path, first, ConfigJsonContext.Default.AppSettings);
        AtomicJsonFile.Write(path, second, ConfigJsonContext.Default.AppSettings);

        Assert.Equal("second", AtomicJsonFile.Read(path, ConfigJsonContext.Default.AppSettings)!.ActivePreset);
        Assert.True(File.Exists(path + ".bak"));
        Assert.Equal("first", AtomicJsonFile.Read(path + ".bak", ConfigJsonContext.Default.AppSettings)!.ActivePreset);
    }

    [Fact]
    public void Read_MissingFile_ReturnsDefault()
        => Assert.Null(AtomicJsonFile.Read(Path.Combine(_dir, "nope.json"), ConfigJsonContext.Default.AppSettings));

    [Fact]
    public void Read_CorruptFile_ThrowsJsonException()
    {
        string path = Path.Combine(_dir, "broken.json");
        File.WriteAllText(path, "{ not json !!");
        Assert.ThrowsAny<JsonException>(() => AtomicJsonFile.Read(path, ConfigJsonContext.Default.AppSettings));
    }

    [Fact]
    public void Preset_EnumsSerializeAsStrings()
    {
        string path = Path.Combine(_dir, "preset.json");
        var preset = new Preset
        {
            Name = "p1",
            AppBinding = new AppBinding { Target = BindingTarget.ProcessName, Match = BindingMatch.Exact },
        };

        AtomicJsonFile.Write(path, preset, ConfigJsonContext.Default.Preset);
        string json = File.ReadAllText(path);

        Assert.Contains("\"ProcessName\"", json, StringComparison.Ordinal);
        Assert.Contains("\"Exact\"", json, StringComparison.Ordinal);
    }
}
