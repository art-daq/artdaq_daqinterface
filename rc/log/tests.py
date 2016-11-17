from rc.util import eq
from rc.log import Logger


def test_single_insert():
    l = Logger()
    l.log("hello world")
    eq(len(l.msgs), 1)


def test_many_inserts_with_circular_buffer():
    l = Logger()
    [l.log("message %d" % i) for i in range(1002)]
    eq(len(l.msgs), 1000)
    eq(l.msgs[-1]["msg"], "message 1001")
