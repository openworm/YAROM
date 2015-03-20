# -*- coding: utf-8 -*-

import unittest

import sys
sys.path.insert(0,".")

import yarom
import yarom as Y
from yarom import *
import tests
import test_data as TD
import rdflib
import rdflib as R
import pint as Q
import os
import subprocess
import tempfile

try:
    import bsddb
    has_bsddb = True
except ImportError:
    try:
        import bsddb3
        has_bsddb = True
    except:
        has_bsddb = False

test_ns = "http://github.com/mwatts15/YAROM/tests/"

def clear_graph(graph):
    graph.update("CLEAR ALL")

def unlink_zodb_db(fname):
    os.unlink(fname)
    os.unlink(fname + '.index')
    os.unlink(fname + '.tmp')
    os.unlink(fname + '.lock')

def make_graph(size=100):
    """ Make an rdflib graph """
    g = R.Graph()
    for i in range(size):
        s = rdflib.URIRef("http://somehost.com/s"+str(i))
        p = rdflib.URIRef("http://somehost.com/p"+str(i))
        o = rdflib.URIRef("http://somehost.com/o"+str(i))
        g.add((s,p,o))
    return g
try:
    TEST_CONFIG = Configuration.open("tests/_test.conf")
except:
    TEST_CONFIG = Configuration.open("tests/test_default.conf")

@unittest.skipIf((TEST_CONFIG['rdf.source'] == 'Sleepycat') and (has_bsddb==False), "Sleepycat store will not work without bsddb")
class _DataTestB(unittest.TestCase):
    TestConfig = TEST_CONFIG
    def delete_dir(self):
        self.path = self.TestConfig['rdf.store_conf']
        try:
            if self.TestConfig['rdf.source'] == "Sleepycat":
                subprocess.call("rm -rf "+self.path, shell=True)
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


class _DataTest(_DataTestB):
    def setUp(self):
        _DataTestB.setUp(self)
        # Set do_logging to True if you like walls of text
        yarom.connect(conf=self.TestConfig, do_logging=False)

    def tearDown(self):
        yarom.disconnect()
        _DataTestB.tearDown(self)

    @property
    def config(self):
        return yarom.config()

class ConfigureTest(unittest.TestCase):
    def test_fake_config(self):
        """ Try to retrieve a config value that hasn't been set """
        with self.assertRaises(KeyError):
            c = Configuration()
            c['not_a_valid_config']

    def test_literal(self):
        """ Assign a literal rather than a ConfigValue"""
        c = Configuration()
        c['seven'] = "coke"
        self.assertEqual(c['seven'], "coke")

    def test_ConfigValue(self):
        """ Assign a ConfigValue"""
        c = Configuration()
        class pipe(ConfigValue):
            def get(self):
                return "sign"
        c['seven'] = pipe()
        self.assertEqual("sign",c['seven'])

    def test_getter_no_ConfigValue(self):
        """ Assign a method with a "get". Should return a the object rather than calling its get method """
        c = Configuration()
        class pipe:
            def get(self):
                return "sign"
        c['seven'] = pipe()
        self.assertIsInstance(c['seven'], pipe)

    def test_late_get(self):
        """ "get" shouldn't be called until the value is *dereferenced* """
        c = Configuration()
        a = {'t' : False}
        class pipe(ConfigValue):
            def get(self):
                a['t'] = True
                return "sign"
        c['seven'] = pipe()
        self.assertFalse(a['t'])
        self.assertEqual(c['seven'], "sign")
        self.assertTrue(a['t'])

    def test_read_from_file(self):
        """ Read configuration from a JSON file """
        try:
            d = Data.open("tests/test.conf")
            self.assertEqual("test_value", d["test_variable"])
        except:
            self.fail("test.conf should exist and be valid JSON")

    def test_read_from_file_fail(self):
        """ Fail on attempt to read configuration from a non-JSON file """
        with self.assertRaises(ValueError):
            Data.open("tests/bad_test.conf")

class ConfigureableTest(unittest.TestCase):
    def test_init_empty(self):
        """Ensure Configureable gets init'd with the defalut if nothing's given"""
        i = Configureable()
        self.assertEqual(Configureable.conf,i.conf)

    def test_init_False(self):
        """Ensure Configureable gets init'd with the defalut if False is given"""
        i = Configureable(conf=False)
        self.assertEqual(Configureable.conf, i.conf)

