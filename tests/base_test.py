from yarom import connect, disconnect
from yarom import config as C
from yarom.configure import Configuration

import rdflib
import unittest
import subprocess
import os

TEST_NS = rdflib.Namespace("YAROM/tests/")

try:
    TEST_CONFIG = Configuration.open("tests/_test.conf")
except:
    TEST_CONFIG = Configuration.open("tests/test_default.conf")


class _DataTestB(unittest.TestCase):
    TestConfig = TEST_CONFIG
    longMessage = True

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



def unlink_zodb_db(fname):
    os.unlink(fname)
    os.unlink(fname + '.index')
    os.unlink(fname + '.tmp')
    os.unlink(fname + '.lock')


def make_graph(size=100):
    """ Make an rdflib graph """
    g = rdflib.Graph()
    for i in range(size):
        s = rdflib.URIRef(TEST_NS["s" + str(i)])
        p = rdflib.URIRef(TEST_NS["p" + str(i)])
        o = rdflib.URIRef(TEST_NS["o" + str(i)])
        g.add((s, p, o))
    return g
