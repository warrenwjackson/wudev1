from django.conf.urls import patterns, include, url
import settings
from django.contrib import admin
import foundation 
import notifications
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
   
    url(r'^test/$', 'resv.views.test_view', name='test_view'), 
    url(r'^testgame/$', 'resv.views.test_view_game', name='test_view_game'), 
    url(r'^resv/$', 'resv.views.resv', name='resv'),
    url(r'^resv/(?P<resv_id>\w+)/$', 'resv.views.resv', name='resv'),
    url(r'^search/$', 'resv.views.search', name='search'),
    url(r'^review/(?P<resv_id>\w+)$', 'resv.views.review', name='review'),
    url(r'^confirm/(?P<resv_id>\w+)$', 'resv.views.confirm', name='confirm'),
    url(r'^cancel/(?P<obj_type>\S+)/(?P<obj_id>\w+)$', 'resv.views.cancel', name='cancel'),
    url(r'^home/$', 'resv.views.home', name='home'),
    url(r'^ranch/patrol/(?P<ranch_id>\w+)$', 'resv.views.patrol', name='patrol'),
    url(r'^ranch/patrol/$', 'resv.views.patrol', name='patrol'),
    url(r'^ranch/admin/(?P<ranch_id>\w+)$', 'resv.views.ranch_admin', name='ranch_admin'),
    
    url(r'^segment/create/$', 'resv.views.segment_POST'),
    url(r'^segment/person/add$', 'resv.views.segment_person_ADD'),
    url(r'^segment/person/drop$', 'resv.views.segment_person_DELETE'),
    url(r'^segment/person/swap$', 'resv.views.segment_person_SWAP'),
    url(r'^segment/(?P<seg_id>\d+)/json/$', 'resv.views.segment_GET'),
    url(r'^segment/(?P<seg_id>\d+)/game/$', 'resv.views.segment_game'),
    url(r'^segment/(?P<seg_id>\d+)/standby/save/$', 'resv.views.standby_save'),
    url(r'^segment/(?P<seg_id>\d+)/person/addlist/$', 'resv.views.segment_person_ADDLIST'),
    url(r'^segment/(?P<seg_id>\d+)/person/add/$', 'resv.views.segment_person_ADD'),
    url(r'^segment/(?P<seg_id>\d+)/datesanddog/$', 'resv.views.segment_dates_and_dog'),

    #url(r'^segment/open/(?P<seg_id>\w+)$', 'resv.views.segment_open'),
    #url(r'^segment/save/', 'resv.views.segment_save'),

    url(r'^login/', 'resv.views.loginview'),
    url(r'^auth/', 'resv.views.auth_and_login'),
    url(r'^signup/', 'resv.views.sign_up_in'),
    
    url('^inbox/notifications/', include(notifications.urls)),

    url(r'^maps/$', 'resv.views.maps', name='maps'),
    url(r'^reports/$', 'resv.views.reports', name='reports'),
    url(r'^admin/', include(admin.site.urls)),
 	url(r'^$', 'resv.views.mktg', name='mktg'),
    url(r'^foundation/', include('foundation.urls')),
    url(r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.STATIC_ROOT}),
)


