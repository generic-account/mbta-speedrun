"""Regression checks for confirmations, duplicate portraits, and uncertain stops."""
import unittest
from photo_selection import select_photos


def photo(file, station, status='confirmed', **extra):
    return dict(file=file, station=station, status=status, include=True,
                number=1, **extra)


class SelectionTests(unittest.TestCase):
    stations = {'a': {'name': 'A'}, 'b': {'name': 'B'}}

    def test_confirming_both_portraits_does_not_restore_duplicate(self):
        photos = [photo('portrait', 'a'), photo('repeat', 'a', confirmedByOwner=True,
                  duplicateOf='portrait', duplicateReason='Same pose')]
        select_photos(photos, self.stations, {})
        self.assertTrue(photos[0]['include'])
        self.assertFalse(photos[1]['include'])
        self.assertEqual(photos[1]['status'], 'confirmed')

    def test_unknown_candidate_is_not_filled_in_from_a_photo_gap(self):
        photos = [photo('signed', 'a'), photo('mystery', 'a', 'review',
                  candidateStations=['a', 'b'])]
        select_photos(photos, self.stations, {})
        self.assertTrue(photos[1]['needsReview'])
        self.assertEqual(photos[1]['station'], 'a')
        self.assertEqual(photos[1]['coverageEvidence'][1]['strength'], 'none')

    def test_covered_candidates_are_omitted_without_inventing_a_label(self):
        photos = [photo('a-sign', 'a'), photo('b-sign', 'b'),
                  photo('mystery', 'a', 'review', candidateStations=['a', 'b'])]
        select_photos(photos, self.stations, {})
        self.assertFalse(photos[2]['needsReview'])
        self.assertFalse(photos[2]['include'])
        self.assertEqual(photos[2]['status'], 'review')

    def test_inferred_fallback_survives_only_without_confirmed_photo(self):
        photos = [photo('a-sign', 'a'), photo('a-guess', 'a', 'inferred'),
                  photo('b-sequence', 'b', 'inferred')]
        select_photos(photos, self.stations, {})
        self.assertFalse(photos[1]['include'])
        self.assertTrue(photos[2]['include'])


if __name__ == '__main__':
    unittest.main()
