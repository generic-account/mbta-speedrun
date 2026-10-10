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
for station in stations.values():
    selected=[photos[file] for file in station['photos']]
    if any(p['status']=='confirmed' for p in selected):
        assert all(p['status']!='inferred' for p in selected), 'Redundant inferred station photo'
# Every deployed image must be referenced by the production manifest.
expected_images={Path(photo[field]).name for photo in photos.values() for field in ['src','thumb']}
assert {p.name for p in (ROOT/'site/assets/photos').glob('*.webp')} == expected_images, 'Unused or missing production images'
assert not (ROOT/'review').exists(), 'Review tools must stay outside the production tree'

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
print(f'Validated: {len(stations)} unique stations, {coverage} with photos, {len(photos)} public photos and {len(expected_images)} production image assets.')
