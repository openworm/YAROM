from .dataObject import DataObject

class Relationship(DataObject):
    """ A Relationship is typically related to a property and is an object that
        one points to for talking about the property relationship.

        For SimpleProperty objects, this acts like a RDF Reified triple.
        """
    _ = [{'name':'subject', 'multiple': False},
         {'name':'property', 'multiple': False},
         {'name':'object', 'multiple': False}]
    def _ident_data(self):
        return [self.subject.values,
                self.property.values,
                self.object.values]

    def defined_augment(self):
        for p in self._ident_data():
            if len(p) < 1:
                return False
        return True

    def identifier_augment(self):
        x = self.make_identifier_from_properties('subject','property','object')
        return x
