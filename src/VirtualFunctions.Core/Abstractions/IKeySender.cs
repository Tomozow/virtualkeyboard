using VirtualFunctions.Core.Input;

namespace VirtualFunctions.Core.Abstractions;

public interface IKeySender
{
    /// <summary>Sends the stroke to the focused window. Returns false when injection failed.</summary>
    bool Send(KeyStroke stroke);
}
