pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.Config

/**
 * The design system, resolved.
 *
 * Reads the token document that `halcyon theme apply` derives from the
 * wallpaper and the user's glass settings, and exposes it as typed
 * properties. Waybar and Hyprland read the same document in their own
 * formats, which is why a colour never has to be defined twice.
 *
 * Every property has a fallback that produces a usable dark theme, so
 * the shell still renders before the first `theme apply` has run.
 */
Singleton {
    id: root

    property var tokens: ({})
    readonly property bool loaded: root.tokens.color !== undefined

    readonly property string mode: root.tokens.mode ?? "dark"
    readonly property bool isDark: root.mode === "dark"

    // ── Colour ─────────────────────────────────────────────────────────

    readonly property var c: root.tokens.color ?? ({})

    function colour(name: string, fallback: color): color {
        const value = root.c[name];
        return value !== undefined ? value : fallback;
    }

    readonly property color accent: root.colour("accent", "#0a84ff")
    readonly property color accentText: root.colour("accentText", "#4ea6ff")
    readonly property color accentHover: root.colour("accentHover", "#2f95ff")
    readonly property color accentPressed: root.colour("accentPressed", "#0060c9")
    readonly property color onAccent: root.colour("onAccent", "#ffffff")
    readonly property color secondary: root.colour("secondary", "#6d8fd0")
    readonly property color tertiary: root.colour("tertiary", "#7fb0a4")

    readonly property color text: root.colour("text", "#e8eaed")
    readonly property color textSecondary: root.colour("textSecondary", "#a6abb3")
    readonly property color textTertiary: root.colour("textTertiary", "#767c85")
    readonly property color textDisabled: root.colour("textDisabled", "#565b62")

    readonly property color backdrop: root.colour("backdrop", "#0b0d10")
    readonly property color surface: root.colour("surface", "#99161a1f")
    readonly property color surfaceRaised: root.colour("surfaceRaised", "#b31d2128")
    readonly property color surfaceSunken: root.colour("surfaceSunken", "#8011141a")
    readonly property color surfaceHover: root.colour("surfaceHover", "#18ffffff")
    readonly property color surfacePressed: root.colour("surfacePressed", "#28ffffff")
    readonly property color surfaceSelected: root.colour("surfaceSelected", "#330a84ff")
    readonly property color surfaceSolid: root.colour("surfaceSolid", "#161a1f")

    readonly property color glassTint: root.colour("glassTint", "#1a0a84ff")
    readonly property color glassHighlight: root.colour("glassHighlight", "#33ffffff")
    readonly property color glassSpecular: root.colour("glassSpecular", "#14ffffff")
    readonly property color glassBorder: root.colour("glassBorder", "#2bffffff")
    readonly property color glassBorderStrong: root.colour("glassBorderStrong", "#4affffff")
    readonly property color glassInnerShadow: root.colour("glassInnerShadow", "#29000000")

    readonly property color separator: root.colour("separator", "#1affffff")
    readonly property color shadow: root.colour("shadow", "#60000000")
    readonly property color scrim: root.colour("scrim", "#6b000000")

    readonly property color success: root.colour("success", "#3ecf8e")
    readonly property color warning: root.colour("warning", "#f5af20")
    readonly property color danger: root.colour("danger", "#f4514f")
    readonly property color info: root.colour("info", "#0a84ff")

    readonly property color workspaceActive: root.colour("workspaceActive", root.accent)
    readonly property color workspaceOccupied: root.colour("workspaceOccupied", "#bfa6abb3")
    readonly property color workspaceIdle: root.colour("workspaceIdle", "#66767c85")

    // ── Glass ──────────────────────────────────────────────────────────

    readonly property var glassTokens: root.tokens.glass ?? ({})
    readonly property real glassOpacity: root.glassTokens.opacity ?? 0.6
    readonly property real saturation: root.glassTokens.saturation ?? 1.2
    readonly property real specular: root.glassTokens.specularStrength ?? 0.5
    readonly property real refraction: root.glassTokens.refraction ?? 0.4
    readonly property real noise: root.glassTokens.noise ?? 0.012
    readonly property real borderOpacity: root.glassTokens.borderOpacity ?? 0.34

    // ── Geometry ───────────────────────────────────────────────────────

    readonly property var radiusTokens: root.tokens.radius ?? ({})
    readonly property int radiusXs: root.radiusTokens.xs ?? 6
    readonly property int radiusSm: root.radiusTokens.sm ?? 10
    readonly property int radiusMd: root.radiusTokens.md ?? 14
    readonly property int radiusLg: root.radiusTokens.lg ?? 18
    readonly property int radiusXl: root.radiusTokens.xl ?? 26
    readonly property int radiusXxl: root.radiusTokens.xxl ?? 36
    readonly property real radiusPower: root.radiusTokens.power ?? 3.0

    readonly property var spacingTokens: root.tokens.spacing ?? ({})
    readonly property int spacingXxs: root.spacingTokens.xxs ?? 2
    readonly property int spacingXs: root.spacingTokens.xs ?? 4
    readonly property int spacingSm: root.spacingTokens.sm ?? 6
    readonly property int spacingMd: root.spacingTokens.md ?? 10
    readonly property int spacingLg: root.spacingTokens.lg ?? 16
    readonly property int spacingXl: root.spacingTokens.xl ?? 24
    readonly property int panelPadding: root.spacingTokens.panel ?? 12
    readonly property int panelPaddingTight: root.spacingTokens.panelTight ?? 8
    readonly property int panelPaddingLoose: root.spacingTokens.panelLoose ?? 18

    // ── Typography ─────────────────────────────────────────────────────

    readonly property var type: root.tokens.typography ?? ({})
    readonly property string fontFamily: root.type.family ?? "Inter"
    readonly property string fontMono: root.type.mono ?? "JetBrains Mono"
    readonly property var fontSizes: root.type.size ?? ({})

    readonly property int sizeCaption: root.fontSizes.caption ?? 11
    readonly property int sizeFootnote: root.fontSizes.footnote ?? 12
    readonly property int sizeBody: root.fontSizes.body ?? 13
    readonly property int sizeBodyLarge: root.fontSizes.bodyLarge ?? 15
    readonly property int sizeTitle: root.fontSizes.title ?? 17
    readonly property int sizeTitleLarge: root.fontSizes.titleLarge ?? 21
    readonly property int sizeDisplay: root.fontSizes.display ?? 30
    readonly property int sizeHero: root.fontSizes.hero ?? 44

    readonly property int weightRegular: 400
    readonly property int weightMedium: 500
    readonly property int weightSemibold: 600
    readonly property int weightBold: 700

    // ── Motion ─────────────────────────────────────────────────────────

    readonly property var motion: root.tokens.motion ?? ({})
    readonly property var durations: root.motion.duration ?? ({})
    readonly property var curves: root.motion.curve ?? ({})

    readonly property bool animationsEnabled: !(root.motion.disabled ?? false)
    readonly property bool reducedMotion: root.motion.reduced ?? false

    readonly property int durInstant: root.animationsEnabled ? (root.durations.instant ?? 90) : 0
    readonly property int durQuick: root.animationsEnabled ? (root.durations.quick ?? 160) : 0
    readonly property int durStandard: root.animationsEnabled ? (root.durations.standard ?? 240) : 0
    readonly property int durEmphasised: root.animationsEnabled ? (root.durations.emphasised ?? 380) : 0
    readonly property int durSlow: root.animationsEnabled ? (root.durations.slow ?? 560) : 0
    readonly property int durOverlay: root.animationsEnabled ? (root.durations.overlay ?? 300) : 0
    readonly property int durHud: root.animationsEnabled ? (root.durations.hud ?? 200) : 0

    /**
     * A named easing curve, in the form QML's BezierSpline wants.
     *
     * Hyprland stores the two free control points of a cubic bezier;
     * `easing.bezierCurve` wants three points ending at (1, 1). Same
     * curve, different spelling — converting here means the shell and the
     * compositor genuinely animate identically.
     */
    function curve(name: string): var {
        const points = root.curves[name];
        const p = (points && points.length === 4) ? points : [0.4, 0.0, 0.2, 1.0];
        return [p[0], p[1], p[2], p[3], 1.0, 1.0];
    }

    readonly property var easeStandard: root.curve("standard")
    readonly property var easeDecel: root.curve("decelerate")
    readonly property var easeAccel: root.curve("accelerate")
    readonly property var easeEmphasis: root.curve("emphasised")
    readonly property var easeOvershoot: root.curve("overshoot")

    // ── Elevation ──────────────────────────────────────────────────────

    readonly property var elevation: root.tokens.elevation ?? []

    /** Shadow parameters for a depth level: 1 raised … 4 modal. */
    function shadowFor(level: int): var {
        if (root.elevation.length > level)
            return root.elevation[level];
        return { blur: 24, y: 8, opacity: 0.3, color: root.shadow };
    }

    // ── Quality and accessibility ──────────────────────────────────────

    readonly property var quality: root.tokens.quality ?? ({})
    readonly property bool lowPower: root.quality.lowPower ?? false
    readonly property bool blurEnabled: (root.tokens.blur ?? ({})).enabled ?? true

    readonly property var access: root.tokens.accessibility ?? ({})
    readonly property bool highContrast: root.access.highContrast ?? false
    readonly property bool focusRing: root.access.focusRing ?? true
    readonly property bool screenReaderLabels: root.access.screenReaderLabels ?? true

    /**
     * Whether an effect that costs real GPU time should be drawn at all.
     *
     * Consulted by every decorative layer — specular highlights, noise,
     * refraction — so "Low Power Graphics" and a nearly flat battery both
     * reach the same switch.
     */
    readonly property bool decorativeEffects: !root.lowPower && !root.highContrast

    readonly property var palette: root.tokens.palette ?? ({})

    // ── Loading ────────────────────────────────────────────────────────

    FileView {
        id: file
        path: Paths.themeFile
        watchChanges: true
        printErrors: false

        onFileChanged: this.reload()
        onLoaded: root.parse(this.text())
        onLoadFailed: error => {
            if (error !== FileViewError.FileNotFound)
                console.warn("halcyon: could not read theme.json:", error);
        }
    }

    function parse(text: string): void {
        if (!text || text.length === 0)
            return;
        try {
            const parsed = JSON.parse(text);
            if (parsed && parsed.color)
                root.tokens = parsed;
        } catch (error) {
            console.warn("halcyon: theme.json is not valid JSON:", error);
        }
    }
}
