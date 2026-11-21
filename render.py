#!/usr/bin/env python3
"""Render the supplied newspaper brief; never open an existing image."""

import argparse
import io
import json
import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
PAPER = "#f7f3ea"
INK = "#1a1a1a"
RED = "#b91c1c"
GREY = "#666460"
WHITE = "#ffffff"
PADDING = 16
ICON_GAP = 12


def font(size, bold=False, serif=False):
    name = "DejaVuSerif" if serif else "DejaVuSans"
    return ImageFont.truetype(str(FONT_DIR / (name + ("-Bold" if bold else "") + ".ttf")), size)


FONTS = {
    "masthead": font(60, True, True),
    "date": font(30, True),
    "edition": font(19),
    "kicker": font(15, True),
    "lead_head": font(40, True),
    "grid_head": font(26, True),
    "band_head": font(28, True),
    "lead_sub": font(21),
    "grid_sub": font(18),
    "band_sub": font(18),
    "also": font(16),
    "footnote": font(14),
}


def fold(text, face, width):
    """One pixel-width wrapper, returning (lines, count), balancing short tails."""
    lines = []
    current = ""
    previous_end = 0
    for match in re.finditer(r"\S+", text):
        word = match.group()
        if face.getlength(word) > width:
            raise ValueError(f"Unbreakable word exceeds {width}px: {word}")
        separator = text[previous_end:match.start()] if current else ""
        candidate = current + separator + word
        if current and face.getlength(candidate) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
        previous_end = match.end()
    if current:
        lines.append(current)
    # Avoid a lone final word in the lead or footer without changing words,
    # font sizes, reserved widths, or the greedy wrapper's line count.
    if len(lines) == 2 and face.getlength(lines[1]) < 0.45 * face.getlength(lines[0]):
        options = []
        for match in list(re.finditer(r"\S+", text))[1:]:
            left, right = text[:match.start()].rstrip(), text[match.start():]
            a, b = face.getlength(left), face.getlength(right)
            if max(a, b) <= width:
                options.append((abs(a - b), left, right))
        if options:
            _, left, right = min(options)
            lines = [left, right]
    return lines, len(lines)


PANELS = [
    {
        "number": 1, "kind": "lead", "box": (36, 160, 988, 370), "icon_width": 160,
        "kicker": "POLAND  |  RUSSIA",
        "headline": "RUSSIAN MISSILES LAND IN POLAND",
        "sub": 'Suspected Russian missiles and a drone come down in the south-east; Tusk: "an intentional provocation"; Rutte: "grave violation."',
        "sub_fallback": 'Suspected Russian missiles and a drone come down in the south-east; Tusk: "an intentional provocation."',
    },
    {
        "number": 2, "kind": "grid", "box": (36, 382, 506, 566), "icon_width": 94,
        "kicker": "UNITED STATES  |  WHITE HOUSE",
        "headline": "FIRST PRESSER SINCE MIDTERMS",
        "sub": 'Healthcare deal eyed; "tremendous tax" on AI data centres abroad.',
    },
    {
        "number": 3, "kind": "grid", "box": (518, 382, 988, 566), "icon_width": 94,
        "kicker": "MARKETS  |  WALL STREET",
        "headline": "S&P 500 SINKS INTO CORRECTION",
        "sub": "S&P 500 falls 3.7% on Friday; Anthropic slides on day two.",
    },
    {
        "number": 4, "kind": "grid", "box": (36, 578, 506, 762), "icon_width": 94,
        "kicker": "INDIA  |  WEATHER",
        "headline": "AKVAN HITS INDIA, NO DEATHS REPORTED",
        "sub": "Landfall near Gopalpur; 372,000 evacuated, no deaths reported.",
    },
    {
        "number": 5, "kind": "grid", "box": (518, 578, 988, 762), "icon_width": 94,
        "kicker": "PERU  |  EARTHQUAKE",
        "headline": "6.7 QUAKE SHAKES CENTRAL PERU",
        "sub": "Felt in Lima; no casualties or major damage reported.",
    },
    {
        "number": 6, "kind": "band", "box": (36, 774, 988, 910), "icon_width": 130,
        "kicker": "CULTURE  |  GAMES",
        "headline": "GTA VI: $3.79BN IN ONE DAY",
        "sub": "Take-Two announced on Friday that day-one retail sales set the record for any entertainment launch; 32.5m copies sold before release.",
    },
]

