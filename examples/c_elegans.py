import yarom as Y

class Worm(Y.DataObject):
    datatypeProperties = [{'name':'scientific_name', 'multiple':False}]
    objectProperties = ['neuron_network', 'muscle']

    def defined_augment(self):
        if len(self.scientific_name.values) < 1:
            return False
        return True

    def identifier_augment(self):
        return self.make_identifier_from_properties('scientific_name')

class Evidence(Y.DataObject):
    _ = ['title', 'asserts']

    def _ident_data(self):
        return [self.title.values]

    def defined_augment(self):
        for p in self._ident_data():
            if len(p) < 1:
                return False
        return True

    def identifier_augment(self):
        return self.make_identifier_from_properties('title')

class Cell(Y.DataObject):
    """
    A biological cell.

    All cells with the same name are considered to be the same object.

    Parameters
    -----------
    name : string
        The name of the cell
    lineageName : string
        The lineageName of the cell
        Example::

            >>> c = Cell(name="ADAL")
            >>> c.lineageName() # Returns ["AB plapaaaapp"]

    Attributes
    ----------
    name : DatatypeProperty
        The 'adult' name of the cell typically used by biologists when discussing C. elegans
    lineageName : DatatypeProperty
        The lineageName of the cell

    description : DatatypeProperty
        A description of the cell
    divisionVolume : DatatypeProperty
        When called with no argument, return the volume of the cell at division
        during development.

        When called with an argument, set the volume of the cell at division
        Example::

            >>> v = Quantity("600","(um)^3")
            >>> c = Cell(lineageName="AB plapaaaap")
            >>> c.divisionVolume(v)
    """
    datatypeProperties = [ 'lineageName',
            {'name':'name', 'multiple':False},
            'divisionVolume',
            'description' ]

    def __init__(self, name=False, **kwargs):
        if name:
            kwargs['name'] = name
        Y.DataObject.__init__(self, **kwargs)

    def _ident_data(self):
        return [self.name.values]

    def defined_augment(self):
        for p in self._ident_data():
            if len(p) < 1:
                return False
        return True

    def identifier_augment(self):
        return self.make_identifier_direct(str(self.name.values[0]))


class Neuron(Cell):
    """
    A neuron.

    See what neurons express some neuropeptide

    Example::

        # Grabs the representation of the neuronal network
        >>> net = P.Worm().get_neuron_network()

        # Grab a specific neuron
        >>> aval = net.aneuron('AVAL')

        >>> aval.type()
        set([u'interneuron'])

        #show how many connections go out of AVAL
        >>> aval.connection.count('pre')
        77

        >>> aval.name()
        u'AVAL'

        #list all known receptors
        >>> sorted(aval.receptors())
        [u'GGR-3', u'GLR-1', u'GLR-2', u'GLR-4', u'GLR-5', u'NMR-1', u'NMR-2', u'UNC-8']

        #show how many chemical synapses go in and out of AVAL
        >>> aval.Syn_degree()
        90

    Parameters
    ----------
    name : string
        The name of the neuron.

    Attributes
    ----------
    type : DatatypeProperty
        The neuron type (i.e., sensory, interneuron, motor)
    receptor : DatatypeProperty
        The receptor types associated with this neuron
    innexin : DatatypeProperty
        Innexin types associated with this neuron
    neurotransmitter : DatatypeProperty
        Neurotransmitters associated with this neuron
    neuropeptide : DatatypeProperty
        Name of the gene corresponding to the neuropeptide produced by this neuron
    neighbor : Property
        Get neurons connected to this neuron if called with no arguments, or
        with arguments, state that neuronName is a neighbor of this Neuron
    connection : Property
        Get a set of Connection objects describing chemical synapses or gap
        junctions between this neuron and others

    """
    datatypeProperties = [
        "type",
        "receptor",
        "innexin",
        "neurotransmitter",
        "neuropeptide"]
    objectProperties = [
            "neighbor",
            "connection"
            ]

    def __init__(self, *args, **kwargs):

        Cell.__init__(self, *args, **kwargs)

class SynapseType:
    Chemical = "send"
    GapJunction = "gapJunction"

class Connection(Y.DataObject):
    """Connection between neurons

    Parameters
    ----------
    pre_cell : string or Neuron, optional
        The pre-synaptic cell
    post_cell : string or Neuron, optional
        The post-synaptic cell
    number : int, optional
        The weight of the connection
    syntype : {'gapJunction', 'send'}, optional
        The kind of synaptic connection. 'gapJunction' indicates
        a gap junction and 'send' a chemical synapse
    synclass : string, optional
        The kind of Neurotransmitter (if any) sent between `pre_cell` and `post_cell`
    """
    datatypeProperties = ['syntype',
                'synclass',
                'number']
    objectProperties = ['pre_cell', 'post_cell']
    def __init__(self,**kwargs):
        Y.DataObject.__init__(self,**kwargs)


        pre_cell = kwargs.get('pre_cell', None)
        post_cell = kwargs('post_cell', None)
        number = kwargs('number', None)

        if isinstance(pre_cell, Y.Neuron):
            self.pre_cell(pre_cell)
        elif pre_cell is not None:
            self.pre_cell(Y.Neuron(name=pre_cell, conf=self.conf))

        if (isinstance(post_cell, Y.Neuron)):
            self.post_cell(post_cell)
        elif post_cell is not None:
            self.post_cell(Y.Neuron(name=post_cell, conf=self.conf))

        if isinstance(number,int):
            self.number(int(number))
        elif number is not None:
            raise Exception("Connection number must be an int, given %s" % number)

        if isinstance(syntype,basestring):
            syntype=syntype.lower()
            if syntype in ('send', SynapseType.Chemical):
                self.syntype(SynapseType.Chemical)
            elif syntype in ('gapjunction', SynapseType.GapJunction):
                self.syntype(SynapseType.GapJunction)
        if isinstance(synclass,basestring):
            self.synclass(synclass)

class Muscle(Cell):
    """A single muscle cell.

    See what neurons innervate a muscle:

    Example::

        >>> mdr21 = P.Muscle('MDR21')
        >>> innervates_mdr21 = mdr21.innervatedBy()
        >>> len(innervates_mdr21)
        4

    Attributes
    ----------
    neurons : ObjectProperty
        Neurons synapsing with this muscle
    receptors : DatatypeProperty
        Get a list of receptors for this muscle if called with no arguments,
        or state that this muscle has the given receptor type if called with
        an argument
    """
    objectProperties = ['innervatedBy']
    datatypeProperties = ['receptor']

    def __init__(self, name=False, **kwargs):
        Cell.__init__(self, name=name, **kwargs)

class Network(Y.DataObject):
    """A network of neurons

    Attributes
    -----------
    neuron
        Representation of neurons in the network
    synapse
        Representation of synapses in the network
    """
    objectProperties = ['synapse', 'neuron']

    def __init__(self, **kwargs):
        Y.DataObject.__init__(self,**kwargs)