class DataObjectTest(_DataTest):

    def test_DataUser(self):
        do = Y.DataObject()
        self.assertTrue(isinstance(do,yarom.DataUser))

    def test_identifier(self):
        """ Test that we can set and return an identifier """
        do = Y.DataObject(ident="http://example.org")
        self.assertEqual(do.identifier(), R.URIRef("http://example.org"))

    def test_call_graph_pattern_twice(self):
        """ Be sure that we can call graph pattern on the same object multiple times and not have it die on us """

        g = make_graph(20)
        d = Y.DataObject(triples=g, key="id")
        self.assertNotEqual(0,len(d.graph_pattern()))
        self.assertNotEqual(0,len(d.graph_pattern()))

    @unittest.skip("Enable output of a graph pattern for a query")
    def test_call_graph_pattern_twice_query(self):
        """ Be sure that we can call graph pattern on the same object multiple times and not have it die on us """

        g = make_graph(20)
        d = Y.DataObject(triples=g)
        self.assertNotEqual(0,len(d.graph_pattern(True)))
        self.assertNotEqual(0,len(d.graph_pattern(True)))

    @unittest.skip("Should be tracked by version control")
    def test_uploader(self):
        """ Make sure that we're marking a statement with it's uploader """

        g = make_graph(20)
        r = Y.DataObject(triples=g,conf=self.config)
        r.save()
        u = r.uploader()
        self.assertEqual(self.config['user.email'], u)

    @unittest.skip("Should be tracked by version control")
    def test_upload_date(self):
        """ Make sure that we're marking a statement with it's upload date """
        g = make_graph(20)
        r = Y.DataObject(triples=g)
        r.save()
        u = r.upload_date()
        self.assertIsNotNone(u)

    def test_triples_cycle(self):
        """ Test that no duplicate triples are released when there's a cycle in the graph """
        class T(Y.DataObject):
            objectProperties = ['s']

        t = T()
        s = T()
        t.s(s)
        s.s(t)
        seen = set()
        for x in t.triples(query=True):
            if (x in seen):
                self.fail("got a duplicate: "+ str(x))
            else:
                seen.add(x)

    def test_triples_clone_sibling(self):
        """ Test that no duplicate triples are released when there's a clone in the graph.

        For example: A->B
                     |
                     +->C->B
        This is to avoid the simple 'guard' solution in triples which would output B
        twice.
        """
        class T(Y.DataObject):
            objectProperties = ['s']

        t = T(key="a")
        s = T(key="b")
        v = T(key="c")
        t.s(s)
        t.s(v)
        v.s(s)
        seen = set()
        for x in t.triples(query=True):
            if (x in seen):
                self.fail("got a duplicate: "+ str(x))
            else:
                seen.add(x)

    def test_property_matching_method_name(self):
        """ Creating a property with the same name as a method should be disallowed """
        class T(Y.DataObject):
            objectProperties = ['load']
        with self.assertRaises(Exception):
            T()

class DataUserTest(_DataTest):

    @unittest.skip("Decide what to do with this case")
    def test_init_no_config(self):
        """ Should fail to initialize since it's lacking basic configuration """
        c = Configureable.conf
        Configureable.conf = False
        with self.assertRaises(BadConf):
            DataUser()

        Configureable.conf = c

    def test_init_no_config_with_default(self):
        """ Should suceed if the default configuration is a Data object """
        DataUser()

    def test_init_False_with_default(self):
        """ Should suceed if the default configuration is a Data object """
        DataUser(conf=False)

    @unittest.skip("Should be tracked by version control")
    def test_add_statements_has_uploader(self):
        """ Assert that each statement has an uploader annotation """
        g = R.Graph()

        # Make a statement (triple)
        s = rdflib.URIRef("http://somehost.com/s")
        p = rdflib.URIRef("http://somehost.com/p")
        o = rdflib.URIRef("http://somehost.com/o")

        # Add it to an RDF graph
        g.add((s,p,o))

        # Make a datauser
        du = DataUser(self.config)

        try:
            # Add all of the statements in the graph
            du.add_statements(g)
        except Exception as e:
            self.fail("Should be able to add statements in the first place: "+str(e))

        g0 = du.conf['rdf.graph']

        # These are the properties that we should find
        uploader_n3_uri = du.conf['rdf.namespace']['uploader'].n3()
        upload_date_n3_uri = du.conf['rdf.namespace']['upload_date'].n3()
        uploader_email = du.conf['user.email']

        # This is the query to get uploader information
        q = """
        Select ?u ?t where
        {
        GRAPH ?g
        {
         <http://somehost.com/s>
         <http://somehost.com/p>
         <http://somehost.com/o> .
        }

        ?g """+uploader_n3_uri+""" ?u.
        ?g """+upload_date_n3_uri+""" ?t.
        } LIMIT 1
        """
        for x in g0.query(q):
            self.assertEqual(du.conf['user.email'],str(x['u']))

    def test_add_statements_completes(self):
        """ Test that we can upload lots of triples.

        This is to address the problem from issue #31 on https://github.com/openworm/yarom/issues
        """
        g = rdflib.Graph()
        for i in range(9000):
            s = rdflib.URIRef("http://somehost.com/s%d" % i)
            p = rdflib.URIRef("http://somehost.com/p%d" % i)
            o = rdflib.URIRef("http://somehost.com/o%d" % i)
            g.add((s,p,o))
        du = DataUser(conf=self.config)
        du.add_statements(g)

