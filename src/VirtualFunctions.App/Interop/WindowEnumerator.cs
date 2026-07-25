using VirtualFunctions.Core.Binding;
using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.Graphics.Dwm;

namespace VirtualFunctions.App.Interop;

/// <summary>
/// Lists the windows a user can actually bring to the foreground, read through the
/// same <see cref="WindowInfoProvider"/> the foreground watcher uses — so a binding
/// picked from this list is guaranteed to match what the watcher will later see.
/// </summary>
public static class WindowEnumerator
{
    public static IReadOnlyList<ForegroundWindowInfo> GetOpenWindows()
    {
        var results = new List<ForegroundWindowInfo>();

        PInvoke.EnumWindows(
            (hwnd, _) =>
            {
                if (!PInvoke.IsWindowVisible(hwnd) ||
                    IsCloaked(hwnd) ||
                    WindowInfoProvider.BelongsToThisProcess(hwnd))
                {
                    return true;
                }

                ForegroundWindowInfo info = WindowInfoProvider.GetInfo(hwnd);
                if (info.Title.Length > 0)
                {
                    results.Add(info);
                }

                return true;
            },
            default);

        return [.. results
            .DistinctBy(w => (w.ProcessName, w.Title, w.ClassName))
            .OrderBy(w => w.ProcessName, StringComparer.OrdinalIgnoreCase)
            .ThenBy(w => w.Title, StringComparer.OrdinalIgnoreCase)];
    }

    /// <summary>Filters DWM-cloaked ghosts (suspended UWP windows) out of the list.</summary>
    private static unsafe bool IsCloaked(HWND hwnd)
    {
        int cloaked = 0;
        HRESULT hr = PInvoke.DwmGetWindowAttribute(
            hwnd, DWMWINDOWATTRIBUTE.DWMWA_CLOAKED, &cloaked, sizeof(int));
        return hr.Succeeded && cloaked != 0;
    }
}
