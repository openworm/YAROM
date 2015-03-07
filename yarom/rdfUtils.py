import rdflib as R

def print_graph(g):
    s = g.serialize(format='n3').decode("UTF-8")
    print(s)
