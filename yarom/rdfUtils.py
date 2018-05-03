from rdflib.term import Literal, URIRef


def print_graph(g, hide_namespaces=False):
    s = g.serialize(format='n3').decode("UTF-8")
    if hide_namespaces:
        lines = s.splitlines()
        s = "\n".join(l for l in lines if not l.startswith("@prefix"))
    print(s)


def serialize_rdflib_term(x, namespace_manager=None):
    return x.n3(namespace_manager)


def deserialize_rdflib_term(x):
    if isinstance(x, Literal):
        x = x.toPython()
        if isinstance(x, Literal):
            x = str(x)
    return x


def triples_to_bgp(trips, namespace_manager=None, show_namespaces=False):
    # XXX: Collisions could result between the variable names of different
    # objects
    g = ""
    ns = set([])
    for y in trips:
        p = ''
        for x in y:
            s = serialize_rdflib_term(x, namespace_manager)
            if isinstance(x, URIRef) and s[0] != '<':
                ns.add(s.split(':', 1)[0])
            elif isinstance(x, Literal) and '^^' in s and s[-1] != '>':
                ns.add(s.split('^^', 1)[1].split(':', 1)[0])

            p += s + ' '
        g += p + ".\n"

    if (namespace_manager is not None) and show_namespaces:
        g = "".join('@prefix ' + str(x) + ': ' + y.n3() + ' .\n'
                    for x, y
                    in namespace_manager.namespaces()
                    if x in ns) + g

    return g