class DataUserTestToo(unittest.TestCase):
    @unittest.skip("Decide what to do with this case")
    def test_init_config_no_Data(self):
        """ Should fail if given a non-Data configuration """
        # XXX: This test touches some machinery in
        # yarom/__init__.py. Feel like it's a bad test
        tmp = Configureable.conf
        Configureable.conf = Configuration()
        with self.assertRaises(BadConf):
            DataUser()
        Configureable.conf = tmp

    def test_inference(self):
        """ A simple test on the inference engine """
        ex = R.Namespace("http://example.org/")
        pred = ex['sameAs']
        with sameAsRules(ex,pred) as rules_file:
            c = Configuration()
            c.copy(TEST_CONFIG)
            c['rdf.source'] = 'zodb'
            c['rdf.store_conf'] = 'zodb'
            c['rdf.namespace'] = test_ns
            Configureable.conf = c
            d = Data()
            Configureable.conf = d
            d['rdf.inference'] = True
            d['rdf.rules'] = rules_file
            d.openDatabase()
            graph = [(ex['x'], pred, ex['z']),
                     (ex['z'], ex['b'], ex['k']),
                     (ex['z'], ex['d'], ex['e'])]
            du = DataUser()
            du.add_statements(graph)
            self.assertIn((ex['x'], ex['b'], ex['k']), du.rdf)
            self.assertIn((ex['x'], ex['d'], ex['e']), du.rdf)
            unlink_zodb_db('zodb')

class sameAsRules(object):
    def __init__(self, ns=False, predicate='sameAs'):
        self.rules = None
        self.ns = ns
        self.predicate = predicate

    def __enter__(self):
        """ make a rules file with a simple 'sameAs' rule and return the file name """
        self.rules = tempfile.mkstemp()[1]
        f = open(self.rules, "w")
        if self.ns:
            ex = self.ns
        else:
            ex = R.Namespace(ns)
        v = {"x" : R.Variable('x').n3(),
                "y" : self.predicate.n3(),
                "z" : R.Variable('z').n3(),
                "m" : R.Variable('m').n3(),
                "n" : R.Variable('n').n3() }
        f.write("{ %(x)s %(y)s %(z)s . %(z)s %(m)s %(n)s } => { %(x)s %(m)s %(n)s } .\n" % v)
        f.close()
        return self.rules

    def __exit__(self, *args,**kwargs):
        os.unlink(self.rules)

class RDFLibTest(unittest.TestCase):
    """Test for RDFLib."""

    @classmethod
    def setUpClass(cls):
        cls.ns = {"ns1" : "http://example.org/"}
    def test_uriref_not_url(self):
        try:
            rdflib.URIRef("daniel@example.com")
        except:
            self.fail("Doesn't actually fail...which is weird")
    def test_uriref_not_id(self):
        """ Test that rdflib throws up a warning when we do something bad """
        #XXX: capture the logged warning
        import io
        import logging
        out = io.StringIO()
        logger = logging.getLogger('rdflib.term')
        stream_handler = logging.StreamHandler(out)
        logger.addHandler(stream_handler)
        try:
            rdflib.URIRef("some random string")
        finally:
            out.flush()
            logger.removeHandler(stream_handler)
        v = out.getvalue()
        out.close()
        self.assertRegex(str(v), r".*some random string.*")

    def test_BNode_equality1(self):
        a = rdflib.BNode("some random string")
        b = rdflib.BNode("some random string")
        self.assertEqual(a, b)

    def test_BNode_equality2(self):
        a = rdflib.BNode()
        b = rdflib.BNode()
        self.assertNotEqual(a, b)

