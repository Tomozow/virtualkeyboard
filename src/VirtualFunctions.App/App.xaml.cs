using System.Globalization;
using System.IO;
using System.Windows;
using Serilog;
using VirtualFunctions.App.Interop;
using VirtualFunctions.App.ViewModels;
using VirtualFunctions.App.Views;

namespace VirtualFunctions.App;

public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        Log.Logger = new LoggerConfiguration()
            .MinimumLevel.Information()
            .WriteTo.File(
                Path.Combine(AppContext.BaseDirectory, "logs", "app-.log"),
                formatProvider: CultureInfo.InvariantCulture,
                rollingInterval: RollingInterval.Day,
                fileSizeLimitBytes: 1_000_000,
                retainedFileCountLimit: 3,
                rollOnFileSizeLimit: true)
            .CreateLogger();

        DispatcherUnhandledException += (_, args) =>
            Log.Fatal(args.Exception, "Unhandled dispatcher exception");

        Log.Information("Virtual Functions starting");

        // Composition root — services are constructed here and only here.
        var keySender = new KeySenderService();
        var viewModel = new FloatingKeyboardViewModel(keySender);
        var window = new FloatingKeyboardWindow(viewModel);
        window.Show();
    }

    protected override void OnExit(ExitEventArgs e)
    {
        Log.Information("Virtual Functions exiting");
        Log.CloseAndFlush();
        base.OnExit(e);
    }
}
