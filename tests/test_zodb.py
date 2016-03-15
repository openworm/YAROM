import unittest
import traceback

from yarom.configure import Configuration, Configureable
from yarom.data import Data
from yarom.zodb import ZODBSource
from .base_test import unlink_zodb_db, TEST_NS, make_graph

HAS_ZODB = False

try:
    import ZODB
    print("ZODB:", ZODB.__file__)  # Quiets 'unused' warnings from pyflakes
    HAS_ZODB = True
except:
    pass


class DataTest(unittest.TestCase):

    @unittest.skipIf((not HAS_ZODB), "ZODB persistence test requires ZODB")
    def test_ZODB_persistence(self):
        c = Configuration()
        fname = 'ZODB.fs'
        c['rdf.source'] = 'ZODB'
        c['rdf.store_conf'] = fname
        c['rdf.namespace'] = TEST_NS
        Configureable.conf = c
        d = Data()
        d.register_source(ZODBSource)
        try:
            d.openDatabase()
            g = make_graph(20)
            for x in g:
                d['rdf.graph'].add(x)
            d.closeDatabase()

            d.openDatabase()
            self.assertEqual(20, len(list(d['rdf.graph'])))
            d.closeDatabase()
        except:
            traceback.print_exc()
            self.fail("Bad state")
        unlink_zodb_db(fname)
