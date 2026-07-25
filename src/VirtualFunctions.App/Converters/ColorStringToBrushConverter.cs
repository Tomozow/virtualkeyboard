using System.Globalization;
using System.Windows;
using System.Windows.Data;
using System.Windows.Media;

namespace VirtualFunctions.App.Converters;

/// <summary>
/// Hex or named color string → Brush. Null/invalid values yield UnsetValue so the
/// Style's theme default applies (v1 crashed on empty color names — floating.py hover bug).
/// </summary>
public sealed class ColorStringToBrushConverter : IValueConverter
{
    public object Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is string text && !string.IsNullOrWhiteSpace(text))
        {
            try
            {
                if (new BrushConverter().ConvertFromString(text) is Brush brush)
                {
                    brush.Freeze();
                    return brush;
                }
            }
            catch (FormatException)
            {
                // fall through to UnsetValue
            }
            catch (NotSupportedException)
            {
                // fall through to UnsetValue
            }
        }

        return DependencyProperty.UnsetValue;
    }

    public object ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
        => Binding.DoNothing;
}
