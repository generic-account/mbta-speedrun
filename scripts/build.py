#!/usr/bin/env python3
"""Assemble public data and a local photo review page; no external dependencies."""
import json
import html
from pathlib import Path
from photo_selection import select_photos, pending_photos
ROOT = Path(__file__).resolve().parent.parent

def build():
    network = json.loads((ROOT / 'review/network.json').read_text())
    map_data = json.loads((ROOT / 'review/map-hotspots.json').read_text())
    network['map'] = {k: v for k, v in map_data.items() if k != 'stations'}
    for station in network['stations']:
        station.pop('latitude', None)
        station.pop('longitude', None)
        station.update(map_data['stations'][station['id']])
    photos = json.loads((ROOT / 'review/photo-inventory.json').read_text())
    stations = {s['id']: s for s in network['stations']}
    overrides_path = ROOT / 'review/photo-overrides.json'
    overrides = json.loads(overrides_path.read_text()) if overrides_path.exists() else {}
    unknown = set(overrides) - {p['file'] for p in photos}
    if unknown:
        raise ValueError(f'Unknown confirmation files: {sorted(unknown)}')
    for p in photos:
        if p['file'] in overrides:
            override = overrides[p['file']]
            sid = override['station']
            if sid is not None and sid not in stations:
                raise ValueError(f"Unknown station {sid} for {p['file']}")
            p['sourceNote'] = p['note']
            p['sourceStation'] = p['station']
            p['sourceSuggestedName'] = p['suggestedName']
            p.update(station=sid, status='confirmed' if sid else 'context',
                     include=override.get('include', True), confirmedByOwner=True,
                     suggestedName=stations[sid]['name'] if sid else None,
                     note=('Owner confirmed ' + stations[sid]['name'] + '. ' if sid else 'Owner selected no station. ')
                     + p['sourceNote'])
        p['src'] = 'assets/photos/' + Path(p['file']).stem + '.webp'
        p['thumb'] = 'assets/photos/' + Path(p['file']).stem + '-thumb.webp'
    curation_path = ROOT / 'review/photo-curation.json'
    curation = json.loads(curation_path.read_text()) if curation_path.exists() else {}
    select_photos(photos, stations, curation)
    pending = pending_photos(photos)
    for sid, station in stations.items():
        eligible = [p for p in photos if p['station'] == sid and p['include'] and p['status'] != 'review']
        eligible.sort(key=lambda p: (not p['primary'], p['status'] != 'confirmed', p['number']))
        station['photos'] = [p['file'] for p in eligible]
    public_fields = ['number', 'file', 'station', 'status', 'note', 'include', 'src', 'thumb']
    public = {**network, 'photos': [{key: p[key] for key in public_fields} for p in photos if p['include'] and p['status'] != 'review']}
    (ROOT / 'site/assets/data.js').write_text('window.MBTA_DATA = ' + json.dumps(public, separators=(',', ':')) + ';\n')
    # A human-readable audit: no uncertain station assignments become public.
    lines = ['# Photo review', '', 'All 288 source images were visually reviewed in filename order. Numbering is an audit sequence, not a merged timeline across cameras.', '',
             'Confirmed = readable sign or directly matching scene. Inferred = strong station-sequence evidence. Review = withheld from the public gallery until you confirm. Context = train interiors, portraits, scenery, and other images without a station assignment.', '',
             '## Needs confirmation', '', '| File | Suggested stop | Evidence / ambiguity |', '| --- | --- | --- |']
    for p in pending:
        lines.append(f"| {p['file']} | {p['suggestedName']} | {p['note']} {p.get('routeEvidence', '')} |")
    lines += ['', '## No assigned public photo', '', 'This describes photo coverage, not proof that a station was skipped.', '']
    lines += ['- ' + s['name'] for s in stations.values() if not s['photos']]
    repeated = [p for p in photos if 'duplicateOf' in p]
    lines += ['', '## Deduplication', '', 'No byte-identical files were found. One marker is used per station, including transfer stations. Repeated compositions below are omitted from public browsing; every original remains in your archive.', '']
    lines += [f"- {p['file']} → keep {p['duplicateOf']} ({p['duplicateReason']})" for p in repeated]
    lines += ['', '## Photos omitted because coverage is already established', '',
              'Owner confirmations remain intact. Browsing choices are applied afterward, so confirming a location does not reintroduce a duplicate. Inferred photos remain only where stronger station evidence is unavailable.', '']
    lines += [f"- {p['file']}: {p['curationNote']}" for p in photos if 'curationNote' in p and 'duplicateOf' not in p]
    (ROOT / 'review/PHOTO-REVIEW.md').write_text('\n'.join(lines) + '\n')
    unassigned = ['# Unassigned and uncertain photos', '', 'Uncertain station shots remain withheld. Between-stops photos are included in the gallery and do not need a station label.', '', '## Uncertain station shots', '', '| Photo | Possible stop | Evidence |', '| --- | --- | --- |']
    for p in pending:
        unassigned.append(f"| [{p['file']}](../site/{p['src']}) | {p['suggestedName']} | {p['note']} {p.get('routeEvidence', '')} |")
    unassigned += ['', '## Between-stops gallery', '', '| Photo | Description |', '| --- | --- |']
    for p in photos:
        if p['station'] is None and p['include']:
            unassigned.append(f"| [{p['file']}](../site/{p['src']}) | {p['note']} |")
    (ROOT / 'review/UNASSIGNED-PHOTOS.md').write_text('\n'.join(unassigned) + '\n')

    review_data = {'photos': photos, 'stations': list(stations.values()), 'overrides': overrides}
    serialized = json.dumps(review_data).replace('<', '\\u003c')
    template = (ROOT / 'scripts/review-template.html').read_text()
    (ROOT / 'review/index.html').write_text(template.replace('/* REVIEW_DATA */', 'const DATA = ' + serialized + ';'))
    print(f"Built {len(stations)} stations, {len(public['photos'])} public photos; {len(pending)} still need confirmation.")

if __name__ == '__main__':
    build()
