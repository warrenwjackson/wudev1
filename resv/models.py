import datetime as dt
import sys
from django.db import models
from django.db.models import Q, Max, Min
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.core.mail import send_mail
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.utils import timezone
from django_fsm import FSMField, transition
from notifications import notify

from resv import rules, email

MEMBERSHIP_STATES = (('CA', 'CA'), ('OR', 'OR'))
RESV_STATES = (('Pending', 'Pending'), ('Held','Held'),('Confirmed','Confirmed'),('Canceled','Canceled'),('Complete','Complete'))
STATUS_MAP = {'Canceled':['Confirmed', 'Pending'], 'Confirmed':['Pending', 'Confirmed']}

def recalc_parent(action):
    def exec_action(obj, *args, **kwargs):
        result = action(obj, *args, **kwargs)
        obj.resv.recalc_state()
        return result
    return exec_action
        
def saveme(action):
    def exec_action(obj, *args, **kwargs):
        result = action(obj, *args, **kwargs)
        obj.save()
        
        return result
    return exec_action

def copy_segment(orig):
    new_seg = ResvSegment()
    new_seg.create(orig.resv.id, orig.blind.id, ' ', orig.start_date, orig.state)
    new_seg.game = orig.game
    new_seg.end_date = orig.end_date
    new_seg.dog = orig.dog
    new_seg.dog_comment = orig.dog_comment
    new_seg.standby_state = orig.standby_state
    new_seg.standby_updated = orig.standby_updated
    new_seg.save()
    for orig_rsp in ResvSegmentPerson.objects.filter(resv_segment=orig):
        new_rsp = ResvSegmentPerson()
        new_rsp.resv_segment = new_seg
        new_rsp.person = orig_rsp.person
        new_rsp.is_hunting = orig_rsp.is_hunting
        new_rsp.is_guest = orig_rsp.is_guest
        new_rsp.save()
    return new_seg


def set_and_pop(obj, kwargs, form_key, obj_key, value):
    if kwargs.has_key(form_key):
        setattr(obj, obj_key, value)
        kwargs.pop(form_key)

def update_obj(obj, **kwargs):
    print 'updating obj'
    for key, value in kwargs.iteritems():
        print key, value
        setattr(obj,key,  value)
    obj.save()
    return obj
def update_or_create(model, id, **kwargs):
    try:
        obj = model.objects.get(id=id)
        return update_obj(obj, **kwargs)
    except ObjectDoesNotExist:
        print 'second'
        obj = model(**kwargs)
        obj.save()
        return obj


def standby_confirm_window(on_point_dt, seg_hunt_date):
    windows = [ [dt.timedelta(days=60), dt.timedelta(hours=168)],
                [dt.timedelta(days=30), dt.timedelta(hours=96)],
                [dt.timedelta(days=14), dt.timedelta(hours=48)],
                [dt.timedelta(days=4), dt.timedelta(hours=24)],
                [dt.timedelta(days=2), dt.timedelta(hours=16)],
                [dt.timedelta(days=1), dt.timedelta(hours=5)],
                [dt.timedelta(days=0), dt.timedelta(hours=1)], 
            ]
    delta = seg_hunt_date - on_point_dt.date()
    print 'Delta is: ', delta
    for window in windows:
        if delta >= window[0]:
            return window[1]

def filter_exclude_standby(segs, exclude_on_point=True):
    segs = segs.filter(~Q(state='Standby - Pending'))
    if exclude_on_point:
        segs = segs.filter(~Q(state='Standby'))
    else:
        segs = segs.filter(~Q(state='Standby') & ~Q(standby_state=1))
    return segs
def filter_only_standby(segs):
    segs = segs.filter(Q(state='Standby - Pending') | Q(state='Standby'))
    return segs

def filter_blockers_only(segs):
    segs = segs.filter(
                    Q(state='Confirmed') | Q(state='Complete') | Q(state='Standby') |
                    Q(state='Pending') & Q(updated__gte=timezone.now() - dt.timedelta(minutes=15)) |
                    Q(state='Standby - Pending') & Q(updated__gte=timezone.now() - dt.timedelta(minutes=15)) 
                    
                    )
    return segs
def filter_blockers_only_w_backup(segs):
    segs = segs.filter(
                    Q(state='Confirmed') | Q(state='Complete') | Q(state='Standby') |
                    Q(state='Pending') & Q(updated__gte=timezone.now() - dt.timedelta(minutes=15)) |
                    Q(state='Standby - Pending') & Q(updated__gte=timezone.now() - dt.timedelta(minutes=15))  |
                    Q(state='Backup') & Q(updated__gte=timezone.now() - dt.timedelta(minutes=15))
                    
                    )
    return segs
def filter_non_expired_only(segs):
    segs = segs.exclude(Q(state='Pending') & Q(updated__lte=timezone.now() - dt.timedelta(minutes=15)))
    segs = segs.filter(~Q(state='Expired'))
    return segs
def filter_non_expired_only_w_backup(segs):
    segs = segs.exclude(Q(state='Pending') & Q(updated__lte=timezone.now() - dt.timedelta(minutes=15)))
    segs = segs.exclude(Q(state='Backup') & Q(updated__lte=timezone.now() - dt.timedelta(minutes=15)))
    segs = segs.filter(~Q(state='Expired'))
    return segs
def filter_expired_pending_only(segs):
    segs = segs.filter(Q(state='Pending') & Q(updated__lte=timezone.now() - dt.timedelta(minutes=15))   |
                       Q(state='Backup') & Q(updated__lte=timezone.now() - dt.timedelta(minutes=15))   |
                       Q(state='Standby - Pending') & Q(updated__gte=timezone.now() - dt.timedelta(minutes=15)))
    return segs
def filter_old_confirmed_only(segs):
    segs = segs.filter(Q(state='Confirmed') & Q(end_date_ltdt.date.today()))
    return segs
def filter_future_blockers_only_w_backup(segs, is_resv=True):
    segs = filter_blockers_only_w_backup(segs).exclude(state='Complete')
    if is_resv:
        resv_ids = []
        for resv in segs:
            if resv.get_end_date() >= dt.date.today():
                resv_ids.append(resv.id)
        return Resv.objects.filter(pk__in=resv_ids)
    else:
        return segs.filter(end_date__gte=dt.date.today())
def filter_future_blockers_only(segs, is_resv=True):
    return filter_future_blockers_only_w_backup(segs, is_resv).exclude(state='Backup')

def filter_past_blockers_only(segs, is_resv=True):
    if is_resv:
        resv_ids = []
        for resv in segs:
            if resv.get_end_date() < dt.date.today():
                resv_ids.append(resv.id)
        return Resv.objects.filter(pk__in=resv_ids)
    else:
        return filter_blockers_only(segs).filter(Q(state='Complete') | Q(state='Confirmed', end_date__lt=dt.date.today()))

