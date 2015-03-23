import yarom as Y
from yarom.rdfUtils import print_graph

import logging as L

Y.connect(conf={'rdf.namespace' : 'http://mark-watts.tk/entities/',
    'rdf.source' : 'default'})

class ToppingAmount(Y.DataObject):
    """ An amount of a topping """

class Topping(Y.DataObject):
    """ A pluralization of a topping type. Represents a topping that can be added to
    pizza rather than a single item in the set of toppings (like, it's not a single
    mushroom, but a collection of mushrooms on a pizza)
    """

    objectProperties = [{'name' : "amount", 'type' : ToppingAmount, 'multiple':False}]

class Meat(Topping):
    pass
class Veggie(Topping):
    pass
class Pepperoni(Meat):
    pass
class Sausage(Meat):
    pass
class Pepper(Veggie):
    pass
class GreenPepper(Pepper):
    pass
class Tomato(Veggie):
    pass
class BlackOlive(Veggie):
    pass

class Pizza(Y.DataObject):
    """ A single pizza """
    objectProperties = [{'name':"topped_with", 'type' : Topping}]

Y.mapper.MappedClass.remap()

def make_melanies_pizza():
    pizza = Pizza(key="Melanie")
    pepperoni = Pepperoni(key="heavy_pepperoni")

    pizza.topped_with(pepperoni)
    pepperoni.amount(ToppingAmount(key="heavy"))
    pizza.save()
    return pizza

def make_georges_pizza():
    pizza = Pizza(key="George")
    pepper = GreenPepper(key="some_green_peppers")
    pepperoni = Pepperoni(key="heavy_pepperoni")

    pizza.topped_with(pepper)
    pizza.topped_with(pepperoni)
    pepper.amount(ToppingAmount(key="light"))
    pepperoni.amount(ToppingAmount(key="heavy"))
    pizza.save()
    return pizza

def make_simons_pizza():
    pizza = Pizza(key="Simon")
    pepper = GreenPepper(key="some_green_peppers")
    pepperoni = Pepperoni(key="light_pepperoni")
    sausage = Sausage(key="light_sausage")

    pizza.topped_with(pepper)
    pizza.topped_with(pepperoni)
    pizza.topped_with(sausage)
    pepper.amount(ToppingAmount(key="medium"))
    pepperoni.amount(ToppingAmount(key="light"))
    sausage.amount(ToppingAmount(key="light"))
    pizza.save()
    return pizza

def get_pizzas_with_pepperoni():
    pizza = Pizza()
    pizza.topped_with(Pepperoni())
    for x in pizza.load():
        yield x

def get_pizzas_with_sausage():
    pizza = Pizza()
    pizza.topped_with(Sausage())
    for x in pizza.load():
        yield x

def get_pizzas_with_peppers():
    pizza = Pizza()
    pizza.topped_with(GreenPepper())
    for x in pizza.load():
        yield x

def list_pizzas():
    pizza = Pizza()
    for x in pizza.load():
        yield x

def print_results(l):
    print("\n".join("  "+str(x) for x in l))


def get_object_graph_legends(p):
    graph = p.get_defined_component()
    return Legends(p, graph)()

class ObjectGraphLegendsAssertionError(AssertionError):
    pass

