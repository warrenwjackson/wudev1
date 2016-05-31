import datetime as dt
from django.db.models import Q
from django.utils import timezone
from notifications import notify




def print_rule(rule):    
    def exec_rule(*args, **kwargs):
        print 'Checking rule {0}...{1}'.format(rule.func_name, ' '*30)[:50],
        result = rule(*args, **kwargs)
        if result:
            print '    Passed!!!!'
        else:
            print '    FAILED'.format(rule.func_name)
        return result
    return exec_rule

@print_rule
def has_blocking_segs(resv):
    ''' Make sure there is at least one valid pending segment to confirm'''
    if resv.get_valid_pending_segs().count() == 0:
        notify.send(resv, recipient=resv.owner, verb=u'There were no changes to confirm.  Pehaps a pending segment expired?  Make sure to confirm all changes within 15 minutes.')
        return False
    return True

@print_rule
def one_resv_per_member(resv):
    ''' A membership family can have more than one reservation of a given type, but no individual within that family may have more than one reservation at a time of a same type.
        Once the last day of a reservation is over, a member may make a new reservation of the same type. '''
    print ''
    print resv.id
    for person in resv.get_persons(): 
        #print person
        if 0 < person.get_future_confirmed_segs().filter(      
                            Q(game__game_type__in=resv.get_game_type_list()),
                            ).exclude(resv=resv).distinct().count():
            notify.send(person, recipient=resv.owner, verb=u'{0} has another reservation for the same game type'.format(person.get_long_name()))
            return False
    return True

@print_rule
def max_resv_length(resv):
    ''' Max reservation length: 7 days. 
        A reservation day is over when a member checks out, or at midnight. 
        Once a reservation day is over, members can extend their reservation by a day.  Member can only hold 7 days at a time. '''
    if not(_max_resv_length(resv.get_start_date(), resv.get_end_date(), max_length=7)):
        notify.send(resv, recipient=resv.owner, verb=u'Reservations can be up to 7 days long')
        return False
    return True
def _max_resv_length(start_date, end_date, max_length=7):
    return not(end_date - max([start_date,dt.date.today()]) >= dt.timedelta(days=max_length))

@print_rule
def continuous_and_one_per_day(resv, exclude_segs=False):
    ''' All days within a reservation must be consecutive. 
        Multi-activity reservation are allowed, but each activity type must be consecutive. 
        '''    
    prev_end_date = dt.date(1900,1,1)
    segs = resv.get_future_blocking_segs_no_sb()
    
    if exclude_segs:
        segs = segs.exclude(id__in=exclude_segs)
    for seg in segs.order_by('start_date'):
        if prev_end_date != dt.date(1900,1,1):
            delta = seg.start_date - prev_end_date 
            print seg
            print delta.days
            if delta.days > 1:
                error_str = u'All days within a reservation must be consecutive.'
                notify.send(seg, recipient=resv.owner, verb=error_str)
                return False
            if delta.days < 1:
                notify.send(seg, recipient=resv.owner, verb=u'Only one ranch may be booked per day')    
                return False
        
        prev_end_date = seg.end_date
    return True

@print_rule
def no_splitting_weekends(resv):
    ''' Splitting weekends is not allowed: no Sun-Sat reservations. '''
    return True
@print_rule
def fifteen_minutes(seg):
    ''' Can only confirm a pending segment within 15 mins'''
    if seg.state == 'Pending':
        if seg.updated > timezone.now() - dt.timedelta(minutes=15):
            return True
        else:
            notify.send(seg, recipient=seg.resv.owner, verb=u'Pending segment expired - please retry and confirm within 15 minutes.')
            return False
    return True

@print_rule
def one_day_one_resv(resv):
    ''' Can only reserve one property per day'''
    for person in resv.get_persons():
        for seg in person.get_confirmed_segs().filter( 
                            ).exclude(resv=resv).distinct():
            if resv.get_start_date() <= seg.end_date and seg.start_date <= resv.get_end_date():
                notify.send(person, recipient=resv.owner, verb=u'{0} has another reservation at the same time'.format(person.get_long_name()))
                return False
    return True

@print_rule
def cant_book_closed_day(resv):
    ''' Make sure that a blind or ranch can't be booked on a non-shoot day or other special closed day 
        But, still allow booking during special open days, regardless of shoot day (e.g., new years)
    '''
    for seg in resv.get_future_blocking_segs():
        if not seg.blind.are_all_shoot_days(seg.start_date, seg.end_date):
            notify.send(seg, recipient=seg.resv.owner, verb=u'{0} is closed on one or more of the days you are trying to book'.format(seg.blind.__unicode__()))   
            return False
    return True

@print_rule
def early_season_resv_length_limit(self, resv):
    ''' Most WF properties limited to 1-day hunts for first 9 days of season. '''
    pass
    
@print_rule
def one_turkey_hunter(self, resv):
    ''' Only one hunter per *segment* per membership.  Plus members can have additional. '''
    pass

@print_rule
def guest_48_hours(self, resv):
    ''' Guests can only be booked 48 hours in advance, unless the member is a plus'''
    tminus = resv.resv.get_start_date() - dt.datetime.now()

    if not resv.owner.family.is_plus and resv.count_guests() > 0 and tminus > dt.timedelta(hours=48):
        notify.send(resv, recipient=resv.owner, verb=u'You can only add guests within 48 hours of a reservation, unless you are a plus member')   
        return False
    return True

@print_rule
def standby_on_point(seg):
    return seg.standby_is_on_point()

@print_rule
def cancel_segment(seg):
    return True