class GameType(models.Model):
    name = models.CharField(max_length=20)
class Game(models.Model):
    game_type = models.ForeignKey('GameType')
    name = models.CharField(max_length=200)

class GameRegion(models.Model):
    name = models.CharField(max_length=200)
    game = models.ForeignKey('Game')

class GameRegionRanch(models.Model):
    game_region = models.ForeignKey('GameRegion')
    ranch = models.ForeignKey('Ranch')

class Cluster(models.Model):
    name = models.CharField(max_length=200)
    
class ClusterRanch(models.Model):
    cluster = models.ForeignKey('Cluster')
    ranch = models.ForeignKey('Ranch')
def get_default_date():
    return dt.date(2000,1,1)
def get_default_datetime():
    return dt.datetime(2000,1,1)
class Ranch(models.Model):
    number = models.CharField(max_length=10)
    name = models.CharField(max_length=200)
    size = models.PositiveIntegerField(blank=True)
    city = models.CharField(max_length=200)
    county = models.CharField(max_length=200)
    comment = models.CharField(max_length=200)
    lat = models.FloatField()
    lon = models.FloatField()
    combo = models.CharField(max_length=24)
    combo2 = models.CharField(max_length=24)
    allows_dogs = models.CharField(max_length=1)
    archery_only = models.CharField(max_length=1)
    open_for_resvs = models.DateTimeField(default=get_default_datetime)  #  uncomment during the next db change

    def display_name(self):
        return self.__unicode__()
    def short_name(self):
        return self.name
    def get_location_html(self):
        return '<a href="http://maps.google.co.uk/maps?q=@{0},{1}&z=15">{0} {1}</a>'.format(self.lat, self.lon)
    def get_allows_dogs(self):
        if self.allows_dogs == '0':
            return 'No'
        return 'Yes'
    def get_archery_only(self):
        if self.archery_only == '0':
            return 'No'
        return 'Yes'
    def get_game(self, hunt_date='all'):
        if hunt_date == 'all':
            return Game.objects.filter(gameregion__gameregionranch__ranch=self)
    def shoot_days(self):
        sd = lambda a,b: ''.join([max(l) for l in zip(a,b)])
        d = '0'*7
        for blind in self.blind_set.all():
            d = sd(d,blind.shoot_days)
        return d
    def get_resvsegments(self, start_date=False, end_date=False):
        segs = ResvSegment.objects.filter(blind__ranch=self)
        if start_date:
            segs = segs.filter(end_date__gte=start_date)
        if end_date:
            segs = segs.filter(start_date__lte=end_date)
        return segs
    def get_roster(self, start_date, end_date=False):
        if not end_date:
            end_date = start_date + dt.timedelta(days=7)
        segs = self.get_resvsegments(start_date, end_date)
        roster = {}
        for seg in segs:
            seg_dets = {'hunters':seg.get_persons(is_hunting=True)}
            seg_dets['nonhunters'] = seg.get_persons(is_hunting=False)
            seg_dets['dog'] = ['No', 'Yes'][min(seg.dog,1)]
            seg_dets['dog_comment'] = seg.dog_comment
            seg_dets['resv_id'] = seg.resv.get_id()
            date_list = [seg.start_date + dt.timedelta(days=x) for x in range(0, (seg.end_date-seg.start_date).days)]
            for day in date_list:
                if roster.has_key(day):
                    roster[day] = roster[day].append(seg_dets)
                else:
                    roster[day] = [seg_dets]
        roster_list = []
        for day in sorted(roster.keys()):
            roster_list.append({'date':day, 'roster':roster[day]})
        return roster_list
    def get_resv(self, start_date=False, end_date=False):
        segs = self.get_resvsegments(start_date, end_date).order_by('start_date')
        resv_ids = [s.resv.id for s in segs]
        return Resv.objects.filter(pk__in=resv_ids)
    def open_for_resv(self):
        m = self.blind_set.aggregate(Min('open_for_resvs'))['open_for_resvs__min']
        if m <= timezone.now():
            return 'Open now'
        return m
    def __unicode__(self):
        return '{0} {1}'.format(self.number, self.name)
def choose_head_limit(capacity):
    if 0 < capacity['hunters']:
        return 'hunters'
    return 'persons'
class Availability:
    def __init__(self, date, blind):
        pass
