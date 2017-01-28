from rdflib import ConjunctiveGraph
import os
import transaction
import traceback
import logging

from .data import RDFSource

L = logging.getLogger(__name__)


class ZODBSource(RDFSource):

    """ Reads from and queries against a configured Zope Object Database.

        If the configured database does not exist, it is created.

        The database store is configured with::

            "rdf.source" = "ZODB"
            "rdf.store_conf" = <location of your ZODB database>

        Leaving unconfigured simply gives an in-memory data store.
    """
    name = "zodb"

    def __init__(self, *args, **kwargs):
        super(ZODBSource, self).__init__(*args, **kwargs)
        self.conf['rdf.store'] = "ZODB"

    def open(self):
        import ZODB
        from ZODB.FileStorage import FileStorage
        self.path = self.conf['rdf.store_conf']
        openstr = os.path.abspath(self.path)
        try:
            fs = FileStorage(openstr)
            self.zdb = ZODB.DB(fs)
            self.conn = self.zdb.open()
            root = self.conn.root()
            if 'rdflib' not in root:
                root['rdflib'] = ConjunctiveGraph('ZODB')
            self.graph = root['rdflib']
            try:
                transaction.commit()
            except Exception:
                # catch commit exception and close db.
                # otherwise db would stay open and follow up tests
                # will detect the db in error state
                L.warning('Forced to abort transaction on ZODB store opening')
                traceback.print_exc()
                transaction.abort()
            transaction.begin()
            self.graph.open(self.path)
        except Exception:
            transaction.abort()
            raise Exception(
                "ZODB format error. This may be a result of using two"
                " different versions of ZODB, such as between Python 3.x and"
                " Python 2.x")

    def close(self):
        if self.graph is None:
            return

        self.graph.close()

        try:
            transaction.commit()
        except Exception:
            # catch commit exception and close db.
            # otherwise db would stay open and follow up tests
            # will detect the db in error state
            traceback.print_exc()
            L.warning('Forced to abort transaction on ZODB store closing')
            transaction.abort()
        self.conn.close()
        self.zdb.close()
        self.graph = None
