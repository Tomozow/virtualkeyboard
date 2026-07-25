using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using VirtualFunctions.Core.Abstractions;

namespace VirtualFunctions.App.ViewModels;

public sealed partial class FloatingKeyboardViewModel : ObservableObject
{
    private readonly IKeySender _keySender;

    public FloatingKeyboardViewModel(IKeySender keySender)
    {
        _keySender = keySender;
        LoadDefaultButtons();
    }

    public ObservableCollection<KeyButtonViewModel> Buttons { get; } = [];

    // M1 placeholder: F13–F24. Replaced by config-driven buttons in M2.
    private void LoadDefaultButtons()
    {
        for (int i = 13; i <= 24; i++)
        {
            Buttons.Add(new KeyButtonViewModel($"F{i}", $"F{i}", _keySender));
        }
    }
}
