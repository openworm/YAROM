# Works like Configuration:
# Inherit from the DataUser class to access data of all kinds (listed above)

import rdflib
from rdflib import Graph, Namespace, ConjunctiveGraph
from rdflib.namespace import NamespaceManager
from .quantity import Quantity
from datetime import datetime as DT
import datetime
import os
import logging
from .configure import Configureable, Configuration, ConfigValue

__all__ = [
    "Data",
    "RDFSource",
    "SerializationSource",
    "TrixSource",
    "SPARQLSource",
    "DefaultSource"]

L = logging.getLogger(__name__)


class Data(Configuration, Configureable):

    """
    Provides configuration for access to the database.

    Usally doesn't need to be accessed directly
    """

    def __init__(self, conf=False):
        Configuration.__init__(self)
        Configureable.__init__(self)
        if conf is not False:
            self.init_conf = conf
        else:
            self.init_conf = Configureable.conf

        # We copy over all of the configuration that we were given
        self.copy(self.init_conf)
        ns_string = self.get(
            'rdf.namespace',
            'http://example.org/TestNamespace/entities/')

        self['rdf.namespace'] = Namespace(ns_string)
        self.namespace = self['rdf.namespace']

        # TODO: Add support for defining additional data types from the configs
        self.dt_ns = Namespace(self.namespace["datatypes"] + "/")
        quant_datatype = self.dt_ns["quantity"]
        if quant_datatype not in rdflib.term._toPythonMapping:
            rdflib.term.bind(quant_datatype, Quantity, Quantity.parse)
        self.sources = dict()
        self.register_source(DefaultSource)

    @classmethod
    def open(cls, file_name):
        """ Open a file storing configuration in a JSON format """
        Configureable.setConf(Configuration.open(file_name))
        return cls()

    def openDatabase(self):
        """ Open a the configured database """
        self._init_rdf_graph()
        L.debug("opening " + str(self.source))
        self.source.open()
        nm = NamespaceManager(self['rdf.graph'])
        self['rdf.namespace_manager'] = nm
        self['rdf.graph'].namespace_manager = nm

        nm.bind("dt", self.dt_ns)
        nm.bind("", self['rdf.namespace'])

        # TODO: Extract classes recorded in the graph
        #       First, look at the :pythonClass attribute attached to the RDF class resource.
        #       - Look up the class in the PythonClassRegistry using the ID
        #         attached at the :pythonClass attribute.
        #       - Verify the python class name in the registry
        #       - Get the python module location (whether remote or local)
        #       - Load the python module (downloading it if necessary) and add it to the yarom
        #         namespace
        # TODO: Add support for loading python packages with setuptools.

    def register_source(self, source):
        if source.name in self.sources:
            raise Exception(
                "There is already an rdf source with the name " +
                str(source.name))
        else:
            self.sources[source.name] = source

    def closeDatabase(self):
        """ Close a the configured database """
        self.source.close()

    def _init_rdf_graph(self):
        # Set these in case they were left out
        c = self.init_conf
        self['rdf.source'] = c['rdf.source'] = c.get('rdf.source', 'default')
        self['rdf.store'] = c['rdf.store'] = c.get('rdf.store', 'default')
        self['rdf.store_conf'] = c['rdf.store_conf'] = c.get(
            'rdf.store_conf',
            'default')

        source_graph = self.sources[self['rdf.source'].lower()]()
        self.source = source_graph

        if self.get("rdf.inference", False):
            if 'rdf.rules' not in self:
                self['rdf.inference'] = False
                raise Exception(
                    "You've set `rdf.inference' in your configuration. Please provide n3 rules in your configuration (property name `rdf.rules') as well in order to use rdf inference.")

            import warnings
            warnings.filterwarnings(
                'ignore',
                "Missing pydot library")  # Filters an obnoxious warning from FuXi
            # Filters a warning from rdflib not closing its files from a parse
            warnings.filterwarnings(
                'ignore',
                ".*unclosed file <_io.BufferedReader .*")
            try:
                from FuXi.Rete.RuleStore import SetupRuleStore
                from FuXi.Rete.Util import generateTokenSet
                from FuXi.Horn.HornRules import HornFromN3
            except ImportError:
                self['rdf.inference'] = False
                raise Exception(
                    "You've set `rdf.inference' in your configuration, but you do not have FuXi installed, so inference cannot be performed.")

            # fetch the derived object's graph
            rule_store, rule_graph, network = SetupRuleStore(makeNetwork=True)

            # build a network of rules
            for rule in HornFromN3(self['rdf.rules']):
                network.buildNetworkFromClause(rule)

            def infer(graph, new_data):
                """ Fire FuXi rule engine to infer triples """
                # apply rules to original facts to infer new facts
                closureDeltaGraph = Graph()
                network.inferredFacts = closureDeltaGraph

                network.feedFactsToAdd(generateTokenSet(new_data))
                # combine original facts with inferred facts
                if graph:
                    for x in closureDeltaGraph:
                        graph.add(x)
            self['fuxi.network'] = network
            self['fuxi.rule_graph'] = rule_graph
            self['fuxi.rule_store'] = rule_store
            self['fuxi.infer_func'] = infer

            # XXX: Not sure if this is the most appropriate way to set
            #      up the network
            source_graph._get = source_graph.get

            def get():
                """ A one-time wrapper. Resets to the actual `get` after being called once """
                g = source_graph._get()  # get the graph in the normal way
                infer(False, g)  # add the initial facts to the rete network
                source_graph.get = source_graph._get  # restore the old `get`
                return g

            source_graph.get = get

        self.link('semantic_net_new', 'semantic_net', 'rdf.graph')
        self['rdf.graph'] = source_graph
        return source_graph


