import datetime as dt
import json
from django.shortcuts import render, render_to_response, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext, loader
from django.core.exceptions import ObjectDoesNotExist
from django.core.context_processors import csrf
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q

from django_fsm import TransitionNotAllowed

from resv import models as m
from resv import forms

def test_view(request):
    return render(request, 'test.html')
def test_view_game(request):
    return render(request, 'test_game.html')
    
@login_required(login_url='/login/')
def home(request):
    #resv_future = request.user
    print request.user
    print request.user.pk
    # print request.user.resv
    resv_future = request.user.get_future_blocking_resv()
    resv_past = request.user.get_past_blocking_resv()
    resv_family = request.user.family.get_future_blocking_resv()
    context = RequestContext(request, {
        'resv_future':resv_future,
        'resv_past':resv_past,
        'resv_family':resv_family
    })
    context.update(csrf(request))
    return render(request, 'resv_home.html', context_instance=context)

def maps(request):
	pass

def filter_optional_form_field(GET, queryset, form_field, model_field):
    if GET.has_key(form_field) and GET[form_field] not in ('',[]):
        print 'about to filter'
        print {model_field:GET[form_field] }
        return queryset.filter(**{model_field:GET[form_field] })
    return queryset



@login_required(login_url='/login/')
def segment_GET(request, seg_id):
    print 'segment GET'
    seg = m.ResvSegment.objects.get(pk=seg_id)
    json_data = json.dumps({'seg':seg.get_json(), 'error':''})
    return HttpResponse(json_data)

@login_required(login_url='/login/')
def segment_POST(request):
    print 'segment POST'
    p = request.POST
    seg = m.ResvSegment()
    error = seg.create(p['resv'], p['resv_blind'], p['owner'], dt.datetime.strptime(p['start_date'], '%Y-%m-%d').date(), 'Pending')
    print 'created'
    json_data = json.dumps({'seg_id':seg.id, 'resv_id':seg.resv.id, 'error':error})
    print 'converted to json'
    return HttpResponse(json_data)

@login_required(login_url='/login/')
def segment_game(request, seg_id):
    print 'segment game',
    if request.method == 'GET':
        print 'GET'
        seg = m.ResvSegment.objects.get(pk=seg_id)
        print 'Found seg'
        print seg
        game_list = seg.blind.get_game_list(seg.start_date)
        print 'Has game list', game_list
        json_data = json.dumps({'seg_id':seg_id, 'game_list':game_list,'error':''})
        print 'Returning'
        return HttpResponse(json_data)    
    if request.method == 'POST':
        print 'POST'
        seg = m.ResvSegment.objects.get(pk=seg_id)
        seg.game = m.Game.objects.get(pk=request.POST['game_id'])
        seg.save()
        json_data = json.dumps({'seg_id':seg_id, 'error':''})
        return HttpResponse(json_data)

@login_required(login_url='/login/')
def segment_person_ADDLIST(request, seg_id):
    seg = m.ResvSegment.objects.get(pk=seg_id)
    person_list = [[p.id,p.get_long_name()] for p in seg.resv.owner.get_delegated_to()]
    json_data = json.dumps({'seg_id':seg.id, 'person_list':person_list, 'error':''})
    return HttpResponse(json_data)



@login_required(login_url='/login/')
def segment_person_ADD(request, seg_id, force=False):
    print 'segment/person/add'
    p = request.POST
    seg = m.ResvSegment.objects.get(pk=seg_id)

    #The below should check for capacity, and other rules
    print p
    seg.add_person(is_hunting=p['is_hunting'], person_id=p['person_id'], force=force)

    person = m.Person.objects.get(pk=p['person_id'])
    json_data = json.dumps({'seg_id':seg.id, 'person_id':person.id, 'person_name':person.get_long_name(), 'error':''})
    return HttpResponse(json_data)
    
@login_required(login_url='/login/')
def segment_person_DELETE(request):
    print 'segment/person/delete'
    p = request.POST
    seg = m.ResvSegment.objects.get(pk=p['seg_id'])
    seg.remove_person(person_id=p['person_id'])
    json_data = json.dumps({'seg_id':seg.id, 'person_id':p['person_id'], 'error':''})
    return HttpResponse(json_data)
    
@login_required(login_url='/login/')
def segment_person_SWAP(request): #This is a dangerous option.  Think twice about enabling due to abuse. 
    print 'segment/person/SWAP'
    p = request.POST
    seg = m.ResvSegment.objects.get(pk=p['seg_id'])

    #The below should check rules for standby, 24 hour guest rule, etc.
    seg.person_swap(person_drop_id=p['person_drop_id'], person_add_id=p['person_add_id'])
    
    person = m.Person.objects.get(pk=p['person_add_id'])
    json_data = json.dumps({'seg_id':seg.id, 'person_id':person.id, 'person_name':person.get_long_name(), 'error':''})
    return HttpResponse(json_data)

