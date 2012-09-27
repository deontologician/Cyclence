"""This module includes much of the core functionality of Cyclence."""

from datetime import date, datetime, timedelta
from itertools import count
from math import ceil
from uuid import uuid4
from hashlib import md5

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID, INTERVAL
from sqlalchemy.orm import relationship, backref
from sqlalchemy import (Column, Integer, String, Boolean, Date, DateTime, ForeignKey)

CyclenceBase = declarative_base()

DUE = 'due'
OVERDUE = 'overdue'
NOT_DUE = 'not due'

class Task(CyclenceBase):
    "Represents a recurring task."

    __tablename__ = "tasks"
    task_id = Column(UUID, primary_key=True)
    user_email = Column(String, ForeignKey('users.email'))
    name = Column(String)
    length = Column(INTERVAL)
    first_due = Column(Date, nullable=True)
    allow_early = Column(Boolean)
    points = Column(Integer)
    decay_length = Column(INTERVAL)
    notes = Column(String)

    user = relationship('User', backref='tasks')

    def __init__(self, name, length, first_due=None, allow_early=True,
                 points=100, decay_length=None, tags=None, notes=None):
        r"""
        `name` is the title of the recurring task
        `length` is a timedelta representing how long this recurrence takes
        `first_due` is the first time this should task should be due
        `allow_early` is whether this task can be completed before its 
            recurrence date
        `points` is how many points this task is worth if completed on time
        `decay_length` is how long it should be before completing this task is 
            worth 0 points
        `tags` are user defined tags for this task
        `notes` is any notes associated with this task
        """
        self.task_id = str(uuid4())
        self.name = name
        self.length = length if type(length) is timedelta else timedelta(length)
        self.allow_early = allow_early
        self.points = points
        self.tags = set(tags) if tags else set()

        if decay_length is None:
            self.decay_length = self.length
        elif type(decay_length) is timedelta:
            self.decay_length = decay_length
        else:
            self.decay_length = timedelta(decay_length)

        if first_due is None:
            # set to due 'tomorrow'
            self.first_due = date.today() + timedelta(1)
        else:
            self.first_due = first_due
            
        self.notes = notes

    @property
    def dueity(self):
        '''Returns a string representing the due status of this task.
        Can be either: 'not due', 'due', or 'overdue' '''
        today = date.today()
        duedate = self.duedate
        if duedate < today:
            return OVERDUE
        elif duedate > today:
            return NOT_DUE
        else:
            return DUE

    @property
    def is_due(self):
        '''Whether this task is due'''
        return self.dueity == DUE
            
    @property
    def is_overdue(self):
        '''Whether this task is overdue'''
        return self.dueity == OVERDUE
    
    @property
    def is_not_due(self):
        '''Whether this task is not due yet'''
        return self.dueity == NOT_DUE


    def complete(self, completed_on = None):
        '''Complete the recurring task.'''
        today = date.today()
        if completed_on is None:
            completed_on = today

        if completed_on > today:
            raise FutureCompletionException('The completion date cannot be in '
                                        'the future.')
        if self.is_not_due and completed_on < self.duedate:
            raise EarlyCompletionException("This task isn't due until {0}, and is "
                                       "not allowed to be completed early.".
                                       format(date_str(self.duedate)))
        # calculate days_late, calculate points
        points_earned = self.duedate
        self.completions.append(Completion(completed_on = completed_on,
                                           points_earned = points_earned,
                                           days_late = completed_on - self.duedate,
                                           recorded_on = today))
            

    def __repr__(self):
        return '{name} starts on {date} and recurs every {length}'\
            .format(name = self.name,
                    date = date_str(self.first_due),
                    length = time_str(self.length.days))


    @property
    def last_completed(self):
        '''Returns the last time the task was completed. If the task has never
        been completed, returns None'''
        if self.completions:
            return self.completions[-1].completed_on
        else:
            return None

    @property
    def duedate(self):
        '''Returns the date the task is due.'''
        last = self.last_completed

        if last is None:
            return self.first_due
        else:
            return last + self.length

    def due_schedule(self):
        '''An infinite generator that produces the next and future due dates of
        this task. If the task is overdue, it only produces today.'''
        if self.is_overdue:
            yield date.today()
            return
        yield self.duedate
        for i in count(1):
            yield self.duedate + i*self.length

    
    def point_worth(self, completed_on=None):
        '''Calculates how many points completing the task on the given date is
        worth, given the `duedate`, when it was `completed_on`, the
        `decay_length` and the `max_points` the task is worth'''
        completed_on = completed_on or date.today()
        if self.duedate >= completed_on:
            return self.points
        elif completed_on >= self.duedate + self.decay_length:
            return 0
        else:
            days_late = (completed_on - self.duedate).days
            points_per_day = self.points / float(self.decay_length.days)
            return self.points - int(ceil(points_per_day * days_late))

    def hue(self, completed_on=None):
        '''A tuple representing the color that represents how overdue the item
        is (in HSL notation). Going from green on the duedate to red when the
        decay_length is exhausted.'''
        hsl = '{},{}%,{}%'
        completed_on = completed_on or date.today()
        days_late = (completed_on - self.duedate).days
        percent_due = (days_late / float(self.decay_length.days))
        if days_late < 0 and not self.allow_early:
            return hsl.format(0, 0, 75) #grey
        elif days_late < 0 and self.allow_early:
            #somewhere between grey and green
            s = percent_due * 100
            return hsl.format(120, s, 75)
        elif days_late >= self.decay_length.days:
            return hsl.format(0, 100, 50) #red
        else:
            return hsl.format(120 * (1 - percent_due), 100, 50)


class Completion(CyclenceBase):
    r'''Represents a completion of a task'''
    __tablename__ = 'completions'
    
    task_id = Column(UUID, ForeignKey('tasks.task_id'), primary_key=True)
    completed_on = Column(Date, primary_key=True)
    points_earned = Column(Integer)
    recorded_on = Column(DateTime)
    days_late = Column(Integer)

    task = relationship("Task", backref=backref("completions", order_by=completed_on))

class User(CyclenceBase):
    r'''Represents a user in the system'''
    __tablename__ = 'users'
    
    email = Column(String, primary_key=True)
    name = Column(String)
    firstname = Column(String)
    lastname = Column(String)
    
    @property
    def gravatar_url(self):
        return 'http://www.gravatar.com/avatar/{hash}'.format(
            hash = md5(self.email).hexdigest())
        


class EarlyCompletionException(Exception):
    '''Thrown when a task is completed ahead of its due date and allow_early is
    False'''
    pass

class FutureCompletionException(Exception):
    '''Thrown when a task is completed with a completion date that is in the
    future'''
    pass

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
