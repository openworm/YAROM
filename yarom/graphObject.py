import logging
from itertools import chain
from pprint import pformat
from .rangedObjects import InRange
import threading

L = logging.getLogger(__name__)

__all__ = [
    "GraphObject",
    "GraphObjectQuerier",
    "GraphObjectChecker",
    "ComponentTripler",
    "IdentifierMissingException"
    ]

# Directions for traversal across triples
UP = 'up'  # left, towards the subject
DOWN = 'down'  # right, towards the object
EMPTY_SET = frozenset([])


class Variable(int):
    pass


class _Range(InRange):
    pass


class GraphObject(object):

    """ An object which can be included in the object graph.

    An abstract base class.
    """

    def __init__(self, **kwargs):
        super(GraphObject, self).__init__(**kwargs)
        self.properties = []
        self.owner_properties = []

    @property
    def identifier(self):
        """ Must return an object representing this object or else
        raise an Exception. """
        raise NotImplementedError()

    @property
    def defined(self):
        """ Returns true if an :meth:`identifier` would return an identifier
        """
        raise NotImplementedError()

    def variable(self):
        """ Must return a :class:`Variable` object that identifies
        this :class:`GraphObject` in queries.

        The variable can be randomly generated when the object is created and
        stored in the object.
        """
        raise NotImplementedError()

    @property
    def idl(self):
        if self.defined:
            return self.identifier
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


class GraphObjectChecker(object):
    def __init__(self, query_object, graph, parallel=False, sort_first=False):
        self.query_object = query_object
        self.graph = graph

    def __call__(self):
        tripler = ComponentTripler(self.query_object)
        for x in sorted(tripler()):
            if x not in self.graph:
                return False
        return True


class GraphObjectValidator(object):
    def __init__(self, query_object, graph, parallel=False):
        self.query_object = query_object
        self.graph = graph

    def __call__(self):
        return True


