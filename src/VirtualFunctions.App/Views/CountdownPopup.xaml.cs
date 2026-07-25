using System.Globalization;
using System.Windows;
using VirtualFunctions.App.Interop;

namespace VirtualFunctions.App.Views;

/// <summary>Small non-activating "⏱️ N.N秒" popup shown above the strip while armed.</summary>
public partial class CountdownPopup : Window
{
    public CountdownPopup()
    {
        InitializeComponent();
    }

    protected override void OnSourceInitialized(EventArgs e)
    {
        base.OnSourceInitialized(e);
        WindowStyler.MakeNoActivateToolWindow(this, alpha: 0.95);
    }

    public void Update(string label, double remainingSeconds)
        => CountdownText.Text = string.Create(
            CultureInfo.InvariantCulture, $"⏱️ {label}: {remainingSeconds:0.0}秒");

    public void PlaceAbove(Window anchor)
    {
        ArgumentNullException.ThrowIfNull(anchor);
        Left = anchor.Left;
        Top = Math.Max(SystemParameters.VirtualScreenTop, anchor.Top - ActualHeight - 8);
    }
}
