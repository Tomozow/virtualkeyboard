using System.Windows;
using System.Windows.Input;
using VirtualFunctions.App.Interop;
using VirtualFunctions.App.ViewModels;
using VirtualFunctions.Core.Config;

namespace VirtualFunctions.App.Views;

public partial class FloatingKeyboardWindow : Window
{
    private readonly ConfigService _config;
    private Point _pressPoint;
    private bool _maybeDrag;
    private bool _trackPosition;

    public FloatingKeyboardWindow(FloatingKeyboardViewModel viewModel, ConfigService config)
    {
        InitializeComponent();
        DataContext = viewModel;
        _config = config;

        (Left, Top) = ClampToVirtualScreen(_config.Settings.Window.X, _config.Settings.Window.Y);
        ContentRendered += (_, _) => _trackPosition = true;
    }

    protected override void OnSourceInitialized(EventArgs e)
    {
        base.OnSourceInitialized(e);
        WindowStyler.MakeNoActivateToolWindow(this, _config.Settings.Window.Opacity);
    }

    protected override void OnLocationChanged(EventArgs e)
    {
        base.OnLocationChanged(e);
        if (!_trackPosition)
        {
            return;
        }

        _config.Settings.Window.X = Left;
        _config.Settings.Window.Y = Top;
        _config.ScheduleSave();
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

    /// <summary>Keeps the strip reachable when a saved position points at a detached monitor.</summary>
    private static (double X, double Y) ClampToVirtualScreen(double x, double y)
    {
        double minX = SystemParameters.VirtualScreenLeft;
        double minY = SystemParameters.VirtualScreenTop;
        double maxX = minX + SystemParameters.VirtualScreenWidth - 80;
        double maxY = minY + SystemParameters.VirtualScreenHeight - 40;
        return (Math.Clamp(x, minX, Math.Max(minX, maxX)), Math.Clamp(y, minY, Math.Max(minY, maxY)));
    }
}
