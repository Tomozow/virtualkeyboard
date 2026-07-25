using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Serilog;
using VirtualFunctions.Core.Abstractions;
using VirtualFunctions.Core.Input;
using VirtualFunctions.Core.Models;

namespace VirtualFunctions.App.ViewModels;

/// <summary>One button on the floating strip.</summary>
public sealed partial class KeyButtonViewModel : ObservableObject
{
    private readonly IKeySender _keySender;

    public KeyButtonViewModel(string label, string keySpec, IKeySender keySender, KeyModifiers modifiers = KeyModifiers.None)
    {
        Label = label;
        KeySpec = keySpec;
        Modifiers = modifiers;
        _keySender = keySender;
    }

    public string Label { get; }

    public string KeySpec { get; }

    public KeyModifiers Modifiers { get; }

    [ObservableProperty]
    public partial bool IsLatched { get; set; }

    [RelayCommand]
    private void Send()
    {
        KeyStroke? stroke = KeyMap.Parse(KeySpec, Modifiers);
        if (stroke is null)
        {
            Log.Warning("Unknown key spec {KeySpec}", KeySpec);
            return;
        }

        bool ok = _keySender.Send(stroke);
        Log.Information("Key {KeySpec} sent={Ok}", KeySpec, ok);
    }
}
