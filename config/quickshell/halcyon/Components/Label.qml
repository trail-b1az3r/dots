import QtQuick
import qs.Config

/**
 * Text with Halcyon's typography already applied.
 *
 * Exists so that no panel has to remember the family, the colour role or
 * the rendering hints — and so that changing the type scale changes every
 * label at once.
 */
Text {
    id: root

    /** caption | footnote | body | bodyLarge | title | titleLarge | display | hero */
    property string variant: "body"
    /** primary | secondary | tertiary | disabled | accent | onAccent | inherit */
    property string tone: "primary"

    font.family: Theme.fontFamily
    font.pixelSize: {
        switch (root.variant) {
        case "caption": return Theme.sizeCaption;
        case "footnote": return Theme.sizeFootnote;
        case "bodyLarge": return Theme.sizeBodyLarge;
        case "title": return Theme.sizeTitle;
        case "titleLarge": return Theme.sizeTitleLarge;
        case "display": return Theme.sizeDisplay;
        case "hero": return Theme.sizeHero;
        default: return Theme.sizeBody;
        }
    }
    font.weight: {
        switch (root.variant) {
        case "title":
        case "titleLarge": return Theme.weightSemibold;
        case "display":
        case "hero": return Theme.weightBold;
        case "caption": return Theme.weightMedium;
        default: return Theme.weightRegular;
        }
    }
    // Large text is set slightly tight and small text slightly loose,
    // which is the difference between type that was set and type that was
    // merely sized.
    font.letterSpacing: {
        if (root.variant === "hero" || root.variant === "display") return -0.6;
        if (root.variant === "titleLarge" || root.variant === "title") return -0.2;
        if (root.variant === "caption") return 0.2;
        return 0;
    }

    color: {
        switch (root.tone) {
        case "secondary": return Theme.textSecondary;
        case "tertiary": return Theme.textTertiary;
        case "disabled": return Theme.textDisabled;
        case "accent": return Theme.accentText;
        case "onAccent": return Theme.onAccent;
        default: return Theme.text;
        }
    }
    textFormat: Text.PlainText
    elide: Text.ElideRight
    verticalAlignment: Text.AlignVCenter
}
