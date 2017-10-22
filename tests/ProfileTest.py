"""
Not actually tests, but benchmarks.
"""
from __future__ import print_function
from yarom import disconnect, connect, yarom_import


def setup():
    connect(conf='tests/test_default.conf')


def teardown():
    disconnect()


def test_do_create():
    DO = yarom_import('yarom.dataObject.DataObject')

    for i in range(10000):
        DO()
