namespace VirtualFunctions.Core.Models;

public enum LayoutDirection
{
    Horizontal,
    Vertical,
}

public enum DisplayMode
{
    Normal,
    Mini,
}

public enum TooltipMode
{
    None,
    Label,
    Key,
    Both,
}

public enum ThemeMode
{
    Light,
    Dark,
}

public enum IconKind
{
    Text,
    Emoji,
    Image,
}

public enum BindingTarget
{
    WindowTitle,
    ProcessName,
    ClassName,
}

public enum BindingMatch
{
    Partial,
    Exact,
}
