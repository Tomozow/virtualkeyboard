using System.Diagnostics;
using VirtualFunctions.Core.Binding;
using Windows.Win32;
using Windows.Win32.Foundation;

namespace VirtualFunctions.App.Interop;

/// <summary>Reads title / class name / process name for a window handle.</summary>
public static class WindowInfoProvider
{
    public static unsafe ForegroundWindowInfo GetInfo(nint hwnd)
    {
        var handle = (HWND)hwnd;

        string title = string.Empty;
        int titleLength = PInvoke.GetWindowTextLength(handle);
        if (titleLength > 0)
        {
            Span<char> buffer = stackalloc char[titleLength + 1];
            fixed (char* p = buffer)
            {
                int copied = PInvoke.GetWindowText(handle, p, buffer.Length);
                title = new string(buffer[..copied]);
            }
        }

        string className = string.Empty;
        Span<char> classBuffer = stackalloc char[256];
        fixed (char* p = classBuffer)
        {
            int copied = PInvoke.GetClassName(handle, p, classBuffer.Length);
            if (copied > 0)
            {
                className = new string(classBuffer[..copied]);
            }
        }

        string processName = string.Empty;
        uint processId = 0;
        _ = PInvoke.GetWindowThreadProcessId(handle, &processId);
        if (processId != 0)
        {
            try
            {
                using var process = Process.GetProcessById((int)processId);
                processName = process.ProcessName;
            }
            catch (ArgumentException)
            {
                // Process exited between the query and the lookup.
            }
        }

        return new ForegroundWindowInfo(hwnd, title, processName, className);
    }

    public static bool BelongsToThisProcess(nint hwnd)
    {
        uint processId = 0;
        unsafe
        {
            _ = PInvoke.GetWindowThreadProcessId((HWND)hwnd, &processId);
        }

        return processId == Environment.ProcessId;
    }
}
