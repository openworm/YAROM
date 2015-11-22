from rdflib import Graph, Namespace
from rdflib.namespace import RDF, NamespaceManager
import logging
from .configure import Configureable
from .data import Data
from .rdfUtils import triples_to_bgp

L = logging.getLogger(__name__)

__all__ = ["DataUser"]


class DataUser(Configureable):
    """ A convenience wrapper for users of the database

    Classes which use the database should inherit from DataUser.
    """

    # TODO: Make these metadata accessible for configuration managers
    # TODO: Illustrate how setting variables in a config file translates into
    #       these configurations
    configuration_variables = {
            "rdf.namespace" : {
                "description" : "The base namespace for user objects and information.",
                "type" : Namespace,
                "directly_configureable" : True
                },
            "rdf.store" : {
                "description" : "Influences how statements are added to the graph.",
                "type" : str,
                "directly_configureable" : True
                },
            "rdf.graph" : {
                "description" : "The rdflib graph object used for querying and storage of user objects and information.",
                "type" : Graph
                },
            "rdf.namespace_manager" : {
                "description" : "The namespace manager associated with the rdf.graph. Stores prefixes that get used by yarom",
                "type" : NamespaceManager
                }
            }

    def __init__(self, **kwargs):
        super(DataUser, self).__init__(**kwargs)

        if not isinstance(self.conf, Data):
            Configureable.setConf(Data())

    @property
    def base_namespace(self):
        return self.conf['rdf.namespace']

    @base_namespace.setter
    def base_namespace(self, value):
        self.conf['rdf.namespace'] = value

    @property
    def rdf(self):
        return self.conf['rdf.graph']

    @rdf.setter
    def rdf(self, value):
        self.conf['rdf.graph'] = value

    @property
    def namespace_manager(self):
        return self.conf['rdf.namespace_manager']

    def _remove_from_store(self, g):
        # Note the assymetry with _add_to_store. You must add actual elements,
        # but deletes can be performed as a query
        for group in grouper(g, 1000):
            temp_graph = Graph()
            for x in group:
                if x is not None:
                    temp_graph.add(x)
                else:
                    break
            s = " DELETE DATA {" + temp_graph.serialize(format="nt") + " } "
            L.debug("deleting. s = " + s)
            self.conf['rdf.graph'].update(s)

    def _add_to_store(self, g, graph_name=False):
        if self.conf['rdf.store'] == 'SPARQLUpdateStore':
            # XXX With Sesame, for instance, it is probably faster to do a PUT
            #     with over the endpoint's rest interface. Just need to do it
            #     for some common endpoints

            try:
                gs = g.serialize(format="nt")
            except:
                gs = triples_to_bgp(g)

            if graph_name:
                s = " INSERT DATA { GRAPH "+graph_name.n3()+" {" + gs + " } } "
            else:
                s = " INSERT DATA { " + gs + " } "
                L.debug("update query = " + s)
                self.conf['rdf.graph'].update(s)
        else:
            gr = self.conf['rdf.graph']
            for x in g:
                gr.add(x)
            if self.conf.get('rdf.inference', False):
                self.conf['fuxi.infer_func'](gr, g)

        if self.conf['rdf.source'] == 'ZODB':
            import transaction
            # Commit the current commit
            transaction.commit()
            # Fire off a new one
            transaction.begin()

    def retract_statements(self, statements):
        """
        Remove a set of statements from the database.

        Parameters
        ----------
        triples : iter of (:class:`rdflib.term.URIRef`, :class:`rdflib.term.URIRef`, :class:`rdflib.term.URIRef`)
            A set of triples to remove
        """
        for x in statements:
            self.rdf.remove(x)

    def _remove_from_store_by_query(self, q):
        import logging as L
        s = " DELETE WHERE {" + q + " } "
        L.debug("deleting. s = " + s)
        self.conf['rdf.graph'].update(s)

    def add_statements(self, graph):
        """
        Add a set of statements to the database.

        Annotates the addition with uploader name, etc

        Parameters
        ----------
        triples : iter of (:class:`rdflib.term.URIRef`, :class:`rdflib.term.URIRef`, :class:`rdflib.term.URIRef`)
            A set of triples to add to the graph
        """
        self._add_to_store(graph)

    def _reify(self, g, s):
        """
        Add a statement object to g that binds to s
        """
        n = self.conf['new_graph_uri'](s)
        g.add((n, RDF['type'], RDF['Statement']))
        g.add((n, RDF['subject'], s[0]))
        g.add((n, RDF['predicate'], s[1]))
        g.add((n, RDF['object'], s[2]))
        return n


def grouper(iterable, n, fillvalue=None):
    """Collect data into fixed-length chunks or blocks"""
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    while True:
        l = []
        try:
            for x in args:
                l.append(next(x))
        except:
            pass
        yield l
        if len(l) < n:
            break
