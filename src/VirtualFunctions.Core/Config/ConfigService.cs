using System.Text.Json;
using VirtualFunctions.Core.Models;

namespace VirtualFunctions.Core.Config;

/// <summary>
/// Owns settings.json: storage-root resolution, load with v1 migration fallback,
/// atomic saves, and a debounced save for high-frequency updates (window drag).
/// </summary>
public sealed class ConfigService : IDisposable
{
    public const string SettingsFileName = "settings.json";

    private readonly Lock _saveLock = new();
    private Timer? _debounceTimer;
    private bool _disposed;

    public ConfigService(string storageRoot)
    {
        StorageRoot = storageRoot;
        Settings = new AppSettings();
    }

    public string StorageRoot { get; }

    public AppSettings Settings { get; private set; }

    public string SettingsPath => Path.Combine(StorageRoot, SettingsFileName);

    /// <summary>Presets produced by a v1 migration during <see cref="Load"/>; empty otherwise.</summary>
    public IReadOnlyList<Preset> MigratedPresets { get; private set; } = [];

    /// <summary>
    /// Picks the app's storage root: the exe directory when writable (portable mode),
    /// otherwise %APPDATA%\VirtualFunctions.
    /// </summary>
    public static string ResolveStorageRoot(string exeDirectory, string appDataDirectory)
    {
        try
        {
            string probe = Path.Combine(exeDirectory, ".writetest");
            File.WriteAllText(probe, string.Empty);
            File.Delete(probe);
            return exeDirectory;
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            Directory.CreateDirectory(appDataDirectory);
            return appDataDirectory;
        }
    }

    /// <summary>
    /// Loads settings.json. When absent, attempts a one-time v1 migration
    /// (results exposed via <see cref="MigratedPresets"/>); otherwise starts with defaults.
    /// A corrupt settings.json is preserved as .corrupt and replaced with defaults.
    /// </summary>
    public void Load()
    {
        if (File.Exists(SettingsPath))
        {
            try
            {
                Settings = AtomicJsonFile.Read(SettingsPath, ConfigJsonContext.Default.AppSettings) ?? new AppSettings();
            }
            catch (JsonException)
            {
                File.Copy(SettingsPath, SettingsPath + ".corrupt", overwrite: true);
                Settings = new AppSettings();
            }

            Settings.Normalize();
            return;
        }

        MigrationResult? migration = ConfigMigratorV1.Migrate(StorageRoot);
        if (migration is not null)
        {
            Settings = migration.Settings;
            MigratedPresets = migration.Presets;
        }

        Settings.Normalize();
        Save();
    }

    public void Save()
    {
        lock (_saveLock)
        {
            _debounceTimer?.Dispose();
            _debounceTimer = null;
            AtomicJsonFile.Write(SettingsPath, Settings, ConfigJsonContext.Default.AppSettings);
        }
    }

    /// <summary>Coalesces bursts of changes (e.g. drag) into one save ~500 ms after the last call.</summary>
    public void ScheduleSave()
    {
        lock (_saveLock)
        {
            if (_disposed)
            {
                return;
            }

            _debounceTimer?.Dispose();
            _debounceTimer = new Timer(_ => Save(), null, dueTime: 500, period: Timeout.Infinite);
        }
    }

    public void Dispose()
    {
        lock (_saveLock)
        {
            if (_disposed)
            {
                return;
            }

            _disposed = true;
            bool pending = _debounceTimer is not null;
            _debounceTimer?.Dispose();
            _debounceTimer = null;
            if (pending)
            {
                AtomicJsonFile.Write(SettingsPath, Settings, ConfigJsonContext.Default.AppSettings);
            }
        }
    }
}
