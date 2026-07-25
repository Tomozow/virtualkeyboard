namespace VirtualFunctions.Core.Binding;

/// <summary>Snapshot of the foreground window used for app-binding matches.</summary>
public sealed record ForegroundWindowInfo(nint Hwnd, string Title, string ProcessName, string ClassName);
