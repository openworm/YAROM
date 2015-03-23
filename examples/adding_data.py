import yarom as Y
import rdflib
Y.connect({'rdf.namespace': rdflib.Namespace("http://example.org/")})

def p1():
    mary = Y.DataObject(key='mary')
    fido = Y.DataObject(key='fido')
    mary.relate('has_pet', fido)
    mary.relate('age', Y.Quantity(23, 'years'))
    mary.relate('email', "mary@example.org")
    Y.print_graph(mary.get_defined_component())

def p2_p3():
    FOAF = rdflib.Namespace("http://xmlns.com/foaf/0.1/")
    Y.config('rdf.namespace_manager').bind('foaf', FOAF)
    class Person(Y.DataObject):
        rdf_type = FOAF['Person']

    class Dog(Y.DataObject):
        pass

    class FOAFAge(Y.DatatypeProperty):
        link = FOAF['age']
        linkName = "foaf_age"
        owner_type = Person
        multiple = False # XXX: Default is True

    class FOAFMbox(Y.UnionProperty):
        link = FOAF['mbox']
        linkName = "foaf_mbox"
        owner_type = Person # XXX: Not defining agent
        multiple = True
    Y.remap()

    mary = Person(key='mary')
    fido = Dog(key='fido')

    mary.relate('has_pet', fido)
    mary.relate('age', Y.Quantity(23, 'years'), FOAFAge)
    mary.relate('email', "mary@example.org", FOAFMbox)
    Y.print_graph(mary.get_defined_component())

    mary.save()
    q_person = Person()
    q_person.relate('has_pet', Dog())

    for p in q_person.load():
        p.relate('dog_lover', True)
        p.save()

    q_person = Person()
    q_person.relate('dog_lover', True)
    for p in q_person.load():
        print(p)

p1()
p2_p3()
