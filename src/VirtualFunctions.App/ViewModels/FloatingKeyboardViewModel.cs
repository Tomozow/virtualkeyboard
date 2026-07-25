using System.Collections.ObjectModel;
using System.Windows;
using System.Windows.Controls;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using VirtualFunctions.App.Services;
using VirtualFunctions.Core.Abstractions;
using VirtualFunctions.Core.Config;
using VirtualFunctions.Core.Models;
using ThemeMode = VirtualFunctions.Core.Models.ThemeMode;

namespace VirtualFunctions.App.ViewModels;

public sealed partial class FloatingKeyboardViewModel : ObservableObject
{
    private const double ButtonSlotWidth = 58;  // button width + margins
    private const double ButtonSlotHeight = 48;

    private readonly ConfigService _config;
    private readonly PresetService _presets;
    private readonly IKeySender _keySender;

    public FloatingKeyboardViewModel(
        ConfigService config,
        PresetService presets,
        IKeySender keySender)
    {
        _config = config;
        _presets = presets;
        _keySender = keySender;

        _presets.ActivePresetChanged += ReloadButtons;
        ReloadButtons();
    }

    public ObservableCollection<KeyButtonViewModel> Buttons { get; } = [];

    [ObservableProperty]
    public partial Orientation PanelOrientation { get; set; }

    [ObservableProperty]
    public partial double PanelMaxWidth { get; set; } = double.PositiveInfinity;

    [ObservableProperty]
    public partial double PanelMaxHeight { get; set; } = double.PositiveInfinity;

    public void ReloadButtons()
    {
        Buttons.Clear();
        TooltipMode tooltipMode = _config.Settings.Window.TooltipMode;
        foreach (ButtonDefinition definition in _presets.Active.Buttons)
        {
            Buttons.Add(new KeyButtonViewModel(definition, _keySender, tooltipMode));
        }

        UpdateLayout();
    }

    [RelayCommand]
    private void ToggleTheme()
    {
        WindowSettings window = _config.Settings.Window;
        window.Theme = window.Theme == ThemeMode.Dark ? ThemeMode.Light : ThemeMode.Dark;
        ThemeService.Apply(window.Theme);
        _config.ScheduleSave();
    }

    [RelayCommand]
    private void ToggleLayout()
    {
        WindowSettings window = _config.Settings.Window;
        window.LayoutDirection = window.LayoutDirection == LayoutDirection.Horizontal
            ? LayoutDirection.Vertical
            : LayoutDirection.Horizontal;
        _config.ScheduleSave();
        UpdateLayout();
    }

    [RelayCommand]
    private static void Exit() => Application.Current.Shutdown();

    private void UpdateLayout()
    {
        int perRow = _presets.Active.Layout.ButtonsPerRow ?? _config.Settings.Window.ButtonsPerRow;
        LayoutDirection direction = _presets.Active.Layout.Direction ?? _config.Settings.Window.LayoutDirection;

        if (direction == LayoutDirection.Horizontal)
        {
            PanelOrientation = Orientation.Horizontal;
            PanelMaxWidth = perRow * ButtonSlotWidth;
            PanelMaxHeight = double.PositiveInfinity;
        }
        else
        {
            PanelOrientation = Orientation.Vertical;
            PanelMaxWidth = double.PositiveInfinity;
            PanelMaxHeight = perRow * ButtonSlotHeight;
        }
    }
}
