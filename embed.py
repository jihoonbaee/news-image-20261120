#!/usr/bin/env python3
"""Embed the rendered PNG as one single-line base64 literal."""

import base64
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main():
    # This is the image read explicitly required by the embedding deliverable.
    png = (ROOT / "entry.png").read_bytes()
    encoded = base64.b64encode(png).decode("ascii")
    assert "\n" not in encoded and "\r" not in encoded
    source = (
        'const fs = require("fs");\n'
        'const path = require("path");\n\n'
        f'const pngBase64 = "{encoded}";\n\n'
        'const outputDir = process.env.MAKEFUN_OUTPUT_DIR || "./out";\n'
        'fs.mkdirSync(outputDir, { recursive: true });\n'
        'const outputPath = path.join(outputDir, "entry.png");\n'
        'const bytes = Buffer.from(pngBase64, "base64");\n'
        'fs.writeFileSync(outputPath, bytes);\n'
        'console.log(`Wrote ${outputPath} (${bytes.length} bytes)`);\n'
    )
    (ROOT / "main.ts").write_text(source, encoding="utf-8")
    print(f"Embedded entry.png: {len(png)} bytes -> {len(encoded)} base64 characters")
    print("Wrote main.ts: one single-line string literal; fs and path only")
    print(f"Embedded source sha256: {hashlib.sha256(png).hexdigest()}")


if __name__ == "__main__":
    main()
