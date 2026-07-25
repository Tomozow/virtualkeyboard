using CommunityToolkit.Mvvm.ComponentModel;
using VirtualFunctions.Core.Input;
using VirtualFunctions.Core.Models;

namespace VirtualFunctions.App.ViewModels;

/// <summary>Edits a working copy of one ButtonDefinition; applied only on OK.</summary>
public sealed partial class ButtonEditViewModel : ObservableObject
{
    public ButtonEditViewModel(ButtonDefinition source)
    {
        ArgumentNullException.ThrowIfNull(source);
        KeyName = source.Key;
        Label = source.Label;
        IconKind = source.Icon.Kind;
        IconValue = source.Icon.Value;
        Background = source.Background ?? string.Empty;
        ToggleEnabled = source.Toggle.Enabled;
        ToggleColor = source.Toggle.Color;
        ModCtrl = source.Modifiers.HasFlag(KeyModifiers.Ctrl);
        ModShift = source.Modifiers.HasFlag(KeyModifiers.Shift);
        ModAlt = source.Modifiers.HasFlag(KeyModifiers.Alt);
        ModWin = source.Modifiers.HasFlag(KeyModifiers.Win);
        Tooltip = source.Tooltip;
    }

    public static IReadOnlyList<string> SpecialKeyNames { get; } =
        [.. KeyMap.AllKeys.Select(k => k.Name)];

    public static IReadOnlyList<string> EmojiPalette { get; } =
    [
        "😀", "😂", "😊", "😎", "🤔", "👍", "👎", "👋", "🙏", "💪",
        "❤️", "💙", "💚", "💛", "🧡", "💜", "🖤", "🤍", "⭐", "🌟",
        "✨", "🔥", "⚡", "💡", "🎯", "🎨", "🎵", "🎮", "📋", "📌",
        "📎", "✂️", "🔍", "🔒", "🔓", "🔑", "⚙️", "🔧", "🔨", "🛠️",
        "📁", "📂", "💾", "🖥️", "⌨️", "🖱️", "📷", "🎬", "⏱️", "⏰",
        "▶️", "⏸️", "⏹️", "⏭️", "⏮️", "🔁", "✅", "❌", "⭕", "❓",
    ];

    [ObservableProperty]
    public partial string KeyName { get; set; }

    [ObservableProperty]
    public partial string Label { get; set; }

    [ObservableProperty]
    public partial IconKind IconKind { get; set; }

    [ObservableProperty]
    public partial string IconValue { get; set; }

    [ObservableProperty]
    public partial string Background { get; set; }

    [ObservableProperty]
    public partial bool ToggleEnabled { get; set; }

    [ObservableProperty]
    public partial string ToggleColor { get; set; }

    [ObservableProperty]
    public partial bool ModCtrl { get; set; }

    [ObservableProperty]
    public partial bool ModShift { get; set; }

    [ObservableProperty]
    public partial bool ModAlt { get; set; }

    [ObservableProperty]
    public partial bool ModWin { get; set; }

    [ObservableProperty]
    public partial string Tooltip { get; set; }

    [ObservableProperty]
    public partial bool IsCapturingKey { get; set; }

    /// <summary>Null when the current key name resolves; otherwise a validation message.</summary>
    public string? Validate()
        => KeyMap.Parse(KeyName) is null ? $"キー名 '{KeyName}' を解決できません" : null;

    public void ApplyTo(ButtonDefinition target)
    {
        ArgumentNullException.ThrowIfNull(target);
        target.Key = KeyName.Trim();
        target.Label = Label.Trim();
        target.Icon.Kind = IconKind;
        target.Icon.Value = IconValue.Trim();
        target.Background = string.IsNullOrWhiteSpace(Background) ? null : Background.Trim();
        target.Toggle.Enabled = ToggleEnabled;
        target.Toggle.Color = string.IsNullOrWhiteSpace(ToggleColor) ? "#d1d5db" : ToggleColor.Trim();
        target.Modifiers =
            (ModCtrl ? KeyModifiers.Ctrl : KeyModifiers.None) |
            (ModShift ? KeyModifiers.Shift : KeyModifiers.None) |
            (ModAlt ? KeyModifiers.Alt : KeyModifiers.None) |
            (ModWin ? KeyModifiers.Win : KeyModifiers.None);
        target.Tooltip = Tooltip.Trim();
    }
}
