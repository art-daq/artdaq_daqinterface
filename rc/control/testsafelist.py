from rc.util import eq
from safelist import SafeList


def test_safelist():
    eq(len(SafeList()), 0)
    eq(len(SafeList([])), 0)
    l = SafeList(["Apple", 5, None])
    eq(len(l), 3)
    l.append("Orange")
    eq(len(l), 4)

    selector = lambda x: type(x) is str and x.startswith("A")
    eq(l.find(selector), ["Apple"])

    eq(len(l.remove(selector)), 3)

    eq(l.map(str), ["5", "None", "Orange"])

    eq(l.list(), [5, None, "Orange"])

    l.add_or_update(lambda x: type(x) is str, "Navy Blue")
    eq(l.list(), [5, None, "Navy Blue"])
