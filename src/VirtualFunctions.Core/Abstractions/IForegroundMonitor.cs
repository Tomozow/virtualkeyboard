using VirtualFunctions.Core.Binding;

namespace VirtualFunctions.Core.Abstractions;

public interface IForegroundMonitor
{
    /// <summary>Raised on the UI thread whenever a window outside this process gains foreground.</summary>
    event Action<ForegroundWindowInfo>? ForegroundChanged;

    /// <summary>Last known foreground window that does not belong to this process.</summary>
    ForegroundWindowInfo? LastExternalWindow { get; }
}
