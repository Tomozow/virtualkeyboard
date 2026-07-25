using System.Windows.Threading;
using Serilog;
using VirtualFunctions.Core.Abstractions;
using VirtualFunctions.Core.Binding;
using VirtualFunctions.Core.Config;

namespace VirtualFunctions.App.Services;

/// <summary>
/// Always-on preset auto-switching (the v1 feature only worked while the Button
/// Manager was open — old button_manager.py:1367-1465). Debounces foreground
/// changes 200 ms so rapid Alt-Tab passes don't thrash presets.
/// </summary>
public sealed class AppBindingService : IDisposable
{
    private readonly ConfigService _config;
    private readonly PresetService _presets;
    private readonly IForegroundMonitor _monitor;
    private readonly DispatcherTimer _debounce;
    private ForegroundWindowInfo? _pending;

    public AppBindingService(ConfigService config, PresetService presets, IForegroundMonitor monitor)
    {
        _config = config;
        _presets = presets;
        _monitor = monitor;
        _debounce = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(200) };
        _debounce.Tick += (_, _) => Evaluate();
        _monitor.ForegroundChanged += OnForegroundChanged;
    }

    public void Dispose()
    {
        _monitor.ForegroundChanged -= OnForegroundChanged;
        _debounce.Stop();
    }

    private void OnForegroundChanged(ForegroundWindowInfo info)
    {
        _pending = info;
        _debounce.Stop();
        _debounce.Start();
    }

    private void Evaluate()
    {
        _debounce.Stop();
        ForegroundWindowInfo? info = _pending;
        _pending = null;
        if (info is null || !_config.Settings.AppBindingEnabled)
        {
            return;
        }

        string? match = AppBindingMatcher.FindBestMatch(info, _presets.Repository.All);
        if (match is null || string.Equals(match, _presets.Active.Name, StringComparison.OrdinalIgnoreCase))
        {
            return;
        }

        Log.Information("App-binding: {Process} / {Title} → preset {Preset}",
            info.ProcessName, info.Title, match);
        _presets.Activate(match, persist: false);
    }
}
