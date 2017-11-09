import unittest
from logging import getLogger
from random import random
from yarom.graphObject import (GraphObject,
                               ComponentTripler,
                               Variable,
                               GraphObjectQuerier,
                               _QueryPreparer)
from yarom.rangedObjects import InRange, LessThan
from pprint import pprint

import rdflib

L = getLogger(__name__)


class G(GraphObject):

    def __init__(self, k=None, v=None, **kwargs):
        super(G, self).__init__(**kwargs)
        if k is None:
            self._v = random() if v is None else v
            self._k = None
        else:
            self._k = k
            self._v = None

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
        if self._k is not None:
            return 'G(' + repr(self._k) + ')'
        else:
            return 'G(v=' + repr(self._v) + ')'


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

    def triples(self, q):
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
            graph.add((x.identifier(),
                       type(self).link,
                       y.identifier()))


class Q(P):
    link = '>>'


class Z(P):
    link = '~>'


class QueryPreparerTest(unittest.TestCase):

    def test_single1(self):
        a = G(v='a')
        b = G(v='b')
        d = G(v='d')
        c = G(1)
        P(b, a)
        P(c, b)
        P(d, a)
        P(c, d)
        expected = [(G(v='a'), [[(Variable(0), '->', None, G(v='a')),
                                 (1, '->', None, G(v='b'))],
                                [(Variable(2), '->', None, G(v='a')),
                                 (1, '->', None, G(v='d'))]])]
        self.assertListEqual(expected, _QueryPreparer(a)())

    def test_single2(self):
        a = G(v='a')
        b = G(v='b')
        d = G(v='d')
        e = G(v='e')
        f = G(2)
        c = G(1)
        P(a, e)
        P(e, f)
        P(b, a)
        P(c, b)
        P(d, a)
        P(c, d)
        qpout = _QueryPreparer(a)()
        expected = [(G(v='a'), [[(Variable(0), '->', None, G(v='a')),
                                 (1, '->', None, G(v='b'))],
                                [(Variable(2), '->', None, G(v='a')),
                                 (1, '->', None, G(v='d'))],
                                [(None, '->', Variable(3), G(v='a')),
                                 (None, '->', 2, G(v='e'))]])]
        self.assertListEqual(expected, qpout)

    def test_single3(self):
        a = G(v='a')
        b = G(v='b')
        d = G(v='d')
        c = G(v='c')
        f = G(v='f')
        goal = G(1)
        P(c, goal)
        P(f, goal)

        P(a, b)
        P(a, c)
        P(b, c)
        P(c, d)
        P(d, f)
        qp = _QueryPreparer(a)
        qpout = qp()

        self.assertListEqual([(G(v='a'),
                               [[(None, '->', Variable(0), G(v='a')),
                                 (None, '->', Variable(2), G(v='b')),
                                 (None, '->', 1, G(v='c'))],
                                [(None, '->', Variable(0), G(v='a')),
                                 (None, '->', Variable(2), G(v='b')),
                                 (None, '->', Variable(3), G(v='c')),
                                 (None, '->', Variable(4), G(v='d')),
                                 (None, '->', 1, G(v='f'))],
                                [(None, '->', Variable(2), G(v='a')),
                                 (None, '->', 1, G(v='c'))],
                                [(None, '->', Variable(2), G(v='a')),
                                 (None, '->', Variable(3), G(v='c')),
                                 (None, '->', Variable(4), G(v='d')),
                                 (None, '->', 1, G(v='f'))]])], qpout)

    def test_multiple1(self):
        a = G(v='a')
        b = G(v='b')
        c = G(1)
        P(a, c)
        P(b, c)

        self.assertListEqual([(G(v='a'), [[(None, '->', 1, G(v='a'))]]),
                              (G(v='b'), [[(None, '->', 1, G(v='b'))]])],
                             _QueryPreparer((a, b))())

    def test_multiple2(self):
        a = G(v='a')
        b = G(v='b')
        d = G(v='d')
        c = G(1)
        P(a, d)
        P(b, d)
        P(d, c)

        self.assertListEqual([(G(v='a'), [[(None, '->', Variable(0), G(v='a')),
                                           (None, '->', 1, G(v='d'))]]),
                              (G(v='b'), [[(None, '->', Variable(0), G(v='b')),
                                           (None, '->', 1, G(v='d'))]])],
                             _QueryPreparer((a, b))())

    def test_multiple3(self):
        a = G(v='a')
        b = G(v='b')
        d = G(v='d')
        c = G(1)
        P(a, b)
        P(b, d)
        P(d, c)

        self.assertListEqual([(G(v='a'), [[(None, '->', Variable(0), G(v='a')),
                                          (None, '->', Variable(2), G(v='b')),
                                          (None, '->', 1, G(v='d'))]]),
                              (G(v='b'), [[(None, '->', Variable(2), G(v='b')),
                                          (None, '->', 1, G(v='d'))]])],
                             _QueryPreparer((a, b))())

    def test_multiple4(self):
        a = G(v='a')
        b = G(v='b')
        d = G(v='d')
        c = G(1)
        P(a, b)
        P(b, d)
        P(d, c)

        self.assertListEqual([(G(v='a'), [[(None, '->', Variable(0), G(v='a')),
                                           (None, '->', Variable(2), G(v='b')),
                                           (None, '->', 1, G(v='d'))]]),
                              (G(v='b'), [[(None, '->', Variable(2), G(v='b')),
                                           (None, '->', 1, G(v='d'))]]),
                              (G(v='d'), [[(None, '->', 1, G(v='d'))]])],
                             _QueryPreparer((a, b, d))())

    def test_multiple5(self):
        a = G(v='a')
        b = G(v='b')
        d = G(v='d')
        c = G(1)
        e = G(2)
        P(a, b)
        P(b, d)
        P(d, c)
        P(d, e)
        qp = _QueryPreparer((a, b, d))
        self.assertListEqual([(G(v='a'), [[(None, '->', Variable(0), G(v='a')),
                                           (None, '->', Variable(2), G(v='b')),
                                           (None, '->', 1, G(v='d'))],
                                          [(None, '->', Variable(0), G(v='a')),
                                           (None, '->', Variable(2), G(v='b')),
                                           (None, '->', 2, G(v='d'))]]),
                              (G(v='b'), [[(None, '->', Variable(2), G(v='b')),
                                           (None, '->', 1, G(v='d'))],
                                          [(None, '->', Variable(2), G(v='b')),
                                           (None, '->', 2, G(v='d'))]]),
                              (G(v='d'), [[(None, '->', 1, G(v='d'))],
                                          [(None, '->', 2, G(v='d'))]])],
                             qp())

    def test_shared_path1(self):
        goal = G(1)
        a = G(v='a')
        b = G(v='b')
        c = G(v='c')
        P(a, b)
        P(a, c)
        P(c, b)
        P(b, goal)
        qp = _QueryPreparer(a)
        self.assertListEqual(
            [(G(v='a'),
              [[(None, '->', Variable(0),
                 G(v='a')),
                (None, '->', 1, G(v='b'))],
               [(None, '->', Variable(2),
                 G(v='a')),
                (None, '->', Variable(0),
                 G(v='c')),
                (None, '->', 1, G(v='b'))]])],
            qp())

    def test_shared_path2(self):
        goal = G(1)
        a = G(v='a')
        b = G(v='b')
        c = G(v='c')
        d = G(v='d')
        P(a, b)
        P(a, c)
        P(c, b)
        P(b, d)
        P(d, goal)
        qp = _QueryPreparer(a)
        print(qp())
        self.assertListEqual(
            [(G(v='a'),
              [[(None, '->', Variable(0),
                 G(v='a')),
                (None, '->', Variable(3),
                 G(v='b')),
                (None, '->', 1, G(v='d'))],
               [(None, '->', Variable(2),
                 G(v='a')),
                (None, '->', Variable(0),
                 G(v='c')),
                (None, '->', Variable(3),
                 G(v='b')),
                (None, '->', 1, G(v='d'))]])],
            qp())