ALSO = "ALSO TODAY:  UK and EU seal food, carbon and youth deals  •  Hayabusa2 drops asteroid landing  •  Trump pardons Pete Rose"
FOOTNOTE = "Full-day edition — all stories verified from reporting on 20 November 2026."


def select_text(panel, field, face, width, limit):
    text = panel[field]
    lines, count = fold(text, face, width)
    attempts = [{"text": text, "width": width, "lines": count}]
    if count > limit:
        raise ValueError(f"Panel {panel['number']} {field}: primary text folds to {count} lines at {width}px; limit is {limit}: {text}")
    return text, lines, attempts


def prepare():
    checks = []
    layouts = []
    for source in PANELS:
        p = dict(source)
        x0, y0, x1, y1 = p["box"]
        kind = p["kind"]
        p["gap"] = 10 if kind == "grid" else ICON_GAP
        width = x1 - x0 - 2 * PADDING - p["gap"] - p["icon_width"]
        p["text_width"] = width
        p["icon_box"] = (x1 - PADDING - p["icon_width"], y0 + PADDING, x1 - PADDING, y1 - PADDING)
        p["runs"] = []
        y = y0 + PADDING
        for field in ("kicker", "headline", "sub"):
            key = "kicker" if field == "kicker" else kind + ("_head" if field == "headline" else "_sub")
            face = FONTS[key]
            limit = 1 if field == "kicker" or (kind == "band" and field == "headline") else 2
            text, lines, attempts = select_text(p, field, face, width, limit)
            # The renderer calls the very same fold function as the checks.
            rendered_lines, rendered_count = fold(text, face, width)
            assert rendered_lines == lines
            step = 18 if field == "kicker" else (46 if key == "lead_head" else 34 if key == "band_head" else 31 if field == "headline" else 25 if kind == "lead" else 23)
            if field == "headline":
                y = y0 + (43 if kind != "band" else 39)
            if field == "sub":
                y += 7 if kind != "band" else 4
            run = {"field": field, "text": text, "lines": rendered_lines, "font_key": key, "x": x0 + PADDING, "y": y, "step": step}
            p["runs"].append(run)
            max_ink_right = 0
            max_ink_bottom = 0
            for index, line in enumerate(rendered_lines):
                bbox = face.getbbox(line, anchor="lt")
                ink_right = x0 + PADDING + bbox[2]
                ink_bottom = y + index * step + bbox[3]
                assert x0 + PADDING + bbox[0] >= x0 + PADDING - 1
                assert ink_right <= p["icon_box"][0] - p["gap"] + 1
                assert ink_bottom <= y1 - PADDING, (p["number"], field, ink_bottom, y1 - PADDING)
                max_ink_right = max(max_ink_right, ink_right)
                max_ink_bottom = max(max_ink_bottom, ink_bottom)
            checks.append({
                "panel": p["number"], "kind": kind, "field": field,
                "text": text, "width": width, "lines": rendered_count,
                "limit": limit, "wrapped": rendered_lines, "font_px": face.size,
                "passes": rendered_count <= limit,
                "changed": text != source[field], "attempts": attempts,
                "max_ink_right": max_ink_right, "max_ink_bottom": max_ink_bottom,
            })
            y += len(rendered_lines) * step
        layouts.append(p)
    also_lines, also_count = fold(ALSO, FONTS["also"], 952)
    assert also_count <= 2
    checks.append({"panel": "footer", "field": "ALSO", "text": ALSO, "width": 952, "lines": also_count, "limit": 2, "wrapped": also_lines, "passes": True})
    return layouts, checks, also_lines


