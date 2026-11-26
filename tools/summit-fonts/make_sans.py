#!/usr/bin/env python3
"""Summit Sans, Summit's text font: make_sans.py GoogleSansFlex[ROND,opsz,slnt,wdth,wght].ttf OUT.ttf

Google Sans Flex (github.com/google/fonts, ofl/googlesansflex; SIL Open Font License 1.1, no Reserved Font Name),
modified: the rounded ends (ROND) set all the way, as Summit's icons are; the slant and width fixed at upright and
normal, which drops those axes; weight and optical size stay variable. It is renamed, because "Google Sans" is a
trademark of Google LLC that a modified version may not carry (TRADEMARKS.md next to the font). Needs fontTools.
"""

import sys

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

FAMILY = "Summit Sans"
NOTE = ("Summit Sans: Google Sans Flex modified for Summit (Halcyon): rounded ends (ROND 100), upright, normal width; "
        "renamed. SIL Open Font License 1.1. Not affiliated with or endorsed by Google.")


def main(src: str, out: str) -> None:
    font = instancer.instantiateVariableFont(TTFont(src), {"ROND": 100, "slnt": 0, "wdth": 100})
    name = font["name"]
    ps_family = FAMILY.replace(" ", "")
    for record in list(name.names):
        text = record.toUnicode()
        if record.nameID in (1, 16):
            record.string = FAMILY
        elif record.nameID == 3:
            record.string = text.replace("GoogleSansFlex", ps_family).replace(";GOOG;", ";HALC;")
        elif record.nameID == 4:
            record.string = f"{FAMILY} {text.split(' ')[-1]}" if " " in text else FAMILY
        elif record.nameID == 6:
            record.string = f"{ps_family}-{text.split('-')[-1]}" if "-" in text else ps_family
        elif record.nameID == 25:
            record.string = ps_family
        elif "Google Sans" in text and record.nameID not in (0, 7, 13, 14):
            record.string = text.replace("Google Sans Flex", FAMILY).replace("GoogleSansFlex", ps_family)
    name.setName(NOTE, 10, 3, 1, 0x409)
    font["OS/2"].achVendID = "HALC"   # not Google's: this is a modified version
    # The named instances keep their style names; their PostScript names follow the new family.
    if "fvar" in font:
        for inst in font["fvar"].instances:
            if inst.postscriptNameID != 0xFFFF:
                old = name.getDebugName(inst.postscriptNameID) or ""
                name.setName(old.replace("GoogleSansFlex", ps_family), inst.postscriptNameID, 3, 1, 0x409)
    font.save(out)
    check = TTFont(out)
    print(check["name"].getDebugName(1), [a.axisTag for a in check["fvar"].axes] if "fvar" in check else [])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
