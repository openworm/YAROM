import unittest
from yarom.configure import Configureable
from yarom.data import Data
from yarom.mapper import Mapper
from yarom.mappedProperty import MappedPropertyClass
from yarom.mappedClass import MappedClass
import yarom
from .base_test import _DataTestB

class MapperTest(_DataTestB):

    def setUp(self):
        _DataTestB.setUp(self)
        self.mapper = Mapper.get_instance()
        Configureable.conf = self.TestConfig
        Configureable.conf = Data()
        Configureable.conf.openDatabase()
        if hasattr(yarom, 'dataObject'):
            self.mapper.reload_module(yarom.dataObject)
            self.mapper.reload_module(yarom.classRegistry)
        else:
            self.mapper.load_module('yarom.dataObject')
            self.mapper.load_module('yarom.classRegistry')

    def tearDown(self):
        Configureable.conf.closeDatabase()
        self.mapper.deregister_all()
        _DataTestB.tearDown(self)

    @unittest.expectedFailure
    def test_addToGraph(self):
        """Test that we can load a descendant of DataObject as a class"""
        # TODO: See related TODO in mapper.py
        dc = MappedClass("TestDOM", (yarom.DataObject,), dict())
        self.assertIn(
            (dc.rdf_type,
             R.RDFS['subClassOf'],
             yarom.DataObject.rdf_type),
            dc.du.rdf)

    def test_access_created_from_module(self):
        """Test that we can add an object and then access it from the yarom module"""
        MappedClass("TestDOM", (yarom.DataObject,), dict())
        self.assertTrue(hasattr(yarom, "TestDOM"))

    def test_object_from_id_class(self):
        """ Ensure we get an object from just the class name """
        dc = MappedClass("TestDOM", (yarom.DataObject,), dict())
        self.mapper.remap()
        g = self.mapper.oid(dc.rdf_type)
        self.assertIsInstance(g, yarom.TestDOM)

    def test_children_are_added(self):
        """ Ensure that, on registration, children are added """
        MappedClass("TestDOM", (yarom.DataObject,), dict())
        self.assertIn(
            yarom.TestDOM,
            yarom.DataObject.children,
            msg="The test class is a child")

    def test_children_are_deregistered(self):
        """ Ensure that, on deregistration, DataObject types are cleared from the module namespace """
        self.assertTrue(
            hasattr(
                yarom,
                'DataObject'),
            "DataObject is in the yarom module")
        self.mapper.deregister_all()
        self.assertFalse(
            hasattr(
                yarom,
                'DataObject'),
            "DataObject is no longer in the yarom module")