class Blind(models.Model):
    ranch = models.ForeignKey('Ranch')
    name = models.CharField(max_length=15)
    
    capacity_parties = models.PositiveSmallIntegerField(blank=True) #make ok to be null
    capacity_hunters = models.PositiveSmallIntegerField(blank=True)
    capacity_persons = models.PositiveSmallIntegerField(blank=True)
    capacity_perparty = models.PositiveSmallIntegerField(blank=True)

    shoot_days = models.CharField(max_length=7)
    open_for_resvs = models.DateTimeField(default=get_default_datetime)
    
    def is_shoot_day(self, date):
        if timezone.now() < self.open_for_resvs:
            return False
        is_shoot_day = self.shoot_days[date.weekday()] == '1'
        special_days = SpecialDay.objects.filter(Q(start_date__lte=date, end_date__gte=date, ranch=self.ranch))
        print '    Checking shoot day {0}, base: {1}, special day count: {2}'.format(date, is_shoot_day, special_days.count())
        if special_days.count() == 0:
            return is_shoot_day
        if special_days.count() > 1:
            print 'Error: Too many special days'
            return is_shoot_day
        return special_days[0].is_open
    def are_all_shoot_days(self, start_date, end_date):
        print 'Checking are_all_shoot_days {0}, {1}, {2}'.format(start_date, end_date, range((end_date-start_date).days + 1))
        for delta in range((end_date-start_date).days + 1):
            if not self.is_shoot_day(start_date + dt.timedelta(days=delta)):
                print 'are_all_shoot_days returning False'
                return False
        print 'are_all_shoot_days returning True'
        return True
    def get_applicable_availability(self, resv_date, game):
        '''
            The logic should be:
                If blind is vacant: 
                    show head count
                    capacity = min(max(hunter_or_persons, perparty), ranch hard limit)
                If blind is not vacant:
                    if party capacity not yet reached:
                        show head count
                        capcity = min(hunter_or_persons, perparty, ranch hard limit)
                    else:
                        show parties (full) 
            hunter_or_persons = use hunters if not 0, else persons
        '''

        occ = self.occupancy(resv_date, game)
        cap = self.get_capacity(resv_date, game)

        output = {'available':['closed', 'open'][self.is_shoot_day(resv_date)]}
        output['dogs'] = occ['dogs']
        output['dog_comments'] = occ['dog_comments']
        print 
        if occ['parties'] == 0:
            print self, ' is vacant'
            if 0 < cap['hunters'] + cap['persons']: #If there is a head limit, use it. 
                output['free_type'] = 'persons'
                output['free'] = cap[choose_head_limit(cap)] - occ[choose_head_limit(cap)] #TODO: improve this logic. what about overbooking one party?
                output['taken_type'] = 'persons'
                output['taken'] = occ[choose_head_limit(cap)]
                output['cap_type'] = choose_head_limit(cap)
            else: # when no head limit
                output['free_type'] = 'parties'
                output['free'] = cap['parties'] - occ['parties']
                output['taken_type'] = 'parties'
                output['taken'] = occ['parties']
        else: # The ranch is not vacant
            print self, ' is NOT vacant'
            if 0 < cap['parties'] and cap['parties'] <= occ['parties']: #Party cap is reached
                print '   Party cap is reached.'
                output['free_type'] = 'parties'
                output['free'] = 0
                output['taken_type'] = 'parties'
                output['taken'] = occ['parties']    
            elif cap[choose_head_limit(cap)]  <= occ[choose_head_limit(cap)]: # Head cap is reached
                print '   Head cap is reached.'
                output['free_type'] = 'persons'
                output['free'] = 0 
                output['taken_type'] = 'persons'
                output['taken'] = occ[choose_head_limit(cap)]    
                output['cap_type'] = choose_head_limit(cap)                       
            elif 0 < cap['hunters'] + cap['persons']: #If there is a head limit, use it. 
                print '   There is a head cap.'
                output['free_type'] = 'persons'
                output['free'] = cap[choose_head_limit(cap)] - occ[choose_head_limit(cap)] #TODO: improve this logic. what about party limit
                output['taken_type'] = 'persons'
                output['taken'] = occ[choose_head_limit(cap)]                
                output['cap_type'] = choose_head_limit(cap)
            else: # when no head limit
                print '   There is NO head cap.'
                output['free_type'] = 'parties'
                output['free'] = cap['parties'] - occ['parties']
                output['taken_type'] = 'parties'
                output['taken'] = occ['parties']            
        print self, output
        return output
    def get_availability(self, resv_date, game, exclude_standby=False):
        output = {'available':['closed', 'open'][self.shoot_days[resv_date.weekday()] == '1']}
        occ = self.occupancy(resv_date, game, exclude_standby)
        cap = self.get_capacity(resv_date, game)
        output['occupancy'] = [{'occ':occ['parties'], 'capacity':cap['parties']},
                            {'occ':occ['hunters'], 'capacity':cap['hunters']},
                            {'occ':occ['hunters'] + occ['nonhunters'], 'capacity':cap['persons']}]
        output['dogs'] = occ['dogs']
        output['dog_comments'] = occ['dog_comments']
        return output  
    def check_availability_parties(self, resv_date, game, party_count=1, ignore_standby=False, exclude_standby=False):                
        occ = self.get_availability(resv_date, False, exclude_standby)
        print 'cap: {0}, occ:{1}'.format(occ['occupancy'][0]['capacity'], occ['occupancy'][0]['occ'] )

        if occ['occupancy'][0]['capacity'] > 0 and occ['occupancy'][0]['capacity'] - occ['occupancy'][0]['occ'] < party_count:
            print 'Cannot create a party - No availability'
            return False
        if not ignore_standby and self.get_standby_list(resv_date).count() > 0:
            print 'Cannot create a party - Standby list is not empty'
            return False
        return True

    def check_availability_people(self, resv_date, game, person_count, ignore_standby=False, exclude_standby=False):
        occ = self.get_availability(resv_date, game, exclude_standby)
        if occ['occupancy'][2]['capacity'] > 0 and occ['occupancy'][2]['capacity'] - occ['occupancy'][2]['occ'] < person_count['total']:
            print 'Complete: cannot because of overall headcount cap: {0}, occ: {1}, open: {2}'.format(occ['occupancy'][2]['capacity'], occ['occupancy'][2]['occ'], occ['occupancy'][2]['capacity'] - occ['occupancy'][2]['occ']  )
            return False
        if person_count['hunters'] > 0 and occ['occupancy'][1]['capacity'] > 0 and occ['occupancy'][1]['capacity'] - occ['occupancy'][1]['occ'] < person_count['hunters']:
            print 'Complete: cannot because of hunter count'
            return False
        if not ignore_standby and self.get_standby_list(resv_date).count() > 0:
            print 'Complete: cannot because Standby list is not empty'
            return False
        print 'Complete: ok to add person'
        return True

    def can_add_party(self, seg, ignore_standby=False):
        print 'checking to see if ok to create party'
        print 'looping through {0} days'.format((seg.end_date - seg.start_date).days)
        for d in [seg.start_date + dt.timedelta(days=i) for i in range((seg.end_date - seg.start_date).days + 1) ]:
            if not self.check_availability_parties(d, seg.game, 1):
                return False
        print 'can create a party'
        return True

    def can_add_person(self, seg, is_hunting, ignore_standby=False):
        print 'Checking: can add person?'
        person_count = {'total':1, 'hunters':[0,1][is_hunting]}
        for d in [seg.start_date + dt.timedelta(days=i) for i in range((seg.end_date - seg.start_date).days + 1) ]:
            if not self.check_availability_people(d, seg.game, person_count, ignore_standby):
                return False
        print 'Complete: ok to add person'
        return True
    def can_upgrade_standby(self, seg):
        # return yes, no, partial
        # For all days of the segment:
            # is there availability (all, or partial)
            # is there a segment on standby point
        print '##########can_upgrade_standby'
        can = []
        for di in (seg.start_date + dt.timedelta(days=n) for n in range((seg.end_date - seg.start_date).days + 1)): 
            print 'Checking ability to upgrade on ', di
            if self.has_standby_on_point(di) and not seg.standby_is_on_point(): # Is there already a standby resv on point?
                print 'Has standby on point'
                can.append(0)
            elif not self.check_availability_parties(di, seg.game, party_count=1, ignore_standby=True, exclude_standby=True): # Is it full by party count?
                print 'Full of parties'
                can.append(0)
            elif self.check_availability_people(di, seg.game, person_count={'total':1, 'hunters':min(1,seg.count_hunters())}, ignore_standby=True, exclude_standby=True):
                print seg.count_heads()
                if self.check_availability_people(di, seg.game, person_count={'total':seg.count_heads(), 'hunters':seg.count_hunters()}, ignore_standby=True, exclude_standby=True):
                    print 'open'
                    can.append(1)
                else:
                    print 'partially open'
                    can.append(-1)
            else:
                can.append(0)
        print '     Can list: ', can
        if len(can) == can.count(1):
            return 'yes'
        if can.count(-1) + can.count(1) > 0:
            return 'partial'
        return 'no'

    def can_add_standby(self, resv_date):
        occ = self.get_availability(resv_date, False)
        if occ['occupancy'][0]['capacity'] > 0 and occ['occupancy'][0]['capacity'] - occ['occupancy'][0]['occ'] < 1:
            print 'Cannot add standby - no more parties'
            return False
        if occ['occupancy'][2]['capacity'] > 0 and occ['occupancy'][2]['capacity'] - occ['occupancy'][2]['occ'] < 1:
            print 'Cannot add standby - overall headcount cap: {0}, occ: {1}, open: {2}'.format(occ['occupancy'][2]['capacity'], occ['occupancy'][2]['occ'], occ['occupancy'][2]['capacity'] - occ['occupancy'][2]['occ']  )
            return False     
        if occ['occupancy'][1]['capacity'] > 0 and occ['occupancy'][1]['capacity'] - occ['occupancy'][1]['occ'] < 1:
            print 'Cannot add standby - hunter count'
            return False   
        return True

    def get_game_list(self, resv_date):
        print 'get_game_list'
        game_region_ranches = self.ranch.gameregionranch_set.distinct()
        game_regions = [_.game_region for _ in game_region_ranches]
        seasons = Season.objects.filter(game_region__in=game_regions, start_date__lte=resv_date, end_date__gte=resv_date)
        game_objs = set([seas.game_region.game for seas in seasons])
        game_list = [[game.id, game.name] for game in game_objs]
        return game_list 

    def get_capacity(self, resv_date, game):
        #TODO: layer on special events
        #TODO: layer on overrides
        #This should really be at a season level
        return {'parties':self.capacity_parties, 'hunters':self.capacity_hunters, 'persons':self.capacity_persons}

    def _get_segs(self, resv_date, exclude_standby=False):
        segs = filter_blockers_only(self.resvsegment_set.filter(start_date__lte=resv_date, end_date__gte=resv_date))
        if exclude_standby:
            segs = filter_exclude_standby(segs, exclude_on_point=False)
        return segs

    def occupancy(self, resv_date, game=False, exclude_standby=False):
        occ = {'parties':0, 'hunters':0,'nonhunters':0, 'dogs':0, 'dog_comments':''}
        segs = self._get_segs(resv_date, exclude_standby)
        print 'occupancy called for date: {0}, game: {1}, looking at segs'.format(resv_date, game),
        print segs
        if game:
            print 'filtering for game', game
            segs = segs.filter(game__game_type=game.game_type)
            print segs
        for seg in segs:
            occ['parties'] += 1
            occ['hunters'] += seg.count_hunters()
            occ['nonhunters'] += seg.count_nonhunters()
            occ['dogs'] += seg.dog
            if seg.dog > 0:
                occ['dog_comments'] += seg.dog_comment + "\n"
        occ['persons'] = occ['hunters'] + occ['nonhunters']
        print 'occupancy returning: ', occ
        return occ
    def get_standby_list(self, resv_date, game=False):
        segs = self._get_segs(resv_date)
        segs = filter_only_standby(segs)
        return segs.order_by('created')
    def has_standby_on_point(self, resv_date):
        print self.get_standby_list(resv_date).filter(standby_state=1)
        if self.get_standby_list(resv_date).filter(standby_state=1).count() > 0:
            return True
        return False

    def __unicode__(self):
        return '{ranch}: {blind}'.format(ranch=self.ranch.display_name(), blind=self.name)