class GraphObjectQuerier(object):

    """ Performs queries for objects in the given graph.

    The querier queries for objects at the center of a star graph. In SPARQL,
    the query has the form::

        SELECT ?x WHERE {
            ?x  <p1> ?o1 .
            ?o1 <p2> ?o2 .
             ...
            ?on <pn> <a> .

            ?x  <q1> ?n1 .
            ?n1 <q2> ?n2 .
             ...
            ?nn <qn> <b> .
        }

    It is allowed that ``<px> == <py>`` for ``x != y``.

    Queries such as::

        SELECT ?x WHERE {
            ?x  <p1> ?o1 .
             ...
            ?on <pn>  ?y .
        }

    or::

        SELECT ?x WHERE {
            ?x  <p1> ?o1 .
             ...
            ?on <pn>  ?x .
        }

    or::

        SELECT ?x WHERE {
            ?x  ?z ?o .
        }

    or::

        SELECT ?x WHERE {
            ?x  ?z <a> .
        }

    are not supported and will be ignored without error.

    """

    def __init__(self, q, graph, parallel=False):
        """ Initialize the querier.

        Call the GraphObjectQuerier object to perform the query.

        Parameters
        ----------
        q : :class:`GraphObject`
            The object which is queried on
        graph : :class:`object`
            The graph from which the objects are queried. Must implement a
            method :meth:`triples` that takes a triple pattern, ``t``, and
            returns a set of triples matching that pattern. The pattern for
            ``t`` is ``t[i] = None``, 0 <= i <= 2, indicates that the i'th
            position can take any value.

            The ``graph`` method can optionally implement the 'range query'
            'interface':
                the graph must have a property ``supports_range_queries``
                equal to ``True`` and ``triples`` must accept, in any position
                of the
        """

        self.query_object = q
        if hasattr(graph, 'triples'):
            self.graph = graph
        else:
            self.graph_iter = graph

        self.parallel = parallel
        self.results = dict()
        self.triples_cache = dict()

    def do_query(self):
        if self.query_object.defined:
            gv = GraphObjectChecker(self.query_object, self.graph)
            if gv():
                return set([self.query_object])
            else:
                return EMPTY_SET

        qp = _QueryPreparer(self.query_object)
        paths = qp()
        if len(paths) == 0:
            return EMPTY_SET
        h = self.merge_paths(paths)
        L.debug('do_query: merge_paths_result: {}'.format(pformat(h)))
        return self.query_path_resolver(h)

    def merge_paths(self, l):
        """ Combines a list of lists into a multi-level table with
        the elements of the lists as the keys. For given::

            [[a, b, c], [a, b, d], [a, e, d]]

        merge_paths returns::

            {a: {b: {c: {},
                     d: {}},
                 e: {d: {}}}}
        """
        res = dict()
        L.debug("merge_paths: {}".format(l))
        for x in l:
            if len(x) > 0:
                tmp = res.get(x[0], [])
                tmp.append(x[1:])
                res[x[0]] = tmp

        for x in res:
            res[x] = self.merge_paths(res[x])

        return res

    def query_path_resolver(self, path_table):
        join_args = []
        par = self.parallel and len(path_table) > 1
        if par:
            cv = threading.Condition()
            tcount = 0
        else:
            cv = None
        if par:
            L.debug("Executing queries in parallel")
        goal = None
        for hop in path_table:
            goal = hop[3]
            if hasattr(self, 'graph'):
                graph = self.graph
            else:
                graph = next(self.graph_iter)

            def f():
                self._qpr_helper(path_table[hop], hop, join_args, cv, graph)

            if par:
                t = threading.Thread(target=f)
                t.start()
                tcount += 1
            else:
                f()

        if par:
            with cv:
                while len(join_args) < tcount:
                    cv.wait()

        if len(join_args) > 0:
            L.debug("Joining {} args on {}".format(len(join_args), goal))
            res = set(join_args[0])
            for x in join_args[1:]:
                #res.intersection_update(x)
                lres = res
                res = set([])
                for z in x:
                    if z in lres:
                        res.add(z)
            L.debug("Joined {} args on {}".format(len(join_args), goal))
            return res
        else:
            return EMPTY_SET

    def _qpr_helper(self, sub, search_triple, join_args, cv, graph):
        seen = set()
        try:
            idx = search_triple.index(None)
            other_idx = 0 if (idx == 2) else 2

            if isinstance(search_triple[other_idx], Variable):
                sub_results = list(self.query_path_resolver(sub))

                if idx == 2:
                    qx = (sub_results, search_triple[1], None)
                else:
                    qx = (None, search_triple[1], sub_results)

                trips = self.triples_choices(qx)
            else:
                trips = self.triples(search_triple[:3])
            seen = set(y[idx] for y in trips)
            L.debug("Done with {} {}".format(search_triple, len(seen)))
        finally:
            if cv:
                with cv:
                    join_args.append(seen)
                    cv.notify()
            else:
                join_args.append(seen)

    def triples_choices(self, query_triple):
        return self.graph.triples_choices(query_triple)

    def triples(self, query_triple):
        if isinstance(query_triple[2], _Range):
            in_range = query_triple[2]
            if in_range.defined:
                if getattr(self.graph, 'supports_range_queries', False):
                    return self.graph.triples(query_triple)
                else:
                    qt = (query_triple[0], query_triple[1], None)
                    return set(x for x in self.graph.triples(qt) if in_range(x[2]))
            else:
                qt = (query_triple[0], query_triple[1], None)
                return self.graph.triples(qt)
        else:
            return self.graph.triples(query_triple)

    def __call__(self):
        res = self.do_query()
        L.debug('GOQ: results:{}'.format(str(pformat(self.results))))
        return res


