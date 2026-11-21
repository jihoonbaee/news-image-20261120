# The World in One Day — 20 November 2026

[![make.fun · news-image-20261120](https://make.fun/badge/news-image-20261120.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)
[![rank](https://make.fun/badge/news-image-20261120/jihoonbaee/news-image-20261120/rank.svg)](https://make.fun/bounty/news-image-20261120/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)
[![reward](https://make.fun/badge/news-image-20261120/jihoonbaee/news-image-20261120/reward.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)

A newspaper front page summarises six stories from Friday, 20 November 2026: Russian missiles landing in Poland, Trump's first press conference since the midterms, and the S&P 500 entering correction. It also covers Cyclone Akvan's landfall in India, the 6.7 earthquake in central Peru, and GTA VI's announced $3.79 billion in day-one retail sales, using the supplied brief and original flat pictograms.

## Run it

Requires Node.js 22 or later; no packages are needed.

```bash
mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts
```

The program creates `entry.png` in `MAKEFUN_OUTPUT_DIR`, or `./out` when the variable is unset. The image is embedded in `main.ts`, so running the entry requires no fonts, Pillow, source image, or network access.

To rebuild the artwork, install Pillow and the DejaVu fonts, run `python3 render.py`, then run `python3 embed.py`. The renderer prints pixel-width fold checks and preserves an exclusive area for every pictogram. See `BUILD-REPORT.md` for dimensions, hashes, text edits, and verification details.