class GraphObjectQuerierTest(unittest.TestCase):

    def test_query_single1(self):
        a = G(1)
        b = G(2)
        c = G(3)
        d = G(4)
        e = G(5)

        g = Graph()
        P(a, b, g)
        P(b, c, g)
        P(a, d, g)
        P(d, e, g)

        at = G(v='at')
        bt = G(v='bt')
        ct = G(3)
        dt = G(v='dt')
        et = G(5)
        P(at, bt)
        P(bt, ct)
        P(at, dt)
        P(dt, et)
        r = set(GraphObjectQuerier(at, g, parallel=False)())
        self.assertSetEqual(set([1]), r)

    def test_query_single2(self):
        a = G(1)
        b = G(2)
        c = G(3)
        d = G(4)
        e = G(5)

        g = Graph()
        P(a, b, g)
        P(b, c, g)
        P(a, d, g)
        P(d, e, g)

        at = G(v='at')
        bt = G(v='bt')
        ct = G(3)
        dt = G(v='dt')
        et = G(5)
        P(at, bt)
        P(bt, ct)
        P(at, dt)
        P(dt, et)
        r = set(GraphObjectQuerier(at, g, parallel=False)())
        self.assertSetEqual(set([1]), r)

    def test_query_single3(self):
        a = G(1)
        b = G(2)
        c = G(3)
        d = G(4)
        e = G(5)

        g = Graph()
        P(a, b, g)
        P(b, c, g)
        P(a, d, g)
        P(d, e, g)

        a = G(1)
        b = G(7)
        c = G(3)
        d = G(8)
        e = G(5)

        P(a, b, g)
        P(b, c, g)
        P(a, d, g)
        P(d, e, g)

        at = G(v='at')
        bt = G(v='bt')
        ct = G(3)
        dt = G(v='dt')
        et = G(5)
        P(at, bt)
        P(bt, ct)
        P(at, dt)
        P(dt, et)
        r = set(GraphObjectQuerier(at, g, parallel=False)())
        self.assertSetEqual(set([1]), r)

    def test_query_single4(self):
        a = G(1)
        b = G(2)
        c = G(3)

        d = G(4)
        e = G(5)

        f = G(6)
        g = Graph()
        P(a, b, g)
        P(b, c, g)

        P(d, e, g)
        P(e, c, g)

        P(d, f, g)
        P(f, e, g)

        at = G(v='a')
        bt = G(v='b')
        ct = G(v='c')
        goal = G(3)

        P(at, bt)
        P(bt, goal)
        P(at, ct)
        P(ct, bt)

        r = set(GraphObjectQuerier(at, g, parallel=False)())
        self.assertSetEqual(set([4]), r)

    def test_query_single5(self):
        a = G(1)
        b = G(2)
        c = G(3)

        d = G(4)
        e = G(5)

        f = G(6)
        g = Graph()
        P(a, b, g)
        P(b, c, g)

        P(d, e, g)
        P(e, c, g)

        P(d, f, g)
        P(f, e, g)

        at = G(v='a')
        bt = G(v='b')
        ct = G(v='c')
        goal = G(1)

        P(at, bt)
        P(bt, goal)
        P(at, ct)
        P(ct, bt)

        r = set(GraphObjectQuerier(at, g, parallel=False)())
        self.assertSetEqual(set([]), r)

    def test_query_multiple1(self):
        a = G(3)
        b = G(1)
        c = G(2)
        d = G(7)

        g = Graph()
        P(a, b, g)
        P(c, d, g)
        P(a, d, g)
        P(b, c, g)

        at = G(v='at')
        bt = G(v='bt')
        t = G(7)
        s = G(2)
        P(at, bt)
        P(bt, s)
        P(at, t)
        r = set(GraphObjectQuerier((at, bt), g, parallel=False)())
        self.assertSetEqual(set([(3, 1)]), r)

    def test_query_multiple2(self):
        a = G(3)
        b = G(1)
        c = G(2)
        d = G(7)

        g = Graph()
        P(a, b, g)
        P(b, c, g)

        P(a, d, g)
        P(d, c, g)

        at = G(v='at')
        bt = G(v='bt')
        s = G(2)

        P(at, bt)
        P(bt, s)

        r = set(GraphObjectQuerier((at, bt), g, parallel=False)())
        self.assertSetEqual(set([(3, 1), (3, 7)]), r)

    def test_query_multiple5(self):
        g = Graph()
        conn = G(1)
        conn_type = G(2)
        syntype = G(3)
        number = G(4)
        P(conn, conn_type, g)
        Q(conn, syntype, g)
        Z(conn, number, g)

        conn = G(v='conn')
        syntype = G(v='syntype')
        number = G(v='number')
        P(conn, conn_type)
        Q(conn, syntype)
        Z(conn, number)

        r = set(GraphObjectQuerier((syntype, number), g, parallel=False)())
        self.assertSetEqual(set([(3, 4)]), r)

    def test_query_multiple3(self):
        e = G(4)
        a = G(3)
        b = G(1)
        c = G(2)
        d = G(7)

        g = Graph()
        P(e, b, g)
        P(b, c, g)

        Q(a, d, g)
        Q(d, c, g)

        at = G(v='at')
        bt = G(v='bt')
        s = G(2)

        P(at, bt)
        P(bt, s)

        r = set(GraphObjectQuerier((at, bt), g, parallel=False)())
        self.assertSetEqual(set([(4, 1)]), r)

    def test_query_multiple4(self):
        a = G(3)
        b = G(1)
        c = G(2)
        d = G(7)

        g = Graph()
        P(a, b, g)
        P(b, c, g)

        Q(a, d, g)
        P(d, c, g)

        at = G(v='at')
        bt = G(v='bt')
        s = G(2)

        P(at, bt)
        P(bt, s)

        r = set(GraphObjectQuerier((at, bt), g, parallel=False)())
        self.assertSetEqual(set([(3, 1), (3, 7)]), r)

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
        r = list(GraphObjectQuerier(at, g, parallel=False)())
        self.assertListEqual([3], r)

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

        r = list(GraphObjectQuerier(at, g, parallel=False)())
        self.assertListEqual([], r)


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
        r = set(GraphObjectQuerier(at, self.g, parallel=False)())
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
        self.g.triples = lambda qt: triples(self.g, qt)
        self.g.supports_range_queries = True

        at = G()
        kt = InRange(2, 5)
        P(at, kt)
        r = set(GraphObjectQuerier(at, self.g, parallel=False)())
        self.assertEqual(set([23, 34]), r)
        self.assertTrue(met[0])

    def test_query_no_lb(self):
        at = G()
        P(at, LessThan(5))
        r = set(GraphObjectQuerier(at, self.g, parallel=False)())
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
        self.assertRaises(Exception, lambda: GraphObjectQuerier(at, g, parallel=False)())

    def test_query_undefined_range(self):
        at = G()
        P(at, InRange())
        r = set(GraphObjectQuerier(at, self.g, parallel=False)())
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
        set(GraphObjectQuerier(at, g, parallel=False)())


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


if __name__ == '__main__':
    unittest.main()
