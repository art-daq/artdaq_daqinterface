from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('rc.web.main.views',
                       url(r'^$', 'home', name='home'),
                       url(r'^environment/$', 'environment', name='environment'),
                       url(r'^larcryomoni/$', 'larcryomoni', name='larcryomoni'),
                       url(r'^lowvoltage/$', 'lowvoltage', name='lowvoltage'),
                       url(r'^highvoltage/$', 'highvoltage', name='highvoltage'),
                       url(r'^monihistory/$', 'monihistory', name='monihistory'),
                       url(r'^runhistory/$', 'runhistory', name='runhistory'),
                       url(r'^getupdates/$', 'getupdates'),
                       url(r'^components/$', 'compstates'),
                       url(r'^admin/', include(admin.site.urls)))

urlpatterns += patterns('rc.web.control.views',
                        url(r'^control/components/$', 'components'),
                        url(r'^control/components/(.+?)/$', 'component'),
                        url(r'^control/moni/(.+?)/(.+?)/$', 'moni'),
                        url(r'^control/moni/$', 'monis'),
                        url(r'^control/monilong/$', 'monislong'),
                        url(r'^control/recent20run/$', 'recent20run'),
                        url(r'^control/recent100run/$', 'recent100run'),
                        url(r'^control/getcurrentdbrun/$', 'getcurrentdbrun'),
                        url(r'^control/getcurrentrun/$', 'getcurrentrun'))


urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
