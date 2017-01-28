import unittest
import traceback
import shutil

from yarom.configure import Configuration, Configureable
from yarom.data import Data
from yarom.sleepycat import SleepyCatSource
from .base_test import TEST_NS, make_graph

HAS_BSDDB = False

try:
    import bsddb
    print("BSDDB:", bsddb.__file__)
    HAS_BSDDB = True
except ImportError:
    try:
        import bsddb3
        print("BSDDB:", bsddb3.__file__)
        HAS_BSDDB = True
    except:
        HAS_BSDDB = False


class DataTest(unittest.TestCase):
    @unittest.skipIf((not HAS_BSDDB), "Sleepycat requires working bsddb")
    def test_Sleepycat_persistence(self):
        """ Should be able to init without these values """
        c = Configuration()
        fname = 'Sleepycat_store'
        c['rdf.source'] = 'Sleepycat'
        c['rdf.store_conf'] = fname
        c['rdf.namespace'] = TEST_NS
        Configureable.conf = c
        d = Data()
        d.register_source(SleepyCatSource)
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

        shutil.rmtree(fname)
