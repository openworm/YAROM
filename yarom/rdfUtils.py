from __future__ import print_function

# Directions for traversal across triples
UP = 'up'
DOWN = 'down'


def print_graph(g, hide_namespaces=False):
    s = g.serialize(format='n3').decode("UTF-8")
    if hide_namespaces:
        lines = s.splitlines()
        s = "\n".join(l for l in lines if not l.startswith("@prefix"))
    print(s)


def serialize_rdflib_term(x, namespace_manager=None):
    return x.n3(namespace_manager)


def deserialize_rdflib_term(x):
    from rdflib.term import Literal
    if isinstance(x, Literal):
        x = x.toPython()
        if isinstance(x, Literal):
            x = str(x)
    return x


def triple_to_n3(trip, namespace_manager=None):
    from rdflib.term import Literal, URIRef
    p = ''
    ns = set([])
    for x in trip:
        s = serialize_rdflib_term(x, namespace_manager)
        if isinstance(x, URIRef) and s[0] != '<':
            ns.add(s.split(':', 1)[0])
        elif isinstance(x, Literal) and '^^' in s and s[-1] != '>':
            ns.add(s.split('^^', 1)[1].split(':', 1)[0])

        p += s + ' '
    return p


def triples_to_bgp(trips, namespace_manager=None, show_namespaces=False):
    # XXX: Collisions could result between the variable names of different
    # objects
    g = ""
    ns = set([])
    for y in trips:
        g += triple_to_n3(y) + ".\n"

    if (namespace_manager is not None) and show_namespaces:
        g = "".join('@prefix ' + str(x) + ': ' + y.n3() + ' .\n'
                    for x, y
                    in namespace_manager.namespaces()
                    if x in ns) + g

    return g


_none_singleton_set = frozenset([None])


def transitive_lookup(graph, start, predicate, context=None, direction=DOWN):
    res = set()
    border = set([start])
    while border:
        new_border = set()
        for b in border:
            if direction is DOWN:
                qx = (b, predicate, None)
                idx = 2
            else:
                qx = (None, predicate, b)
                idx = 0

            itr = graph.triples(qx, context=context)
            for t in itr:
                o = t[0][idx] if isinstance(t[0], tuple) else t[idx]
                if o not in res:
                    new_border.add(o)
        res |= border
        border = new_border
    res -= _none_singleton_set
    return res


transitive_subjects = transitive_lookup
