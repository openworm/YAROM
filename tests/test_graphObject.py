import unittest
from logging import getLogger
from random import random
from yarom.graphObject import (GraphObject,
                               ComponentTripler,
                               GraphObjectQuerier,
                               TQLayer,
                               ZeroOrMoreTQLayer)

from yarom.rangedObjects import InRange, LessThan
from yarom.rdfUtils import UP

import rdflib

L = getLogger(__name__)


class G(GraphObject):

    def __init__(self, k=None, **kwargs):
        super(G, self).__init__(**kwargs)
        if k is None:
            self._v = random()
            self._k = None
        else:
            self._k = k
            self._v = None

    @property
    def identifier(self):
        return self._k

    def variable(self):
        return self._v

    def __hash__(self):
        return hash(self._k)

    @property
    def defined(self):
        return self._k is not None

    def __repr__(self):
        return 'G(' + repr(self._k) + ')' if self._k else 'G()'


class Graph(object):
    def __init__(self):
        self.s = set([])

    def __contains__(self, o):
        return o in self.s

    def add(self, o):
        self.s.add(o)

    def triples_choices(self, triple, context=None):
        """
        A variant of triples that can take a list of terms instead of a single
        term in any slot.  Stores can implement this to optimize the response
        time from the default 'fallback' implementation, which will iterate
        over each term in the list and dispatch to triples
        """
        subject, predicate, object_ = triple
        if isinstance(object_, list):
            assert not isinstance(
                subject, list), "object_ / subject are both lists"
            assert not isinstance(
                predicate, list), "object_ / predicate are both lists"
            if object_:
                for obj in object_:
                    for (s1, p1, o1) in self.triples(
                            (subject, predicate, obj)):
                        yield (s1, p1, o1)
            else:
                for (s1, p1, o1) in self.triples(
                        (subject, predicate, None)):
                    yield (s1, p1, o1)

        elif isinstance(subject, list):
            assert not isinstance(
                predicate, list), "subject / predicate are both lists"
            if subject:
                for subj in subject:
                    for (s1, p1, o1) in self.triples(
                            (subj, predicate, object_)):
                        yield (s1, p1, o1)
            else:
                for (s1, p1, o1) in self.triples(
                        (None, predicate, object_)):
                    yield (s1, p1, o1)

        elif isinstance(predicate, list):
            assert not isinstance(
                subject, list), "predicate / subject are both lists"
            if predicate:
                for pred in predicate:
                    for (s1, p1, o1) in self.triples(
                            (subject, pred, object_)):
                        yield (s1, p1, o1)
            else:
                for (s1, p1, o1) in self.triples(
                        (subject, None, object_)):
                    yield (s1, p1, o1)

    def triples(self, q, context=None):
        s = q[0]
        p = q[1]
        o = q[2]
        if s is None:
            if p is None:
                if o is None:
                    return set(self.s)
                else:
                    return set((x for x in self.s if x[2] == o))
            else:
                if o is None:
                    return set((x for x in self.s if x[1] == p))
                else:
                    return set((x for x in self.s if x[1] == p and x[2] == o))
        else:
            if p is None:
                if o is None:
                    return set((x for x in self.s if x[0] == s))
                else:
                    return set((x for x in self.s if x[0] == s and x[2] == o))
            else:
                if o is None:
                    return set((x for x in self.s if x[0] == s and x[1] == p))
                else:
                    return set([q]) if q in self.s else set([])


class P(object):
    link = '->'

    def __init__(self, x, y, graph=None):
        self.values = [y]
        self.owner = x

        if isinstance(y, InRange):
            vcname = 'G' + y.__class__.__name__
            vclass = y.__class__
            y.__class__ = type(vcname, (vclass, G), {})
            G.__init__(y)

        y.owner_properties.append(self)
        x.properties.append(self)
        if graph is not None and x.defined and y.defined:
            graph.add((x.identifier, P.link, y.identifier))


class GraphObjectQuerierTest(unittest.TestCase):

    def test_query_defined_and_in_graph_returns_self(self):
        a = G(3)
        b = G(1)
        c = G(2)
        d = G(7)
        g = Graph()
        P(a, b, g)
        P(c, d, g)
        P(a, d, g)

        at = G(3)
        r = list(GraphObjectQuerier(at, g)())
        self.assertListEqual([at], r)

    def test_query_defined_validates(self):
        """
        Query that starts with a defined value
        """
        a = G(3)
        b = G(1)
        c = G(2)
        d = G(7)
        g = Graph()
        P(a, b, g)
        P(c, d, g)
        P(a, d, g)

        at = G(3)
        kt = G(5)
        P(at, kt)

        r = list(GraphObjectQuerier(at, g)())
        self.assertListEqual([], r)

    def test_query_layered(self):
        a = G(3)
        b = G(1)
        c = G(2)
        d = G(7)
        g = Graph()
        P(a, b, g)
        P(c, d, g)
        P(a, d, g)

        at = G()
        kt = G(7)
        P(at, kt)

        ge = TQLayer(g)

        r = set(GraphObjectQuerier(at, ge)())
        self.assertEqual(set([2, 3]), r)


