using Serilog;
using VirtualFunctions.Core.Abstractions;
using VirtualFunctions.Core.Binding;
using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.UI.Accessibility;

namespace VirtualFunctions.App.Interop;

/// <summary>
/// Event-driven foreground tracking via SetWinEventHook(EVENT_SYSTEM_FOREGROUND) —
/// replaces the Python version's 100 ms polling thread (services/focus.py).
/// Must be created on the UI thread (out-of-context hooks deliver via the message pump).
/// The delegate is kept in a field so the GC can't collect it while the hook lives.
/// </summary>
public sealed class ForegroundWatcherService : IForegroundMonitor, IDisposable
{
    private readonly WINEVENTPROC _callback;
    private UnhookWinEventSafeHandle? _hook;

    public ForegroundWatcherService()
    {
        _callback = OnWinEvent;
    }

    public event Action<ForegroundWindowInfo>? ForegroundChanged;

    public ForegroundWindowInfo? LastExternalWindow { get; private set; }

    public void Start()
    {
        if (_hook is not null)
        {
            return;
        }

        _hook = PInvoke.SetWinEventHook(
            PInvoke.EVENT_SYSTEM_FOREGROUND,
            PInvoke.EVENT_SYSTEM_FOREGROUND,
            null,
            _callback,
            idProcess: 0,
            idThread: 0,
            PInvoke.WINEVENT_OUTOFCONTEXT);

        if (_hook.IsInvalid)
        {
            Log.Error("SetWinEventHook failed — app-binding auto-switch disabled");
        }

        // Seed with the current foreground window so bindings work before the first switch.
        HWND current = PInvoke.GetForegroundWindow();
        if (current != HWND.Null)
        {
            HandleForeground(current);
        }
    }

    public void Dispose()
    {
        _hook?.Dispose();
        _hook = null;
    }

    private void OnWinEvent(
        HWINEVENTHOOK hook, uint eventId, HWND hwnd, int objectId, int childId, uint threadId, uint timestamp)
    {
        if (eventId != PInvoke.EVENT_SYSTEM_FOREGROUND || hwnd == HWND.Null)
        {
            return;
        }

        HandleForeground(hwnd);
    }

    private void HandleForeground(HWND hwnd)
    {
        if (WindowInfoProvider.BelongsToThisProcess(hwnd))
        {
            return;
        }

        ForegroundWindowInfo info = WindowInfoProvider.GetInfo(hwnd);
        LastExternalWindow = info;
        ForegroundChanged?.Invoke(info);
    }
}