class ComponentTripler(object):

    """ Gets a set of triples that are connected to the given object by
    objects which have an identifier.

    The ComponentTripler does not query against a backing graph, but instead
    uses the properties attached to the object.
    """

    def __init__(self, start, traverse_undefined=False, generator=False):
        self.start = start
        self.seen = set()
        self.generator = generator
        self.traverse_undefined = traverse_undefined

    def g(self, current_node, i=0):
        if not self.see_node(current_node):
            if self.traverse_undefined or current_node.defined:
                for x in chain(self.recurse_upwards(current_node, i),
                               self.recurse_downwards(current_node, i)):
                    yield x

    def recurse_upwards(self, current_node, depth):
        for prop in current_node.owner_properties:
            for x in self.recurse(prop.owner, prop, current_node, UP, depth):
                yield x

    def recurse_downwards(self, current_node, depth):
        for prop in current_node.properties:
            for val in prop.values:
                for x in self.recurse(current_node, prop, val, DOWN, depth):
                    yield x

    def recurse(self, lhs, via, rhs, direction, depth):
        (ths, nxt) = (rhs, lhs) if direction is UP else (lhs, rhs)
        if self.traverse_undefined or nxt.defined:
            yield (lhs.idl, via.link, rhs.idl)
            for x in self.g(nxt, depth + 1):
                yield x

    def see_node(self, node):
        node_id = id(node)
        if node_id in self.seen:
            return True
        else:
            self.seen.add(node_id)
            return False

    def __call__(self):
        x = self.g(self.start)
        if self.generator:
            return x
        else:
            return set(x)


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
            direction):
        L.debug("gpap: current_node %s", current_node)
        ret = []
        is_good = False
        for this_property in property_list:
            L.debug("this_property is %s", this_property)
            if direction is UP:
                others = [this_property.owner]
            else:
                others = this_property.values

            for other in others:
                other_id = other.idl

                if isinstance(other, InRange):
                    other_id = _Range(other.min_value, other.max_value)
                elif not other.defined:
                    other_id = self.var(other_id)

                if direction is UP:
                    self.stack.append((other_id, this_property.link, None,
                                      current_node))
                else:
                    self.stack.append((None, this_property.link, other_id,
                                      current_node))
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
        L.debug("prepare: current_node %s", repr(current_node))
        if current_node.defined or isinstance(current_node, InRange):
            if len(self.stack) > 0:
                self.paths.append(list(self.stack))
            return True, _QueryPathElement()
        else:
            if current_node in self.seen:
                return False, _QueryPathElement()
            else:
                self.seen.append(current_node)
            owner_parts = self.gather_paths_along_properties(
                current_node,
                current_node.owner_properties,
                UP)
            owned_parts = self.gather_paths_along_properties(
                current_node,
                current_node.properties,
                DOWN)

            self.seen.pop()
            subpaths = owner_parts[1] + owner_parts[1]
            if len(subpaths) == 1:
                ret = subpaths[0]
            else:
                ret = _QueryPathElement()
                ret.subpaths = subpaths
            return (owner_parts[0] or owned_parts[0], ret)

    def __call__(self):
        x = self.prepare(self.start)
        L.debug("self.prepare() result:" + str(x))
        L.debug("_QueryPreparer paths:" + str(pformat(self.paths)))
        return self.paths


class DescendantTripler(object):

    """ Gets triples that the object points to, optionally transitively. """

    def __init__(self, start, graph=None, transitive=True):
        """
        Parameters
        ----------
        start : GraphObject
            the node to start from
        graph : rdflib.graph.Graph, optional
            if given, the graph to draw descedants from. Otherwise the object
            graph is used
        """
        self.seen = set()
        self.seen_edges = set()
        self.start = start
        self.graph = graph
        self.results = list()
        self.transitve = transitive

    def g(self, current_node):
        if current_node in self.seen:
            return
        else:
            self.seen.add(current_node)

        if not current_node.defined:
            return

        if self.graph is not None:
            for triple in self.graph.triples((current_node.idl, None, None)):
                self.results.append(triple)
                if self.transitve:
                    self.g(_DTWrapper(triple[2]))
        else:
            for e in current_node.properties:
                if id(e) not in self.seen_edges:
                    self.seen_edges.add(id(e))
                    for val in e.values:
                        if val.defined:
                            self.results.append((current_node.idl, e.link, val.idl))
                            if self.transitve:
                                self.g(val)

    def __call__(self):
        self.g(self.start)
        return self.results


class _DTWrapper():
    """ Used by DescendantTripler to wrap identifiers in GraphObjects """
    defined = True
    __slots__ = ['idl']

    def __init__(self, ident):
        self.idl = ident

    def __hash__(self):
        return hash(self.idl)

    def __eq__(self, other):
        if type(other) == type(self):
            return (other is self) or (other.idl == self.idl)
        else:
            return False


class LegendFinder(object):

    """ Gets a list of the objects which can not be deleted freely from the
    transitive closure.

    Essentially, this is the 'mark' phase of the "mark-and-sweep" garbage
    collection algorithm.

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
        self.seen_edges = set()
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
                if (DOWN, id(e)) not in self.seen_edges:
                    self.seen_edges.add((DOWN, id(e)))
                    for val in e.values:
                        if val.defined:
                            self.results.add((o.idl, e.link, val.idl))

            for e in o.owner_properties:
                if (UP, id(e)) not in self.seen_edges:
                    self.seen_edges.add((UP, id(e)))
                    if e.owner.defined:
                        self.results.add((e.owner.idl, e.link, o.idl))

    def __call__(self):
        self.refs(self.start)
        return self.results


class IdentifierMissingException(Exception):

    """ Indicates that an identifier should be available for the object in
        question, but there is none """

    def __init__(self, dataObject="[unspecified object]", *args, **kwargs):
        super(IdentifierMissingException, self).__init__(
            "An identifier should be provided for {}".format(
                str(dataObject)),
            *args,
            **kwargs)