class ZeroOrMoreTQLayerTest(unittest.TestCase):
    # test ZeroOrMore literal fails
    # test ZeroOrMore triples_choices

    def test_triples_1(self):
        from yarom.go_modifiers import ZeroOrMore
        a = G(3)
        b = G(1)
        c = G(2)
        d = G(7)
        g = Graph()
        P(a, b, g)
        P(b, c, g)
        P(c, d, g)

        at = G()
        kt = G(ZeroOrMore(1, P.link))
        P(at, kt)

        r = ZeroOrMoreTQLayer(g).triples((None, P.link, ZeroOrMore(1, P.link)))
        self.assertEqual(set([(3, P.link, 1),
                              (1, P.link, 2),
                              (2, P.link, 7)]),
                         set(r))

    def test_triples_2(self):
        from yarom.go_modifiers import ZeroOrMore
        a = G(3)
        b = G(1)
        c = G(2)
        d = G(7)
        g = Graph()
        P(a, b, g)
        P(b, c, g)
        P(c, d, g)

        at = G()
        kt = G(ZeroOrMore(2, P.link))
        P(at, kt)

        r = ZeroOrMoreTQLayer(g).triples((None, P.link, ZeroOrMore(2, P.link)))
        self.assertEqual(set([(1, P.link, 2),
                              (2, P.link, 7)]),
                         set(r))

    def test_triples_3(self):
        from yarom.go_modifiers import ZeroOrMore
        a = G(3)
        b = G(1)
        c = G(2)
        d = G(7)
        g = Graph()
        P(a, b, g)
        P(b, c, g)
        P(c, d, g)

        at = G()
        kt = G(ZeroOrMore(2, P.link, direction=UP))
        P(at, kt)

        r = ZeroOrMoreTQLayer(g).triples((None, P.link, ZeroOrMore(2, P.link, direction=UP)))
        self.assertEqual(set([(1, P.link, 2), (3, P.link, 1)]), set(r))

    def test_triples_choices_filtered(self):
        from yarom.go_modifiers import ZeroOrMore
        a = G(3)
        b0 = G(1)
        b1 = G(4)
        b10 = G(5)
        b11 = G(6)
        c0 = G(7)
        c1 = G(8)
        g = Graph()
        P(a, b0, g)
        P(c0, b0, g)
        P(c1, b0, g)
        P(a, b11, g)
        P(b1, b10, g)
        P(b10, b11, g)

        r = ZeroOrMoreTQLayer(g).triples_choices(([3, 7], P.link, ZeroOrMore(4, P.link)))
        self.assertEqual(set([(3, P.link, 6)]), set(r))

    def test_triples_choices_multiple_result(self):
        from yarom.go_modifiers import ZeroOrMore
        a = G(3)
        b0 = G(1)
        b1 = G(4)
        b10 = G(5)
        b11 = G(6)
        c0 = G(7)
        c1 = G(8)
        g = Graph()
        P(a, b0, g)
        P(c0, b0, g)
        P(c1, b0, g)
        P(a, b11, g)
        P(b1, b10, g)
        P(b10, b11, g)
        P(c0, b10, g)

        r = ZeroOrMoreTQLayer(g).triples_choices(([3, 7], P.link, ZeroOrMore(4, P.link)))
        self.assertEqual(set([(3, P.link, 6),
                              (7, P.link, 5)]), set(r))

    def test_triples_choices_empty(self):
        from yarom.go_modifiers import ZeroOrMore
        g = Graph()

        r = ZeroOrMoreTQLayer(g).triples_choices(([3, 7], P.link, ZeroOrMore(4, P.link)))
        self.assertEqual(set([]), set(r))

    def test_no_links_empty_result(self):
        from yarom.go_modifiers import ZeroOrMore
        a = G(3)
        b0 = G(1)
        b11 = G(6)
        c0 = G(7)
        c1 = G(8)
        g = Graph()
        P(a, b0, g)
        P(c0, b0, g)
        P(c1, b0, g)
        P(a, b11, g)

        r = ZeroOrMoreTQLayer(g).triples_choices(([3, 7], P.link, ZeroOrMore(4, P.link)))
        self.assertEqual(set(), set(r))

    def test_no_links_non_empty(self):
        from yarom.go_modifiers import ZeroOrMore
        a = G(3)
        b0 = G(1)
        b11 = G(6)
        c0 = G(7)
        c1 = G(8)
        g = Graph()
        P(a, b0, g)
        P(c0, b0, g)
        P(c1, b0, g)
        P(a, b11, g)

        r = ZeroOrMoreTQLayer(g).triples_choices(([3, 7], P.link, ZeroOrMore(6, P.link)))
        self.assertEqual(set([(3, P.link, 6)]), set(r))


