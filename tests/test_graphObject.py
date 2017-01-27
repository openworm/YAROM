import unittest
from logging import getLogger
from random import random
from yarom.graphObject import GraphObject, ComponentTripler

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

    def identifier(self):
        return self._k

    def variable(self):
        return self._v

    def __hash__(self):
        return hash(self._k)

    @property
    def defined(self):
        return self._k is not None


class P(object):
    link = '->'

    def __init__(self, x, y):
        self.values = [y]
        self.owner = x
        y.owner_properties.append(self)
        x.properties.append(self)


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
        print(a, b)
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
