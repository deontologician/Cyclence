# Copyright 2013 Josh Kuhn

# This file is part of Cyclence.

# Cyclence is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.

# Cyclence is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for
# more details.

# You should have received a copy of the GNU Affero General Public License
# along with Cyclence.  If not, see <http://www.gnu.org/licenses/>.

'''Utility functions for Cyclence'''
from datetime import datetime, timedelta, date

def relative_time(dt):
    if dt is None:
        return "never"
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
    if dt is None:
        return 'never'
    else:
        return dt.strftime('%b %d, %Y')

def fmt_time(dt):
    r"""Returns a datetime as a human readable string"""
    if dt is None:
        return 'never'
    else:
        if dt == datetime.today():
            return dt.strftime('%I:%M%p')
        else:
            return dt.strftime('%b %d, %Y %I:%M%p')

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
