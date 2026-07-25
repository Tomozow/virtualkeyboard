using System.Windows;
using System.Windows.Interop;
using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.UI.WindowsAndMessaging;

namespace VirtualFunctions.App.Interop;

/// <summary>
/// Applies the extended styles that make the floating strip a non-activating,
/// taskbar-invisible, whole-window-alpha tool window
/// (port of floating.py:48-110, without AllowsTransparency).
/// </summary>
public static class WindowStyler
{
    /// <summary>Call from OnSourceInitialized. Alpha is 0.0–1.0.</summary>
    public static void MakeNoActivateToolWindow(Window window, double alpha)
    {
        var hwnd = (HWND)new WindowInteropHelper(window).Handle;

        nint exStyle = PInvoke.GetWindowLongPtr(hwnd, WINDOW_LONG_PTR_INDEX.GWL_EXSTYLE);
        exStyle |= (nint)(WINDOW_EX_STYLE.WS_EX_NOACTIVATE
                          | WINDOW_EX_STYLE.WS_EX_TOOLWINDOW
                          | WINDOW_EX_STYLE.WS_EX_LAYERED);
        PInvoke.SetWindowLongPtr(hwnd, WINDOW_LONG_PTR_INDEX.GWL_EXSTYLE, exStyle);

        SetAlpha(window, alpha);
    }

    public static void SetAlpha(Window window, double alpha)
    {
        var hwnd = (HWND)new WindowInteropHelper(window).Handle;
        byte alphaByte = (byte)Math.Clamp(Math.Round(alpha * 255), 0, 255);
        PInvoke.SetLayeredWindowAttributes(hwnd, new COLORREF(0), alphaByte,
            LAYERED_WINDOW_ATTRIBUTES_FLAGS.LWA_ALPHA);
    }
}
