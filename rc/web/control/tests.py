from rc.util import eq
import rc.web.control.models as models


def test_component_model():
    with models.cleanup_objects():
        c = models.Component(name="artdaq")
        c.save()
        eq(c.state, "STOPPED")
        c.state = "RUNNING"
        c.save()
        eq(c.state, "RUNNING")
