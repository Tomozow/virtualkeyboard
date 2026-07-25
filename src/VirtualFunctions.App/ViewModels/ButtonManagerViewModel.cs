using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Serilog;
using VirtualFunctions.App.Services;
using VirtualFunctions.Core.Config;
using VirtualFunctions.Core.Models;

namespace VirtualFunctions.App.ViewModels;

/// <summary>
/// Backs the Button Manager window: button CRUD/reorder for the selected preset,
/// preset lifecycle operations, and the per-preset app-binding rule.
/// All edits persist immediately; the floating strip refreshes via PresetService.
/// </summary>
public sealed partial class ButtonManagerViewModel : ObservableObject
{
    private readonly ConfigService _config;
    private readonly PresetService _presets;
    private Preset? _selected;
    private bool _loadingBinding;

    public ButtonManagerViewModel(ConfigService config, PresetService presets)
    {
        _config = config;
        _presets = presets;
        AppBindingGloballyEnabled = _config.Settings.AppBindingEnabled;
        RefreshPresetNames(_presets.Active.Name);
    }

    /// <summary>Set by the window: prompts the user for a name (title, prompt, initial); null = cancelled.</summary>
    public Func<string, string, string, string?>? PromptForName { get; set; }

    /// <summary>Set by the window: opens the edit dialog for a definition; false = cancelled.</summary>
    public Func<ButtonDefinition, bool>? EditButtonInteraction { get; set; }

    /// <summary>Set by the window: yes/no confirmation.</summary>
    public Func<string, bool>? Confirm { get; set; }

    public ObservableCollection<string> PresetNames { get; } = [];

    public ObservableCollection<ButtonDefinition> Buttons { get; } = [];

    [ObservableProperty]
    public partial string? SelectedPresetName { get; set; }

    [ObservableProperty]
    public partial ButtonDefinition? SelectedButton { get; set; }

    [ObservableProperty]
    public partial bool AppBindingGloballyEnabled { get; set; }

    [ObservableProperty]
    public partial bool BindingEnabled { get; set; }

    [ObservableProperty]
    public partial string BindingPattern { get; set; } = string.Empty;

    [ObservableProperty]
    public partial BindingTarget BindingTarget { get; set; }

    [ObservableProperty]
    public partial BindingMatch BindingMatch { get; set; }

    [ObservableProperty]
    public partial int BindingPriority { get; set; } = 1;

    public bool IsSelectedPresetActive =>
        _selected is not null &&
        string.Equals(_selected.Name, _presets.Active.Name, StringComparison.OrdinalIgnoreCase);

    partial void OnSelectedPresetNameChanged(string? value)
    {
        if (value is not null && _presets.Repository.TryGet(value, out Preset preset))
        {
            LoadPreset(preset);
        }
    }

    partial void OnAppBindingGloballyEnabledChanged(bool value)
    {
        _config.Settings.AppBindingEnabled = value;
        _config.ScheduleSave();
    }

    partial void OnBindingEnabledChanged(bool value) => SaveBinding();

    partial void OnBindingPatternChanged(string value) => SaveBinding();

    partial void OnBindingTargetChanged(BindingTarget value) => SaveBinding();

    partial void OnBindingMatchChanged(BindingMatch value) => SaveBinding();

    partial void OnBindingPriorityChanged(int value) => SaveBinding();

    // --- button operations -------------------------------------------------

    [RelayCommand]
    private void AddButton()
    {
        if (_selected is null)
        {
            return;
        }

        var definition = new ButtonDefinition { Key = "F13", Label = "F13", Icon = new ButtonIcon { Value = "F13" } };
        if (EditButtonInteraction?.Invoke(definition) != true)
        {
            return;
        }

        _selected.Buttons.Add(definition);
        Buttons.Add(definition);
        SelectedButton = definition;
        SavePreset();
    }