def star(draw, cx, cy, radius, colour, scale_x=1):
    points = []
    for i in range(20):
        angle = -math.pi / 2 + i * math.pi / 10
        r = radius if i % 2 == 0 else radius * 0.49
        points.append((cx + math.cos(angle) * r * scale_x, cy + math.sin(angle) * r))
    draw.polygon(points, fill=colour)


def pictogram(draw, number, box):
    """All artwork is drawn from simple shapes inside the reserved rectangle."""
    x0, y0, x1, y1 = box
    width, height = x1 - x0, y1 - y0
    # Retain the original pictograms' vertical scale, compressing only x.
    original_width = 200 if number == 1 else 130
    size = min(original_width, height)
    xsize = min(width, size)
    ox = x0 + (width - size) / 2 if number == 6 else x1 - xsize
    oy = y0 + (height - size) / 2

    def p(x, y):
        return (ox + xsize * x / 100, oy + size * y / 100)

    def poly(points, fill):
        draw.polygon([p(x, y) for x, y in points], fill=fill)

    def line(points, fill, stroke=3):
        draw.line([p(x, y) for x, y in points], fill=fill, width=stroke, joint="curve")

    def rect(bounds, fill):
        draw.rectangle([p(*bounds[:2]), p(*bounds[2:])], fill=fill)

    if number == 1:
        star(draw, *p(69, 70), size * 0.29, "#d48649", xsize / size)
        star(draw, *p(69, 70), size * 0.18, "#b94e39", xsize / size)
        poly([(14, 16), (27, 14), (66, 53), (54, 65)], "#77858b")
        poly([(54, 65), (66, 53), (72, 72)], "#a43e32")
        poly([(23, 31), (18, 47), (40, 46)], "#435560")
        poly([(33, 21), (49, 16), (49, 38)], "#435560")
        line([(10, 8), (19, 17)], "#b5b1a8", 4)
        line([(7, 20), (15, 28)], "#b5b1a8", 3)
        line([(27, 5), (33, 11)], "#b5b1a8", 3)
    elif number == 2:
        rect((19, 47, 83, 55), "#283f50")
        poly([(26, 55), (76, 55), (70, 88), (32, 88)], "#435d70")
        rect((25, 88, 78, 94), "#283f50")
        line([(53, 46), (53, 30), (65, 19)], "#68747c", 4)
        draw.ellipse([p(59, 12), p(73, 24)], fill="#283f50")
        rect((42, 62, 62, 65), "#a9b5bd")
        rect((42, 70, 62, 73), "#a9b5bd")
    elif number == 3:
        line([(9, 13), (9, 89), (95, 89)], "#a7a4a0", 2)
        rect((20, 30, 34, 87), "#b7bfc4")
        rect((43, 45, 57, 87), "#9aa5ac")
        rect((66, 61, 80, 87), "#7c8d98")
        line([(20, 13), (48, 30), (62, 27), (88, 56)], RED, 5)
        # The tip is lower on the page than either wing: unambiguously down.
        poly([(75, 55), (91, 66), (90, 45)], RED)
    elif number == 4:
        blue = "#567e96"
        for i, radius in enumerate((42, 32, 22)):
            draw.arc([p(50 - radius, 50 - radius), p(50 + radius, 50 + radius)], 22 + i * 39, 321 + i * 39, fill=blue, width=6)
        draw.ellipse([p(44, 44), p(56, 56)], fill="#b1c6d1")
        line([(14, 82), (36, 82)], "#b1c6d1", 3)
        line([(64, 17), (87, 17)], "#b1c6d1", 3)
    elif number == 5:
        for gy in (22, 39, 56):
            line([(5, gy), (96, gy)], "#e0dcd5", 1)
        line([(5, 40), (23, 40), (31, 25), (40, 60), (50, 12), (59, 53), (68, 35), (77, 40), (96, 40)], "#766052", 3)
        poly([(5, 75), (38, 71), (48, 80), (60, 71), (96, 75), (96, 93), (5, 93)], "#b7a28e")
        line([(49, 73), (43, 81), (55, 85), (48, 94)], "#68594f", 3)
        line([(44, 81), (34, 84)], "#68594f", 2)
    elif number == 6:
        line([(9, 12), (9, 89), (96, 89)], "#b9c4b9", 2)
        rect((19, 65, 34, 87), "#a8b99e")
        rect((43, 46, 58, 87), "#809d79")
        rect((67, 26, 82, 87), "#537e62")
        line([(18, 49), (43, 30), (59, 34), (85, 9)], "#3f7455", 4)
        poly([(74, 9), (90, 5), (86, 22)], "#3f7455")


