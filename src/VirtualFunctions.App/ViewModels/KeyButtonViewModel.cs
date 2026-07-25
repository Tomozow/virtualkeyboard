using System.IO;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Serilog;
using VirtualFunctions.App.Services;
using VirtualFunctions.Core.Input;
using VirtualFunctions.Core.Models;

namespace VirtualFunctions.App.ViewModels;

/// <summary>One button on the floating strip, built from a ButtonDefinition.</summary>
public sealed partial class KeyButtonViewModel : ObservableObject
{
    private readonly KeyDispatchService _dispatcher;

    public KeyButtonViewModel(ButtonDefinition definition, KeyDispatchService dispatcher, TooltipMode tooltipMode)
    {
        ArgumentNullException.ThrowIfNull(definition);
        Definition = definition;
        _dispatcher = dispatcher;
        TooltipText = BuildTooltip(definition, tooltipMode);
    }

    public ButtonDefinition Definition { get; }

    public string Label => string.IsNullOrEmpty(Definition.Label) ? Definition.Key : Definition.Label;

    /// <summary>Text shown on the button: the icon text/emoji, falling back to the label.</summary>
    public string DisplayText =>
        Definition.Icon.Kind != IconKind.Image && !string.IsNullOrEmpty(Definition.Icon.Value)
            ? Definition.Icon.Value
            : Label;

    /// <summary>Image file path when the icon is an image and the file exists; otherwise null.</summary>
    public string? ImagePath =>
        Definition.Icon.Kind == IconKind.Image && File.Exists(Definition.Icon.Value)
            ? Definition.Icon.Value
            : null;

    public string? TooltipText { get; }

    /// <summary>Explicit background (hex/named) honoring the latch state; null → theme default.</summary>
    public string? CurrentBackground =>
        IsLatched ? Definition.Toggle.Color
        : string.IsNullOrEmpty(Definition.Background) ? null : Definition.Background;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(CurrentBackground))]
    public partial bool IsLatched { get; set; }

    [RelayCommand]
    private void Send()
    {
        if (Definition.Toggle.Enabled)
        {
            IsLatched = !IsLatched;
        }

        KeyStroke? stroke = KeyMap.Parse(Definition.Key, Definition.Modifiers);
        if (stroke is null)
        {
            Log.Warning("Unknown key spec {KeySpec}", Definition.Key);
            return;
        }

        _dispatcher.Dispatch(stroke, Label);
    }

    private static string? BuildTooltip(ButtonDefinition definition, TooltipMode mode)
    {
        string label = string.IsNullOrEmpty(definition.Label) ? definition.Key : definition.Label;
        string? custom = string.IsNullOrEmpty(definition.Tooltip) ? null : definition.Tooltip;
        string? text = mode switch
        {
            TooltipMode.None => null,
            TooltipMode.Label => label,
            TooltipMode.Key => definition.Key,
            _ => label == definition.Key ? definition.Key : $"{label} ({definition.Key})",
        };

        return custom is null ? text : text is null ? custom : $"{custom}\n{text}";
    }
}
