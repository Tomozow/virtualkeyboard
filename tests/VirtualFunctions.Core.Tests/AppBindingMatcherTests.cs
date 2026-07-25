using VirtualFunctions.Core.Binding;
using VirtualFunctions.Core.Models;

namespace VirtualFunctions.Core.Tests;

public class AppBindingMatcherTests
{
    private static readonly ForegroundWindowInfo Notepad =
        new(Hwnd: 1234, Title: "メモ - Notepad", ProcessName: "notepad", ClassName: "Notepad");

    private static Preset MakePreset(
        string name,
        string pattern,
        BindingTarget target = BindingTarget.WindowTitle,
        BindingMatch match = BindingMatch.Partial,
        int priority = 1,
        bool enabled = true) => new()
        {
            Name = name,
            AppBinding = new AppBinding
            {
                Enabled = enabled,
                Pattern = pattern,
                Target = target,
                Match = match,
                Priority = priority,
            },
        };

    [Fact]
    public void FindBestMatch_PartialTitle_IsCaseInsensitive()
    {
        Preset[] presets = [MakePreset("p1", "NOTEPAD")];
        Assert.Equal("p1", AppBindingMatcher.FindBestMatch(Notepad, presets));
    }

    [Fact]
    public void FindBestMatch_ProcessNameAndClassNameTargets()
    {
        Preset[] presets =
        [
            MakePreset("byProcess", "notepad", BindingTarget.ProcessName),
            MakePreset("byClass", "Notepad", BindingTarget.ClassName),
        ];

        Assert.Equal("byProcess", AppBindingMatcher.FindBestMatch(Notepad, [presets[0]]));
        Assert.Equal("byClass", AppBindingMatcher.FindBestMatch(Notepad, [presets[1]]));
    }

    [Fact]
    public void FindBestMatch_ExactMatch_RequiresFullEquality()
    {
        Preset[] partialOnly = [MakePreset("p1", "Notepad", match: BindingMatch.Exact)];
        Assert.Null(AppBindingMatcher.FindBestMatch(Notepad, partialOnly));

        Preset[] exact = [MakePreset("p2", "メモ - Notepad", match: BindingMatch.Exact)];
        Assert.Equal("p2", AppBindingMatcher.FindBestMatch(Notepad, exact));
    }

    [Fact]
    public void FindBestMatch_HighestPriorityWins()
    {
        Preset[] presets =
        [
            MakePreset("low", "Notepad", priority: 1),
            MakePreset("high", "Notepad", priority: 10),
            MakePreset("mid", "Notepad", priority: 5),
        ];

        Assert.Equal("high", AppBindingMatcher.FindBestMatch(Notepad, presets));
    }

    [Fact]
    public void FindBestMatch_TiedPriority_FirstListedWins()
    {
        Preset[] presets =
        [
            MakePreset("first", "Notepad", priority: 3),
            MakePreset("second", "Notepad", priority: 3),
        ];

        Assert.Equal("first", AppBindingMatcher.FindBestMatch(Notepad, presets));
    }

    [Fact]
    public void FindBestMatch_DisabledOrEmptyPattern_NeverMatches()
    {
        Preset[] presets =
        [
            MakePreset("disabled", "Notepad", enabled: false),
            MakePreset("empty", ""),
        ];

        Assert.Null(AppBindingMatcher.FindBestMatch(Notepad, presets));
    }

    [Fact]
    public void FindBestMatch_EmptyTargetField_NeverMatches()
    {
        var noTitle = new ForegroundWindowInfo(1, "", "proc", "cls");
        Preset[] presets = [MakePreset("p1", "anything")];
        Assert.Null(AppBindingMatcher.FindBestMatch(noTitle, presets));
    }
}
