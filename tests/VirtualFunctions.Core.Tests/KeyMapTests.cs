using VirtualFunctions.Core.Input;
using VirtualFunctions.Core.Models;

namespace VirtualFunctions.Core.Tests;

public class KeyMapTests
{
    [Theory]
    [InlineData("F1", 0x70)]
    [InlineData("F12", 0x7B)]
    [InlineData("F13", 0x7C)]
    [InlineData("F24", 0x87)]
    public void FunctionKeys_ResolveToExpectedVk(string name, int vk)
    {
        Assert.True(KeyMap.TryResolveKey(name, out KeyDefinition def));
        Assert.Equal((ushort)vk, def.Vk);
    }

    [Fact]
    public void F13AndAbove_AreVkOnly()
    {
        for (int i = 13; i <= 24; i++)
        {
            Assert.True(KeyMap.TryResolveKey($"F{i}", out KeyDefinition def));
            Assert.True(def.Flags.HasFlag(KeySendOptions.VkOnly));
        }
    }

    // v1-compatible IME keys and their Japanese aliases (win32_types.py:27-32, keysender.py:412-417).
    [Theory]
    [InlineData("Kana", 0x15)]
    [InlineData("かな", 0x15)]
    [InlineData("Kanji", 0x19)]
    [InlineData("Hankaku", 0x19)]
    [InlineData("Zenkaku", 0x19)]
    [InlineData("Hankaku/Zenkaku", 0x19)]
    [InlineData("半角/全角", 0x19)]
    [InlineData("Convert", 0x1C)]
    [InlineData("Henkan", 0x1C)]
    [InlineData("変換", 0x1C)]
    [InlineData("NonConvert", 0x1D)]
    [InlineData("Muhenkan", 0x1D)]
    [InlineData("無変換", 0x1D)]
    [InlineData("IME_ON", 0xF2)]
    [InlineData("IME_OFF", 0xF3)]
    public void ImeKeys_ResolveToV1CompatibleVk(string name, int vk)
    {
        Assert.True(KeyMap.TryResolveKey(name, out KeyDefinition def));
        Assert.Equal((ushort)vk, def.Vk);
        Assert.True(def.Flags.HasFlag(KeySendOptions.VkOnly));
    }

    [Theory]
    [InlineData("A", 0x41)]
    [InlineData("Z", 0x5A)]
    [InlineData("0", 0x30)]
    [InlineData("9", 0x39)]
    [InlineData("Space", 0x20)]
    [InlineData("Enter", 0x0D)]
    [InlineData("Semicolon", 0xBA)]
    [InlineData("Quote", 0xDE)]
    public void LettersDigitsSpecialsSymbols_Resolve(string name, int vk)
    {
        Assert.True(KeyMap.TryResolveKey(name, out KeyDefinition def));
        Assert.Equal((ushort)vk, def.Vk);
    }

    [Fact]
    public void Lookup_IsCaseInsensitive()
    {
        Assert.True(KeyMap.TryResolveKey("f13", out KeyDefinition def));
        Assert.Equal(0x7C, def.Vk);
    }

    [Fact]
    public void NavigationKeys_AreExtended()
    {
        foreach (string name in new[] { "Up", "Down", "Left", "Right", "Insert", "Delete", "Home", "End", "PageUp", "PageDown" })
        {
            Assert.True(KeyMap.TryResolveKey(name, out KeyDefinition def));
            Assert.True(def.Flags.HasFlag(KeySendOptions.Extended), $"{name} should be extended");
        }
    }

    [Fact]
    public void Parse_SingleKey_HasNoModifiers()
    {
        KeyStroke? stroke = KeyMap.Parse("F13");
        Assert.NotNull(stroke);
        Assert.Equal(0x7C, stroke.Vk);
        Assert.Equal(KeyModifiers.None, stroke.Modifiers);
    }

    [Fact]
    public void Parse_Combination_CollectsModifiers()
    {
        KeyStroke? stroke = KeyMap.Parse("Ctrl+Shift+C");
        Assert.NotNull(stroke);
        Assert.Equal(0x43, stroke.Vk);
        Assert.Equal(KeyModifiers.Ctrl | KeyModifiers.Shift, stroke.Modifiers);
    }

    [Fact]
    public void Parse_MergesPerButtonModifiers()
    {
        KeyStroke? stroke = KeyMap.Parse("C", KeyModifiers.Ctrl);
        Assert.NotNull(stroke);
        Assert.Equal(KeyModifiers.Ctrl, stroke.Modifiers);
    }

    [Theory]
    [InlineData("")]
    [InlineData("NoSuchKey")]
    [InlineData("Hyper+C")]
    [InlineData("Ctrl+")]
    public void Parse_InvalidSpecs_ReturnNull(string spec)
    {
        Assert.Null(KeyMap.Parse(spec));
    }

    [Fact]
    public void NameFromVk_RoundTripsCanonicalNames()
    {
        Assert.Equal("F13", KeyMap.NameFromVk(0x7C));
        Assert.Equal("Convert", KeyMap.NameFromVk(0x1C));
        Assert.Null(KeyMap.NameFromVk(0xFF));
    }

    [Fact]
    public void AllKeys_HaveUniqueNames()
    {
        var names = KeyMap.AllKeys.Select(k => k.Name).ToList();
        Assert.Equal(names.Count, names.Distinct(StringComparer.OrdinalIgnoreCase).Count());
    }
}
