# -*- coding: utf-8 -*-

import unittest

import yarom
from yarom.configure import (Configuration,
                             ConfigValue,
                             Configureable,
                             BadConf)
from yarom.data import Data
from yarom.dataUser import DataUser
from yarom.simpleProperty import Property
from yarom.quantity import Quantity

from yarom import yarom_import

import rdflib
import rdflib as R
import pint as Q
import os
import tempfile
import six
import traceback
from .base_test import TEST_CONFIG, TEST_NS, make_graph
from .data_test import _DataTest
from . import test_data as TD

HAS_FUXI = False


try:
    import FuXi
    print("FuXi:", FuXi.__file__)  # Quiets 'unused' warnings from pyflakes
    HAS_FUXI = True
except ImportError:
    pass


def clear_graph(graph):
    graph.update("CLEAR ALL")


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
        self.assertEqual("sign", c['seven'])

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
        a = {'t': False}

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
        except Exception:
            self.fail("test.conf should exist and be valid JSON")

    def test_read_from_file_fail(self):
        """ Fail on attempt to read configuration from a non-JSON file """
        with self.assertRaises(ValueError):
            Data.open("tests/bad_test.conf")


class ConfigureableTest(unittest.TestCase):

    def test_init_empty(self):
        """Ensure Configureable gets init'd with the defalut if nothing's given"""
        i = Configureable()
        self.assertEqual(Configureable.conf, i.conf)