    [RelayCommand]
    private void EditButton()
    {
        if (_selected is null || SelectedButton is null)
        {
            return;
        }

        if (EditButtonInteraction?.Invoke(SelectedButton) == true)
        {
            int index = Buttons.IndexOf(SelectedButton);
            SavePreset();
            ReloadButtons(index);
        }
    }

    [RelayCommand]
    private void DuplicateButton()
    {
        if (_selected is null || SelectedButton is null)
        {
            return;
        }

        ButtonDefinition copy = Clone(SelectedButton);
        int index = _selected.Buttons.IndexOf(SelectedButton) + 1;
        _selected.Buttons.Insert(index, copy);
        Buttons.Insert(index, copy);
        SelectedButton = copy;
        SavePreset();
    }

    [RelayCommand]
    private void RemoveButton()
    {
        if (_selected is null || SelectedButton is null)
        {
            return;
        }

        int index = _selected.Buttons.IndexOf(SelectedButton);
        _selected.Buttons.Remove(SelectedButton);
        Buttons.Remove(SelectedButton);
        SelectedButton = Buttons.Count > 0 ? Buttons[Math.Min(index, Buttons.Count - 1)] : null;
        SavePreset();
    }

    [RelayCommand]
    private void MoveButtonUp() => MoveButton(-1);

    [RelayCommand]
    private void MoveButtonDown() => MoveButton(+1);

    // --- preset operations -------------------------------------------------

    [RelayCommand]
    private void ApplyPreset()
    {
        if (_selected is not null)
        {
            _presets.Activate(_selected.Name);
            OnPropertyChanged(nameof(IsSelectedPresetActive));
        }
    }

    [RelayCommand]
    private void NewPreset()
    {
        string? name = PromptForName?.Invoke("新規プリセット", "プリセット名:", string.Empty);
        if (name is null || _presets.Repository.TryGet(name, out _))
        {
            return;
        }

        var preset = new Preset { Name = name, Description = string.Empty };
        _presets.Repository.Save(preset);
        RefreshPresetNames(name);
    }

    [RelayCommand]
    private void DuplicatePreset()
    {
        if (_selected is null)
        {
            return;
        }

        string? name = PromptForName?.Invoke("プリセットを複製", "複製先のプリセット名:", _selected.Name + " (copy)");
        if (name is null || _presets.Repository.TryGet(name, out _))
        {
            return;
        }

        var copy = new Preset
        {
            Name = name,
            Description = _selected.Description,
            Layout = new LayoutSettings
            {
                Direction = _selected.Layout.Direction,
                ButtonsPerRow = _selected.Layout.ButtonsPerRow,
                IconSize = _selected.Layout.IconSize,
            },
            AppBinding = new AppBinding
            {
                Enabled = _selected.AppBinding.Enabled,
                Pattern = _selected.AppBinding.Pattern,
                Target = _selected.AppBinding.Target,
                Match = _selected.AppBinding.Match,
                Priority = _selected.AppBinding.Priority,
            },
        };
        copy.Buttons.AddRange(_selected.Buttons.Select(Clone));
        _presets.Repository.Save(copy);
        RefreshPresetNames(name);
    }

    [RelayCommand]
    private void RenamePreset()
    {
        if (_selected is null)
        {
            return;
        }

        string? name = PromptForName?.Invoke("プリセット名の変更", "新しい名前:", _selected.Name);
        if (name is null || name == _selected.Name)
        {
            return;
        }

        bool wasActive = IsSelectedPresetActive;
        if (!_presets.Repository.Rename(_selected.Name, name))
        {
            return;
        }

        if (wasActive)
        {
            _presets.Activate(name);
        }

        RefreshPresetNames(name);
    }

    [RelayCommand]
    private void DeletePreset()
    {
        if (_selected is null || PresetNames.Count <= 1)
        {
            return;
        }

        if (Confirm?.Invoke($"プリセット '{_selected.Name}' を削除しますか？") != true)
        {
            return;
        }

        string deleted = _selected.Name;
        _presets.Repository.Delete(deleted);
        string fallback = _presets.Repository.All.First().Name;
        if (string.Equals(_presets.Active.Name, deleted, StringComparison.OrdinalIgnoreCase))
        {
            _presets.Activate(fallback);
        }

        RefreshPresetNames(fallback);
    }

