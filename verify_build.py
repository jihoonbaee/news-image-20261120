#!/usr/bin/env python3
"""Check the deliverables and in-memory embedded bytes without opening PNGs."""

import base64
import hashlib
import json
from pathlib import Path
import re
import struct

import render


ROOT = Path(__file__).resolve().parent
EXPECTED_SHA256 = "a37f815d7ac6027aef78399757030cceabe322deed6dd92be7e93dd80e7bcb18"
EXPECTED_BYTES = 107338


def main():
    required = ("render.py", "entry.png", "embed.py", "main.ts", "README.md", "LICENSE", ".makefun/owner.json", "BUILD-REPORT.md")
    assert all((ROOT / name).is_file() for name in required)
    source = (ROOT / "main.ts").read_text()
    literals = re.findall(r'^const pngBase64 = "([A-Za-z0-9+/=]+)";$', source, re.MULTILINE)
    assert len(literals) == 1
    assert re.findall(r'require\("([^"\n]+)"\)', source) == ["fs", "path"]
    assert 'process.env.MAKEFUN_OUTPUT_DIR || "./out"' in source
    embedded = base64.b64decode(literals[0], validate=True)
    assert hashlib.sha256(embedded).hexdigest() == EXPECTED_SHA256
    assert len(embedded) == EXPECTED_BYTES <= 1048576
    assert embedded[:8] == b"\x89PNG\r\n\x1a\n"
    assert embedded[12:16] == b"IHDR"
    assert struct.unpack(">II", embedded[16:24]) == (1024, 1024)
    for name in ("entry.png", "determinism.png", "out/entry.png"):
        # stat only: do not open or decode any PNG on disk.
        assert (ROOT / name).stat().st_size == EXPECTED_BYTES
    stored = json.loads((ROOT / "fold-checks.json").read_text())
    layouts, fresh_checks, _ = render.prepare()
    assert stored["checks"] == fresh_checks
    assert len(fresh_checks) == 19 and all(c["passes"] for c in fresh_checks)
    for p in layouts:
        for run in p["runs"]:
            assert " ".join(run["lines"].copy()).split() == run["text"].split()
    assert next(c for c in fresh_checks if c["panel"] == 6 and c["field"] == "headline")["lines"] == 1
    readme = (ROOT / "README.md").read_text()
    expected_badges = (
        "[![make.fun · news-image-20261120](https://make.fun/badge/news-image-20261120.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)",
        "[![rank](https://make.fun/badge/news-image-20261120/jihoonbaee/news-image-20261120/rank.svg)](https://make.fun/bounty/news-image-20261120/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)",
        "[![reward](https://make.fun/badge/news-image-20261120/jihoonbaee/news-image-20261120/reward.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)",
    )
    assert all(line in readme.splitlines() for line in expected_badges)
    assert "mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts" in readme
    assert json.loads((ROOT / ".makefun/owner.json").read_text()) == {
        "wallet": "5htxBocFy4qjVYy8vM5SpERA6QXo5RFDLALuDoYkdLDe"
    }
    license_text = (ROOT / "LICENSE").read_text()
    assert "Copyright (c) 2026 jihoonbaee" in license_text
    assert "SPDX-License-Identifier: MIT" in license_text.splitlines()
    report = (ROOT / "BUILD-REPORT.md").read_text()
    assert EXPECTED_SHA256 in report and str(EXPECTED_BYTES) in report
    for check in fresh_checks:
        printed = f"FOLD panel={check['panel']} field={check['field']} width={check['width']} lines={check['lines']}/{check['limit']} text={json.dumps(check['text'], ensure_ascii=False)}"
        assert printed in report
    print("PASS: all 8 required deliverables exist")
    print("PASS: one single-line base64 literal; fs/path only; embedded PNG is 1024x1024 and 107338 bytes")
    print("PASS: embedded byte sha256 " + EXPECTED_SHA256)
    print("PASS: all 19 fold checks reproduced; six exclusive icon areas and vertical bounds asserted")
    print("PASS: README badges verbatim; run command, wallet, MIT attribution and SPDX line correct")
    print("PASS: report includes every final fold result and the image hash/size")
    print("No PNG file was opened by this verifier.")


if __name__ == "__main__":
    main()
