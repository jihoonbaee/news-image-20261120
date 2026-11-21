from base64 import b64encode
from pathlib import Path


def embed_front_page():
    png_bytes = Path('entry.png').read_bytes()
    encoded_png = b64encode(png_bytes).decode('ascii')

    entrypoint = Path('main.ts')
    source = entrypoint.read_text(encoding='utf-8')
    marker = '__EMBEDDED_PNG_BASE64__'
    if source.count(marker) != 1:
        raise SystemExit('Expected exactly one PNG placeholder in main.ts.')

    entrypoint.write_text(source.replace(marker, encoded_png), encoding='utf-8')
    print(f'Embedded {len(png_bytes)} PNG bytes as {len(encoded_png)} base64 characters.')


if __name__ == '__main__':
    embed_front_page()
