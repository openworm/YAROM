import yarom as Y

class Worm(Y.DataObject):
    datatypeProperties = [{'name':'scientific_name', 'multiple':False}]

class Evidence(Y.DataObject):
    _ = ['asserts']