def modification_date(filename):
    t = os.path.getmtime(filename)
    return datetime.datetime.fromtimestamp(t)


class RDFSource(ConfigValue, Configureable):

    """ Base class for data sources.

    Alternative sources should dervie from this class
    """

    def __init__(self, **kwargs):
        super(RDFSource, self).__init__(**kwargs)
        self.graph = False

    def get(self):
        if self.graph is False:
            raise Exception(
                "Must call openDatabase on Data object before using the database")
        return self.graph

    def close(self):
        if self.graph is False:
            return
        self.graph.close()
        self.graph = False

    def open(self):
        """ Called on ``yarom.connect()`` to set up and return the rdflib graph.
        Must be overridden by sub-classes.
        """
        raise NotImplementedError()

    def __repr__(self):
        return self.__class__.__name__ + "()"

class SerializationSource(RDFSource):

    """ Reads from an RDF serialization or, if the configured database is more recent, then from that.

        The database store is configured with::

            "rdf.source" = "serialization"
            "rdf.store" = <your rdflib store name here>
            "rdf.serialization" = <your RDF serialization>
            "rdf.serialization_format" = <your rdflib serialization format used>
            "rdf.store_conf" = <your rdflib store configuration here>

    """
    name = 'serialization'

    def open(self):
        if not self.graph:
            self.graph = True
            import glob
            # Check the ages of the files. Read the more recent one.
            g0 = ConjunctiveGraph(store=self.conf['rdf.store'])
            database_store = self.conf['rdf.store_conf']
            source_file = self.conf['rdf.serialization']
            file_format = self.conf['rdf.serialization_format']
            # store_time only works for stores that are on the local
            # machine.
            try:
                store_time = modification_date(database_store)
                # If the store is newer than the serialization
                # get the newest file in the store
                for x in glob.glob(database_store + "/*"):
                    mod = modification_date(x)
                    if store_time < mod:
                        store_time = mod
            except:
                store_time = DT.min

            trix_time = modification_date(source_file)

            g0.open(database_store, create=True)

            if store_time > trix_time:
                # just use the store
                pass
            else:
                # delete the database and read in the new one
                # read in the serialized format
                import warnings
                # Filters a warning from rdflib not closing its files from a
                # parse
                warnings.filterwarnings(
                    'ignore',
                    ".*unclosed file <_io.BufferedReader .*")
                g0.parse(source_file, format=file_format)

            self.graph = g0

        return self.graph


class TrixSource(SerializationSource):

    """ A SerializationSource specialized for TriX

        The database store is configured with::

            "rdf.source" = "trix"
            "rdf.trix_location" = <location of the TriX file>
            "rdf.store" = <your rdflib store name here>
            "rdf.store_conf" = <your rdflib store configuration here>

    """

    name = 'trix'

    def __init__(self, **kwargs):
        super(TrixSource, self).__init__(**kwargs)
        h = self.conf.get('trix_location', 'UNSET')
        self.conf.link('rdf.serialization', 'trix_location')
        self.conf['rdf.serialization'] = h
        self.conf['rdf.serialization_format'] = 'trix'


class SPARQLSource(RDFSource):

    """ Reads from and queries against a remote data store

        Configure like::

            "rdf.source" = "sparql_endpoint"
    """
    name = 'sparql_endpoint'

    def open(self):
        # XXX: If we have a source that's read only, should we need to set the
        # store separately??
        g0 = ConjunctiveGraph('SPARQLUpdateStore')
        g0.open(tuple(self.conf['rdf.store_conf']))
        self.graph = g0
        return self.graph


class DefaultSource(RDFSource):

    """ Reads from and queries against a configured database.

        The default configuration.

        The database store is configured with::

            "rdf.source" = "default"
            "rdf.store" = <your rdflib store name here>
            "rdf.store_conf" = <your rdflib store configuration here>

        Leaving unconfigured simply gives an in-memory data store.
    """
    name = 'default'

    def open(self):
        self.graph = ConjunctiveGraph(self.conf['rdf.store'])
        self.graph.open(self.conf['rdf.store_conf'], create=True)


class _UTC(datetime.tzinfo):

    """UTC"""

    ZERO = datetime.timedelta(0)

    def utcoffset(self, dt):
        return _UTC.ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return _UTC.ZERO
utc = _UTC()


class _B(ConfigValue):

    def __init__(self, f):
        self.v = False
        self.f = f

    def get(self):
        if not self.v:
            self.v = self.f()

        return self.v

    def invalidate(self):
        self.v = False
