"""`halcyon text`: the helpers, and real OCR of images and PDFs when Tesseract is installed."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HALCYON = Path(__file__).resolve().parent.parent / "dots/.config/hypr/hyprland/halcyon"
sys.path.insert(0, str(HALCYON))

import halcyon_text as ht  # noqa: E402

FONT = next((p for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans.ttf")
             if os.path.exists(p)), None)
HAS_OCR = shutil.which("tesseract") is not None and FONT is not None


def text_image(path: Path, lines: list[str]) -> None:
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(FONT, 40)
    img = Image.new("RGB", (1200, 80 + 70 * len(lines)), "white")
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        draw.text((40, 40 + 70 * i), line, fill="black", font=font)
    img.save(path)


def text_pdf(path: Path, line: str) -> None:
    """A one-page PDF with a real text layer, written by hand."""
    stream = f"BT /F1 24 Tf 72 720 Td ({line}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(bytes(out))


class HelperTests(unittest.TestCase):
    def test_languages(self):
        listed = 'List of available languages in "/usr/share/tessdata/" (3):\neng\ndeu\nosd\n'
        self.assertEqual(ht.languages(listed, None), "eng+deu")
        self.assertEqual(ht.languages(listed, "fra"), "fra")
        self.assertEqual(ht.languages("", None), "eng")

    def test_tidy(self):
        self.assertEqual(ht.tidy("a  \n\n\n\nb\f\n"), "a\n\nb")
        self.assertEqual(ht.tidy("one para-\ngraph that\nwraps\n\nnext", join=True), "one paragraph that wraps\n\nnext")

    def test_window_geometry(self):
        self.assertEqual(ht.window_geometry({"at": [10, 20], "size": [800, 600]}), "10,20 800x600")
        self.assertIsNone(ht.window_geometry({}))
        self.assertIsNone(ht.window_geometry({"at": [0, 0], "size": [0, 10]}))

    def test_preview(self):
        self.assertEqual(ht.preview("a\nb   c"), "a b c")
        self.assertTrue(ht.preview("x" * 300).endswith("…"))


@unittest.skipUnless(HAS_OCR, "tesseract or a font is not installed")
class OcrTests(unittest.TestCase):
    def run_tool(self, *args):
        env = {k: v for k, v in os.environ.items() if k not in ("WAYLAND_DISPLAY", "HYPRLAND_INSTANCE_SIGNATURE")}
        return subprocess.run([sys.executable, str(HALCYON / "halcyon-theme"), "text", *args],
                              capture_output=True, text=True, env=env, check=False)

    def test_image(self):
        with tempfile.TemporaryDirectory() as d:
            img = Path(d) / "shot.png"
            text_image(img, ["Halcyon reads this line", "and this second one"])
            result = self.run_tool(str(img), "--print", "--lang", "eng")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Halcyon reads this line", result.stdout)
            self.assertIn("second one", result.stdout)

    def test_join(self):
        with tempfile.TemporaryDirectory() as d:
            img = Path(d) / "shot.png"
            text_image(img, ["a sentence that", "keeps going here"])
            result = self.run_tool(str(img), "--print", "--join", "--lang", "eng")
            self.assertIn("a sentence that keeps going here", result.stdout)

    @unittest.skipUnless(shutil.which("pdftoppm"), "poppler is not installed")
    def test_scanned_pdf(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            img = Path(d) / "page.png"
            text_image(img, ["Scanned page text"])
            pdf = Path(d) / "scan.pdf"
            Image.open(img).save(pdf)   # an image only: no text layer
            result = self.run_tool(str(pdf), "--print", "--lang", "eng")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Scanned page text", result.stdout)

    @unittest.skipUnless(shutil.which("pdftotext"), "poppler is not installed")
    def test_pdf_with_text_layer(self):
        with tempfile.TemporaryDirectory() as d:
            pdf = Path(d) / "doc.pdf"
            text_pdf(pdf, "Typed text layer")
            result = self.run_tool(str(pdf), "--print")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Typed text layer", result.stdout)

    def test_errors(self):
        self.assertEqual(self.run_tool("/nonexistent.png", "--print").returncode, 1)
        with tempfile.NamedTemporaryFile(suffix=".txt") as f:
            result = self.run_tool(f.name, "--print")
            self.assertEqual(result.returncode, 1)
            self.assertIn("not an image", result.stderr)

    def test_blank_image_has_no_text(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            img = Path(d) / "blank.png"
            Image.new("RGB", (400, 200), "white").save(img)
            result = self.run_tool(str(img), "--print", "--lang", "eng")
            self.assertEqual(result.returncode, 1)
            self.assertIn("no text found", result.stderr)


if __name__ == "__main__":
    unittest.main()
