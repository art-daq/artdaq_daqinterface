import json
import rc.web.control.models as models
from rc.util import eq, isin
from django.test.client import Client
from rc.control.component import Component
from rc.control.control import Control
from dbserv import DBServ


def test_state_view_creating_component():
    eq(0, models.Component.objects.count())
    c = Client()
    got = c.get("/control/components/")
    eq(200, got.status_code)
    eq([], json.loads(got.content))

    with models.cleanup_objects():
        with DBServ():
            with Control(web_host='localhost') as control:
                with Component(name="artdaq", rpc_port=6666) as artdaq:
                    control.wait_with_wakeup(
                        lambda: models.Component.objects.all())
                    eq("stopped", artdaq.state("artdaq"))

                    with Component(name="otherdaq", rpc_port=6667):
                        control.wait_with_wakeup(
                            lambda: len(models.Component.objects.all()) == 2)

                        # Check broken URLs
                        eq(404,
                           c.post("/control/components/foo/").status_code)
                        eq(404,
                           c.post("/control/components/artdaq/",
                                  {"action": "meditate"}).status_code)

                        # Start artdaq...
                        post = c.post("/control/components/artdaq/",
                                      {"action": "init"})
                        post = c.post("/control/components/artdaq/",
                                      {"action": "start"})
                        eq(post.status_code, 200)

                        control.wait_with_wakeup(
                            lambda: artdaq.state("artdaq") == "running")

                        # ... and wait for monitoring data to flow:
                        control.wait_with_wakeup(
                            lambda: models.Moni.objects.count(),
                            timeout=2)

                        # Fetch same via monitoring URLs:
                        xurl = c.get("/control/moni/artdaq/x/")
                        eq(200, xurl.status_code)
                        values = json.loads(xurl.content)
                        assert type(values) is list
                        assert values

                        # Fetch ALL monitoring as well:
                        moniurl = c.get("/control/moni/")
                        eq(200, moniurl.status_code)
                        isin("Service", moniurl.content)

                        # Stop artdaq and wait for appropriate state:
                        post = c.post("/control/components/artdaq/",
                                      {"action": "stop"})
                        eq(post.status_code, 200)

                        control.wait_with_wakeup(
                            lambda: artdaq.state("artdaq") == "ready")

                        # Terminate artdaq and wait for appropriate state:
                        post = c.post("/control/components/artdaq/",
                                      {"action": "terminate"})
                        eq(post.status_code, 200)

                        control.wait_with_wakeup(
                            lambda: artdaq.state("artdaq") == "stopped")
