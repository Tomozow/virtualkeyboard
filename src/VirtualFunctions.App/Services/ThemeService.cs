using System.Windows;
using ThemeMode = VirtualFunctions.Core.Models.ThemeMode;

namespace VirtualFunctions.App.Services;

/// <summary>Swaps the theme ResourceDictionary (slot 0 of the app's merged dictionaries).</summary>
public static class ThemeService
{
    public static void Apply(ThemeMode mode)
    {
        var dictionary = new ResourceDictionary
        {
            Source = new Uri($"pack://application:,,,/Themes/{mode}.xaml"),
        };

        var merged = Application.Current.Resources.MergedDictionaries;
        if (merged.Count == 0)
        {
            merged.Add(dictionary);
        }
        else
        {
            merged[0] = dictionary;
        }
    }
}
