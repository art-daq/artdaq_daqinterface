import datetime
import rc.web.control.models as models
import json
from django.http import HttpResponse as hr
from rc.web.util.html import (div, inp, html, head, title, link, script,
                              body, h1, strong, p, span, code, br, a, target)


def compstates(request):
    return hr(div(*[fmt_comp(c) for c in models.Component.objects.all()]))


def fmt_comp(comp):
    return div(inp(type="button", disabled="disabled",
                   klass="state_%s statebutton" % comp.state.lower(),
                   value=comp.name),
               klass="singlecomp")


def home(request):
    components = models.Component.objects.all()
    return hr(
        html(head(title("DUNE Run Control"),
                  link(rel="stylesheet", href="/static/site.css"),
                  link(href="http://fonts.googleapis.com/css?family=Pacifico",
                       rel="stylesheet", type="text/css"),
                  script(src="http://cdnjs.cloudflare.com/ajax/libs/"
                             "d3/3.0.1/d3.v3.min.js"),
                  script(src="http://cdnjs.cloudflare.com/ajax/libs/"
                             "underscore.js/1.5.1/underscore-min.js"),
                  script(src="http://code.jquery.com/jquery-1.10.2.min.js"),
                  script(src="/static/jquery.jclock.js"),
                  script(src="/static/jclock-action.js"),
                  script(src="/static/highstock.js"),
                  script(src="/static/highcharts-more.js"),
                  script(src="/static/exporting.js"),
                  script(src="/static/site.js")),
             body(div(h1("DUNE ",
                         span("Run Control"),
                         span("[35 ton prototype]", klass="parenthetic"),
                         span(id='jclock', klass="livebar", style="margin:20px 20px"),
                         span(id='jclock2', klass="livebar", style="margin:20px 20px")),
                      id="header"),
                  div(
                      strong(a("APA Low Voltage", href="/lbnerc/lowvoltage",
                               style="margin:20px 20px")),
                      strong(a("APA High Voltage", href="/lbnerc/highvoltage",
                               style="margin:20px 20px")),
                      strong(a("Environmental", href="/lbnerc/environment",
                               style="margin:20px 20px")),
                      strong(a("Argon Monitoring", href="/lbnerc/larcryomoni",
                               style="margin:20px 20px")),
                      strong(a("Logbook", href="http://dbweb5.fnal.gov:8080/ECL/lbne_35t/E/index",
                               target="_blank", style="margin:20px 20px")),
                      strong(a("Shift Guide",
                               href="https://cdcvs.fnal.gov/redmine/projects/35ton/wiki/Instructions_for_Shifters",
                               target="_blank", style="margin:20px 20px")),
                      strong(a("DAQ Ganglia",
                               href="http://lbne35t-gateway01.fnal.gov/ganglia_1.html",
                               target="_blank", style="margin:20px 20px")),
                      id="nav"),
                  div(
                      div(strong("**DAQ Status summary**"),br(),br(),
                          span(" RCReporter current Run number: ",span(id="getcurrentrun")),
                          span(id="getcurrentdbrun"),
                       ),
                      id="summary"),
                  div(div(strong("COMPONENTS"),
                          # *[fmt_comp(c) for c in components],
                          div(id="comp-states"),
                          klass="column-content", id="sysgrid"),
                      div(klass="spacer"),
                      div(strong(a("RECENT DATA", href="/lbnerc/monihistory")),
                          div(id="moni-values"),
                          klass="column-content", id="monis"),
                      div(klass="spacer"),
                      div(p(strong("Graphs")),
                          p(id="graph-h1", klass="plot",
                            style="height: 250px; width: 500px"),
                          br(),
                          p(id="graph-h2", klass="plot",
                            style="height: 250px; width: 500px"),
                          klass="column-content", id="graphs"),
                      id="container"),
                  div(strong(a("RECENT RUNS", href="/lbnerc/runhistory")),
                      span(id="recent20run"),
                      klass="column-content"),
                  div(p("""
                        Status buttons for each component are
                        updated in realtime to reflect their
                        state. State changes, run information 
                        and monitoring information are visible 
                        immediately.
                        """),
                      p("""
                        If you have issues or suggestions, please 
                        let me know:  blaufuss (at) umd.edu
                      """)))))


def getupdates(request):
    return hr(json.dumps([str(datetime.datetime.utcnow())]))

