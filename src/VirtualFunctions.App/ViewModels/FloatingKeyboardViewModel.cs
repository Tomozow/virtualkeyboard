using System.Collections.ObjectModel;
using System.Windows;
using System.Windows.Controls;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using VirtualFunctions.App.Services;
using VirtualFunctions.Core.Config;
using VirtualFunctions.Core.Models;
using ThemeMode = VirtualFunctions.Core.Models.ThemeMode;

namespace VirtualFunctions.App.ViewModels;

public sealed partial class FloatingKeyboardViewModel : ObservableObject
{
    private const double SlotMargin = 6;

    private readonly ConfigService _config;
    private readonly PresetService _presets;
    private readonly KeyDispatchService _dispatcher;

    public FloatingKeyboardViewModel(
        ConfigService config,
        PresetService presets,
        KeyDispatchService dispatcher)
    {
        _config = config;
        _presets = presets;
        _dispatcher = dispatcher;
        IsDelayModeEnabled = _config.Settings.DelayInput.Enabled;

        _presets.ActivePresetChanged += ReloadButtons;
        ReloadButtons();
    }

    public ObservableCollection<KeyButtonViewModel> Buttons { get; } = [];

    /// <summary>Set by the composition root: opens (or activates) the Button Manager window.</summary>
    public Action? OpenManagerRequested { get; set; }

    [ObservableProperty]
    public partial Orientation PanelOrientation { get; set; }

    [ObservableProperty]
    public partial double PanelMaxWidth { get; set; } = double.PositiveInfinity;

    [ObservableProperty]
    public partial double PanelMaxHeight { get; set; } = double.PositiveInfinity;

    [ObservableProperty]
    public partial bool IsDelayModeEnabled { get; set; }

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(ButtonWidth))]
    [NotifyPropertyChangedFor(nameof(ButtonHeight))]
    [NotifyPropertyChangedFor(nameof(ButtonFontSize))]
    public partial bool IsMiniMode { get; set; }

    public double ButtonWidth => IsMiniMode ? 40 : 52;

    public double ButtonHeight => IsMiniMode ? 30 : 42;

    public double ButtonFontSize => IsMiniMode ? 11 : 13;

    public void ReloadButtons()
    {
        IsMiniMode = _config.Settings.Window.DisplayMode == DisplayMode.Mini;

        Buttons.Clear();
        TooltipMode tooltipMode = _config.Settings.Window.TooltipMode;
        foreach (ButtonDefinition definition in _presets.Active.Buttons)
        {
            Buttons.Add(new KeyButtonViewModel(definition, _dispatcher, tooltipMode));
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
        // Flips the *effective* direction — a per-preset override (every migrated
        // v1 preset has one) must follow the toggle, not swallow it.
        if (LayoutResolver.ToggleDirection(_presets.Active, _config.Settings.Window))
        {
            _presets.Repository.Save(_presets.Active);
        }

        _config.ScheduleSave();
        UpdateLayout();
    }

    [RelayCommand]
    private void ToggleDisplayMode()
    {
        WindowSettings window = _config.Settings.Window;
        window.DisplayMode = window.DisplayMode == DisplayMode.Mini ? DisplayMode.Normal : DisplayMode.Mini;
        _config.ScheduleSave();
        IsMiniMode = window.DisplayMode == DisplayMode.Mini;
        UpdateLayout();
    }

    [RelayCommand]
    private void ToggleDelayMode()
    {
        DelayInputSettings delay = _config.Settings.DelayInput;
        delay.Enabled = !delay.Enabled;
        if (!delay.Enabled)
        {
            _dispatcher.Cancel();
        }

        IsDelayModeEnabled = delay.Enabled;
        _config.ScheduleSave();
    }

    [RelayCommand]
    private void OpenManager() => OpenManagerRequested?.Invoke();

    [RelayCommand]
    private static void Exit() => Application.Current.Shutdown();

    private void UpdateLayout()
    {
        int perRow = LayoutResolver.EffectiveButtonsPerRow(_presets.Active, _config.Settings.Window);
        LayoutDirection direction = LayoutResolver.EffectiveDirection(_presets.Active, _config.Settings.Window);

        double slotWidth = ButtonWidth + SlotMargin;
        double slotHeight = ButtonHeight + SlotMargin;

        if (direction == LayoutDirection.Horizontal)
        {
            PanelOrientation = Orientation.Horizontal;
            PanelMaxWidth = IsMiniMode ? double.PositiveInfinity : perRow * slotWidth;
            PanelMaxHeight = double.PositiveInfinity;
        }
        else
        {
            PanelOrientation = Orientation.Vertical;
            PanelMaxWidth = double.PositiveInfinity;
            PanelMaxHeight = IsMiniMode ? double.PositiveInfinity : perRow * slotHeight;
        }
    }
}
