using System.Globalization;
using System.Windows.Data;

namespace VirtualFunctions.App.Converters;

/// <summary>Two-way enum↔bool for RadioButton groups (parameter = the enum value).</summary>
public sealed class EnumEqualsConverter : IValueConverter
{
    public object Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
        => Equals(value, parameter);

    public object ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
        => value is true && parameter is not null ? parameter : Binding.DoNothing;
}
