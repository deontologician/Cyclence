'''Utility functions for Cyclence'''
from datetime import datetime, timedelta, date

def relative_time(dt):
    if isinstance(dt, datetime):
        dt = dt.date()
    today = date.today()
    delta = dt - today
    if delta == timedelta(0):
        fmt = 'today'
    elif delta == timedelta(-1):
        fmt = 'yesterday'
    elif delta == timedelta(1):
        fmt = 'tomorrow'
    elif delta < timedelta(0):
        fmt = '{num} {units} ago'
    elif delta > timedelta(0):
        fmt = 'in {num} {units}'
    days = abs(delta.days)
    if days < 7:
        num = days
        units = 'days'
    elif 7 <= days < 30:
        num = days / 7
        units = 'weeks' if num != 1 else 'week'
    elif 30 <= days < 365:
        num = int(days / 30)
        units = 'months' if num != 1 else 'month'
    else:
        num = int(days / 365.25)
        units = 'years' if num != 1 else 'year'
    return fmt.format(num=num, units=units)

def date_str(dt):
    """Returns a human readable date used throughout Cyclence to represent dates
    as strings"""
    return dt.strftime('%b %d, %Y')

def time_str(length):
    '''Returns a human comprehensible string from length. Either a timedelta can
    be passed in, or a integer representing a number of days can be passed in.
       
       >>> time_str(3)
       '3 days'
       >>> time_str(10)
       '1 week, 3 days'
       >>> time_str(366)
       '1 year, 1 day'
       >>> time_str(0)
       'never'
       >>> time_str(timedelta(14))
       '2 weeks'
    '''
    if type(length) is timedelta:
        days = length.days
    else:
        days = length

    if days == 0:
        return 'never'

    #pluralizer
    def pl(word, i):
        if i == 0 or i > 1:
            return '{0}s'.format(word)
        else:
            return word

    result = []
    while days != 0:
        if days // 365 > 0:
            years = days // 365
            result.append('{0} {1}'.format(years, pl('year',years)))
            days = days % 365
        elif days // 7 > 0:
            weeks = days // 7
            result.append('{0} {1}'.format(weeks, pl('week',weeks)))
            days = days % 7
        else:
            result.append('{0} {1}'.format(days, pl('day', days)))
            days = 0

    return ', '.join(result)
