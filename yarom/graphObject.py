import rdflib as R

class GraphObject(object):
    def identifier(self):
        raise NotImplementedError()

    def defined(self):
        raise NotImplementedError()

    @property
    def idl(self):
        if self.defined:
            return self.identifier
        else:
            return self.variable

    def owner_properties(self):
        raise NotImplementedError()

    def properties(self):
        raise NotImplementedError()

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
        qu = QU(self.query_object)
        h = self.hoc(qu())
        return self.qpr(self.graph, h)

    def hoc(self,l):
        res = dict()
        for x in l:
            if len(x) > 0:
                tmp = res.get(x[0], [])
                tmp.append(x[1:])
                res[x[0]] = tmp

        for x in res:
            res[x] = self.hoc(res[x])

        return res

    def qpr(self, g, h, i=0):
        join_args = []
        for x in h:
            sub_answers = set()
            sub = h[x]
            idx = x.index(None)
            if idx == 2:
                other_idx = 0
            else:
                other_idx = 2

            if isinstance(x[other_idx], R.Variable):
                for z in self.qpr(g, sub, i+1):
                    if idx == 2:
                        qx = (z, x[1], None)
                    else:
                        qx = (None, x[1], z)

                    for y in g.triples(qx):
                        sub_answers.add(y[idx])
            else:
                for y in g.triples(x):
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
        return self.do_query()

class SV(object):
    def __init__(self):
        self.seen = set()
        self.results = R.Graph()

    def g(self, current_node, i=0):
        if current_node in self.seen:
            return
        else:
            self.seen.add(current_node)

        if not current_node.defined:
            return

        for e in current_node.owner_properties:
            p = e.owner
            if p.defined:
                self.results.add((p.idl, e.link, current_node.idl))
                self.g(p,i+1)

        for e in current_node.properties:
            for val in e.values:
                if val.defined:
                    self.results.add((current_node.idl, e.link, val.idl))
                    self.g(val,i+1)

    def __call__(self, current_node):
        self.g(current_node)
        return self.results

class QN(tuple):
    def __new__(cls):
        return tuple.__new__(cls, ([],[]))

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

class QU(object):
    def __init__(self, start):
        self.seen = list()
        self.lean = list()
        self.paths = list()
        self.start = start

    def b(self, CUR, LIST, IS_INV):
        ret = []
        is_good = False

        for e in LIST:
            if IS_INV:
                p = [e.owner]
            else:
                p = e.values

            for x in p:
                if IS_INV:
                    self.lean.append((x.idl, e.link, None))
                else:
                    self.lean.append((None, e.link, x.idl))

                subpath = self.g(x)
                if len(self.lean) > 0:
                    self.lean.pop()

                if subpath[0]:
                    is_good = True
                    subpath[1].path.insert(0, (CUR.idl, e, x.idl))
                    ret.insert(0, subpath[1])
        return is_good, ret

    def k(self):
        pass

    def g(self, current_node):
        if current_node.defined:
            if len(self.lean) > 0:
                tmp = list(self.lean)
                self.paths.append(tmp)
            return True, QN()
        else:
            if current_node in self.seen:
                return False, QN()
            else:
                self.seen.append(current_node)

            retp = self.b(current_node, current_node.owner_properties, True)
            reto = self.b(current_node, current_node.properties, False)

            self.seen.pop()
            subpaths = retp[1]+reto[1]
            if (len(subpaths) == 1):
                ret = subpaths[0]
            else:
                ret = QN()
                ret.subpaths = subpaths
            return (retp[0] or reto[0], ret)

    def __call__(self):
        self.g(self.start)
        return self.paths

class DescendantTripler(object):
    def __init__(self, start):
        self.seen = set()
        self.start = start
        self.graph = R.Graph()

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

class Legends(object):
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
                    self.legends(value, depth+1)

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
        self.results = R.Graph()
        self.graph = graph

        if legends is None:
            self.legends = Legends(self.start, graph)()
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
                    self.heros(value, depth+1)
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