#class TimeTest(unittest.TestCase):
    #def test_datetime_isoformat_has_timezone(self):
        #time_stamp = now(utc).isoformat()
        #self.assertRegexp(time_stamp, r'.*[+-][0-9][0-9]:[0-9][0-9]$')

class PintTest(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.ur = Q.UnitRegistry()
        self.Q = self.ur.Quantity
    def test_atomic_short(self):
        q = self.Q(23, "mL")
        self.assertEqual("milliliter", str(q.units))
        self.assertEqual(23, q.magnitude)

    def test_atomic_long_singular(self):
        q = self.Q(23, "milliliter")
        self.assertEqual("milliliter", str(q.units))
        self.assertEqual(23, q.magnitude)

    def test_atomic_long_plural(self):
        q = self.Q(23, "milliliters")
        self.assertEqual("milliliter", str(q.units))
        self.assertEqual(23, q.magnitude)

    def test_atomic_long_plural_to_string(self):
        #XXX: Maybe there's a way to have the unit name pluralized...
        q = self.Q(23, "milliliters")
        self.assertEqual("23 milliliter", str(q))

    def test_string_init_long_plural_to_string(self):
        #XXX: Maybe there's a way to have the unit name pluralized...
        q = self.Q("23 milliliters")
        self.assertEqual("23 milliliter", str(q))

    def test_string_init_short(self):
        q = self.Q("23 mL")
        self.assertEqual("milliliter", str(q.units))
        self.assertEqual(23, q.magnitude)

    def test_string_init_short_no_space(self):
        q = self.Q("23mL")
        self.assertEqual("milliliter", str(q.units))
        self.assertEqual(23, q.magnitude)

    def test_string_init_long_singular(self):
        q = self.Q("23 milliliter")
        self.assertEqual("milliliter", str(q.units))
        self.assertEqual(23, q.magnitude)

    def test_string_init_long_plural(self):
        q = self.Q("23 milliliters")
        self.assertEqual("milliliter", str(q.units))
        self.assertEqual(23, q.magnitude)

    def test_init_magnitude_with_string(self):
        """ Pint doesn't care if you don't give it a number """
        q = self.Q("23", "milliliters")
        self.assertEqual("milliliter", str(q.units))
        self.assertEqual("23", q.magnitude)

        q = self.Q("worm", "milliliters")
        self.assertEqual("worm", q.magnitude)

class QuantityTest(unittest.TestCase):
    def test_string_init_short(self):
        q = Quantity.parse("23 mL")
        self.assertEqual("milliliter", q.unit)
        self.assertEqual(23, q.value)

    def test_string_init_volume(self):
        q = Quantity.parse("23 inches^3")
        self.assertEqual("inch ** 3", q.unit)
        self.assertEqual(23, q.value)

    def test_string_init_compound(self):
        q = Quantity.parse("23 inches/second")
        self.assertEqual("inch / second", q.unit)
        self.assertEqual(23, q.value)

    def test_atomic_short(self):
        q = Quantity(23, "mL")
        self.assertEqual("milliliter", q.unit)
        self.assertEqual(23, q.value)

    def test_atomic_long(self):
        q = Quantity(23, "milliliters")
        self.assertEqual("milliliter", q.unit)
        self.assertEqual(23, q.value)

class DataTest(unittest.TestCase):
    def test_namespace_manager(self):
        c = Configuration()
        c['rdf.source'] = 'default'
        c['rdf.store'] = 'default'
        c['rdf.namespace'] = test_ns
        Configureable.conf = c
        d = Data()
        d.openDatabase()

        self.assertIsInstance(d['rdf.namespace_manager'], R.namespace.NamespaceManager)

    def test_init_no_rdf_store(self):
        """ Should be able to init without these values """
        # XXX: If I don't provide some random config value here, this test doesn't work
        #      I have no idea why.
        c = Configuration(nothing='something')
        Configureable.conf = c
        d = Data()
        try:
            d.openDatabase()
        except:
            traceback.print_exc()
            self.fail("Bad state")

    def test_ZODB_persistence(self):
        """ Should be able to init without these values """
        c = Configuration()
        fname ='ZODB.fs'
        c['rdf.source'] = 'ZODB'
        c['rdf.store_conf'] = fname
        c['rdf.namespace'] = test_ns
        Configureable.conf = c
        d = Data()
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

    @unittest.skipIf((has_bsddb==False), "Sleepycat requires working bsddb")
    def test_Sleepycat_persistence(self):
        """ Should be able to init without these values """
        c = Configuration()
        fname='Sleepycat_store'
        c['rdf.source'] = 'Sleepycat'
        c['rdf.store_conf'] = fname
        c['rdf.namespace'] = test_ns
        Configureable.conf = c
        d = Data()
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

        subprocess.call("rm -rf "+fname, shell=True)

    def test_trix_source(self):
        """ Test that we can load the datbase up from an XML file.
        """
        t = tempfile.mkdtemp()
        f = tempfile.mkstemp()

        c = Configuration()
        c['rdf.source'] = 'trix'
        c['rdf.store'] = 'default'
        c['rdf.namespace'] = test_ns
        c['trix_location'] = f[1]

        with open(f[1],'w') as fo:
            fo.write(TD.TriX_data)

        connect(conf=c)
        c = config()

        try:
            g = c['rdf.graph']
            b = g.query("ASK { ?S ?P ?O }")
            for x in b:
                self.assertTrue(x)
        except ImportError:
            pass
        finally:
            disconnect()
        os.unlink(f[1])

    def test_trig_source(self):
        """ Test that we can load the datbase up from a trig file.
        """
        t = tempfile.mkdtemp()
        f = tempfile.mkstemp()

        c = Configuration()
        c['rdf.source'] = 'serialization'
        c['rdf.serialization'] = f[1]
        c['rdf.serialization_format'] = 'trig'
        c['rdf.store'] = 'default'
        c['rdf.namespace'] = test_ns
        with open(f[1],'w') as fo:
            fo.write(TD.Trig_data)

        connect(conf=c)
        c = config()

        try:
            g = c['rdf.graph']
            b = g.query("ASK { ?S ?P ?O }")
            for x in b:
                self.assertTrue(x)
        except ImportError:
            pass
        finally:
            disconnect()

class PropertyTest(_DataTest):
    def test_one(self):
        """ `one` should return None if there isn't a value or just the value if there is one """
        class T(Property):
            def __init__(self):
                Property.__init__(self)
                self.b = False

            def get(self):
                if self.b:
                    yield "12"
        t = T()
        self.assertIsNone(t.one())
        t.b=True
        self.assertEqual('12', t.one())

class MapperTest(_DataTestB):
    def setUp(self):
        _DataTestB.setUp(self)
        Configureable.conf = self.TestConfig
        Configureable.conf = Data()
        Configureable.conf.openDatabase()

    def tearDown(self):
        Configureable.conf.closeDatabase()
        _DataTestB.tearDown(self)

    @unittest.expectedFailure
    def test_addToGraph(self):
        """Test that we can load a descendant of DataObject as a class"""
        # TODO: See related TODO in mapper.py
        dc = MappedClass("TestDOM", (Y.DataObject,), dict())
        self.assertIn((dc.rdf_type, R.RDFS['subClassOf'], Y.DataObject.rdf_type), dc.du.rdf)

    def test_access_created_from_module(self):
        """Test that we can add an object and then access it from the yarom module"""
        dc = MappedClass("TestDOM", (Y.DataObject,), dict())
        self.assertTrue(hasattr(Y,"TestDOM"))

    def test_object_from_id_class(self):
        """ Ensure we get an object from just the class name """
        MappedClass("TestDOM", (Y.DataObject,), dict())
        MappedClass.remap()
        g = mapper.oid(Configureable.conf['rdf.namespace']['TestDOM'])
        self.assertIsInstance(g,Y.TestDOM)

class RDFPropertyTest(_DataTest):
    def test_getInstanceTwice(self):
        from yarom.dataObject import RDFProperty
        self.assertEqual(RDFProperty.getInstance(), RDFProperty.getInstance())

    def test_init_direct(self):
        with self.assertRaises(Exception):
            yarom.dataObject.RDFProperty()

    def test_type_is_class(self):
        from yarom.dataObject import RDFProperty,RDFSClass
        types = RDFProperty.getInstance().rdf_type_property.values
        self.assertIn(RDFSClass.getInstance(), types)

class SimplePropertyTest(_DataTest):
    def __init__(self,*args,**kwargs):
        _DataTest.__init__(self,*args,**kwargs)
        id_tests = []

    def setUp(self):
        _DataTest.setUp(self)

        # Done dynamically to ensure that all of the yarom setup happens before the class is created
        class K(Y.DataObject):
            datatypeProperties = [{'name':'boots', 'multiple':False}, 'bets']

            objectProperties = [{'name':'bats', 'multiple':False}, 'bits']
        self.k = K

    # XXX: auto generate some of these tests...
    @unittest.skip
    def test_same_value_same_id_not_empty(self):
        """
        Test that two SimpleProperty with the same name have the same identifier()
        XXX: Make this evoke the related relation object and compare those
        """
        do = self.k(key="a")
        do1 = self.k(key="a")
        do.boots('partition')
        do1.boots('partition')
        self.assertEqual(do.boots.identifier(),do1.boots.identifier())

    @unittest.skip
    def test_same_value_same_id_not_empty_object_property(self):
        """
        Test that two SimpleProperty with the same name have the same identifier()
        XXX: Make this evoke the related relation object and compare those
        """
        do = self.k(key="a")
        do1 = self.k(key="a")
        dz = self.k(key="b")
        dz1 = self.k(key="b")
        do.bats(dz)
        do1.bats(dz1)
        self.assertEqual(do.bats.identifier(),do1.bats.identifier())

    @unittest.skip
    def test_diff_value_diff_id_not_empty(self):
        """
        Test that two SimpleProperty with the same name have the same identifier()
        XXX: Make this evoke the related relation object and compare those
        """
        do = self.k(key="a")
        do1 = self.k(key="a")
        do.boots('join')
        do1.boots('partition')
        self.assertNotEqual(do.boots.link,do1.boots.link)

    @unittest.skip
    def test_diff_value_insert_order_same_id_object_property(self):
        """
        Test that two SimpleProperty with the same name have the same identifier()
        XXX: Make this evoke the related relation object and compare those
        """
        do = self.k(key="a")
        do1 = self.k(key="a")
        oa = self.k(key="1")
        ob = self.k(key="2")
        oc = self.k(key="3")

        do.bits(oa)
        do.bits(ob)
        do.bits(oc)
        do1.bits(oc)
        do1.bits(oa)
        do1.bits(ob)
        self.assertEqual(do.bits.identifier(), do1.bits.identifier())

    def test_non_multiple_saves_single_values(self):
        class C(Y.DataObject):
            datatypeProperties = [{'name':'t', 'multiple':False}]
        do = C(key="s")
        do.t("value1")
        do.t("vaule2")
        do.save()

        do1 = C(key="s")
        self.assertEqual(len(list(do1.t.get())), 1)

    def test_unset_single(self):
        boots = self.k().boots

        boots.set("l")
        boots.unset("l")
        self.assertEqual(len(boots.values), 0)

    def test_unset_single_property_value(self):
        from yarom.simpleProperty import PropertyValue
        boots = self.k().boots

        boots.set("l")
        boots.unset(PropertyValue("l"))
        self.assertEqual(len(boots.values), 0)

    def test_unset_single_by_identifier(self):
        from yarom.simpleProperty import PropertyValue
        bats = self.k().bats

        o = self.k(key='blah')
        bats.set(o)
        bats.unset(o.identifier())
        self.assertEqual(len(bats.values), 0)

    def test_unset_multiple(self):
        bets = self.k().bets
        bets.set("l")
        bets.unset("l")
        self.assertEqual(len(bets.values), 0)

    def test_unset_empty(self):
        """ Attempting to unset a value that isn't set should raise an error """
        bits = self.k().bits
        with self.assertRaises(Exception):
            bits.unset("random")

    def test_unset_wrong_value(self):
        """ Attempting to unset a value that isn't set should raise an error """
        bits = self.k().bits
        bits.set(self.k(key='roger'))
        with self.assertRaises(Exception):
            bits.unset("random")

class ObjectCollectionTest(_DataTest):
    """ Tests for the simple container class """
    def test_member_can_be_restored(self):
        """ Test that we can retrieve a saved collection and its members """
        oc = Y.ObjectCollection('test')
        do = Y.DataObject(key="s")
        oc.member(do)
        oc.save()
        ocr = Y.ObjectCollection('test')
        dor = ocr.member.one()
        self.assertEqual(do, dor)

def main(*args,**kwargs):
    unittest.main(*args,**kwargs)

if __name__ == '__main__':
    if len(sys.argv) == 3:
        main(defaultTest=sys.argv[1])
    else:
        main()