def centered(draw, text, y, face, fill):
    draw.text(((1024 - face.getlength(text)) / 2, y), text, font=face, fill=fill, anchor="lt")


def render(output, check_output=None):
    layouts, checks, also_lines = prepare()
    image = Image.new("RGB", (1024, 1024), PAPER)
    draw = ImageDraw.Draw(image)
    draw.line((36, 18, 988, 18), fill=INK, width=1)
    centered(draw, "THE WORLD IN ONE DAY", 28, FONTS["masthead"], INK)
    draw.line((36, 84, 988, 84), fill=INK, width=1)
    centered(draw, "FRIDAY • 20 NOVEMBER 2026", 96, FONTS["date"], RED)
    centered(draw, "Six stories that defined the day — full-day edition", 132, FONTS["edition"], GREY)
    for panel in layouts:
        draw.rectangle(panel["box"], fill=WHITE, outline=INK, width=1)
        pictogram(draw, panel["number"], panel["icon_box"])
        for run in panel["runs"]:
            for index, text in enumerate(run["lines"]):
                draw.text((run["x"], run["y"] + index * run["step"]), text, font=FONTS[run["font_key"]], fill=RED if run["field"] == "kicker" else INK, anchor="lt")
    for index, text in enumerate(also_lines):
        draw.text((36, 924 + index * 21), text, font=FONTS["also"], fill=INK, anchor="lt")
    draw.line((36, 975, 988, 975), fill="#c9c3b9", width=1)
    centered(draw, FOOTNOTE, 989, FONTS["footnote"], GREY)
    assert image.size == (1024, 1024)
    # Verify the Pillow encoder's output in memory; never reopen a PNG file.
    encoded = io.BytesIO()
    image.save(encoded, format="PNG", optimize=True, compress_level=9)
    png = encoded.getvalue()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert int.from_bytes(png[16:20], "big") == 1024
    assert int.from_bytes(png[20:24], "big") == 1024
    assert len(png) <= 1048576
    Path(output).write_bytes(png)
    for check in checks:
        print(f"FOLD panel={check['panel']} field={check['field']} width={check['width']} lines={check['lines']}/{check['limit']} text={json.dumps(check['text'], ensure_ascii=False)}")
    summary = {
        "image": {"format": "PNG", "width": image.width, "height": image.height, "mode": image.mode, "bytes": len(png)},
        "checks": checks,
        "reservations": [{"panel": p["number"], "box": p["box"], "padding": PADDING, "icon_width": p["icon_width"], "gap": p["gap"], "text_width": p["text_width"], "icon_box": p["icon_box"]} for p in layouts],
        "no_overlap": True,
    }
    if check_output:
        Path(check_output).write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(f"PNG {output}: {image.width}x{image.height}, {len(png)} bytes; all fold and reserved-area checks PASS")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", default=str(ROOT / "entry.png"))
    parser.add_argument("--checks", help="Write machine-readable fit and layout results")
    args = parser.parse_args()
    try:
        render(args.output, args.checks)
    except (AssertionError, ValueError, OSError) as exc:
        (ROOT / "BUILD-REPORT.md").write_text(f"# Build report\n\nRendering stopped: {type(exc).__name__}: {exc}\n")
        raise
