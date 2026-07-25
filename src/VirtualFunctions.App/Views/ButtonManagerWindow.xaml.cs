using System.Windows;
using System.Windows.Input;
using Microsoft.Win32;
using VirtualFunctions.App.ViewModels;

namespace VirtualFunctions.App.Views;

public partial class ButtonManagerWindow : Window
{
    private readonly ButtonManagerViewModel _viewModel;

    public ButtonManagerWindow(ButtonManagerViewModel viewModel)
    {
        InitializeComponent();
        _viewModel = viewModel;
        DataContext = viewModel;

        viewModel.PromptForName = (title, prompt, initial) => TextPromptDialog.Show(this, title, prompt, initial);
        viewModel.Confirm = message =>
            MessageBox.Show(this, message, "ボタンマネージャ", MessageBoxButton.YesNo, MessageBoxImage.Question)
                == MessageBoxResult.Yes;
        viewModel.PickWindowInteraction = () =>
        {
            var picker = new WindowPickerDialog { Owner = this };
            return picker.ShowDialog() == true
                ? (picker.SelectedPattern, picker.SelectedTarget)
                : null;
        };
        viewModel.EditButtonInteraction = definition =>
        {
            var editViewModel = new ButtonEditViewModel(definition);
            var dialog = new ButtonEditDialog(editViewModel) { Owner = this };
            if (dialog.ShowDialog() != true)
            {
                return false;
            }

            editViewModel.ApplyTo(definition);
            return true;
        };
    }

    private void OnButtonListDoubleClick(object sender, MouseButtonEventArgs e)
    {
        if (_viewModel.EditButtonCommand.CanExecute(null))
        {
            _viewModel.EditButtonCommand.Execute(null);
        }
    }

    private void OnImportPreset(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFileDialog
        {
            Title = "プリセットをインポート",
            Filter = "プリセット JSON|*.json|すべてのファイル|*.*",
        };
        if (dialog.ShowDialog(this) == true)
        {
            _viewModel.ImportPresetFrom(dialog.FileName);
        }
    }

    private void OnExportPreset(object sender, RoutedEventArgs e)
    {
        var dialog = new SaveFileDialog
        {
            Title = "プリセットをエクスポート",
            Filter = "プリセット JSON|*.json",
            FileName = $"{_viewModel.SelectedPresetName}.json",
        };
        if (dialog.ShowDialog(this) == true)
        {
            _viewModel.ExportSelectedTo(dialog.FileName);
        }
    }
}
