using System.Windows;
using System.Windows.Input;
using VirtualFunctions.App.Interop;
using VirtualFunctions.Core.Binding;
using VirtualFunctions.Core.Models;

namespace VirtualFunctions.App.Views;

/// <summary>
/// Lets the user pick a running window as the app-binding source instead of
/// typing a pattern by hand. The chosen field value is exactly what the
/// foreground watcher reports, so the resulting Exact match cannot drift.
/// </summary>
public partial class WindowPickerDialog : Window
{
    public WindowPickerDialog()
    {
        InitializeComponent();
        Refresh();
    }

    /// <summary>Value to match on; set when the dialog returns true.</summary>
    public string SelectedPattern { get; private set; } = string.Empty;

    public BindingTarget SelectedTarget { get; private set; } = BindingTarget.ProcessName;

    private void Refresh() => WindowList.ItemsSource = WindowEnumerator.GetOpenWindows();

    private void OnRefresh(object sender, RoutedEventArgs e) => Refresh();

    private void OnListDoubleClick(object sender, MouseButtonEventArgs e)
    {
        if (WindowList.SelectedItem is not null)
        {
            OnOk(sender, e);
        }
    }

    private void OnOk(object sender, RoutedEventArgs e)
    {
        if (WindowList.SelectedItem is not ForegroundWindowInfo info)
        {
            MessageBox.Show(this, "ウィンドウを選択してください。", Title,
                MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }

        SelectedTarget =
            TargetTitle.IsChecked == true ? BindingTarget.WindowTitle :
            TargetClass.IsChecked == true ? BindingTarget.ClassName :
            BindingTarget.ProcessName;

        SelectedPattern = SelectedTarget switch
        {
            BindingTarget.WindowTitle => info.Title,
            BindingTarget.ClassName => info.ClassName,
            _ => info.ProcessName,
        };

        if (SelectedPattern.Length == 0)
        {
            MessageBox.Show(this, "選択したウィンドウからその値を取得できませんでした。別の一致対象を選んでください。",
                Title, MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        DialogResult = true;
    }
}
