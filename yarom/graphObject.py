import logging
import six
from pprint import pprint,pformat

L = logging.getLogger(__name__)

__all__ = ["GraphObject", "GraphObjectQuerier", "ComponentTripler"]

class Variable(int):
    pass

class GraphObject(object):

    """ An object which can be included in the object graph.

    An abstract base class.
    """

    def __init__(self, **kwargs):
        super(GraphObject, self).__init__(**kwargs)
        self.properties = []
        self.owner_properties = []

    def identifier(self):
        """ Must return an object representing this object or else
        raise an Exception. """
        raise NotImplementedError()

    @property
    def defined(self):
        """ Returns true if an :meth:`identifier` would return an identifier """
        raise NotImplementedError()

    def variable(self):
        """ Must return a :class:`Variable` object that identifies
        this :class:`GraphObject` in queries.

        The variable can be randomly generated when the object is created and stored in
        the object.
        """
        raise NotImplementedError()

    @property
    def idl(self):
        if self.defined:
            return self.identifier()
        else:
            return self.variable()

    def __hash__(self):
        raise NotImplementedError()

    def __eq__(self, other):
        if id(self) == id(other):
            return True
        elif isinstance(other, GraphObject):
            return self.idl == other.idl

    def __lt__(self, other):
        if isinstance(other, GraphObject):
            return self.idl < other.idl
        else:
            return id(self) < id(other)


class GraphObjectQuerier(object):

    def __init__(self, q, graph):
        self.query_object = q
        self.graph = graph

    def do_query(self):
        qu = _QueryPreparer(self.query_object)
        h = self.hoc(qu())
        return self.qpr(h)

    def hoc(self, l):
        res = dict()
        L.debug("hoc: {}".format(l))
        for x in l:
            if len(x) > 0:
                tmp = res.get(x[0], [])
                tmp.append(x[1:])
                res[x[0]] = tmp

        for x in res:
            res[x] = self.hoc(res[x])

        return res

    def qpr(self, h, i=0):
        join_args = []
        for x in h:
            sub_answers = set()
            sub = h[x]
            idx = x.index(None)
            if idx == 2:
                other_idx = 0
            else:
                other_idx = 2

            if isinstance(x[other_idx], Variable):
                for z in self.qpr(sub, i + 1):
                    if idx == 2:
                        qx = (z, x[1], None)
                    else:
                        qx = (None, x[1], z)

                    for y in self.graph.triples(qx):
                        sub_answers.add(y[idx])
            else:
                for y in self.graph.triples(x):
                    sub_answers.add(y[idx])
            join_args.append(sub_answers)

        if len(join_args) > 0:
            res = join_args[0]
            for x in join_args[1:]:
                res = res & x
            return res
        else:
            return set()

    def __call__(self):
        res = self.do_query()
        return res


class ComponentTripler(object):

    def __init__(self, start):
        self.start = start
        self.seen = set()
        self.results = set()

    def g(self, current_node, i=0):

        L.debug("g({},{})".format(current_node, i))
        if id(current_node) in self.seen:
            return
        else:
            self.seen.add(id(current_node))

        if not current_node.defined:
            return

        for e in current_node.owner_properties:
            p = e.owner
            if p.defined:
                self.results.add((p.idl, e.link, current_node.idl))
                self.g(p, i + 1)

        L.debug("current_node.properties = {}".format(current_node.properties))
        for e in current_node.properties:
            L.debug("values = {}".format(e.values))
            for val in e.values:
                L.debug("val = {}".format(val))
                if val.defined:
                    self.results.add((current_node.idl, e.link, val.idl))
                    self.g(val, i + 1)

    def __call__(self):
        self.g(self.start)
        return self.results


class _QueryPathElement(tuple):

    def __new__(cls):
        return tuple.__new__(cls, ([], []))

    @property
    def subpaths(self):
        return self[0]

    @subpaths.setter
    def subpaths(self, toset):
        del self[0][:]
        self[0].extend(toset)

    @property
    def path(self):
        return self[1]