@login_required(login_url='/login/')
def segment_dates_and_dog(request, seg_id):
    seg = m.ResvSegment.objects.get(pk=seg_id)
    segment_dog(request, seg)
    change_error = segment_dates_CHANGE(request, seg)
    json_data = json.dumps({'seg_id':seg.id, 'resv_id':seg.resv.id, 'error':change_error, 'happy_url':request.POST['happy_url']})
    print json_data
    return HttpResponse(json_data)

def segment_dates_CHANGE(request, seg): 
    print 'segment/dates/change'
    p = request.POST
    #The below chould check for capacity, rules, etc.
    start_date = dt.datetime.strptime(p['start_date'], '%m/%d/%Y').date()
    duration = int(p['duration'])
    print 'copying segment'
    #new_seg = m.copy_segment(seg)
    #if new_seg.state == 'Confirmed':  #is this needed? Should be handled by model?
    #    new_seg.make_pending()        #is this needed? Should be handled by model?
    #    new_seg.save()                #is this needed? Should be handled by model?
    #seg.state = 'Pending - Backup'
    #seg.save()
    new_seg = seg
    print p
    make_standby_if_full = True
    if p['make_standby_if_full'] == 'false':
        print 'Changing make_standby_if_full to False'
        make_standby_if_full = False
    result = new_seg.change_dates(new_start_date=start_date, new_duration=duration, make_standby_if_full=make_standby_if_full)
    print 'segment/dates/change returning'
    if result:
        new_seg.save()
        return ''
    else:
        return 'standby'
    

'''
#def confirm(request, resv_id):
    print "Confirming resv:", resv_id
    resv = m.Resv.objects.get(pk=resv_id)
    print 'Resv ID {0}, is {1}'.format(resv_id, resv)
    #resv.change_state('Confirmed')
    try:
        resv.confirm()
        resv.save()
        print 'Confirmed.'
    except TransitionNotAllowed:
        print 'transition not allowed'
   
        return review(request, resv_id)
    return redirect(home)
'''
def segment_dog(request, seg): 
    print 'segment/dog/change'
    p = request.POST
    seg.set_dog_details(has_dog=p['dog'], dog_comment=p['dog_comment'])

@login_required(login_url='/login/')
def standby_save(request, seg_id):
    print 'segment/standby/save'



class Cell():
    cell_type = 'raw'
    val = ''
    def __init__(self, **kwargs):
        for key, value in  kwargs.iteritems():
            self[key] = value
def create_cell(**kwargs):
    cell = {'cell_type':'raw', 'val':''}
    for key, value in kwargs.iteritems():
        cell[key] = value
    return cell



@login_required(login_url='/login/')
def search(request):
    ''' AJAX.  Recieves ranch search, and provides table details back.'''
    print 'search called', request.method
    if request.method == 'GET':
        print 'method was get'
        form = forms.RanchSearchForm(request.GET)
        if form.is_valid():
            print form.cleaned_data
            q_ranches = m.Ranch.objects.all()
            q_ranches = filter_optional_form_field(form.cleaned_data, q_ranches, 'ranch', 'id__in')
            q_ranches = filter_optional_form_field(form.cleaned_data, q_ranches, 'allows_dogs', 'allows_dogs__in')
            q_ranches = filter_optional_form_field(form.cleaned_data, q_ranches, 'archery', 'archery_only__in')
            q_ranches = filter_optional_form_field(form.cleaned_data, q_ranches, 'game', 'gameregionranch__game_region__game__id__in')
            q_ranches = filter_optional_form_field(form.cleaned_data, q_ranches, 'cluster', 'clusterranch__cluster__id__in')
            q_ranches = filter_optional_form_field(form.cleaned_data, q_ranches, 'DFGZone', 'gameregionranch__game_region__id__in')

            start_date = form.cleaned_data['start_date']
            date_range = [start_date + dt.timedelta(days=i) for i in range(7)]

            jason = {'success':True}
            header = [create_cell(val='#'), create_cell(val='Ranch name'), create_cell(val='Blind')]#, create_cell(val='Capacity')]
            jason['header'] = header + [create_cell(val=d.strftime('%b %d')) for d in date_range]
            rows = []
            for ranch in q_ranches:
                for blind in ranch.blind_set.all().order_by('ranch__number', 'name'):
                    row = [create_cell(val=ranch.number), create_cell(val=ranch.name), create_cell(val=blind.name)]
                    cap_cell = create_cell(cell_type='capacity',
                            val=[[blind.capacity_parties, 'parties'],[blind.capacity_hunters,'hunters'],[blind.capacity_persons, 'people']])
                   # row.append(cap_cell)

                    for date in date_range:
                        availability = blind.get_applicable_availability(date, game=False) #TODO:Make game actually right
                        #occ = blind.occupancy(date)
                        occ_cell = create_cell(cell_type=availability['available'],
                                  ranch_id=ranch.id,
                                  ranch_display_name=ranch.display_name(),
                                  blind_id=blind.id,
                                  date=date.strftime('%Y-%m-%d'),
                                  #occupancies=availability['occupancy'],
                                  free=availability['free'],
                                  free_type=availability['free_type'],
                                  taken=availability['taken'],
                                  taken_type=availability['taken_type'],
                                  #cap_type=availability['cap_type'],
                                  has_dogs=availability['dogs'] > 0
                                )
                        row.append(occ_cell)
                    rows.append(row)
            jason['table_data'] = rows
            print jason
            json_data = json.dumps(jason)
          #  print 'json_data', json_data
            return HttpResponse(json_data)
        else:
            print 'invalid form'
            print form.errors
            pass # bad things
    else:
        print 'wtf'

