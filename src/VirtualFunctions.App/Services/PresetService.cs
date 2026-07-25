using Serilog;
using VirtualFunctions.Core.Config;
using VirtualFunctions.Core.Models;

namespace VirtualFunctions.App.Services;

/// <summary>Tracks which preset is active and notifies the UI when it changes.</summary>
public sealed class PresetService
{
    private readonly ConfigService _config;

    public PresetService(ConfigService config, PresetRepository repository)
    {
        _config = config;
        Repository = repository;
        Active = new Preset { Name = PresetRepository.DefaultPresetName };
    }

    public PresetRepository Repository { get; }

    public Preset Active { get; private set; }

    public event Action? ActivePresetChanged;

    /// <summary>Resolves the startup preset from settings, falling back to the first available.</summary>
    public void Initialize()
    {
        Repository.EnsureDefault();
        if (Repository.TryGet(_config.Settings.ActivePreset, out Preset preset))
        {
            Active = preset;
            return;
        }

        Active = Repository.All.First();
        _config.Settings.ActivePreset = Active.Name;
        _config.ScheduleSave();
    }

    /// <summary>Switches the active preset. Returns false when the name is unknown.</summary>
    public bool Activate(string name, bool persist = true)
    {
        if (!Repository.TryGet(name, out Preset preset))
        {
            Log.Warning("Preset {Name} not found", name);
            return false;
        }

        if (ReferenceEquals(preset, Active))
        {
            return true;
        }

        Active = preset;
        if (persist)
        {
            _config.Settings.ActivePreset = name;
            _config.ScheduleSave();
        }

        Log.Information("Active preset: {Name}", name);
        ActivePresetChanged?.Invoke();
        return true;
    }

    /// <summary>Re-raises the change event after the active preset was edited in place.</summary>
    public void NotifyActiveEdited() => ActivePresetChanged?.Invoke();
}
