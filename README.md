[![Build Status](https://travis-ci.org/mwatts15/YAROM.png?branch=master)](https://travis-ci.org/mwatts15/YAROM)

YAROM
=====

A unified, simple data access library for data & facts about *C. elegans* biology

Basic Usage
-----------

You may need to install some dependencies in order to use yarom. These can be installed with:

    python setup.py develop --user

To get started, you'll probably want to load in the database. If you cloned the repository from Github, then the database will be in the OpenWormData subdirectory. You can read it in
by doing 

```python
  >>> import yarom as P
  >>> P.connect('yarom/default.conf')

  >>> P.loadData('OpenWormData/out.n3', 'n3')

  >>> P.disconnect()

```

Then you can try out a few things:

```python
  # Set up
  >>> P.connect('yarom/default.conf')

  # Grabs the representation of the neuronal network
  >>> net = P.Worm().get_neuron_network()
  >>> list(net.aneuron('AVAL').type())
  ['interneuron']

  #show how many connections go out of AVAL
  >>> net.aneuron('AVAL').connection.count('pre')
  77

```
  
  
More examples
-------------
  
Returns information about individual neurons::

```python
  >>> list(net.aneuron('AVAL').name())
  ['AVAL']

  #list all known receptors
  >>> s = set(net.aneuron('AVAL').receptors())
  >>> s == set(['GLR-1', 'NMR-1', 'GLR-4', 'GLR-2', 'GGR-3', 'UNC-8', 'GLR-5', 'NMR-2'])
  True

  >>> list(net.aneuron('DD5').type())
  ['motor']
  >>> list(net.aneuron('PHAL').type())
  ['sensory']

  #show how many chemical synapses go in and out of AVAL
  >>> net.aneuron('AVAL').Syn_degree()
  74

```

Returns the list of all neurons::

```python
  >>> len(set(P.Neuron().load()))
  302

```

Returns the list of all muscles::

```python
  >>> 'MDL08' in (x.name.one() for x in P.Worm().muscles())
  True

```


Returns provenance information providing evidence about facts::

```python
  >>> ader = P.Neuron('ADER')
  >>> s = set(ader.receptors())
  >>> s == set(['ACR-16', 'TYRA-3', 'DOP-2', 'EXP-1'])
  True

  #look up what reference says this neuron has a receptor EXP-1
  >>> e = P.Evidence()
  >>> e.asserts(P.Neuron('ADER').receptor('EXP-1')) 
  asserts=receptor=EXP-1
  >>> list(e.doi())
  ['10.100.123/natneuro']

```

Add provenance information::

```python
  >>> e = P.Evidence(author='Sulston et al.', date='1983')
  >>> e.asserts(P.Neuron(name="AVDL").lineageName("AB alaaapalr"))
  asserts=lineageName=AB alaaapalr
  >>> e.save()

```

See what some evidence stated::
```python
  >>> e0 = P.Evidence(author='Sulston et al.', date='1983')
  >>> list(e0.asserts())
  [Neuron(name=AVDL,lineageName=AB alaaapalr)]

```

See what neurons express some receptor::
```python
  >>> n = P.Neuron()
  >>> n.receptor("TH")
  receptor=TH

  >>> s = set(x.name.one() for x in n.load()) 
  >>> s == set(['CEPVL','CEPVR','PDEL','PDER','CEPDR'])
  True

```

To get any object's possible values, use load()::
```python
  >>> list(P.Neuron().load())
  [
   ...
   Neuron(lineageName=, name= Neighbor(), Connection(), type=, receptor=, innexin=),
   Neuron(lineageName=, name= Neighbor(), Connection(), type=, receptor=VGluT, innexin=),
   Neuron(lineageName=, name= Neighbor(), Connection(), type=, receptor=EAT-4, innexin=),
   Neuron(lineageName=, name= Neighbor(), Connection(), type=, receptor=, innexin=),
   Neuron(lineageName=, name= Neighbor(), Connection(), type=, receptor=, innexin=),
   Neuron(lineageName=, name=Neighbor(), Connection(), type=, receptor=, innexin=),
   Neuron(lineageName=, name=Neighbor(), Connection(), type=, receptor=FLP-1, innexin=),
   Neuron(lineageName=, name=Neighbor(), Connection(), type=, receptor=, innexin=),
   ...
  ]
  # Properties are a little different
  >>> next(P.Neuron().receptor.load())
  receptor=INS-1;FLP-6;FLP-21;FLP-20;NLP-21...

```

Get direct access to the RDFLib graph::
```python
 # we get it from Worm, but any object will do
 >>> Worm().rdf.query(...)

```

Returns the c. elegans connectome represented as a [NetworkX](http://networkx.github.io/documentation/latest/) graph::

```python
  >>> net.as_networkx()
  <networkx.classes.digraph.DiGraph object at 0x10f28bc10>

```

More examples can be found [here](http://pyopenworm.readthedocs.org/en/alpha0.5/making_dataObjects.html) and [here](https://github.com/mwatts15/YAROM/tree/alpha0.5/examples).


Ease of use
-----------

This library should be easy to use and easy to install, to make it most accessible.  Python beginners should be able to get information out about c. elegans from this library.  Sytactical constructs in this library should be intuitive and easy to understand what they will return within the knowledge domain of c. elegans, 
rather than in the programming domain of its underlying technologies.  Values that are returned should be easily interpretable and easy to read.
Wherever possible, pure-python libraries or those with few compilation requirements, rather than those that create extra dependencies on external native libraries are used.

Installation
------------

See INSTALL.md
