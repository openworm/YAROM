#!/usr/bin/env python3

# Schema definition
import yarom as Y
Y.connect()
from yarom import DataObject
from c_elegans import Worm, Evidence

class Drug(DataObject):
    # We set up properties in __init__
    _ = ['name']
    def defined_augment(self):
        return len(self.name.values) > 0

    def identifier_augment(self):
        return self.make_identifier_from_properties('name')

class Experiment(DataObject):
    _ = [{'name':'drug', 'type':Drug, 'multiple':False},
         {'name':'subject', 'type':Worm},
         'experimenter',
         'summary',
         'route_of_entry',
         'reaction']
Y.remap()

# Experiment description
d = Drug(name='moon rocks')
d.relate('granularity', 'ground up')

e = Experiment(key='E2334', summary='C. elegans exposure to Moon rocks', experimenter='Cave Johnson') # experiment performed

w = Worm(generate_key=True, scientific_name="C. elegans") # the worm tested

ev = Evidence(key='ApertureLabs')
ev.relate('organization', "Aperture Labs") # Organization releasing the experimental data

e.subject(w)
e.drug(d)
e.route_of_entry('ingestion')
e.reaction('no reaction')
ev.asserts(e)
ev.save()
Y.print_graph(ev.get_defined_component())