class GraphObjectQuerierRangeQueryTest(unittest.TestCase):

    def setUp(self):
        x = G(12)
        y = G(23)
        z = G(34)

        b = G(2)
        c = G(3)
        d = G(4)

        g = Graph()

        P(x, b, g)
        P(y, c, g)
        P(z, d, g)

        self.g = g

    def test_query(self):
        """
        Query for value in a range
        """

        at = G()
        kt = InRange(2, 5)
        P(at, kt)
        r = set(GraphObjectQuerier(at, self.g)())
        self.assertEqual(set([23, 34]), r)

    def test_query_when_supported(self):
        met = [False]

        def triples(self, query_triple):
            if isinstance(query_triple[2], InRange):
                met[0] = True
                in_range = query_triple[2]
                qt = (query_triple[0], query_triple[1], None)
                return [x for x in self._triples(qt) if in_range(x[2])]
            else:
                return self._triples(query_triple)

        self.g._triples = self.g.triples
        self.g.triples = lambda qt, ctx: triples(self.g, qt)
        self.g.supports_range_queries = True

        at = G()
        kt = InRange(2, 5)
        P(at, kt)
        r = set(GraphObjectQuerier(at, self.g)())
        self.assertEqual(set([23, 34]), r)
        self.assertTrue(met[0])

    def test_query_no_lb(self):
        at = G()
        P(at, LessThan(5))
        r = set(GraphObjectQuerier(at, self.g)())
        self.assertEqual(set([12, 23, 34]), r)

    def test_query_unorderable_types(self):
        """
        If the ordering of types isn't defined, there isn't necessarily an
        error, especially if you're in Python2 land. Also, in rdflib, which
        defines the comparisons we'll probably actually be doing, the
        specification the code is based on doesn't even fully specify. We
        may be second-guessing the user, but for the Python2/Python3 thing
        alone, we are going to be nice to our users and throw an error in
        case they have incomprable types in their database
        """
        x = G(12)
        y = G(23)
        z = G(34)
        b = G(rdflib.Literal(2))
        c = G(0)
        d = G(rdflib.Literal(1))

        g = Graph()

        P(x, b, g)
        P(y, c, g)
        P(z, d, g)

        g = g

        at = G()
        P(at, LessThan(rdflib.Literal(5)))
        self.assertRaises(Exception,
                          lambda: GraphObjectQuerier(at, g)())

    def test_query_undefined_range(self):
        at = G()
        P(at, InRange())
        r = set(GraphObjectQuerier(at, self.g)())
        self.assertEqual(set([12, 23, 34]), r)

    def test_query_unorderable_types_with_undefined_range(self):
        """
        If there's no comparisons to make, then we shouldn't error out when
        types aren't orderable
        """
        x = G(12)
        y = G(23)
        z = G(34)
        b = G(rdflib.Literal(2))
        c = G(0)
        d = G(rdflib.Literal(1))

        g = Graph()

        P(x, b, g)
        P(y, c, g)
        P(z, d, g)

        g = g

        at = G()
        P(at, InRange())
        set(GraphObjectQuerier(at, g)())


class ComponentTriplerTest(unittest.TestCase):
    longMessage = True

    def test_split_nodes(self):
        """ Verify that nodes which have their definition split over
        multiple GraphObject instances are included in the graph
        """
        z = G(2)
        a = G(4)
        b = G(4)
        c = G(6)
        d = G(7)

        P(z, a)
        P(z, b)
        P(b, c)
        P(a, d)
        expected = set([(2, P.link, 4), (4, P.link, 6), (4, P.link, 7)])
        self.assert_component_matches(expected, z)

    def test_over_owner(self):
        """ Verify that we can get the triples pointing to a node """
        z = G(1)
        a = G(2)
        b = G(4)
        P(a, z)
        P(b, z)
        expected = set([(4, P.link, 1), (2, P.link, 1)])
        self.assert_component_matches(expected, z)

    def test_no_traverse_undef(self):
        """ Verify undefined graph objects are not traversed """
        z = G(1)
        a = G()
        b = G(4)
        P(z, a)
        P(a, b)
        expected = set([])
        self.assert_component_matches(expected, z)

    def assert_component_matches(self, expected, start_node):
        g = ComponentTripler(start_node, generator=False)()
        self.assertEqual(expected, g)


class TQLayerTest(unittest.TestCase):

    def test_getattr_success(self):
        class A(object):
            def __init__(self):
                self.a = 3

        cut = TQLayer()
        cut.next = A()
        self.assertEqual(cut.a, 3)

    def test_getattr_fail(self):
        class A(object):
            pass

        cut = TQLayer()
        cut.next = A()
        with self.assertRaises(AttributeError):
            cut.ax


if __name__ == '__main__':
    unittest.main()
