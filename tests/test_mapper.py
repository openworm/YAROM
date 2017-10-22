import unittest
from yarom.configure import Configureable
from yarom.data import Data
from yarom.mapper import Mapper
from yarom.mappedClass import MappedClass

from .base_test import _DataTestB
import rdflib


class MapperTest(_DataTestB):

    def setUp(self):
        _DataTestB.setUp(self)
        self.mapper = Mapper(('yarom.dataObject.DataObject',
                              'yarom.simpleProperty.SimpleProperty'))
        self.DataObject = self.mapper.load_class('yarom.dataObject.DataObject')
        Configureable.conf = self.TestConfig
        Configureable.conf = Data()
        Configureable.conf.openDatabase()

    def tearDown(self):
        Configureable.conf.closeDatabase()
        self.mapper.deregister_all()
        self.mapper = None
        _DataTestB.tearDown(self)

    @unittest.expectedFailure
    def test_add_to_graph(self):
        """Test that we can load a descendant of DataObject as a class"""
        # TODO: See related TODO in mapper.py
        dc = MappedClass("TestDOM", (self.DataObject,), dict())
        self.assertIn(
            (dc.rdf_type,
             rdflib.RDFS['subClassOf'],
             self.DataObject.rdf_type),
            dc.du.rdf)

    def test_object_from_id_class(self):
        """ Ensure we get an object from just the class name """
        dc = MappedClass("TestDOM", (self.DataObject,), dict())
        self.mapper.add_class(dc)
        self.mapper.remap()
        g = self.mapper.oid(dc.rdf_type)
        self.assertIsInstance(g, dc)

    def test_children_are_added(self):
        """ Ensure that, on registration, children are added """
        cls = MappedClass("TestDOM", (self.DataObject,), dict())
        self.mapper.add_class(cls)
        self.assertIn(
            cls,
            self.DataObject.children,
            msg="The test class is a child")

    def test_children_are_deregistered(self):
        """ Ensure that, on deregistration, DataObject types are cleared from
            the module namespace
        """
        self.mapper.deregister_all()
        self.assertEqual(len(self.mapper.MappedClasses), 0,
                         msg="No mapped classes")
