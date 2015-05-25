""" A demonstration of relationship """

import yarom as Y
import xlrd

Y.connect({'rdf.namespace':'http://example.com/cherries/'})

class SciName(Y.DataObject):
    datatypeProperties = ['genus', 'species']

    def identifier_augment(self):
        return self.make_identifier_from_properties('genus','species')

    def defined_augment(self):
        return (len(self.genus.values) > 0) or (len(self.species.values) > 0)


class Ref(Y.DataObject):
    _ = ['url', 'refentry', 'asserts']

    def identifier_augment(self):
        return self.make_identifier_from_properties('url','refentry')

    def defined_augment(self):
        return (len(self.url.values) > 0) and (len(self.refentry.values) > 0)

class Kind(Y.DataObject):
    """ Sort-of like a class """
    objectProperties = [{'name':'subkind_of'}]

class CherryCultivar(Y.DataObject):
    _ = ['name','height','spread']
Y.remap()

fruitkind = Kind(key='Fruit')
drupekind = Kind(key='Drupe', subkind_of=fruitkind)
cherrykind = Kind(key='Cherry', subkind_of=drupekind)
cherrykind.relate('scientific_name', SciName(genus="Prunus"))

s = xlrd.open_workbook('cherry.xls').sheets()[0]
for row in range(1, s.nrows):
    print("ROW",row)
    name = s.cell(row, 0).value
    height = s.cell(row, 1).value
    try:
        height = Y.Quantity.parse(height)
    except:
        height = height
    spread = s.cell(row, 2).value
    ref = s.cell(row, 3).value
    refurl = s.cell(row, 4).value
    name_key = name.replace(' ', '_').replace('(',';')
    cult = CherryCultivar(key=name_key, name=name, height=height, spread=spread)
    prop = cherrykind.relate('cultivar', cult)
    Ref(url=refurl, refentry=ref).asserts(prop.rel())
Y.remap()
Y.print_graph(cherrykind.get_defined_component())
