from yarom import (Configuration, connect, disconnect)
from yarom import config as C
import unittest
import subprocess
import os

HAS_BSDDB = False
TEST_NS = "http://github.com/mwatts15/YAROM/tests/"


try:
    TEST_CONFIG = Configuration.open("tests/_test.conf")
except:
    TEST_CONFIG = Configuration.open("tests/test_default.conf")


class _DataTestB(unittest.TestCase):
    TestConfig = TEST_CONFIG

    def delete_dir(self):
        self.path = self.TestConfig['rdf.store_conf']
        try:
            if self.TestConfig['rdf.source'] == "Sleepycat":
                subprocess.call("rm -rf " + self.path, shell=True)
            elif self.TestConfig['rdf.source'] == "ZODB":
                unlink_zodb_db(self.path)
        except OSError as e:
            if e.errno == 2:
                # The file may not exist and that's fine
                pass
            else:
                raise e

    def setUp(self):
        self.delete_dir()

    def tearDown(self):
        self.delete_dir()


@unittest.skipIf(
    (TEST_CONFIG['rdf.source'] == 'Sleepycat') and (not HAS_BSDDB),
    "Sleepycat store will not work without bsddb")
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
        return C(*args)


def unlink_zodb_db(fname):
    os.unlink(fname)
    os.unlink(fname + '.index')
    os.unlink(fname + '.tmp')
    os.unlink(fname + '.lock')
