from itertools import cycle
import unittest
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock

from yarom.rdfUtils import transitive_subjects


class TransitiveLookupTest(unittest.TestCase):

    def test_lookup_1(self):
        g = Mock()
        g.triples.return_value = [(('start', 'predicate', 'start'), ())]
        self.assertEqual(set(['start']), transitive_subjects(g, 'start', 'predicate'))

    def test_lookup_2(self):
        g = Mock()
        g.triples.side_effect = cycle([[(('start', 'predicate', 'start'), ())],
                                       [(('start', 'predicate', 'end'), ())]])
        self.assertEqual(set(['end', 'start']), transitive_subjects(g, 'start', 'predicate'))

    def test_lookup_3(self):
        g = Mock()
        g.triples.return_value = []
        self.assertEqual(set(['start']), transitive_subjects(g, 'start', 'predicate'))

    def test_lookup_4(self):
        g = Mock()
        g.triples.return_value = []
        self.assertEqual(set([]), transitive_subjects(g, None, 'predicate'))
