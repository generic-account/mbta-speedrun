#!/usr/bin/env python3
"""Check coverage integrity, station references, and every published photo asset."""
import json
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parent.parent
raw=(ROOT/'site/assets/data.js').read_text()
data=json.loads(raw.removeprefix('window.MBTA_DATA = ').removesuffix(';\n'))
stations={s['id']:s for s in data['stations']}
assert len(stations)==len(data['stations'])==125, 'Expected 125 unique subway/trolley stations'
photos={p['file']:p for p in data['photos']}
assert len(photos)==len(data['photos']), 'Duplicate public photo records'
for route in data['routes']:
    assert len(route['stops'])==len(set(route['stops'])), 'Repeated station in route'
    for sid in route['stops']:
        assert sid in stations and route['id'] in stations[sid]['routes']
for s in stations.values():
    assert all(isinstance(s[k],(int,float)) for k in ['x','y','radius'])
    assert 0 < s['radius'] < 20
    assert 0 <= s['x'] <= data['map']['width'] and 0 <= s['y'] <= data['map']['height']
    for file in s['photos']:
        assert file in photos and photos[file]['station']==s['id']
for photo in photos.values():
    assert photo['include'] and photo['status']!='review', 'Unconfirmed photo leaked into manifest'
    assert photo['station'] is None or photo['station'] in stations
    for field in ['src','thumb']:
        assert (ROOT/'site'/photo[field]).is_file(), f"Missing {photo[field]}"
    if photo['station']:
        assert photo['file'] in stations[photo['station']]['photos']
inventory=json.loads((ROOT/'review/photo-inventory.json').read_text())
assert len(inventory)==288 and len({p['file'] for p in inventory})==288
curation_path=ROOT/'review/photo-curation.json'
curation=json.loads(curation_path.read_text()) if curation_path.exists() else {}
for photo in inventory:
    keeper=curation.get(photo['file'],{}).get('duplicateOf',photo.get('duplicateOf'))
    if keeper:
        assert not (photo['file'] in photos and keeper in photos), 'Repeated composition published twice'
for station in stations.values():
    selected=[photos[file] for file in station['photos']]
    if any(p['status']=='confirmed' for p in selected):
        assert all(p['status']!='inferred' for p in selected), 'Redundant inferred station photo'
# The public page and local review share one full image and one thumbnail per original.
expected_images=set()
for photo in inventory:
    stem=Path(photo['file']).stem
    for suffix in ['.webp','-thumb.webp']:
        asset=ROOT/'site/assets/photos'/f'{stem}{suffix}'
        assert asset.is_file(), f'Missing shared photo asset {asset.name}'
        expected_images.add(asset.name)
assert {p.name for p in (ROOT/'site/assets/photos').glob('*.webp')} == expected_images
assert not (ROOT/'review/previews').exists(), 'Review must use shared photo assets'

class Links(HTMLParser):
    def handle_starttag(self, tag, attrs):
        for key,value in attrs:
            if key in ['src','href'] and value and not value.startswith(('http','#','data:')):
                assert (ROOT/'site'/value).is_file(), f'Missing HTML resource {value}'
Links().feed((ROOT/'site/index.html').read_text())
assert (ROOT/'site'/data['map']['image']).is_file()
assert data['map']['image'].endswith('.svg'), 'Map must remain vector artwork'
assert len({(s['x'],s['y']) for s in stations.values()}) == len(stations), 'Hotspots overlap'
coverage=sum(bool(s['photos']) for s in stations.values())
print(f'Validated: {len(stations)} unique stations, {coverage} with photos, {len(photos)} public photos and {len(expected_images)} shared image assets (288 full images + 288 thumbnails).')
