using System.Runtime.InteropServices;
using Serilog;
using VirtualFunctions.Core.Abstractions;
using VirtualFunctions.Core.Input;
using VirtualFunctions.Core.Models;
using Windows.Win32;
using Windows.Win32.UI.Input.KeyboardAndMouse;

namespace VirtualFunctions.App.Interop;

/// <summary>
/// Injects keystrokes with a single SendInput call:
/// modifiers down → main key down/up → modifiers up (reverse order).
/// </summary>
public sealed class KeySenderService : IKeySender
{
    private const ushort VkShift = 0x10;
    private const ushort VkControl = 0x11;
    private const ushort VkMenu = 0x12;
    private const ushort VkLWin = 0x5B;

    public bool Send(KeyStroke stroke)
    {
        ArgumentNullException.ThrowIfNull(stroke);

        var inputs = new List<INPUT>(8);
        ushort[] modifierVks = [.. EnumerateModifierVks(stroke.Modifiers)];

        foreach (ushort vk in modifierVks)
        {
            inputs.Add(BuildKeyInput(vk, KeySendOptions.None, keyUp: false));
        }

        inputs.Add(BuildKeyInput(stroke.Vk, stroke.Flags, keyUp: false));
        inputs.Add(BuildKeyInput(stroke.Vk, stroke.Flags, keyUp: true));

        foreach (ushort vk in modifierVks.Reverse())
        {
            inputs.Add(BuildKeyInput(vk, KeySendOptions.None, keyUp: true));
        }

        INPUT[] buffer = [.. inputs];
        uint sent = PInvoke.SendInput(buffer, Marshal.SizeOf<INPUT>());
        if (sent != buffer.Length)
        {
            int error = Marshal.GetLastWin32Error();
            Log.Warning("SendInput injected {Sent}/{Total} events (Win32 error {Error}) for VK 0x{Vk:X2}",
                sent, buffer.Length, error, stroke.Vk);
            return false;
        }

        return true;
    }

    private static IEnumerable<ushort> EnumerateModifierVks(KeyModifiers modifiers)
    {
        if (modifiers.HasFlag(KeyModifiers.Ctrl))
        {
            yield return VkControl;
        }

        if (modifiers.HasFlag(KeyModifiers.Shift))
        {
            yield return VkShift;
        }

        if (modifiers.HasFlag(KeyModifiers.Alt))
        {
            yield return VkMenu;
        }

        if (modifiers.HasFlag(KeyModifiers.Win))
        {
            yield return VkLWin;
        }
    }

    private static INPUT BuildKeyInput(ushort vk, KeySendOptions keyFlags, bool keyUp)
    {
        KEYBD_EVENT_FLAGS flags = keyUp ? KEYBD_EVENT_FLAGS.KEYEVENTF_KEYUP : 0;
        ushort scan = 0;

        if (!keyFlags.HasFlag(KeySendOptions.VkOnly))
        {
            scan = (ushort)PInvoke.MapVirtualKey(vk, MAP_VIRTUAL_KEY_TYPE.MAPVK_VK_TO_VSC);
        }

        if (keyFlags.HasFlag(KeySendOptions.Extended))
        {
            flags |= KEYBD_EVENT_FLAGS.KEYEVENTF_EXTENDEDKEY;
        }

        return new INPUT
        {
            type = INPUT_TYPE.INPUT_KEYBOARD,
            Anonymous =
            {
                ki = new KEYBDINPUT
                {
                    wVk = (VIRTUAL_KEY)vk,
                    wScan = scan,
                    dwFlags = flags,
                    time = 0,
                    dwExtraInfo = 0,
                },
            },
        };
    }
}
