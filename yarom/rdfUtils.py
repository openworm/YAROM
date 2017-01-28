import rdflib as R


def print_graph(g, hide_namespaces=False):
    s = g.serialize(format='n3').decode("UTF-8")
    if hide_namespaces:
        lines = s.splitlines()
        s = "\n".join(l for l in lines if not l.startswith("@prefix"))
    print(s)


def serialize_rdflib_term(x, namespace_manager=None):
    return x.n3(namespace_manager)


def deserialize_rdflib_term(x):
    if isinstance(x, R.Literal):
        x = x.toPython()
        if isinstance(x, R.Literal):
            x = str(x)
    return x


def triples_to_bgp(trips, namespace_manager=None):
    # XXX: Collisions could result between the variable names of different
    # objects
    g = ""
    for y in trips:
        g += " ".join(serialize_rdflib_term(x, namespace_manager)
                      for x in y) + " .\n"
    return g
