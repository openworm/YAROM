"""
Not actually tests, but benchmarks.
"""
from __future__ import print_function
import yarom as Y
from yarom import disconnect, connect


def setup():
    connect(conf='tests/test_default.conf')


def teardown():
    disconnect()


def test_do_create():
    for i in range(10000):
        Y.DataObject()
