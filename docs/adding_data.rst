.. _adding_data:

Adding Data to *YOUR* YAROM Database
====================================

So, you've got some data about the and you'd like to save it with |pow|,
but you don't know how it's done?

You've come to the right place!

Depending on your needs you may be able to use the default classes directly to define your data. For example,
you can write a little about a person::

    import yarom as Y
    Y.connect({'rdf.namespace': rdflib.namespace.Namespace("http://example.org/")})
    mary = Y.DataObject(key='mary')
    fido = Y.DataObject(key='fido')
    mary.relate('has_pet', fido)
    mary.relate('age', Y.Quantity(23, 'years'))
    mary.relate('email', "mary@example.org")

and get the following graph (namespace prefixes omitted)::

    :DataObject a rdfs:Class .

    :Relationship a rdfs:Class ;
        rdfs:subClassOf :DataObject .

    rdf:Property a rdfs:Class .

    rdfs:Class a rdfs:Class .

    DataObject:mary a :DataObject ;
        DataObject:age "23 year"^^<http://example.org/datatypes/quantity> ;
        DataObject:email "mary@example.org" ;
        DataObject:has_pet DataObject:fido .

    Relationship:subject a rdf:Property ;
        rdfs:domain :Relationship .

    :SimpleProperty a rdf:Property .

    rdf:type a rdf:Property ;
        rdfs:domain :DataObject ;
        rdfs:range rdfs:Class .

    DataObject:fido a :DataObject .

Of course, this description lacks some specificity in types, and one may want to use the well-known FOAF vocabulary (while ignoring the cultural myopia that entails) for defining the age and email address of 'DataObject:mary'. To add this information in |pow|, you would do something like the following::

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

and get a graph like::

    @prefix : <http://example.org/> .
    @prefix Dog: <http://example.org/Dog/> .
    @prefix Person: <http://example.org/Person/> .
    @prefix Relationship: <http://example.org/Relationship/> .
    @prefix foaf: <http://xmlns.com/foaf/0.1/> .
    @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

    :DataObject a rdfs:Class .

    :Dog a rdfs:Class ;
        rdfs:subClassOf :DataObject .

    :Relationship a rdfs:Class ;
        rdfs:subClassOf :DataObject .

    rdf:Property a rdfs:Class .

    rdfs:Class a rdfs:Class .

    foaf:Person a rdfs:Class ;
        rdfs:subClassOf :DataObject .

    Relationship:subject a rdf:Property ;
        rdfs:domain :Relationship .

    :SimpleProperty a rdf:Property .

    rdf:type a rdf:Property ;
        rdfs:domain :DataObject ;
        rdfs:range rdfs:Class .

    Person:mary a foaf:Person ;
        Person:has_pet Dog:fido ;
        foaf:age "23 year"^^<http://example.org/datatypes/quantity> ;
        foaf:mbox "mary@example.org" .

    foaf:mbox a rdf:Property ;
        rdfs:domain foaf:Person .

    Dog:fido a :Dog .

More information on making new DataObject types is given in :ref:`Making data objects <making_dataObjects>`.

Typically, you'll want to attach the data that you insert to entities already in the database. You can do this by specifying an to change, loading it, making additions, and saving the object::

    mary.save()
    q_person = Person()
    q_person.relate('has_pet', Dog())

    for p in q_person.load():
        p.relate('dog_lover', True)
        p.save()

    q_person = Person()
    q_person.relate('dog_lover', True)
    for p in q_person.load():
        print(p) # Prints `Person:mary`