class LegendsTests(object):
    def assertEqual(self, a, b):
        if not (a == b):
            raise AssertionError(str(a) + " != " + str(b))

    def assertObjectGraphLegends(self, p, s):
        graph = p.get_defined_component()
        res = Legends(p, graph)()

        if not (res == s):
            err = ObjectGraphLegendsAssertionError(str(res) + " != " + str(s))
            err.graph = graph
            raise err

    def assertNumberOfObjectGraphLegends(self, p, n):
        graph = p.get_defined_component()
        res = Legends(p, graph)()

        if not (len(res) == n):
            err = ObjectGraphLegendsAssertionError(str(len(res)) + " != " + str(n))
            err.graph = graph
            raise err

    def setup(self):
        Y.MappedClass.remap()

    def test_legends_1(self):
        p = Pizza(key="p")
        self.assertNumberOfObjectGraphLegends(p, 0)

    def test_legends_2(self):
        p = Pizza(key="p")
        p.relate("is_impressed_with", p)
        self.assertNumberOfObjectGraphLegends(p, 0)

    def test_legends_3(self):
        p = Pizza(key="p")
        q = Pizza(key="q")
        r = Pizza(key="r")
        p.relate("owes_money_to", q)
        r.relate("owes_money_to", q)
        self.assertObjectGraphLegends(p, set([q, p.rdf_type_object]))

    def test_legends_4(self):
        p = Pizza(key="p")
        q = Pizza(key="q")
        r = Pizza(key="r")
        p.relate("owes_money_to", q)
        q.relate("owes_money_to", r)
        r.relate("owes_money_to", p)
        self.assertNumberOfObjectGraphLegends(p, 0)

    def test_legends_5(self):
        p = Pizza(key="p")
        q = Pizza(key="q")
        r = Pizza(key="r")

        p.relate("owes_money_to", q)
        q.relate("owes_money_to", p)

        r.relate("owes_money_to", p)

        self.assertObjectGraphLegends(p, set([p.rdf_type_object]))

    def test_legends_6(self):
        p = Pizza(key="p")
        r = Pizza(key="r")

        p.relate("owes_money_to", p)
        r.relate("owes_money_to", p)

        self.assertObjectGraphLegends(p, set([p.rdf_type_object]))

    def test_legends_7(self):
        p = Pizza(key="p")
        r = Pizza(key="r")

        p.relate("owes_money_to", r)
        p.relate("owes_money_to", r)

        self.assertObjectGraphLegends(p, set([]))

    def test_legends_8(self):
        p = Pizza(key="p")
        r = Pizza(key="r")

        p.relate("owes_money_to", r)
        r.relate("owes_money_to", r)

        self.assertObjectGraphLegends(p, set([]))

    def test_legends_9(self):
        p = Pizza(key="p")
        r = Pizza(key="r")
        q = Pizza(key="q")

        p.relate("owes_money_to", q)
        q.relate("owes_money_to", r)
        p.relate("owes_money_to", r)

        self.assertObjectGraphLegends(p, set([]))

    def test_legends_10(self):
        p = Pizza(key="p")
        r = Pizza(key="r")
        s = Pizza(key="s")
        q = Pizza(key="q")

        p.relate("owes_money_to", q)
        q.relate("owes_money_to", r)
        p.relate("owes_money_to", s)
        s.relate("owes_money_to", r)
        s.relate("owes_money_to", s)

        self.assertObjectGraphLegends(p, set([]))

    @classmethod
    def run(cls):
        to = cls()
        tests = [t for t in dir(to) if t.startswith('test_')]
        for test in tests:
            try:
                to.setup()
                getattr(to, test)()
            except ObjectGraphLegendsAssertionError as e:
                print("failed", test, str(e))
                testfunc = getattr(to, test)
                if testfunc.__doc__ is not None:
                    print(testfunc.__doc__)

                print("graph:")
                print_graph(e.graph, hide_namespaces=True)

def heading(s):
    spaces = "="*(len(s)+10)
    print(spaces)
    print(" "*5+s)
    print(spaces)

def pizza_demo():
    heading("deleting all of the pizzas (;_;)")
    for x in Pizza().load():
        retract(x)

    mels = make_melanies_pizza()
    georges = make_georges_pizza()
    simons = make_simons_pizza()
    print_graph(mels.rdf, True)

    heading("all pizzas")
    print_results(list_pizzas())
    heading("pizzas with pepperoni")
    print_results(get_pizzas_with_pepperoni())
    heading("pizzas with sausage")
    print_results(get_pizzas_with_sausage())
    heading("pizzas with green peppers")
    print_results(get_pizzas_with_peppers())
    heading("Mel's pizza toppings")
    print_results(mels.topped_with())
    heading("eating all of the pizzas")

    for x in Pizza().load():
        retract(x)

    print_graph(mels.rdf, True)
    Y.disconnect()

def KillHeros_demo():
    p = Pizza(key="p")
    r = Pizza(key="r")
    s = Pizza(key="s")
    q = Pizza(key="q")

    p.relate("owes_money_to", q)
    q.relate("owes_money_to", r)
    p.relate("owes_money_to", s)
    s.relate("owes_money_to", r)
    s.relate("owes_money_to", s)


    Y.mapper.MappedClass.remap()

    graph = p.get_defined_component()

    print_graph(graph)
    #KillHeros(p, graph)()
    #print_graph(graph, True)

def render_graph_dot(g):
    import tempfile
    from subprocess import call
    from os import fork
    from sys import exit
    from rdflib.tools.rdf2dot import rdf2dot

    with tempfile.TemporaryFile() as f:
        rdf2dot(g, f)
        f.seek(0, 0) # start of stream
        g,gname = tempfile.mkstemp()
        call("dot -T png -o "+gname, stdin = f, shell=True)
        call("feh "+gname, shell = True)

def retract(o):
    o.retract_objectG()

if __name__ == '__main__':
    pizza_demo()