@login_required(login_url='/login/')
def resv(request, resv_id='new'):
    ''' Displays the reservation search page'''
    q_ranches = m.Ranch.objects.all()
    search_form = forms.RanchSearchForm(initial={'resv':resv_id})
    context = RequestContext(request, {
        'form':search_form,
    #    'alerts':[{'level':'warning', 'text':'test alert'}]
    })
    context.update(csrf(request))
    return render(request, 'resv_search.html', context_instance=context)

@login_required(login_url='/login/')
def review(request, resv_id):
    print 'Reviewing resv: ', resv_id
    resv = m.Resv.objects.get(pk=resv_id)
    print '######testing  valid count',
    print resv.get_valid_pending_segs().count()
    segs = resv.get_blocking_segs_w_backup()
    if segs.count() == 0:
        return redirect(home)
    context = RequestContext(request, {
        'segments': segs,
        'resv':resv
    })
    context.update(csrf(request))
    return render(request, 'resv_review.html', context_instance=context)

@login_required(login_url='/login/')  
def confirm(request, resv_id):
    print "Confirming resv:", resv_id
    resv = m.Resv.objects.get(pk=resv_id)
    print 'Resv ID {0}, is {1}'.format(resv_id, resv)
    #resv.change_state('Confirmed')
    try:
        resv.confirm()
        resv.save()
        print 'Confirmed.'
    except TransitionNotAllowed:
        print 'transition not allowed'
   
        return review(request, resv_id)
    return redirect(home)



@login_required(login_url='/login/')  
def cancel(request, obj_type, obj_id):
    print "Canceling {0}: {1}".format(obj_type, obj_id),
    if obj_type == 'segment':
        obj = m.ResvSegment.objects.get(pk=obj_id)
    elif obj_type == 'resv':
        obj = m.Resv.objects.get(pk=obj_id)  
    obj.cancel()  
    obj.save()
    print 'Done.'
    if obj_type == 'segment':
        obj.resv.recalc_state()
        obj.resv.check_rules()
        return redirect(review, resv_id=obj.resv.id)
    return redirect(home)
@login_required(login_url='/login/')
def standby_choice_review(request, seg_id):
    seg = m.ResvSegment.objects.get(pk=seg_id)
    if seg.standby_is_on_point():
        # Show the user a choice screen
        context = RequestContext(request, {
        'seg':seg,
        })
        return render(request, 'resv_standby_choice.html', context_instance=context)
    else:
        # Print a message like: This standby segment is not able to be filled yet, or the confirmation window has expired. 
        pass
@login_required(login_url='/login/')  
def ranch_mrktg(request, ranch_id):
    pass
@login_required(login_url='/login/')  
def ranch_admin(request, ranch_id):
    ranch = m.Ranch.objects.get(pk=ranch_id)
    context = RequestContext(request, {
        'ranch':ranch,
        'roster':ranch.get_roster(dt.date.today(), dt.date.today() + dt.timedelta(days=7))
    })
    context.update(csrf(request))
    return render(request, 'resv_ranch_admin.html', context_instance=context)

@login_required(login_url='/login/')  
def patrol(request, ranch_id=False):
    d = {}
    if ranch_id:
        ranch = m.Ranch.objects.get(pk=ranch_id)
        d['ranch'] = ranch
    d['ranch_list'] = [{'id':ranch.id, 'name':ranch.display_name()} for ranch in m.Ranch.objects.all()]
    d['default_date'] = dt.date.today().strftime('%m/%d/%Y')
    
    context = RequestContext(request, d)
    return render(request, 'resv_patrol.html', context_instance=context)

@login_required(login_url='/login/')  
def reports(request):
	pass
def mktg(request):
    template = loader.get_template('base_mktg.html')
    context = RequestContext(request, {
        'latest_poll_list': 1,
    })
    return HttpResponse(template.render(context))

def loginview(request):
    c = {}
    c.update(csrf(request))
    return render_to_response('login.html', c)

def auth_and_login(request, onsuccess='/home/', onfail='/login/'):
    print request.POST['email']
    print request.POST['password']
    print request.user
    
    user = authenticate(username=request.POST['email'], password=request.POST['password'])
    if user is not None:
        print 'Logged in'
        login(request, user)
        return redirect(onsuccess)
    else:
        print 'Log in failure'
        return redirect(onfail)

def sign_up_in(request):
    post = request.POST
    if not m.person_exists(post['email']):
        user = m.create_person(username=post['email'], email=post['email'], password=post['password'])
        return auth_and_login(request)
    else:
        return redirect("/login/")

def logoutview(request):
    logout(request)
    return redirect("/")