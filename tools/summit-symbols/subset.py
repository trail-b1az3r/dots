#!/usr/bin/env python3
"""Cut Material Symbols Rounded (the variable font) to the icons Summit uses: subset.py VARIABLE.ttf SummitSymbols-vN.ttf.
Keeps the icons' name ligatures and all four axes; see dots/.config/quickshell/Summit/assets/README.md."""
import sys
from fontTools.ttLib import TTFont
from fontTools import subset
src, out = sys.argv[1], sys.argv[2]
# The family and the file both carry the cut's version: every cut with new icons gets the next one.
#  - The family: an older cut stays installed (the package's, ~/.local/share/fonts) until it is updated, and Qt and
#    fontconfig take an installed font of the same family over the one Summit loads: the new icons showed as their
#    names.
#  - The file: Quickshell reloads Summit in the same process when its files change, and Qt keeps a font it has loaded
#    by its path, so a new cut under the old file name was shaped with the new font and drawn with the old one: the
#    icons came out as other icons.
# Summit loads assets/fonts/SummitSymbols-vN.ttf (common/Theme.qml); halcyon/summit/summit.rasi and rofi-menu name the
# family, and the package installs the file. Raise N in all of them together (tests/test_summit_side.py checks).
FAMILY = "Summit Symbols v4"
NAMES = """apps bedtime chevron_left chevron_right clear_day cloud foggy landscape partly_cloudy_day
partly_cloudy_night power_settings_new rainy search thunderstorm weather_snowy wifi wifi_2_bar wifi_1_bar lan wifi_off
volume_off volume_up volume_down volume_mute battery_charging_full battery_full battery_5_bar battery_3_bar
battery_1_bar battery_alert content_paste keyboard select_window eco balance speed bolt schedule close check
settings refresh lock logout restart_alt dark_mode light_mode brightness_medium notifications palette
water_drop air near_me umbrella device_thermostat
arrow_back battery_saver bluetooth bluetooth_connected bluetooth_disabled brightness_low calendar_month check_circle
checklist clear_all coffee colorize delete do_not_disturb_on expand_less expand_more headphones mic mic_off mouse
mobile nightlight notifications_off notifications_unread pause play_arrow priority_high radio_button_checked
radio_button_unchecked replay screenshot_region speaker sports_esports timer tune wb_twilight""".split()
f = TTFont(src)
cmap = f.getBestCmap()
by_name = {}
for cp, g in cmap.items():
    by_name.setdefault(g, cp)
# The ligature glyph for each name: GSUB maps the letters to it; its glyph name is the icon name.
order = set(f.getGlyphOrder())
missing = [n for n in NAMES if n not in order]
if missing:
    print("not in the font:", missing)
keep_glyphs = [n for n in NAMES if n in order]
letters = "abcdefghijklmnopqrstuvwxyz0123456789_"
opts = subset.Options()
opts.layout_features = ["liga", "rlig", "ccmp", "calt"]
opts.layout_closure = False
opts.name_IDs = ["*"]
opts.notdef_outline = True
opts.glyph_names = True
sub = subset.Subsetter(opts)
sub.populate(glyphs=keep_glyphs, unicodes=[ord(c) for c in letters] + [by_name[g] for g in keep_glyphs if g in by_name])
sub.subset(f)
for rec in f["name"].names:
    if rec.nameID in (1, 4, 16):
        rec.string = FAMILY
    elif rec.nameID == 6:
        rec.string = FAMILY.replace(" ", "")
f.save(out)
g = TTFont(out)
print("glyphs", len(g.getGlyphOrder()), "axes", [a.axisTag for a in g["fvar"].axes])
