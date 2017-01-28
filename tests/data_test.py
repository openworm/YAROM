import unittest

from yarom import connect, disconnect, config
from .base_test import TEST_CONFIG, TEST_NS, _DataTestB
from .test_sleepycat import HAS_BSDDB
from .test_zodb import HAS_ZODB


# TODO: Manage this with more robust feature toggles
@unittest.skipIf(
    ((TEST_CONFIG['rdf.source'] == 'Sleepycat') and (not HAS_BSDDB)) or
    ((TEST_CONFIG['rdf.source'] == 'zodb') and (not HAS_ZODB)),
    "The source library is missing for this test")
class _DataTest(_DataTestB):

    def setUp(self):
        self.TestConfig['rdf.namespace'] = TEST_NS
        _DataTestB.setUp(self)
        # Set do_logging to True if you like walls of text
        connect(conf=self.TestConfig, do_logging=False)

    def tearDown(self):
        disconnect()
        _DataTestB.tearDown(self)

    @property
    def config(self, *args):
        return config(*args)
