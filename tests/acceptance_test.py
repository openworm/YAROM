from __future__ import print_function

import traceback
import logging
import tempfile
import shutil
from random import random
from time import time

import yarom
from yarom import (connect, disconnect, config)
from yarom.configure import Configuration

class AcceptanceTest(object):

    """ Acceptance testing """

    def __init__(self, sizes):
        self.sizes = sizes

    def runner(self):
        for s in self.sizes:
            self.setUp()
            self.gather_data(s)
            self.tearDown()

    def setUp(self):
        conf = Configuration.open("tests/testl.conf")
        self.dname = tempfile.mkdtemp(suffix=".db")
        conf['rdf.store_conf'] = self.dname
        connect(conf)

        class C(yarom.DataObject):
            datatypeProperties = ['flexo']

            def __init__(self, x=False, **kwargs):
                super(C, self).__init__(**kwargs)
                if x:
                    self.flexo(x)

            def defined_augment(self):
                return len(self.flexo.defined_values) > 0

            def identifier_augment(self):
                return self.make_identifier(self.flexo.defined_values)
        C.mapper.remap()
        self.C = C

    def tearDown(self):
        disconnect()
        shutil.rmtree(self.dname)

    def gather_data(self, size):
        # feel free to add more if you have the time
        try:
                print(
                    'running',
                    size,
                    'sized test on a',
                    type(config('rdf.graph').store),
                    'store')
                v = yarom.ObjectCollection('zim')
                for z in range(int(size)):
                    v.add(self.C(random()))
                t0 = time()
                v.save()
                for _ in self.C().flexo():
                    pass
                t1 = time()
                print("took", t1 - t0, "seconds")
        except:
            traceback.print_exc()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    AcceptanceTest([10, 100, 1000, 10000]).runner()
