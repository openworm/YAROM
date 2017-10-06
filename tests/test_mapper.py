import unittest
from yarom.configure import Configureable
from yarom.data import Data
from yarom.mapper import Mapper
from yarom.mappedClass import MappedClass
import yarom
import logging
from .base_test import _DataTestB
import rdflib

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('yarom.mapper')

class MapperFilter(object):
    def filter(self, record):
        if 'yarom.mapper' in record.name:
            if 'Adding class' in record.msg or 'Replacing' in record.msg:
                return True
            return False
        return True

#logger.addFilter(MapperFilter())
class MappedClassFilter(object):
    def filter(self, record):
        return 'SimpleProperty' in record.msg
logger = logging.getLogger('yarom.mappedProperty')
logger.addFilter(MappedClassFilter())


class MapperTest(_DataTestB):

    def setUp(self):
        _DataTestB.setUp(self)
        self.mapper = Mapper(('yarom.dataObject.DataObject',
                              'yarom.simpleProperty.SimpleProperty'))
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
        dc = MappedClass("TestDOM", (yarom.DataObject,), dict())
        self.assertIn(
            (dc.rdf_type,
             rdflib.RDFS['subClassOf'],
             yarom.DataObject.rdf_type),
            dc.du.rdf)

    def test_access_created_from_module(self):
        """
        Test that we can add an object and then access it from the yarom
        module
        """
        cls = MappedClass("TestDOM", (yarom.DataObject,), dict())
        self.mapper.add_class(cls)
        self.assertTrue(hasattr(yarom, "TestDOM"))

    def test_object_from_id_class(self):
        """ Ensure we get an object from just the class name """
        dc = MappedClass("TestDOM", (yarom.DataObject,), dict())
        self.mapper.add_class(dc)
        self.mapper.remap()
        g = self.mapper.oid(dc.rdf_type)
        self.assertIsInstance(g, yarom.TestDOM)

    def test_children_are_added(self):
        """ Ensure that, on registration, children are added """
        cls = MappedClass("TestDOM", (yarom.DataObject,), dict())
        self.mapper.add_class(cls)
        self.assertIn(
            cls,
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
