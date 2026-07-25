using System.Text.Json;
using VirtualFunctions.Core.Input;
using VirtualFunctions.Core.Models;

namespace VirtualFunctions.Core.Config;

/// <summary>
/// CRUD over presets\*.json. One file per preset; preset identity is its Name
/// (unique, case-insensitive). Buttons live only here — never in settings.json
/// (v1 kept a duplicate copy in config.json; that duplication is gone).
/// </summary>
public sealed class PresetRepository
{
    public const string DefaultPresetName = "default";

    private readonly Dictionary<string, Preset> _presets = new(StringComparer.OrdinalIgnoreCase);
    private readonly List<string> _loadErrors = [];

    public PresetRepository(string presetsDirectory)
    {
        PresetsDirectory = presetsDirectory;
    }

    public string PresetsDirectory { get; }

    /// <summary>Files that failed to parse during <see cref="Load"/> (kept on disk, skipped).</summary>
    public IReadOnlyList<string> LoadErrors => _loadErrors;

    public IReadOnlyCollection<Preset> All =>
        [.. _presets.Values.OrderBy(p => p.Name, StringComparer.OrdinalIgnoreCase)];

    public void Load()
    {
        _presets.Clear();
        _loadErrors.Clear();
        if (!Directory.Exists(PresetsDirectory))
        {
            return;
        }

        foreach (string file in Directory.EnumerateFiles(PresetsDirectory, "*.json"))
        {
            try
            {
                Preset? preset = AtomicJsonFile.Read(file, ConfigJsonContext.Default.Preset);
                // v1 preset files (no schemaVersion → 0 after deserialization defaults?) are
                // migrated by ConfigMigratorV1 before this repository ever sees the directory;
                // anything unparsable or non-v2 here is skipped, never overwritten.
                if (preset is null || preset.SchemaVersion < 2 || string.IsNullOrWhiteSpace(preset.Name))
                {
                    _loadErrors.Add(file);
                    continue;
                }

                _presets[preset.Name] = preset;
            }
            catch (JsonException)
            {
                _loadErrors.Add(file);
            }
        }
    }

    public bool TryGet(string name, out Preset preset)
    {
        if (_presets.TryGetValue(name, out Preset? found))
        {
            preset = found;
            return true;
        }

        preset = null!;
        return false;
    }

    /// <summary>Adds or updates a preset and persists it.</summary>
    public void Save(Preset preset)
    {
        ArgumentNullException.ThrowIfNull(preset);
        ArgumentException.ThrowIfNullOrWhiteSpace(preset.Name);

        preset.Modified = DateTimeOffset.Now;
        _presets[preset.Name] = preset;
        AtomicJsonFile.Write(PathFor(preset.Name), preset, ConfigJsonContext.Default.Preset);
    }

    public bool Delete(string name)
    {
        if (!_presets.Remove(name))
        {
            return false;
        }

        string path = PathFor(name);
        if (File.Exists(path))
        {
            File.Delete(path);
        }

        return true;
    }

    public bool Rename(string oldName, string newName)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(newName);
        if (!_presets.TryGetValue(oldName, out Preset? preset) || _presets.ContainsKey(newName))
        {
            return false;
        }

        Delete(oldName);
        preset.Name = newName;
        Save(preset);
        return true;
    }

    /// <summary>Imports a preset JSON file; renames on collision ("name (2)"). Returns the stored preset.</summary>
    public Preset? Import(string sourcePath)
    {
        Preset? preset;
        try
        {
            preset = AtomicJsonFile.Read(sourcePath, ConfigJsonContext.Default.Preset);
        }
        catch (JsonException)
        {
            return null;
        }

        if (preset is null || string.IsNullOrWhiteSpace(preset.Name))
        {
            return null;
        }

        string name = preset.Name;
        for (int i = 2; _presets.ContainsKey(name); i++)
        {
            name = $"{preset.Name} ({i})";
        }

        preset.Name = name;
        Save(preset);
        return preset;
    }

    public void Export(string name, string destinationPath)
    {
        if (!TryGet(name, out Preset preset))
        {
            throw new KeyNotFoundException($"Preset not found: {name}");
        }

        AtomicJsonFile.Write(destinationPath, preset, ConfigJsonContext.Default.Preset);
    }

    /// <summary>Ensures at least one preset exists; creates the default F13–F24 set when empty.</summary>
    public Preset EnsureDefault()
    {
        if (_presets.Count > 0)
        {
            return All.First();
        }

        var preset = new Preset
        {
            Name = DefaultPresetName,
            Description = "F13-F24",
        };
        for (int i = 13; i <= 24; i++)
        {
            preset.Buttons.Add(new ButtonDefinition
            {
                Key = $"F{i}",
                Label = $"F{i}",
                Icon = new ButtonIcon { Kind = IconKind.Text, Value = $"F{i}" },
            });
        }

        Save(preset);
        return preset;
    }

    private string PathFor(string presetName)
    {
        // Preset names may contain characters invalid in file names.
        var sanitized = new string([.. presetName.Select(c => Path.GetInvalidFileNameChars().Contains(c) ? '_' : c)]);
        return Path.Combine(PresetsDirectory, sanitized + ".json");
    }
}
