"""Validate the public static package without the private master archive."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
site = root / 'dist'
catalog = json.loads((site / 'data/site-catalog.json').read_text(encoding='utf-8-sig'))
assert catalog['defaultProgress'] == 0, 'New readers must start at zero'
for name in ['index.html', 'app.js', 'model.js', 'styles.css', 'data/site-catalog.js']:
    assert (site / name).is_file(), f'Missing dependency: {name}'
assert not (site / 'assets/originals').exists(), 'Master archive must stay outside the site'
for entry in catalog['entries']:
    assert len(entry['assetIds']) <= 1, f'Multiple variants: {entry["id"]}'
    assert all(aid in catalog['assets'] for aid in entry['assetIds']), 'Missing reference'
for asset in catalog['assets'].values():
    relative = Path(asset['path'])
    assert asset['path'].startswith('assets/images/') and '..' not in relative.parts
    image = site / relative
    assert image.is_file() and image.stat().st_size == asset['bytes'], f'Missing/truncated: {relative}'
    with image.open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == asset['sha256'], f'Checksum mismatch: {relative}'
size = sum(p.stat().st_size for p in site.rglob('*') if p.is_file())
assert size < 1_000_000_000, f'Package exceeds 1 GB: {size}'
print(f'Validated {len(catalog["assets"])} images; package {size:,} bytes; bookmark zero.')
