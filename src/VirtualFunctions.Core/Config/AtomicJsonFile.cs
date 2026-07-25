using System.Text.Json;
using System.Text.Json.Serialization.Metadata;

namespace VirtualFunctions.Core.Config;

/// <summary>
/// Crash-safe JSON persistence: serialize to a sibling .tmp file, then swap it
/// into place with File.Replace (keeping a .bak of the previous version).
/// </summary>
public static class AtomicJsonFile
{
    public static void Write<T>(string path, T value, JsonTypeInfo<T> typeInfo)
    {
        string directory = Path.GetDirectoryName(Path.GetFullPath(path))
            ?? throw new ArgumentException($"Path has no directory: {path}", nameof(path));
        Directory.CreateDirectory(directory);

        string tempPath = path + ".tmp";
        string backupPath = path + ".bak";

        File.WriteAllText(tempPath, JsonSerializer.Serialize(value, typeInfo));

        if (File.Exists(path))
        {
            File.Replace(tempPath, path, backupPath, ignoreMetadataErrors: true);
        }
        else
        {
            File.Move(tempPath, path);
        }
    }

    /// <summary>Returns default when the file is absent; throws JsonException on corrupt content.</summary>
    public static T? Read<T>(string path, JsonTypeInfo<T> typeInfo)
    {
        if (!File.Exists(path))
        {
            return default;
        }

        return JsonSerializer.Deserialize(File.ReadAllText(path), typeInfo);
    }
}
