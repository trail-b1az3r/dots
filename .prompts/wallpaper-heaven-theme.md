# Prompt for Claude Opus 5.5: Wallpaper Heaven built-in theme

You are Claude Opus 5.5, working in the Halcyon repository. Build one new built-in theme from the wallpaper in this repo. Work through it end to end, and keep the rest of the repo unchanged unless a step below says otherwise.

## The wallpaper

- File: `dots/.config/hypr/hyprland/halcyon/themes/wallpapers/wallpaper-heaven-kenami.jpg` (2560 x 1440, converted from the original PNG).
- Subject: a road at sunset with a large red ring in the sky. Warm orange and red light, dark silhouetted foreground.
- Artist signature: "Kenami". The image comes from Wallpaper Heaven. Credit both in the theme's `description` and in the About page Credits section.

## What to build

1. A new built-in theme file, `dots/.config/hypr/hyprland/halcyon/themes/wallpaper-heaven-kenami.json`, that follows the schema of the existing themes (`fractured-glass.json`, `shattered-glass.json`). Use the wallpaper above. Derive the colour seed and scheme from the sunset palette, and check that the palette is readable.
2. Floating-window borders: follow the rule already in `halcyon-theme`'s `render_lua`. Floating windows get a rounder corner and a border darkened from the theme's active colour. This theme is not in `PLAIN_WINDOW_THEMES`, so it gets the rule automatically. Check the rendered Lua.
3. The time feature. The user said this theme "will have this feature". The most likely reading is that the theme is auto-applied at a set time, for example at sunset. The user has not defined the exact behaviour, and the built-in time auto-apply is not built yet. Before you build any time logic, confirm with the user what the feature is and how it should work. If the user confirms it, implement it and cover it with tests. If not, build only the theme.

## Rules

- Do not claim a feature works until you have verified it. Run `./scripts/validate.sh`, `python3 -m unittest tests/test_assistant.py`, and check the theme with `halcyon-theme` in a temporary config directory. Note that `halcyon-theme apply` in a temp directory fails without the installed shell scripts, which is a test limit and not a bug.
- Do not commit personal data, and do not change package names, upstream links, or the config path `~/.config/illogical-impulse`.
- Commit with `Co-Authored-By: Claude <noreply@anthropic.com>` and the session trailer. Do not put a model identifier in commits, PR text, or code comments.

## When you are done

Once the theme is built, the validation passes, and you have verified it on screen or by rendering it, tell the user it is ready and bug free. Then delete this file, `.prompts/wallpaper-heaven-theme.md`, in the same commit that completes the theme. If anything is still open, do not delete this file, and list what is left.
