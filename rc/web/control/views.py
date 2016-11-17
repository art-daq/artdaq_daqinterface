import json
import models
import time
from rc.io.rpc import rpc_client
from django.http import HttpResponse, Http404
from rc.web.util.html import table, th, tr, td, p, span, br, a


def components(request):
    comps = models.Component.objects.all()
    return HttpResponse(json.dumps([c.name for c in comps]))


def component(request, compname):
    if request.method != 'POST':
        raise Http404
    try:
        models.Component.objects.get(name=compname)
        action = request.POST.get("action", None)
    except models.Component.DoesNotExist:
        raise Http404
    if action not in ['start', 'stop', 'init', 'pause', 'resume', 'terminate']:
        raise Http404

    if action == 'start':
        with rpc_client() as c:
            c.start([compname])
        return HttpResponse('OK')
    elif action == 'stop':
        with rpc_client() as c:
            c.stop([compname])
        return HttpResponse('OK')
    elif action == 'pause':
        with rpc_client() as c:
            c.pause([compname])
        return HttpResponse('OK')
    elif action == 'resume':
        with rpc_client() as c:
            c.resume([compname])
        return HttpResponse('OK')
    elif action == 'init':
        with rpc_client() as c:
            c.initialize([compname])
        return HttpResponse('OK')
    elif action == 'terminate':
        with rpc_client() as c:
            c.terminate([compname])
        return HttpResponse('OK')


# FIXME: moni views should go in a different app? Or maybe 'control'
# is the wrong name?
def moni(request, service, varname):
    ms = models.Moni.objects.filter(
        service=service,
        varname=varname).order_by('-t')[:100].values_list('t', 'value')
    return HttpResponse(json.dumps([(int(time.mktime(t.timetuple()) * 1000), v)
                                    for (t, v) in reversed(ms)]))


def monis(request):
    ms = models.Moni.objects.order_by('-t')[:20].values_list(
        'service', 'varname', 'value', 't')
    return HttpResponse(table(tr(th("Service"),
                                 th("Variable"),
                                 th("Time"),
                                 th("Value")),
                              *[tr(td(s),
                                   td(vn),
                                   td(str(t)),
                                   td(str(val)))
                                for (s, vn, val, t) in ms]))


def monislong(request):
    ms = models.Moni.objects.order_by('-t')[:500].values_list(
        'service', 'varname', 'value', 't')
    return HttpResponse(table(tr(th("Service"),
                                 th("Variable"),
                                 th("Time"),
                                 th("Value")),
                              *[tr(td(s),
                                   td(vn),
                                   td(str(t)),
                                   td(str(val)))
                                for (s, vn, val, t) in ms]))

def getcurrentrun(request):
    currentrun = int(models.Moni.objects.filter(service="RCReporter",
                                            varname="Data.Logger.Run.Number").latest('t').value)
    return HttpResponse(currentrun)

def getcurrentdbrun(request):
    ms = models.Runs.objects.latest('start')
    run= str(ms.run)
    print run
    return HttpResponse(p(span("DB Latest Run Info Run: %s " % str(ms.run)),br(),
                          span("Configuration: %s" % ms.config),br(),        
                          span("Run Type: %s" % ms.runtype),br(),
                          span("DAQ Components: %s" % ms.components),br(),
                          span("Start time: %s," % str(ms.start)),br(),
                          span("Stop Time: %s" % str(ms.stop))))

                          
def recent20run(request):
    ms = models.Runs.objects.order_by('-start')[:20].values_list(
        'run', 'config', 'runtype', 'components', 'start', 'stop')
    return HttpResponse(table(tr(th("Run Number"),
                                 th("Config Name"),
                                 th("Run Type"),
                                 th("Components"),
                                 th("Start Time"),
                                 th("Stop Time"),
                                 th("Monitoring")),
                              *[tr(td(str(run)),
                                   td(cfg),
                                   td(rt),
                                   td(comp),
                                   td(str(start)),
                                   td(str(stop)),
                                   td(a("DQMPlots",
                                     href="http://lbne-dqm.fnal.gov/OnlineMonitoring/Run%sSubrun1/"% str(run),
                                     target="_blank")))
                                for (run, cfg, rt, comp, start, stop) in ms]))


def recent100run(request):
    ms = models.Runs.objects.order_by('-start')[:100].values_list(
        'run', 'config', 'runtype', 'components', 'start', 'stop')
    return HttpResponse(table(tr(th("Run Number"),
                                 th("Config Name"),
                                 th("Run Type"),
                                 th("Components"),
                                 th("Start Time"),
                                 th("Stop Time"),
                                 th("Monitoring")),
                              *[tr(td(str(run)),
                                   td(cfg),
                                   td(rt),
                                   td(comp),
                                   td(str(start)),
                                   td(str(stop)),
                                   td(a("DQMPlots",
                                     href="http://lbne-dqm.fnal.gov/OnlineMonitoring/Run%sSubrun1/"% str(run),
                                     target="_blank")))
                                for (run, cfg, rt, comp, start, stop) in ms]))
