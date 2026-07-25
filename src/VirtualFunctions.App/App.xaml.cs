using System.Globalization;
using System.IO;
using System.Windows;
using Serilog;
using VirtualFunctions.App.Interop;
using VirtualFunctions.App.Services;
using VirtualFunctions.App.ViewModels;
using VirtualFunctions.App.Views;
using VirtualFunctions.Core.Config;

namespace VirtualFunctions.App;

// Disposables are released in OnExit — WPF's Application has no IDisposable slot.
[System.Diagnostics.CodeAnalysis.SuppressMessage("Design", "CA1001:Types that own disposable fields should be disposable",
    Justification = "Lifetime matches the process; disposed in OnExit")]
public partial class App : Application
{
    private Mutex? _singleInstanceMutex;
    private ConfigService? _config;

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        _singleInstanceMutex = new Mutex(initiallyOwned: true, @"Local\VirtualFunctions", out bool createdNew);
        if (!createdNew)
        {
            MessageBox.Show("Virtual Functions は既に起動しています。", "Virtual Functions",
                MessageBoxButton.OK, MessageBoxImage.Information);
            Shutdown();
            return;
        }

        string storageRoot = ConfigService.ResolveStorageRoot(
            AppContext.BaseDirectory,
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "VirtualFunctions"));

        Log.Logger = new LoggerConfiguration()
            .MinimumLevel.Information()
            .WriteTo.File(
                Path.Combine(storageRoot, "logs", "app-.log"),
                formatProvider: CultureInfo.InvariantCulture,
                rollingInterval: RollingInterval.Day,
                fileSizeLimitBytes: 1_000_000,
                retainedFileCountLimit: 3,
                rollOnFileSizeLimit: true)
            .CreateLogger();

        DispatcherUnhandledException += (_, args) =>
            Log.Fatal(args.Exception, "Unhandled dispatcher exception");

        Log.Information("Virtual Functions starting (storage root: {Root})", storageRoot);

        // Composition root — services are constructed here and only here.
        _config = new ConfigService(storageRoot);
        _config.Load();

        var repository = new PresetRepository(Path.Combine(storageRoot, "presets"));
        if (_config.MigratedPresets.Count > 0)
        {
            BackupV1Presets(repository.PresetsDirectory);
            foreach (Core.Models.Preset preset in _config.MigratedPresets)
            {
                repository.Save(preset);
            }

            Log.Information("Migrated v1 config: {Count} preset(s)", _config.MigratedPresets.Count);
        }

        repository.Load();
        foreach (string file in repository.LoadErrors)
        {
            Log.Warning("Skipped unreadable preset file {File}", file);
        }

        var presetService = new PresetService(_config, repository);
        presetService.Initialize();

        ThemeService.Apply(_config.Settings.Window.Theme);

        var keySender = new KeySenderService();
        var viewModel = new FloatingKeyboardViewModel(_config, presetService, keySender);
        var window = new FloatingKeyboardWindow(viewModel, _config);
        window.Show();
    }

    protected override void OnExit(ExitEventArgs e)
    {
        Log.Information("Virtual Functions exiting");
        _config?.Dispose();
        Log.CloseAndFlush();
        _singleInstanceMutex?.Dispose();
        base.OnExit(e);
    }

    /// <summary>Preserves the original v1 preset files before v2 files overwrite the directory.</summary>
    private static void BackupV1Presets(string presetsDirectory)
    {
        if (!Directory.Exists(presetsDirectory))
        {
            return;
        }

        string backupDirectory = Path.Combine(presetsDirectory, "_v1_backup");
        Directory.CreateDirectory(backupDirectory);
        foreach (string file in Directory.EnumerateFiles(presetsDirectory, "*.json"))
        {
            File.Copy(file, Path.Combine(backupDirectory, Path.GetFileName(file)), overwrite: true);
        }
    }
}
