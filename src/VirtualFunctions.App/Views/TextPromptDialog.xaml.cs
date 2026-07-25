using System.Windows;

namespace VirtualFunctions.App.Views;

public partial class TextPromptDialog : Window
{
    public TextPromptDialog(string title, string prompt, string initialValue = "")
    {
        InitializeComponent();
        Title = title;
        PromptText.Text = prompt;
        InputBox.Text = initialValue;
        Loaded += (_, _) =>
        {
            InputBox.SelectAll();
            InputBox.Focus();
        };
    }

    public string Value => InputBox.Text;

    /// <summary>Shows the prompt; returns the entered text, or null when cancelled/empty.</summary>
    public static string? Show(Window owner, string title, string prompt, string initialValue = "")
    {
        var dialog = new TextPromptDialog(title, prompt, initialValue) { Owner = owner };
        bool? result = dialog.ShowDialog();
        string text = dialog.Value.Trim();
        return result == true && text.Length > 0 ? text : null;
    }

    private void OnOk(object sender, RoutedEventArgs e) => DialogResult = true;
}
