"""Curate browsing independently of owner confirmations and source evidence."""
from collections import defaultdict


def select_photos(photos, stations, curation):
    by_file = {p['file']: p for p in photos}
    unknown = set(curation) - set(by_file)
    if unknown:
        raise ValueError(f'Unknown curation files: {sorted(unknown)}')
    for p in photos:
        rule = curation.get(p['file'], {})
        if 'duplicateOf' in rule:
            p.update(duplicateOf=rule['duplicateOf'], duplicateReason=rule['reason'])
        if rule.get('include') is False:
            p.update(include=False, curationNote=rule['reason'])
        p['needsReview'] = p['status'] == 'review'

    # A location confirmation must not restore a repeated composition.
    # Do not suppress a retained alternate when its preferred image was omitted.
    for p in photos:
        keep = p.get('duplicateOf')
        if keep:
            if keep not in by_file or keep == p['file']:
                raise ValueError(f"Invalid duplicate reference for {p['file']}")
            if by_file[keep]['include'] and by_file[keep]['status'] != 'review':
                p.update(include=False, needsReview=False,
                         curationNote=f"Repeated composition; keep {keep}. {p['duplicateReason']}")

    strong = defaultdict(list)
    for p in photos:
        if p['station'] and p['include'] and p['status'] == 'confirmed':
            strong[p['station']].append(p['file'])
    for p in photos:
        if p['status'] == 'inferred' and p['include'] and strong[p['station']]:
            p.update(include=False, curationNote='Sequence-only photo omitted: this station '
                     + 'already has confirmed photos (' + ', '.join(strong[p['station']]) + ').')
        if p['status'] == 'review':
            candidates = [sid for sid in p.get('candidateStations', [p['station']]) if sid]
            if candidates and all(strong[sid] for sid in candidates):
                names = ', '.join(stations[sid]['name'] for sid in candidates)
                p.update(include=False, needsReview=False,
                         curationNote=f'Location left unresolved: all possible stops ({names}) '
                         + 'already have confirmed photos. Omitted rather than guessed.')

    # Show coverage and evidence beside unresolved frames without turning a
    # missing photo into an assertion that the travelers skipped a stop.
    for p in photos:
        if p['status'] != 'review':
            continue
        evidence = []
        for sid in p.get('candidateStations', [p['station']]):
            if sid is None:
                evidence.append({'name': 'Between stops', 'strength': 'context', 'files': []})
                continue
            available = [q for q in photos if q['station'] == sid and q['include']
                         and q['status'] != 'review']
            evidence.append({'name': stations[sid]['name'],
                             'strength': 'confirmed' if strong[sid] else 'inferred' if available else 'none',
                             'files': strong[sid] or [q['file'] for q in available]})
        p['coverageEvidence'] = evidence
        p['reviewPriority'] = 0 if any(e['strength'] == 'none' for e in evidence) else 1


def pending_photos(photos):
    return sorted((p for p in photos if p['needsReview']),
                  key=lambda p: (p['reviewPriority'], p['number']))
