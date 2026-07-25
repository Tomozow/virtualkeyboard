using VirtualFunctions.Core.Models;

namespace VirtualFunctions.Core.Binding;

/// <summary>
/// Pure matching of a foreground window against preset app-bindings.
/// Semantics ported from the Python v1 app-integration build
/// (old/current_app_with_app_integration/.../button_manager.py:1367-1436):
/// case-insensitive, Partial = Contains / Exact = Equals, highest priority wins,
/// first-listed preset wins ties.
/// </summary>
public static class AppBindingMatcher
{
    /// <summary>Returns the name of the best-matching preset, or null when nothing matches.</summary>
    public static string? FindBestMatch(ForegroundWindowInfo window, IEnumerable<Preset> presets)
    {
        ArgumentNullException.ThrowIfNull(window);
        ArgumentNullException.ThrowIfNull(presets);

        string? bestName = null;
        int bestPriority = int.MinValue;

        foreach (Preset preset in presets)
        {
            AppBinding binding = preset.AppBinding;
            if (!binding.Enabled || string.IsNullOrEmpty(binding.Pattern))
            {
                continue;
            }

            string target = binding.Target switch
            {
                BindingTarget.ProcessName => window.ProcessName,
                BindingTarget.ClassName => window.ClassName,
                _ => window.Title,
            };

            if (!IsMatch(target, binding.Pattern, binding.Match))
            {
                continue;
            }

            if (binding.Priority > bestPriority)
            {
                bestPriority = binding.Priority;
                bestName = preset.Name;
            }
        }

        return bestName;
    }

    private static bool IsMatch(string target, string pattern, BindingMatch match)
    {
        if (string.IsNullOrEmpty(target))
        {
            return false;
        }

        return match == BindingMatch.Exact
            ? string.Equals(target, pattern, StringComparison.OrdinalIgnoreCase)
            : target.Contains(pattern, StringComparison.OrdinalIgnoreCase);
    }
}
