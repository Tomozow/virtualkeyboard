using VirtualFunctions.Core.Models;

namespace VirtualFunctions.Core.Input;

/// <summary>Per-key send quirks, carried as data in <see cref="KeyMap"/>.</summary>
[Flags]
public enum KeySendOptions
{
    None = 0,

    /// <summary>Send with KEYEVENTF_EXTENDEDKEY (arrows, nav cluster, NumLock…).</summary>
    Extended = 1,

    /// <summary>Send the virtual key without a scan code (F13–F24, IME keys).</summary>
    VkOnly = 2,
}

/// <summary>A fully resolved key press: main VK + modifiers to hold.</summary>
public sealed record KeyStroke(ushort Vk, KeyModifiers Modifiers, KeySendOptions Flags);
