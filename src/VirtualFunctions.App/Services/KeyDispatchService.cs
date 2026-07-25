using System.Windows.Threading;
using Serilog;
using VirtualFunctions.Core.Abstractions;
using VirtualFunctions.Core.Config;
using VirtualFunctions.Core.Input;

namespace VirtualFunctions.App.Services;

/// <summary>
/// Routes button presses: immediate send, or an armed countdown when delay-input
/// mode is on (port of floating.py:1978-2068 — v1 hard-coded 3000 ms and ignored
/// its own config; here the configured DelayMs is honored).
/// A new press during a countdown re-arms it with the new key.
/// </summary>
public sealed class KeyDispatchService : IDisposable
{
    private readonly ConfigService _config;
    private readonly IKeySender _sender;
    private readonly DispatcherTimer _timer;
    private KeyStroke? _pending;
    private string _pendingLabel = string.Empty;
    private DateTime _fireAt;

    public KeyDispatchService(ConfigService config, IKeySender sender)
    {
        _config = config;
        _sender = sender;
        _timer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(100) };
        _timer.Tick += (_, _) => Tick();
    }

    /// <summary>Raised ~10×/s while a countdown runs: (button label, remaining seconds).</summary>
    public event Action<string, double>? CountdownTick;

    /// <summary>Raised when a countdown finishes or is cancelled.</summary>
    public event Action? CountdownEnded;

    public void Dispatch(KeyStroke stroke, string label)
    {
        ArgumentNullException.ThrowIfNull(stroke);

        if (!_config.Settings.DelayInput.Enabled)
        {
            SendNow(stroke, label);
            return;
        }

        _pending = stroke;
        _pendingLabel = label;
        _fireAt = DateTime.UtcNow.AddMilliseconds(_config.Settings.DelayInput.DelayMs);
        CountdownTick?.Invoke(label, _config.Settings.DelayInput.DelayMs / 1000.0);
        _timer.Start();
    }

    public void Cancel()
    {
        if (_pending is null)
        {
            return;
        }

        _pending = null;
        _timer.Stop();
        CountdownEnded?.Invoke();
    }

    public void Dispose() => _timer.Stop();

    private void Tick()
    {
        if (_pending is null)
        {
            _timer.Stop();
            return;
        }

        double remaining = (_fireAt - DateTime.UtcNow).TotalSeconds;
        if (remaining > 0)
        {
            CountdownTick?.Invoke(_pendingLabel, remaining);
            return;
        }

        KeyStroke stroke = _pending;
        string label = _pendingLabel;
        _pending = null;
        _timer.Stop();
        CountdownEnded?.Invoke();
        SendNow(stroke, label);
    }

    private void SendNow(KeyStroke stroke, string label)
    {
        bool ok = _sender.Send(stroke);
        Log.Information("Key {Label} sent={Ok}", label, ok);
    }
}
