import unittest
import traceback
import rdflib as R
from PyOpenWorm import *

class AcceptanceTest(unittest.TestCase):
    """ Acceptance testing """
    def setUp(self):
        connect("tests/test.conf")

    def tearDown(self):
        disconnect()

    def test_open_set(self):
        print(DataObject.openSet())
        values('exo-skeleton')
        values(', ex=')
        print(DataObject.openSet())

    def test_l(self):
        """
        Test that a property can be loaded when the owning
        object doesn't have any other values set
        This test is for many objects of the same kind
        """
        disconnect()
        from random import random
        from time import time
        from subprocess import call
        import os
        # Generate data sets from 10 to 10000 in size
        #  query for properties
        print('starting testl')
        class _to(DataObject):
            def __init__(self,x=False):
                DataObject.__init__(self)
                DatatypeProperty('flexo',owner=self)
                if x:
                    self.flexo(x)
        # feel free to add more if you have the time
        nums = [10, 1e2, 1e3]

        connect("tests/testl.conf")
        try:
            #for 1000, takes about 10 seconds...
            for x in nums:
                print('running ',x,'sized test on a ',Configureable.default['rdf.graph'].store,'store')
                v = values('zim')
                for z in range(int(x)):
                    v.add(_to(random()))
                t0 = time()
                v.save()
                for _ in _to().flexo():
                    pass
                t1 = time()
                print("took", t1 - t0, "seconds")
                Configureable.default['rdf.graph'].remove((None,None,None))
        except:
            traceback.print_exc()
        disconnect()

if __name__ == '__main__':
    if len(sys.argv) == 3:
        main(defaultTest="AcceptanceTest" + sys.argv[1])
    else:
        main()
