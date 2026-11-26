#!/usr/bin/env python3
"""Cut Material Symbols Rounded (the variable font from Google Fonts) to the icons Summit uses: subset.py VARIABLE.ttf OUT.ttf.
Keeps the icons' name ligatures and all four axes; see dots/.config/quickshell/Summit/assets/README.md."""
import sys
from fontTools.ttLib import TTFont
from fontTools import subset
src, out = sys.argv[1], sys.argv[2]
# The family, with the cut's version: every cut with new icons gets the next one. An older cut stays installed
# system-wide until its package updates (and in ~/.local/share/fonts), and Qt and fontconfig take an installed font of
# the same family over the one Summit loads itself, so with one name for every cut the new icons showed as their names.
# Summit asks for this name (FontLoader); halcyon/summit/summit.rasi and rofi-menu name it too.
FAMILY = "Summit Symbols v3"
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