class _QueryPreparer(object):

    def __init__(self, start):
        self.seen = list()
        self.stack = list()
        self.paths = list()
        self.start = start
        self.variables = dict()
        self.vcount = 0
        # TODO: Refactor. The return values are not actually
        # used for anything

    def gather_paths_along_properties(
            self,
            current_node,
            property_list,
            is_inverse):
        L.debug("gpap: current_node %s", current_node)
        ret = []
        is_good = False
        for this_property in property_list:
            L.debug("this_property is %s", this_property)
            if is_inverse:
                others = [this_property.owner]
            else:
                others = this_property.values

            for other in others:
                other_id = other.idl
                if not other.defined:
                    other_id = self.var(other_id)

                if is_inverse:
                    self.stack.append((other_id, this_property.link, None))
                else:
                    self.stack.append((None, this_property.link, other_id))
                L.debug("gpap: preparing %s from %s", other, this_property)
                subpath = self.prepare(other)

                if len(self.stack) > 0:
                    self.stack.pop()

                if subpath[0]:
                    is_good = True
                    subpath[1].path.insert(
                        0, (current_node.idl, this_property, other.idl))
                    ret.insert(0, subpath[1])

        L.debug("gpap: exiting %s", "good" if is_good else "bad")
        return is_good, ret

    def var(self, v):
        if v in self.variables:
            return self.variables[v]
        else:
            var = Variable(self.vcount)
            self.variables[v] = var
            self.vcount += 1
            return var


    def prepare(self, current_node):
        L.debug("prepare: current_node %s", current_node)
        if current_node.defined:
            if len(self.stack) > 0:
                tmp = list(self.stack)
                self.paths.append(tmp)
            return True, _QueryPathElement()
        else:
            if current_node in self.seen:
                return False, _QueryPathElement()
            else:
                self.seen.append(current_node)
            owner_parts = self.gather_paths_along_properties(
                current_node,
                current_node.owner_properties,
                True)
            owned_parts = self.gather_paths_along_properties(
                current_node,
                current_node.properties,
                False)

            self.seen.pop()
            subpaths = owner_parts[1] + owner_parts[1]
            if len(subpaths) == 1:
                ret = subpaths[0]
            else:
                ret = _QueryPathElement()
                ret.subpaths = subpaths
            return (owner_parts[0] or owned_parts[0], ret)

    def __call__(self):
        self.prepare(self.start)
        L.debug("_QueryPreparer paths:"+ str(pformat(self.paths)))
        return self.paths


class DescendantTripler(object):

    def __init__(self, start):
        self.seen = set()
        self.start = start
        self.graph = set()

    def g(self, current_node):
        if current_node in self.seen:
            return
        else:
            self.seen.add(current_node)

        if not current_node.defined:
            return

        for e in current_node.properties:
            for val in e.values:
                if val.defined:
                    self.graph.add((current_node.idl, e.link, val.idl))
                    self.g(val)

    def __call__(self):
        self.g(self.start)
        return self.graph


class LegendFinder(object):

    """ Gets a list of the objects which can not be deleted freely from the transitive closure.

    "Heroes get remembered, but legends never die."
    """

    def __init__(self, start, graph=None):
        self.talked_about = dict()
        self.seen = set()
        self.start = start
        self.graph = graph

    def legends(self, o, depth=0):
        if o in self.seen:
            return
        self.seen.add(o)
        for prop in o.properties:
            for value in prop.values:
                if value != self.start:
                    count = self.count(value)
                    self.talked_about[value] = count - 1
                    self.legends(value, depth + 1)

    def count(self, o):
        if o in self.talked_about:
            return self.talked_about[o]
        else:
            i = 0
            if self.graph is not None:
                for _ in self.graph.triples((None, None, o.idl)):
                    i += 1
            else:
                for prop in o.owner_properties:
                    if prop.owner.defined:
                        i += 1
            return i

    def __call__(self):
        self.legends(self.start)
        return {x for x in self.talked_about if self.talked_about[x] > 0}


class HeroTripler(object):

    def __init__(self, start, graph=None, legends=None):
        self.seen = set()
        self.start = start
        self.heroslist = set()
        self.results = set()
        self.graph = graph

        if legends is None:
            self.legends = LegendFinder(self.start, graph)()
        else:
            self.legends = legends

    def isLegend(self, o):
        return o in self.legends

    def isHero(self, o):
        return o in self.heroslist

    def heros(self, o, depth=0):
        if o in self.seen:
            return
        self.seen.add(o)

        for prop in o.properties:
            for value in prop.values:
                if not self.isLegend(value):
                    self.heros(value, depth + 1)
                    self.hero(value)

    def hero(self, o):
        if not self.isHero(o):
            if self.graph is not None:
                for trip in self.graph.triples((o.idl, None, None)):
                    self.results.add(trip)
            else:
                for e in o.properties:
                    for val in e.values:
                        if val.defined:
                            self.results.add((o.idl, e.link, val.idl))
            self.heroslist.add(o)

    def __call__(self):
        self.heros(self.start)
        self.hero(self.start)
        return self.results


class ReferenceTripler(object):

    def __init__(self, start, graph=None):
        self.seen = set()
        self.start = start
        self.results = set()
        self.graph = graph

    def refs(self, o):
        if self.graph is not None:
            from itertools import chain
            for trip in chain(
                self.graph.triples(
                    (None, None, o.idl)),
                self.graph.triples(
                    (o.idl, None, None))):
                self.results.add(trip)
        else:
            for e in o.properties:
                for val in e.values:
                    if val.defined:
                        self.results.add((o.idl, e.link, val.idl))

            for e in o.owner_properties:
                if e.owner.defined:
                    self.results.add((e.owner.idl, e.link, o.idl))

    def __call__(self):
        self.refs(self.start)
        return self.results


class IdentifierMissingException(Exception):

    """ Indicates that an identifier should be available for the object in
        question, but there is none """

    def __init__(self, dataObject="[unspecified object]", *args, **kwargs):
        super().__init__(
            "An identifier should be provided for {}".format(
                str(dataObject)),
            *args,
            **kwargs)