def lowvoltage(request):
    return hr(
        html(head(title("Low Voltage"),
                  link(rel="stylesheet", href="/static/site.css"),
                  script(src="http://cdnjs.cloudflare.com/ajax/libs/"
                         "d3/3.0.1/d3.v3.min.js"),
                  script(src="http://cdnjs.cloudflare.com/ajax/libs/"
                         "underscore.js/1.5.1/underscore-min.js"),
                  script(src="http://code.jquery.com/jquery-1.10.2.min.js"),
                  script(src="/static/jquery.jclock.js"),
                  script(src="/static/jclock-action.js"),
                  script(src="/static/highstock.js"),
                  script(src="/static/highcharts-more.js"),
                  script(src="/static/exporting.js"),
                  script(src="/static/lowvoltage.js")),
             body(div(h1("APA Low Voltage ",
                         span(id='jclock', klass="livebar", style="margin:20px 20px"),
                         span(id='jclock2', klass="livebar", style="margin:20px 20px")),
                  id="header")),
             p(strong(a("DUNE RC Main Page", href="/lbnerc/"))),
             p(""" APA low voltage and currents. """),
             p(""" Note: graphs do not automatically updated due to the large number of plots and lines.  Please reload as needed. """),
             p(strong("""Graphs""")),
             div(
                 p(id="graph1", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
                 p(id="graph2", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
             ),
             div(
                 p(id="graph3", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
                 p(id="graph4", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
             ),
             div(
                 p(id="graph5", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
                 p(id="graph6", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
             ),
             div(
                 p(id="graph7", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
                 p(id="graph8", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
             ),
             div(
                 p(id="graph9", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
                 p(id="graph10", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
             ),
         ))


def environment(request):
    return hr(
        html(head(title("DUNE 35t Environment"),
                  link(rel="stylesheet", href="/static/site.css"),
                  script(src="http://cdnjs.cloudflare.com/ajax/libs/"
                         "d3/3.0.1/d3.v3.min.js"),
                  script(src="http://cdnjs.cloudflare.com/ajax/libs/"
                         "underscore.js/1.5.1/underscore-min.js"),
                  script(src="http://code.jquery.com/jquery-1.10.2.min.js"),
                  script(src="/static/jquery.jclock.js"),
                  script(src="/static/jclock-action.js"),
                  script(src="/static/highstock.js"),
                  script(src="/static/highcharts-more.js"),
                  script(src="/static/exporting.js"),
                  script(src="/static/environment.js")),
             body(div(h1("DUNE 35t Environment Monitoring ",
                         span(id='jclock', klass="livebar", style="margin:20px 20px"),
                         span(id='jclock2', klass="livebar", style="margin:20px 20px")),
                  id="header")),
             p(strong(a("DUNE RC Main Page", href="/lbnerc/"))),
             p(""" DUNE 35t Environmental Monitoring. """),
             p(strong("""Graphs""")),
             div(
                 p(id="graph1", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
                 p(id="graph2", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
             ),
             div(
                 p(id="graph5", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
                 p(id="graph2a", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
             ),
             div(
                 p(id="graph0", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
                 p(id="graph0a", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
             ),
             div(
                 p(id="graph3", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
                 p(id="graph4", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
             ),
         ))

def larcryomoni(request):
    return hr(
        html(head(title("DUNE 35t Liquid Argon Monitoring"),
                  link(rel="stylesheet", href="/static/site.css"),
                  script(src="http://cdnjs.cloudflare.com/ajax/libs/"
                         "d3/3.0.1/d3.v3.min.js"),
                  script(src="http://cdnjs.cloudflare.com/ajax/libs/"
                         "underscore.js/1.5.1/underscore-min.js"),
                  script(src="http://code.jquery.com/jquery-1.10.2.min.js"),
                  script(src="/static/jquery.jclock.js"),
                  script(src="/static/jclock-action.js"),
                  script(src="/static/highstock.js"),
                  script(src="/static/highcharts-more.js"),
                  script(src="/static/exporting.js"),
                  script(src="/static/larcryo.js")),
             body(div(h1("DUNE 35t Liquid Argon Monitoring ",
                         span(id='jclock', klass="livebar", style="margin:20px 20px"),
                         span(id='jclock2', klass="livebar", style="margin:20px 20px")),
                  id="header")),
             p(strong(a("DUNE RC Main Page", href="/lbnerc/"))),
             p(""" DUNE 35t Liquid Argon Monitoring. """),
             p(strong("""Graphs""")),
             div(
                 p(id="largraph0", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
                 p(id="largraph1", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
             ),
             div(
                 p(id="largraph2", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
                 p(id="graph5", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
             ),
             div(
                 p(id="largraph3", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
                 p(id="largraph4", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
             ),

         ))


def highvoltage(request):
    return hr(
        html(head(title("APA Bias and Drift Voltages"),
                  link(rel="stylesheet", href="/static/site.css"),
                  script(src="http://cdnjs.cloudflare.com/ajax/libs/"
                         "d3/3.0.1/d3.v3.min.js"),
                  script(src="http://cdnjs.cloudflare.com/ajax/libs/"
                         "underscore.js/1.5.1/underscore-min.js"),
                  script(src="http://code.jquery.com/jquery-1.10.2.min.js"),
                  script(src="/static/jquery.jclock.js"),
                  script(src="/static/jclock-action.js"),
                  script(src="/static/highstock.js"),
                  script(src="/static/highcharts-more.js"),
                  script(src="/static/exporting.js"),
                  script(src="/static/highvoltage.js")),
             body(div(h1("APA Bias and Drift field High Voltages ",
                         span(id='jclock', klass="livebar", style="margin:20px 20px"),
                         span(id='jclock2', klass="livebar", style="margin:20px 20px")),
                      id="header")),
             p(strong(a("DUNE RC Main Page", href="/lbnerc/"))),
             p(""" APA high voltage and currents. """),
             p(""" Note: graphs do not automatically updated due to the large number of plots and lines.  Please reload as needed. """),
             p(strong("""Graphs""")),
             div(
                 p(id="graph0", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
                 p(id="graph0a", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
             ),
             div(
                 p(id="graph1", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
                 p(id="graph2", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
             ),
             div(
                 p(id="graph3", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
                 p(id="graph4", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
             ),
             div(
                 p(id="graph5", klass="plot",
                  style="height: 300px; width: 500px; margin:20px 50px"),
                 p(id="graph6", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
             ),
             div(
                 p(id="graph7", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
                 p(id="graph8", klass="plot",
                   style="height: 300px; width: 500px; margin:20px 50px"),
             ),
         ))

def monihistory(request):
    return hr(
        html(head(title("Monitoring messages"),
                  link(rel="stylesheet", href="/static/site.css"),
                  script(src="http://cdnjs.cloudflare.com/ajax/libs/"
                         "d3/3.0.1/d3.v3.min.js"),
                  script(src="http://cdnjs.cloudflare.com/ajax/libs/"
                         "underscore.js/1.5.1/underscore-min.js"),
                  script(src="http://code.jquery.com/jquery-1.10.2.min.js"),
                  script(src="/static/jquery.jclock.js"),
                  script(src="/static/jclock-action.js"),
                  script(src="/static/highstock.js"),
                  script(src="/static/highcharts-more.js"),
                  script(src="/static/history.js"),
                  script(src="/static/exporting.js")),
             body(div(h1("Monitoring message history ",
                         span(id='jclock', klass="livebar", style="margin:20px 20px"),
                         span(id='jclock2', klass="livebar", style="margin:20px 20px")),
                      id="header")),
             p(strong(a("DUNE RC Main Page", href="/lbnerc/"))),
             p(""" Last 500 monitoring messages """),
             div(strong("RECENT DATA"),
                 div(id="moni-values-long"),
                 klass="column-content", id="monislong"),
         ))

def runhistory(request):
    return hr(
        html(head(title("Recent Run History"),
                  link(rel="stylesheet", href="/static/site.css"),
                  script(src="http://cdnjs.cloudflare.com/ajax/libs/"
                         "d3/3.0.1/d3.v3.min.js"),
                  script(src="http://cdnjs.cloudflare.com/ajax/libs/"
                         "underscore.js/1.5.1/underscore-min.js"),
                  script(src="http://code.jquery.com/jquery-1.10.2.min.js"),
                  script(src="/static/jquery.jclock.js"),
                  script(src="/static/jclock-action.js"),
                  script(src="/static/highstock.js"),
                  script(src="/static/highcharts-more.js"),
                  script(src="/static/runhistory.js"),
                  script(src="/static/exporting.js")),
             body(div(h1("Run History ",
                         span(id='jclock', klass="livebar", style="margin:20px 20px"),
                         span(id='jclock2', klass="livebar", style="margin:20px 20px")),
                      id="header")),
             p(strong(a("DUNE RC Main Page", href="/lbnerc/"))),
             p(""" Last 100 Runs """),
             div(strong("RECENT RUNS"),
                 div(id="recent100run"),
                 klass="column-content", id="recent100run"),
         ))
