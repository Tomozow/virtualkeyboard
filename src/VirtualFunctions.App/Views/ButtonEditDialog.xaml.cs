using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using Microsoft.Win32;
using VirtualFunctions.App.ViewModels;
using VirtualFunctions.Core.Input;
using VirtualFunctions.Core.Models;

namespace VirtualFunctions.App.Views;

public partial class ButtonEditDialog : Window
{
    private readonly ButtonEditViewModel _viewModel;

    public ButtonEditDialog(ButtonEditViewModel viewModel)
    {
        InitializeComponent();
        _viewModel = viewModel;
        DataContext = viewModel;
    }

    // Physical key capture (port of button_edit_dialog.py:674-740).
    protected override void OnPreviewKeyDown(KeyEventArgs e)
    {
        if (!_viewModel.IsCapturingKey)
        {
            base.OnPreviewKeyDown(e);
            return;
        }

        Key key = e.Key == Key.System ? e.SystemKey : e.Key;
        if (key is Key.LeftShift or Key.RightShift or Key.LeftCtrl or Key.RightCtrl
            or Key.LeftAlt or Key.RightAlt or Key.LWin or Key.RWin)
        {
            e.Handled = true;
            return; // modifiers alone don't finish a capture
        }

        int vk = KeyInterop.VirtualKeyFromKey(key);
        string? name = KeyMap.NameFromVk((ushort)vk);
        if (name is not null)
        {
            _viewModel.KeyName = name;
            _viewModel.IsCapturingKey = false;
        }

        e.Handled = true;
    }

    private void OnBrowseImage(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFileDialog
        {
            Title = "アイコン画像を選択",
            Filter = "画像ファイル|*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.ico;*.webp|すべてのファイル|*.*",
        };
        if (dialog.ShowDialog(this) == true)
        {
            _viewModel.IconValue = dialog.FileName;
            _viewModel.IconKind = IconKind.Image;
        }
    }

    private void OnEmojiPicked(object sender, RoutedEventArgs e)
    {
        if (sender is Button { Content: string emoji })
        {
            _viewModel.IconValue = emoji;
            _viewModel.IconKind = IconKind.Emoji;
        }
    }

    private void OnOk(object sender, RoutedEventArgs e)
    {
        string? error = _viewModel.Validate();
        if (error is not null)
        {
            MessageBox.Show(this, error, "ボタン編集", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        DialogResult = true;
    }
}
