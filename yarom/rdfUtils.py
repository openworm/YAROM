import rdflib as R

def print_graph(g, hide_namespaces=False):
    s = g.serialize(format='n3').decode("UTF-8")
    if hide_namespaces:
        lines = s.splitlines()
        s = "\n".join(l for l in lines if not l.startswith("@prefix"))
    print(s)

def serialize_rdflib_term(x, namespace_manager=None):
    if isinstance(x, R.BNode):
        return _bnode_to_var(x)
    elif isinstance(x, R.URIRef) and DataObject._is_variable(x):
        return DataObject._graph_variable_to_var(x)
    else:
        return x.n3(namespace_manager)

def deserialize_rdflib_term(x):
    if isinstance(x, R.Literal):
        x = x.toPython()
        if isinstance(x, R.Literal):
            x = str(x)
    return x

