using System.Windows;
using System.Windows.Input;
using VirtualFunctions.App.Interop;
using VirtualFunctions.App.ViewModels;

namespace VirtualFunctions.App.Views;

public partial class FloatingKeyboardWindow : Window
{
    private Point _pressPoint;
    private bool _maybeDrag;

    public FloatingKeyboardWindow(FloatingKeyboardViewModel viewModel)
    {
        InitializeComponent();
        DataContext = viewModel;
    }

    protected override void OnSourceInitialized(EventArgs e)
    {
        base.OnSourceInitialized(e);
        WindowStyler.MakeNoActivateToolWindow(this, alpha: 0.85);
    }

    // Drag-from-anywhere with click/drag disambiguation (port of floating.py:554-607).
    protected override void OnPreviewMouseLeftButtonDown(MouseButtonEventArgs e)
    {
        base.OnPreviewMouseLeftButtonDown(e);
        _pressPoint = e.GetPosition(this);
        _maybeDrag = true;
    }

    protected override void OnPreviewMouseMove(MouseEventArgs e)
    {
        base.OnPreviewMouseMove(e);
        if (!_maybeDrag || e.LeftButton != MouseButtonState.Pressed)
        {
            return;
        }

        Point current = e.GetPosition(this);
        bool passedThreshold =
            Math.Abs(current.X - _pressPoint.X) > SystemParameters.MinimumHorizontalDragDistance ||
            Math.Abs(current.Y - _pressPoint.Y) > SystemParameters.MinimumVerticalDragDistance;
        if (!passedThreshold)
        {
            return;
        }

        _maybeDrag = false;
        (Mouse.Captured as UIElement)?.ReleaseMouseCapture();
        try
        {
            DragMove();
        }
        catch (InvalidOperationException)
        {
            // Mouse button released between the check and the call — nothing to drag.
        }
    }

    protected override void OnPreviewMouseLeftButtonUp(MouseButtonEventArgs e)
    {
        base.OnPreviewMouseLeftButtonUp(e);
        _maybeDrag = false;
    }
}
