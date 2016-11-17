from rc.util import eq
from django.test.client import Client


def test_slash():
    c = Client()
    eq(200, c.get("/").status_code)
    eq(200, c.post("/getupdates/").status_code)
