using System.Text.Json.Serialization;
using VirtualFunctions.Core.Models;

namespace VirtualFunctions.Core.Config;

[JsonSourceGenerationOptions(
    WriteIndented = true,
    PropertyNamingPolicy = JsonKnownNamingPolicy.CamelCase,
    UseStringEnumConverter = true,
    DefaultIgnoreCondition = JsonIgnoreCondition.Never)]
[JsonSerializable(typeof(AppSettings))]
[JsonSerializable(typeof(Preset))]
public sealed partial class ConfigJsonContext : JsonSerializerContext;