class DataObjectTest(_DataTest):

    def setUp(self):
        super(DataObjectTest, self).setUp()
        self.DataObject = yarom_import('yarom.dataObject.DataObject')

    def test_DataUser(self):
        do = self.DataObject()
        self.assertTrue(isinstance(do, DataUser))

    def test_identifier(self):
        """ Test that we can set and return an identifier """
        do = self.DataObject(ident="http://example.org")
        self.assertEqual(do.identifier, R.URIRef("http://example.org"))

    def test_call_graph_pattern_twice(self):
        """ Be sure that we can call graph pattern on the same object multiple times and not have it die on us """

        d = self.DataObject(key="id")
        self.assertNotEqual(0, len(d.graph_pattern()))
        self.assertNotEqual(0, len(d.graph_pattern()))

    @unittest.skip("Enable output of a graph pattern for a query")
    def test_call_graph_pattern_twice_query(self):
        """ Be sure that we can call graph pattern on the same object multiple times and not have it die on us """

        g = make_graph(20)
        d = self.DataObject(triples=g)
        self.assertNotEqual(0, len(d.graph_pattern(True)))
        self.assertNotEqual(0, len(d.graph_pattern(True)))

    @unittest.skip("Should be tracked by version control")
    def test_uploader(self):
        """ Make sure that we're marking a statement with it's uploader """

        g = make_graph(20)
        r = self.DataObject(triples=g, conf=self.config)
        r.save()
        u = r.uploader()
        self.assertEqual(self.config['user.email'], u)

    @unittest.skip("Should be tracked by version control")
    def test_upload_date(self):
        """ Make sure that we're marking a statement with it's upload date """
        g = make_graph(20)
        r = self.DataObject(triples=g)
        r.save()
        u = r.upload_date()
        self.assertIsNotNone(u)

    def test_triples_cycle(self):
        """
        Test that no duplicate triples are released when there's a cycle in the
        graph
        """
        class T(self.DataObject):
            objectProperties = ['s']
            defined = True

            @property
            def identifier(self):
                return TEST_NS["soup"]

        T.mapper.add_class(T)
        T.mapper.remap()

        t = T()
        s = T()
        t.s(s)
        s.s(t)
        g = rdflib.Graph()
        g.namespace_manager = t.rdf.namespace_manager
        trips = list(t.triples())
        for e in trips:
            g.add(e)
        self.assertEquals(len(set(trips)), len(trips))

    def test_triples_clone_sibling(self):
        """ Test that no duplicate triples are released when there's a clone in the graph.

        For example: A->B
                     |
                     +->C->B
        This is to avoid the simple 'guard' solution in triples which would output B
        twice.
        """
        class T(self.DataObject):
            objectProperties = ['s']
        T.mapper.add_class(T)
        T.mapper.remap()
        t = T(key="a")
        s = T(key="b")
        v = T(key="c")
        t.s(s)
        t.s(v)
        v.s(s)
        seen = set()
        for x in t.triples():
            if (x in seen):
                self.fail("got a duplicate: " + str(x))
            else:
                seen.add(x)

    def test_property_matching_method_name(self):
        """ Creating a property with the same name as a method should be disallowed """
        class T(self.DataObject):
            objectProperties = ['load']
        T.mapper.add_class(T)
        T.mapper.remap()
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

    @unittest.skip("Should be tracked by version control")
    def test_add_statements_has_uploader(self):
        """ Assert that each statement has an uploader annotation """
        g = R.Graph()

        # Make a statement (triple)
        s = rdflib.URIRef("http://somehost.com/s")
        p = rdflib.URIRef("http://somehost.com/p")
        o = rdflib.URIRef("http://somehost.com/o")

        # Add it to an RDF graph
        g.add((s, p, o))

        # Make a datauser
        du = DataUser(self.config)

        try:
            # Add all of the statements in the graph
            du.add_statements(g)
        except Exception as e:
            self.fail(
                "Should be able to add statements in the first place: " +
                str(e))

        g0 = du.conf['rdf.graph']

        # These are the properties that we should find
        uploader_n3_uri = du.conf['rdf.namespace']['uploader'].n3()
        upload_date_n3_uri = du.conf['rdf.namespace']['upload_date'].n3()

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

        ?g """ + uploader_n3_uri + """ ?u.
        ?g """ + upload_date_n3_uri + """ ?t.
        } LIMIT 1
        """
        for x in g0.query(q):
            self.assertEqual(du.conf['user.email'], str(x['u']))

    def test_add_statements_completes(self):
        """ Test that we can upload lots of triples.

        This is to address the problem from issue #31 on https://github.com/openworm/yarom/issues
        """
        g = rdflib.Graph()
        for i in range(9000):
            s = rdflib.URIRef("http://somehost.com/s%d" % i)
            p = rdflib.URIRef("http://somehost.com/p%d" % i)
            o = rdflib.URIRef("http://somehost.com/o%d" % i)
            g.add((s, p, o))
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

    @unittest.skipIf(
        (HAS_FUXI == False),
        "Cannot test inference without the FuXi package")
    def test_inference(self):
        """ A simple test on the inference engine """
        ex = R.Namespace("http://example.org/")
        pred = ex['sameAs']
        with sameAsRules(ex, pred) as rules_file:
            c = Configuration()
            c.copy(TEST_CONFIG)
            c['rdf.namespace'] = TEST_NS
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


class sameAsRules(object):

    def __init__(self, ns=False, predicate='sameAs'):
        self.rules = None
        self.ns = ns
        self.predicate = predicate

    def __enter__(self):
        """ make a rules file with a simple 'sameAs' rule and return the file name """
        self.rules = tempfile.mkstemp()[1]
        f = open(self.rules, "w")
        v = {"x": R.Variable('x').n3(),
             "y": self.predicate.n3(),
             "z": R.Variable('z').n3(),
             "m": R.Variable('m').n3(),
             "n": R.Variable('n').n3()}
        f.write(
            "{ %(x)s %(y)s %(z)s . %(z)s %(m)s %(n)s } => { %(x)s %(m)s %(n)s } .\n" %
            v)
        f.close()
        return self.rules

    def __exit__(self, *args, **kwargs):
        os.unlink(self.rules)


class RDFLibTest(unittest.TestCase):

    """Test for RDFLib."""

    @classmethod
    def setUpClass(cls):
        cls.ns = {"ns1": "http://example.org/"}

    def test_uriref_not_url(self):
        try:
            rdflib.URIRef("daniel@example.com")
        except Exception:
            self.fail("Doesn't actually fail...which is weird")

    @unittest.skipIf(six.PY2, "In Python 2.7, no error is thrown by rdflib")
    def test_uriref_not_id(self):
        """ Test that rdflib throws up a warning when we do something bad """
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
        if six.PY2:
            six.assertRegex(self, str(v), r".*some random string.*")
        else:
            self.assertRegex(str(v), ".*some random string.*")

    def test_BNode_equality1(self):
        a = rdflib.BNode("some random string")
        b = rdflib.BNode("some random string")
        self.assertEqual(a, b)

    def test_BNode_equality2(self):
        a = rdflib.BNode()
        b = rdflib.BNode()
        self.assertNotEqual(a, b)

    def test_datatyped_Literal_equality(self):
        """
        From http://www.w3.org/TR/rdf11-concepts/#section-Datatypes::

            Literal term equality: Two literals are term-equal (the same
            RDF literal) if and only if the two lexical forms, the two datatype
            IRIs, and the two language tags (if any) compare equal, character by
            character. Thus, two literals can have the same value without being
            the same RDF term. For example::

               "1"^^xs:integer
               "01"^^xs:integer
        __eq__ for literals in rdflib do not follow this.
        """
        self.assertTrue(
            R.Literal(
                "1", datatype=R.XSD['integer']), R.Literal(
                "01", datatype=R.XSD['integer']))


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
        # XXX: Maybe there's a way to have the unit name pluralized...
        q = self.Q(23, "milliliters")
        self.assertEqual("23 milliliter", str(q))

    def test_string_init_long_plural_to_string(self):
        # XXX: Maybe there's a way to have the unit name pluralized...
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

    def test_quantity_from_literal(self):
        rdf_datatype = rdflib.URIRef("http://example.com/datatypes/quantity")
        rdflib.term.bind(rdf_datatype, Quantity, Quantity.parse)
        q_rdf = rdflib.Literal("23 mL", datatype=rdf_datatype)
        self.assertEqual("23 milliliter", str(q_rdf))
        q = Quantity(23, "milliliter")
        self.assertEqual(q, q_rdf.toPython())

    def test_quantity_to_literal_and_back(self):
        q = Quantity.parse('22 N')
        k = rdflib.term.Literal(q)
        self.assertEqual(q, k.toPython())


class DataTest(unittest.TestCase):

    def test_namespace_manager(self):
        c = Configuration()
        c['rdf.source'] = 'default'
        c['rdf.store'] = 'default'
        c['rdf.namespace'] = TEST_NS
        Configureable.conf = c
        d = Data()
        d.openDatabase()

        self.assertIsInstance(
            d['rdf.namespace_manager'],
            R.namespace.NamespaceManager)

    def test_init_no_rdf_store(self):
        """ Should be able to init without these values """
        # XXX: If I don't provide some random config value here, this test doesn't work
        #      I have no idea why.
        c = Configuration(nothing='something')
        Configureable.conf = c
        d = Data()
        try:
            d.openDatabase()
        except Exception:
            traceback.print_exc()
            self.fail("Bad state")

    def test_trix_source(self):
        """ Test that we can load the datbase up from an XML file.
        """
        f = tempfile.mkstemp()

        c = Configuration()
        c['rdf.source'] = 'trix'
        c['rdf.store'] = 'default'
        c['rdf.namespace'] = TEST_NS
        c['trix_location'] = f[1]

        with open(f[1], 'w') as fo:
            fo.write(TD.TriX_data)

        yarom.connect(conf=c)
        c = yarom.config()

        try:
            g = c['rdf.graph']
            b = g.query("ASK { ?S ?P ?O }")
            for x in b:
                self.assertTrue(x)
        except ImportError:
            pass
        finally:
            yarom.disconnect()
        os.unlink(f[1])

    def test_trig_source(self):
        """ Test that we can load the datbase up from a trig file.
        """
        f = tempfile.mkstemp()

        c = Configuration()
        c['rdf.source'] = 'serialization'
        c['rdf.serialization'] = f[1]
        c['rdf.serialization_format'] = 'trig'
        c['rdf.store'] = 'default'
        c['rdf.namespace'] = TEST_NS
        with open(f[1], 'w') as fo:
            fo.write(TD.Trig_data)

        yarom.connect(conf=c)
        c = yarom.config()

        try:
            g = c['rdf.graph']
            b = g.query("ASK { ?S ?P ?O }")
            for x in b:
                self.assertTrue(x)
        except ImportError:
            pass
        finally:
            yarom.disconnect()


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
        t.b = True
        self.assertEqual('12', t.one())


class RDFPropertyTest(_DataTest):

    def test_getInstanceTwice(self):
        from yarom.dataObject import RDFProperty
        self.assertEqual(RDFProperty.getInstance(), RDFProperty.getInstance())

    def test_init_direct(self):
        with self.assertRaises(Exception):
            yarom.dataObject.RDFProperty()

    def test_type_is_class(self):
        from yarom.dataObject import RDFProperty, RDFSClass
        types = RDFProperty.getInstance().rdf_type_property.values
        self.assertIn(RDFSClass.getInstance(), types)


class SimplePropertyTest(_DataTest):

    def setUp(self):
        _DataTest.setUp(self)

        # Done dynamically to ensure that all of the yarom setup happens before
        # the class is created
        class K(yarom_import('yarom.dataObject.DataObject')):
            datatypeProperties = [{'name': 'boots', 'multiple': False}, 'bets']
            objectProperties = [{'name': 'bats', 'multiple': False}, 'bits']

        K.mapper.add_class(K)
        K.mapper.remap()
        self.k = K

    def test_non_multiple_saves_single_values(self):
        class C(yarom_import('yarom.dataObject.DataObject')):
            datatypeProperties = [{'name': 't', 'multiple': False}]
        C.mapper.add_class(C)
        C.mapper.remap()
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
        bats = self.k().bats

        o = self.k(key='blah')
        bats.set(o)
        bats.unset(o.identifier)
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


class PropertyValueTest(unittest.TestCase):

    def test_init_identifier(self):
        from yarom.simpleProperty import PropertyValue
        pv = PropertyValue(R.URIRef("http://example.com"))
        self.assertTrue(hasattr(pv, "value"))
        self.assertIsNotNone(getattr(pv, "value"))


class UnionPropertyTest(_DataTest):

    def setUp(self):
        _DataTest.setUp(self)

        # Done dynamically to ensure that all of the yarom setup happens before
        # the class is created
        class K(yarom_import('yarom.dataObject.DataObject')):
            _ = ['name']
        self.k = K
        self.k.mapper.add_class(self.k)
        self.k.mapper.remap()

    def test_get_literal(self):
        k = self.k(generate_key=True)
        k.name('val')
        k.save()
        k.name.unset('val')
        self.assertIn('val', k.name(), "stored literal is returned")

    def test_get_DataObject(self):
        j = self.k(generate_key=True)
        k = self.k(generate_key=True)
        k.name(j)
        k.save()
        k.name.unset(j)
        val = k.name.one()
        self.assertIsInstance(
            val,
            self.k,
            '{} is a {}'.format(val, type(val)))
        self.assertEqual(val, j, "returned value equals stored value")


class ObjectCollectionTest(_DataTest):

    """ Tests for the simple container class """

    def test_member_can_be_restored(self):
        """ Test that we can retrieve a saved collection and its members """
        DataObject = yarom_import('yarom.dataObject.DataObject')
        ObjectCollection = yarom_import('yarom.objectCollection.ObjectCollection')
        oc = ObjectCollection('test')
        do = DataObject(key="s")
        oc.member(do)
        oc.save()
        ocr = ObjectCollection('test')
        dor = ocr.member.one()
        self.assertEqual(do, dor)


def main(*args, **kwargs):
    unittest.main(*args, **kwargs)

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 3:
        main(defaultTest=sys.argv[1])
    else:
        main()