class Season(models.Model):
    start_date = models.DateField()
    end_date = models.DateField()
    game_region = models.ForeignKey('GameRegion')
    resv_open = models.DateField(default=dt.date.today)

class SpecialDay(models.Model):
    start_date = models.DateField()
    end_date = models.DateField()
    ranch = models.ForeignKey('Ranch')
    is_open = models.BooleanField(default=True)

class RuleRanch(models.Model):
    ranch = models.ForeignKey('Ranch')
    rule = models.ForeignKey('Rule')

class Rule(models.Model):
    desc = models.TextField()

class Resv(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey('Person')
    state = FSMField(default='Pending')
    status = models.CharField(choices=RESV_STATES, max_length=10, default='Pending') # not sure if this is needed, but reincluding now.
    def get_game(self):
        games = []
        for seg in self.get_blocking_segs():
            games.append(seg.game.name)
        return set(games)
    def get_game_unicode(self):
        return ', '.join(self.get_game())[:20]
    def get_blocking_segs(self):
        return filter_blockers_only(self.resvsegment_set.all())
    def get_blocking_segs_w_backup(self):
        return filter_blockers_only_w_backup(self.resvsegment_set.all())    
    def get_non_expired_segs(self):
        return filter_non_expired_only(self.resvsegment_set.all())
    def get_future_blocking_segs(self):
        return filter_future_blockers_only(self.get_blocking_segs(), is_resv=False)
    def get_future_blocking_segs_w_backup(self):
        return filter_future_blockers_only_w_backup(self.get_blocking_segs_w_backup(), is_resv=False)
    def get_future_blocking_segs_no_sb(self):    
        return filter_exclude_standby(self.get_future_blocking_segs())
    def get_valid_pending_segs(self):
        return self.get_blocking_segs().filter(state__in=['Pending','Standby - Pending'], updated__gte=timezone.now() - dt.timedelta(minutes=15))
    def get_past_blocking_segs(self):
        return filter_past_blockers_only(self.get_blocking_segs())
    def get_start_date(self):
        return min([resv.start_date for resv in self.get_blocking_segs().exclude(state='Backup')] + [dt.date(2300, 1,1)])
    def get_end_date(self):
        return max([resv.end_date for resv in self.get_blocking_segs().exclude(state='Backup')] + [dt.date(1800, 1,1)])
    def get_blinds(self):
        return [(resv.blind.__unicode__(), resv.start_date) for resv in self.resvsegment_set.all() ]
    def get_first_blind(self):
        return sorted(self.get_blinds(), key=lambda blind: blind[1])[0][0]
    def get_ranch_summary(self):
        ranches = []
        for seg in self.get_blocking_segs().order_by('start_date'):
            if seg.blind.ranch not in ranches:
                ranches.append(seg.blind.ranch)
        return ', '.join([ranch.short_name() for ranch in ranches])[:80]

        #return self.resvsegment_set.order_by('start_date')[0].blind.ranch.display_name() #TODO: make a smart list of ranches
    def get_persons(self):
        ppl = []
        for seg in self.get_blocking_segs():
            ppl += seg.get_persons()
        return ppl
    def get_segpersons(self):
        ppl = []
        for seg in self.get_blocking_segs():
            ppl += seg.get_segpersons()
        return ppl

    def count_guests(self):
        return self.get_segpersons().filter(is_guest=True).count()

    def get_game_list(self):
        game = []
        for seg in self.get_blocking_segs():
            game.append(seg.game)
        return game
    def get_game_type_list(self):
        game_types = []
        for game in self.get_game_list():
            game_types.append(game.game_type)
        return set(game_types)
    def get_id(self):
        return self.id
    def __unicode__(self):
        if self.get_blocking_segs().count() == 0:
            return 'Expired pending reservation'
        return 'Owner: {0}, status: {1}, last update: {2}, start date: {3}, end date: {4}, first blind: {5}'.format(self.owner, self.state, 
                self.updated, self.get_start_date(), self.get_end_date(), self.get_first_blind())
    @transition(field=state, source=['Pending', 'Held', 'Confirmed'], target='Confirmed', 
        conditions=[rules.has_blocking_segs, rules.one_resv_per_member, rules.max_resv_length, rules.continuous_and_one_per_day, rules.no_splitting_weekends, rules.one_day_one_resv, rules.cant_book_closed_day])
    def confirm(self):
        print 'Now confirming segments'
        seg_list =  [seg for seg in self.get_future_blocking_segs_w_backup()]
        print 'segs:', seg_list
        for seg in seg_list:
            print '    ', seg
            if seg.state == 'Standby - Pending':
                print 'Holding stanby segment'
                seg.standby_hold()
            elif seg.state == 'Backup':
                print 'Cancelling backup'
                seg.cancel()
            elif seg.state == 'Standby' and seg.standby_is_on_point():
                print 'Confirming standby'
                seg.standby_confirm()
            else:
                print 'Confirming segment'
                seg.confirm()

        #Two loops, so that nothing is saved if there is an issue with one segment.
        for seg in seg_list:
            seg.save()
        email.resv_confirm(self)

    def check_rules(self):
        if not rules.one_resv_per_member(self) or not rules.max_resv_length(self) or not rules.continuous_and_one_per_day(self) or not rules.no_splitting_weekends(self) or not rules.one_day_one_resv(self):
            self.make_pending()
            notify.send(self, recipient=self.owner, verb=u'This reservation breaks one or more rules and has been changed to Pending status.  You have 15 minutes to fix and confirm.')
    

    @saveme
    @transition(field=state, source=['Pending', 'Held', 'Confirmed'], target='Pending')
    def make_pending(self):
        seg_list =  [seg for seg in self.get_future_blocking_segs()]
        for seg in seg_list:
            seg.make_pending()

    @saveme
    @transition(field=state, source=['Pending', 'Held', 'Confirmed', 'Standby - Pending', 'Standby'], target='Canceled')
    def cancel(self):
        seg_list =  [seg for seg in self.get_future_blocking_segs()]
        for seg in seg_list:
            seg.cancel()
            seg.save()
       # self.recalc_state()

    def change_state(self, new_state):
        if self.state not in STATUS_MAP[new_state]:
            raise Exception("Error: only {0} reservations can be {1}".format(STATUS_MAP[new_state], new_state))
        for seg in self.resvsegment_set.filter(state__in=STATUS_MAP[new_state]):
            seg.change_state(new_state)
        self.state = new_state
        self.save()

    def recalc_state(self):
        print 'Recalc: {0}'.format(self.id) ,
        segs = self.get_non_expired_segs().order_by('created')
        if segs.count() == 0:
            print '  Count zero'
            self.state = 'Canceled'
        for state in ['Confirmed', 'Pending', 'Complete', 'Canceled']:
            if segs.filter(state=state).count() > 0:
                self.state = state
                self.save()
                print '| HAS {0} '.format(state),
                break
            print '| no {0} '.format(state),
        print ' Exiting'
    def delete(self):
        for seg in self.resvsegment_set.all():
            seg.delete()
        super(Resv, self).delete()

class ResvSegment(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    resv = models.ForeignKey('Resv')
    blind = models.ForeignKey('Blind')
    game = models.ForeignKey('Game')
    start_date = models.DateField()
    end_date = models.DateField()
    dog = models.PositiveIntegerField(default=0)
    dog_comment = models.CharField(max_length=100, blank=True)
    state = FSMField(default='Pending')
    standby_state = models.PositiveIntegerField(default=0)
    standby_updated = models.DateTimeField(auto_now_add=True)
    status = models.CharField(choices=RESV_STATES, max_length=10, default='Pending') #Not sure if needed but reincluding now.
    
    @saveme
    def create(self, resv_id, blind_id, owner_id, resv_start_date, state='Pending'):
        print 'seg.create()'
        error = ''
        print resv_id, blind_id, owner_id, resv_start_date, state
        if resv_id == 'new':
            print 'creating a new resv'
            owner = Person.objects.get(pk=owner_id)
            resv = Resv(owner=owner, state=state)
            resv.save()
            resv_id = resv.id
            print 'new resv created'
        print 'set resv'
        self.resv = Resv.objects.get(pk=resv_id)
        self.blind = Blind.objects.get(pk=blind_id)
        self.game = Game.objects.get(pk=1)
        self.start_date = resv_start_date        
        self.end_date = resv_start_date 
        self.state = state
        if not self.blind.can_add_party(self):
            print 'setting state to standby pending'
            self.state = 'Standby - ' + self.state
            error = "standby"
        return error


    @transition(field=state, source=['Pending', 'Held', 'Confirmed'], target='Confirmed', conditions=[rules.fifteen_minutes])
    def confirm(self):
        #TODO: do some checks. 
        print 'Confirming segment', self
    @transition(field=state, source=['Standby - Pending'], target='Standby', conditions=[rules.fifteen_minutes])
    def standby_hold(self):
        #TODO: do some checks. 
        print 'Holding standby', self
    @saveme
    @transition(field=state, source=['Standby'], target='Confirmed', conditions=[rules.standby_on_point])#TODO: add rules to ensure this gets executed right
    def standby_confirm(self):
        #TODO: do some checks. 
        print 'Confirming standby', self
        self.standby_state = 0



    @saveme
    def standby_on_point(self):
        # Set this segment on point for standby
        self.standby_state = 1
        self.standby_updated = timezone.now()
        email.standby_notification(self)

    def standby_is_on_point(self):
       # print 'standby_updated', self.standby_updated
        #print 'confirm window', standby_confirm_window(self.standby_updated, self.start_date) > timezone.now()
        if self.state == 'Standby' and self.standby_state == 1 and self.standby_updated + standby_confirm_window(self.standby_updated, self.start_date) > timezone.now():
            return True
        return False

    @transition(field=state, source=['Confirmed'], target='Complete')
    def complete(self):
        #TODO: do some checks. 
        print 'Completing segment', self
        self.resv.recalc_state()

    @recalc_parent
    @saveme
    @transition(field=state, source=['Pending', 'Held', 'Confirmed', 'Standby - Pending', 'Standby', 'Backup'], target='Canceled', conditions=[rules.cancel_segment])
    def cancel(self): #, recalc_parent=True):
        self.resv.recalc_state()
        pass
    
    @saveme
    @transition(field=state, source=['Pending', 'Held', 'Confirmed'], target='Pending')
    def make_pending(self):
        pass


    def change_state(self, new_status):
        if self.state not in STATUS_MAP[new_status]:
            raise Exception("Error: only {0} segments can be {1}".format(STATUS_MAP[new_status], new_status)) 
        self.state = new_status
        self.save()
        self.resv.recalc_state()

    def can_change_dates(self, new_start_date, new_duration):
        person_count = {'total':self.count_heads(), 'hunters':self.count_hunters()}
        
        new_end_date = new_start_date + dt.timedelta(days=new_duration-1)
        # Check if merely shortening reservation
        if self.start_date <= new_start_date and new_start_date <= self.end_date and new_end_date <= self.end_date:
            return True
        # Check each day to see if there is capacity
        for delta_day in range(0, new_duration):
            test_date = new_start_date + dt.timedelta(days=delta_day)
            if test_date < self.start_date or self.end_date < test_date:
                if not self.blind.check_availability_parties(test_date, self.game, party_count=1):
                    print 'Cannot add date {0} because of party cap'.format(test_date)
                    return False
                if not self.blind.check_availability_people(test_date, self.game, person_count):
                    print 'Cannot add date {0} because of person cap'.format(test_date)
                    return False
        return True
        
    @saveme
    def change_dates(self, new_start_date, new_duration, make_standby_if_full=False):
        # if not available return error
        if not self.can_change_dates(new_start_date, new_duration):
            if make_standby_if_full:
                print 'Making standby'
                self.state = 'Standby - Pending'
            else:
                # add notification here
                print 'Cannot change dates, and make standby flag is False'
                return False
        new_end_date = new_start_date + dt.timedelta(days=new_duration-1)
        # if no risk: just change the dates (risk: dropped dates)
        if new_start_date <= self.start_date and self.end_date <= new_end_date:
            print 'No risk, changing dates'
            self.change_dates_execute(new_start_date, new_duration)
            self.save()
        else: #if risky: create backup, change dates on new copy, leave both as standby (should the old one be 'standby - backup'?)
            print 'Risky, backingup and changing on new segment'
            new_seg = copy_segment(self)
            new_seg.change_dates_execute(new_start_date, new_duration)
            new_seg.state = 'Pending'
            new_seg.save()
            self.state = 'Backup' # should this be 'backup'?
            self.save()
        self.resv.recalc_state()
        return True

    @saveme
    def change_dates_execute(self, new_start_date, new_duration):    
        self.start_date = new_start_date
        self.end_date = new_start_date + dt.timedelta(days=new_duration-1)

        

    def count_heads(self, is_hunting=-1):
        if is_hunting == -1:
            return self.resvsegmentperson_set.count()    
        else:
            return self.resvsegmentperson_set.filter(is_hunting=is_hunting).count()
    def count_hunters(self):
        return self.count_heads(is_hunting=True)
    def count_nonhunters(self):
        return self.count_heads(is_hunting=False)
    def get_persons(self, is_hunting=-1):
        if is_hunting == -1:
            return [rsp.person for rsp in ResvSegmentPerson.objects.filter(resv_segment=self).distinct()]
        else:
            return [rsp.person for rsp in ResvSegmentPerson.objects.filter(resv_segment=self, is_hunting=is_hunting).distinct()]

    def get_segpersons(self):
        return ResvSegmentPerson.objects.filter(resv_segment=self).distinct().order_by('created')

    def remove_person(self, person_id):
        pseg = ResvSegmentPerson.objects.get(resv_segment__id=self.id, person__id=person_id)
        pseg.delete()

    def person_swap(self, person_drop_id, person_add_id):
        #Check some rules
        pseg = ResvSegmentPerson.objects.get(resv_segment__id=self.id, person__id=person_id)
        is_hunting = pseg.is_hunting
        self.remove_person(person_drop_id)
        self.add_person(is_hunting, person_add_id)

    @saveme
    def add_person(self, is_hunting, person_id, force=False):
        print 'Adding person {0} person_id, is_hunting:{1}'.format(person_id, is_hunting)
        print type(is_hunting)
        is_hunting = is_hunting not in [False, 'false', u'false', u'False']
        person = Person.objects.get(id=person_id)
        if not self.blind.can_add_person(self, is_hunting) and not force:
            print 'setting state to standby pending'
            self.state = 'Standby - Pending'
        pseg = update_or_create(model=ResvSegmentPerson, id=-1, resv_segment=self, 
                        person=person, is_hunting=is_hunting, is_guest=person.is_guest)
        

    @saveme
    def set_dog_details(self, has_dog, dog_comment=''):
        self.dog = has_dog
        self.dog_comment = dog_comment

    def set_resv(self, kwargs):
        if kwargs.has_key('resv'):
            print 'kwargs has key'
            if kwargs['resv'] == 'new':
                print 'Creating new resv'
                resv = Resv(owner=self.owner, state='Pending')
                resv.save()
                kwargs.pop('resv')
            else:
                print 'Getting resv {0}'.format(kwargs['resv'])
                resv = Resv.objects.get(pk=kwargs.pop('resv'))
                resv.save()
            print 'Setting resv'
            setattr(self, 'resv', resv)
    
    def get_json(self):
        rep = {'start_date':self.start_date.strftime('%m/%d/%Y'), 'end_date':self.end_date.strftime('%m/%d/%Y'),
        'duration':(self.end_date - self.start_date + dt.timedelta(days=1)).days, 
        'created':str(self.created), 'updated':str(self.updated)}
        rep.update({'seg_id':self.id, 'resv_id':self.resv.id, 'game':self.game.name})
        rep.update({'blind':self.blind.name, 'blind_id':self.blind.id, 'ranch':self.blind.ranch.__unicode__(), 'ranch_id':self.blind.ranch.id, 'ranch_blind':self.blind.__unicode__()})
        rep.update({'dog':self.dog, 'dog_comment':self.dog_comment})
        rep.update({'state':self.state})
        rep['people'] = [[rsp.person.id, rsp.person.__unicode__(), rsp.is_hunting, rsp.is_guest] for rsp in self.get_segpersons()]
        print 'json people'
        print rep['people']
        return rep

    def update(self, **kwargs):
        print 'updating ResvSegment with:'
        print kwargs
        #set_and_pop(self, kwargs, 'owner', 'owner', value)
        if kwargs.has_key('owner'):
            setattr(self, 'owner', Person.objects.get(pk=kwargs.pop('owner')))
        self.set_resv(kwargs)
        if kwargs.has_key('resv_blind'):
            setattr(self, 'blind', Blind.objects.get(pk=kwargs.pop('resv_blind')))
        if kwargs.has_key('resv_start_date'):
            setattr(self, 'start_date', kwargs.pop('resv_start_date'))        
        delta = dt.timedelta(days=0)
        if kwargs.has_key('resv_length'):
            delta = dt.timedelta(days=int(kwargs.pop('resv_length'))-1)
        setattr(self, 'end_date', self.start_date + delta)        
        if kwargs.has_key('resv_game'):
            setattr(self, 'game', Game.objects.get(pk=kwargs.pop('resv_game')))
        print kwargs
        try:
            self.save()            
        except Exception as inst:
            print '##################################################'
            print '############  this save did not work #############'
            print '##################################################'
            print type(inst)
            print inst
            print inst.args

        print 'Setting variables in bulk'
        form_people = []
        for key, value in kwargs.iteritems():
            if key[:6] in ('nonhun', 'hunter') and value != '' and value is not None:                
                print key, value
                form_people.append(int(value))
                self.add_person(key[:6] == 'hunter', value)
            else:
                setattr(self, key, value)
        for p in self.get_persons():
            if p.id not in form_people:
                self.remove_person(p.id)
        self.save()
    def show_me(self):
        print self.resv.owner, self.resv, self.blind, self.start_date
    def __unicode__(self):
        return 'id: {0} - {1}  {2} - {3}  for {4} hunters and {5} nonhunters'.format(self.id, self.blind.__unicode__(), self.start_date, self.end_date, self.count_hunters(), self.count_nonhunters())
    def email_body(self):
        body = ['Property: {0}'.format(self.blind)]
        body.append('Reservation Dates: {0} to {1}'.format(self.start_date, self.end_date))
        body.append('Reservation type: {0}'.format(self.game))
        body.append('Lock combo: {0}'.format(self.blind.ranch.combo))
        hunters = self.resvsegmentperson_set.filter(is_hunting=True)
        if hunters:
            body += ['','Hunters:']
            for resvperson in hunters:
                body.append('- {0} {1}'.format(resvperson.person, ['', '(guest)'][resvperson.is_guest]))
        
        nonhunters = self.resvsegmentperson_set.filter(is_hunting=False)
        if nonhunters:
            body += ['','Nonhunters:']
            for resvperson in nonhunters:
                body.append('- {0} {1}'.format(resvperson.person, ['', '(guest)'][resvperson.is_guest]))
        body.append('<br/>Insert global msg')
        body.append('<br/>Insert property msg')
        body.append('<br/>Insert season msg')
        body.append('<br/>Insert driving directions with map link')
        body.append('<br/>Insert weather forecast link')
        body.append('<br/>Insert local emergency info: <br/>   Local Hospital (phone and address with map link), <br/>   Police (phone and address with map link), <br/>   Animal Hospital(phone and address with map link), <br/>   WU emergency number (phone)')
        return '<br/>'.join(body)

    def delete(self):
        for segpers in self.resvsegmentperson_set.all():
            segpers.delete()

class ResvSegmentPerson(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    resv_segment = models.ForeignKey('ResvSegment')
    person = models.ForeignKey('Person')
    is_hunting = models.BooleanField()
    is_guest = models.BooleanField()

class ResvSegmentGuest(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    resv_segment = models.ForeignKey('ResvSegment')
    guest_name = models.CharField(max_length=50)
    is_hunting = models.BooleanField()

class MembershipState(models.Model): #CA, OR
    name = models.CharField(max_length=2)

class MembershipType(models.Model): #BG, Bird, etc.
    name = models.CharField(max_length=10)
    def __unicode__(self):
        return self.name    

class MembershipBlock(models.Model):
    name = models.CharField(max_length=10)

class MembershipStatus(models.Model): #Current, delinq, etc.
    status = models.CharField(max_length=20)

class Family(models.Model):
    created = models.DateTimeField(auto_now_add=True) #specific to the user model
    updated = models.DateTimeField(auto_now=True)  #specific to the user model
    joined = models.DateField() #specific to the actual membership
    number = models.CharField(max_length=10)
    membership_type = models.ForeignKey('MembershipType')
    status = models.ForeignKey('MembershipStatus')
    block = models.ForeignKey('MembershipBlock')
    is_retired = models.BooleanField()
    resv_freeze = models.BooleanField()
    is_plus = models.BooleanField()
    membership_state = models.ForeignKey('MembershipState')
    
    def get_blocking_resv(self):
        return filter_blockers_only(Resv.objects.filter(resvsegment__resvsegmentperson__person__family=self))
    def get_blocking_segs(self):
        return filter_blockers_only(ResvSegment.objects.filter(resvsegmentperson__person__family=self))
    def get_future_blocking_resv(self):
        return filter_future_blockers_only(self.get_blocking_resv())
    def get_past_blocking_resv(self):
        return filter_past_blockers_only(self.get_blocking_resv())
    def get_membership_type(self):
        return '{0}{1}'.format(self.membership_type, ['', ' Plus'][self.is_plus])


class PersonManager(BaseUserManager):
    def _create_user(self, member_number, email, password, dob, first_name, last_name, 
            id_number, is_superuser=False, is_staff=False, is_guest=False, **extra_fields):
        family = Family.objects.get(number=member_number)
        if not email:
            raise ValueError('An email address is required')
        email = self.normalize_email(email)
        user = self.model(family=family, email=email, date_of_birth=dob, 
                    first_name=first_name, last_name=last_name, id_number=id_number, 
                    is_superuser=is_superuser, is_staff=is_staff, is_guest=is_guest, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_user(self, email, password=None, **extra_fields):
        return self._create_user(email=email, password=password, is_staff=False, is_superuser=False,
                                 **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        return self._create_user(email=email, password=password, is_staff=True, is_superuser=True, is_guest=False,
                                 **extra_fields)

class Person(AbstractBaseUser, PermissionsMixin):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    family = models.ForeignKey('Family')
    date_of_birth = models.DateField()
    first_name = models.CharField(max_length=40)
    last_name = models.CharField(max_length=40)
    email = models.EmailField(max_length=255, unique=True)
    USERNAME_FIELD = 'email'
    id_number = models.CharField(max_length=20) #Driver's, passport, etc.
    is_guest = models.CharField(max_length=1)
    REQUIRED_FIELDS = ['family', 'date_of_birth', 'first_name', 'last_name', 'id_number', 'is_guest']
    is_active = models.BooleanField(default=True) #for Django Auth
   # is_superuser = models.BooleanField(default=False) #for Django Auth  #name collision
    is_staff = models.BooleanField(default=True) #for Django Auth

    objects = PersonManager()
    
    def get_short_name(self):
        return self.first_name
    def get_long_name(self):
        return '{0} {1}'.format(self.first_name, self.last_name)
    def email_user(self, subject, message, from_email=None):
        send_mail(subject, message, from_email, [self.email])
    def get_resv(self):
        return Resv.objects.filter(resvsegment__resvsegmentperson__person=self)
    def get_blocking_resv(self):
        return filter_blockers_only(Resv.objects.filter(resvsegment__resvsegmentperson__person=self))
    def get_blocking_segs(self):
        return filter_blockers_only(ResvSegment.objects.filter(resvsegmentperson__person=self))
    def get_future_blocking_resv(self):
        return filter_future_blockers_only(self.get_blocking_resv())
    def get_past_blocking_resv(self):
        return filter_past_blockers_only(self.get_blocking_resv())
    def get_confirmed_segs(self):
        return self.get_blocking_segs().filter(state='Confirmed')
    def get_future_confirmed_segs(self):
        return filter_future_blockers_only(self.get_blocking_segs().filter(state='Confirmed'), is_resv=False)
    def get_membership_type(self):
        if self.is_guest == '1':
            return 'Guest'
        return self.family.get_membership_type()
    def get_delegated_to(self):
        return self.family.person_set.all()
    def __unicode__(self):
        return '{0} {1}'.format(self.first_name, self.last_name)
def create_person(member_number, email, password, dob, first_name, last_name, id_number, is_guest=False):
    print 'create person called'
    family = Family.objects.get(number=member_number)
    print 'Found family', family
    person = Person(family=family, email=email, date_of_birth=dob, first_name=first_name, last_name=last_name, id_number=id_number, is_guest=is_guest)
    print 'Person obj created', person
    person.set_password(password)
    print 'Set password'
    person.save()
    print 'saved, returning'
    return person
 
def person_exists(email):
    try:
        Person.objects.get(email=email)
        return True
    except ObjectDoesNotExist:
        return False
    except MultipleObjectsReturned:
        print 'Error: multiple objects'
        raise 

class Address(models.Model):
    person = models.ForeignKey('Person') #is there a way to make this either person or family?
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    is_primary = models.BooleanField()
    is_primary_family = models.BooleanField()
    line1 = models.CharField(max_length=40)
    line2 = models.CharField(max_length=40)
    city = models.CharField(max_length=40)
    state = models.CharField(max_length=2)
    zip_code = models.CharField(max_length=5)
    lat = models.FloatField()
    lon = models.FloatField()

class MastChangeLog(models.Model):
    change_time = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey('Person', related_name='actor')
    member = models.ForeignKey('Person', related_name='member')
    change_type = models.CharField(max_length=40)
    model_name = models.CharField(max_length=40)
    instance_pk = models.PositiveIntegerField(blank=True)
    initial_value = models.CharField(max_length=40)
    new_value = models.CharField(max_length=40)

#class StandbyTracker(models.Model):
#    blind = models.ForeignKey('Blind')

# Warnings - person or family level
# 


#######################################################
############  Standby Functions  ######################
#######################################################

def find_standby(resv_date, blind):
    segs = ResvSegment.objects.filter(state='Standby', blind=blind, start_date__lte=resv_date, end_date__gte=resv_date).order_by('created')
    if segs.count() > 0:
        return segs[0]
    return False
    
def expire_on_point(seg):
    pass

def notify_standby(seg):
    email.standby_notification(seg)

def put_seg_on_point(seg):
    print 'Putting seg on point: ', seg
    seg.standby_on_point()
    seg.save()


def check_standby_list(take_action=False, resv_date=False, blind=False):
    # Find all current standby segments, ordered by created date
    segs = ResvSegment.objects.filter(state='Standby', end_date__gte=dt.date.today()).order_by('standby_updated')
    if resv_date: # If we're looking for segs on one particular day
        segs = segs.filter(start_date__lte=resv_date, end_date__gte=resv_date)
    
    #Cycle through segs, if there is at least partial availability, take action (if take_action == True)
    for seg in segs:
        print '################################'
        print 'Checking seg: ', seg
        #try something like this:
        can_upgrade = seg.blind.can_upgrade_standby(seg)
                #Works when full
                #Does not work when party limit ==1, and first party just cancelled.
        print '     Can upgrade response: ', can_upgrade
        if can_upgrade in ['yes', 'partial']:
            if take_action:
                print '... taking action'
                put_seg_on_point(seg)


#######################################################
############  Chron Functions  ########################
#######################################################

def expire_pending():
    segs = filter_expired_pending_only(ResvSegment.objects.all())
    segs.update(state="Expired")
    segs.save()



#######################################################
############  trash  ########################
#######################################################


def garbage():
    blinds = Blind.objects.filter(resvsegment__state='Pending')
    if blind:
        segs = segs.filter(blind=blind)
        blinds = blinds.filter(pk=blind.id)
    
    for blind in blinds:
        print 'Standby: checking blind: {0}'.format(blind)
        blind_segs = segs.filter(blind=blind)
        print blind_segs
        max_date = blind_segs.aggregate(Max('end_date'))
        min_date = blind_segs.aggregate(Min('start_date'))
        print min_date
        for di in range((max_date - min_date).days + 1):
            find_next = True
            idate = min_date + dt.timedelta(days=di)
            print '    Looking at date {0}'.format(idate)
            if blind.can_add_standby():
                blind_segs_dt_range = blind_segs.filter(start_date__lte=idate, end_date__gte=idate)
                blind_segs_onpoint = blind_segs_dt_range.filter(standby_state=1)
                if 0 < blind_segs_onpoint.count():
                    print '        Seg on point',
                    if blind_segs_onpoint[0].has_standby_expired():
                        print ' but it is expired, cancelling'
                        blind_segs_onpoint[0].cancel()
                        blind_segs_onpoint[0].save()
                    else:
                        find_next = False
                next_segs = blind_segs_dt_range.filter(standby_state=0).order_by('created')
                found_winner = False
                for nseg in next_segs:
                    #check if standby people are on hold for something else
                    if not found_winner:
                        if take_action:
                            print 'Putting seg on point: ', nseg
                            nseg.standby_on_point()
                            nseg.save()
                        found_winner = True


                # Are there  standby resvs on point?
                    # Has their window expired?
                        #No: Break for this date/blind
                        #Yes: expire and go to next in line
                # No one on point (or we just expired someone):
                    # Go to next seg in line:
                        # Check if the standby people have another standby seg that is waiting for them to confirm/skip/cancel
                        # if take_action
                            # Put them on point and notify