    // Import/Export are handled by the window (file dialogs) via these entry points.
    public void ImportPresetFrom(string path)
    {
        Preset? imported = _presets.Repository.Import(path);
        if (imported is null)
        {
            Log.Warning("Preset import failed: {Path}", path);
            return;
        }

        RefreshPresetNames(imported.Name);
    }

    public void ExportSelectedTo(string path)
    {
        if (_selected is not null)
        {
            _presets.Repository.Export(_selected.Name, path);
        }
    }

    // --- internals ---------------------------------------------------------

    private void MoveButton(int delta)
    {
        if (_selected is null || SelectedButton is null)
        {
            return;
        }

        int index = _selected.Buttons.IndexOf(SelectedButton);
        int target = index + delta;
        if (index < 0 || target < 0 || target >= _selected.Buttons.Count)
        {
            return;
        }

        (_selected.Buttons[index], _selected.Buttons[target]) = (_selected.Buttons[target], _selected.Buttons[index]);
        Buttons.Move(index, target);
        SavePreset();
    }

    private void LoadPreset(Preset preset)
    {
        _selected = preset;
        ReloadButtons(0);

        _loadingBinding = true;
        try
        {
            BindingEnabled = preset.AppBinding.Enabled;
            BindingPattern = preset.AppBinding.Pattern;
            BindingTarget = preset.AppBinding.Target;
            BindingMatch = preset.AppBinding.Match;
            BindingPriority = preset.AppBinding.Priority;
        }
        finally
        {
            _loadingBinding = false;
        }

        OnPropertyChanged(nameof(IsSelectedPresetActive));
    }

    private void ReloadButtons(int selectIndex)
    {
        Buttons.Clear();
        if (_selected is null)
        {
            return;
        }

        foreach (ButtonDefinition button in _selected.Buttons)
        {
            Buttons.Add(button);
        }

        if (Buttons.Count > 0)
        {
            SelectedButton = Buttons[Math.Clamp(selectIndex, 0, Buttons.Count - 1)];
        }
    }

    private void RefreshPresetNames(string select)
    {
        PresetNames.Clear();
        foreach (Preset preset in _presets.Repository.All)
        {
            PresetNames.Add(preset.Name);
        }

        SelectedPresetName = PresetNames.FirstOrDefault(n => string.Equals(n, select, StringComparison.OrdinalIgnoreCase))
            ?? PresetNames.FirstOrDefault();
    }

    private void SaveBinding()
    {
        if (_selected is null || _loadingBinding)
        {
            return;
        }

        _selected.AppBinding.Enabled = BindingEnabled;
        _selected.AppBinding.Pattern = BindingPattern.Trim();
        _selected.AppBinding.Target = BindingTarget;
        _selected.AppBinding.Match = BindingMatch;
        _selected.AppBinding.Priority = BindingPriority;
        SavePreset(reloadStrip: false);
    }

    private void SavePreset(bool reloadStrip = true)
    {
        if (_selected is null)
        {
            return;
        }

        _presets.Repository.Save(_selected);
        if (reloadStrip && IsSelectedPresetActive)
        {
            _presets.NotifyActiveEdited();
        }
    }

    private static ButtonDefinition Clone(ButtonDefinition source) => new()
    {
        Key = source.Key,
        Label = source.Label,
        Icon = new ButtonIcon { Kind = source.Icon.Kind, Value = source.Icon.Value },
        Background = source.Background,
        Toggle = new ToggleSettings { Enabled = source.Toggle.Enabled, Color = source.Toggle.Color },
        Modifiers = source.Modifiers,
        Tooltip = source.Tooltip,
    };
}
