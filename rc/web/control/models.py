import contextlib
from django.db import models


class Component(models.Model):
    name = models.CharField(max_length=80)
    state = models.CharField(max_length=30, default="STOPPED")


class Moni(models.Model):
    service = models.TextField()
    value = models.FloatField()
    varname = models.TextField()
    t = models.DateTimeField()

class Runs(models.Model):
    run = models.IntegerField()
    config = models.TextField()
    runtype = models.TextField()
    components = models.TextField()
    start = models.DateTimeField()
    stop = models.DateTimeField(null=True)

@contextlib.contextmanager
def cleanup_objects():
    yield
    for klass in [Component, Moni]:
        klass.objects.all().delete()
