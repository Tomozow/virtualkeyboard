namespace VirtualFunctions.Core.Models;

/// <summary>Modifier keys held down while a button's main key is sent.</summary>
[Flags]
public enum KeyModifiers
{
    None = 0,
    Ctrl = 1,
    Shift = 2,
    Alt = 4,
    Win = 8,
}
