"""This module includes much of the core functionality of Cyclence."""

from datetime import date, timedelta
from itertools import count
from collections import namedtuple
from math import ceil
from uuid import uuid4

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref
from sqlalchemy import (Column, Integer, String, Boolean, DateTime, ForeignKey)

CyclenceBase = declarative_base()

DUE = 'due'
OVERDUE = 'overdue'
NOT_DUE = 'not due'

class RecurringTask(CyclenceBase):
    "Represents a recurring task."

    __tablename__ = "recurring_tasks"
    task_id = Column(UUID, primary_key=True)
    name = Column(String)
    length = Column(Integer)
    first_due = Column(DateTime, nullable=True)
    allow_early = Column(Boolean)
    points = Column(Integer)
    decay_length = Column(Integer)
    notes = Column(String)

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
        self.task_id = uuid4()
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
            
        #Internal state setup
        self.completion_history = []

    @property
    def dueity(self):
        '''Returns a string representing the due status of this task.
        Can be either: 'not due', 'due', or 'overdue' '''
        today = date.today()
        duedate = self.duedate
        if duedate < today:
            return RecurringTask.OVERDUE
        elif duedate > today:
            return RecurringTask.NOT_DUE
        else:
            return RecurringTask.DUE

    @property
    def is_due(self):
        '''Whether this task is due'''
        return self.dueity == RecurringTask.DUE
            
    @property
    def is_overdue(self):
        '''Whether this task is overdue'''
        return self.dueity == RecurringTask.OVERDUE
    
    @property
    def is_not_due(self):
        '''Whether this task is not due yet'''
        return self.dueity == RecurringTask.NOT_DUE


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
        c = CompletionRec(completed_on = completed_on,
                          points_earned = points_earned,
                          days_late = completed_on - self.duedate,
                          recorded_on = today)
        self.completion_history.append(c)
            

    def __repr__(self):
        return '{name} starts on {date} and recurs every {length}'\
            .format(name = self.name,
                    date = date_str(self.first_due),
                    length = time_str(self.length.days))


    @property
    def last_completed(self):
        '''Returns the last time the task was completed. If the task has never
        been completed, returns None'''
        if self.completion_history:
            return self.completion_history[-1].completed_on
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

class Completion(CyclenceBase):
    r'''Represents a completion of a task'''
    __tablename__ = 'completions'
    
    completed_on = Column(DateTime, primary_key=True)
    task_id = Column(UUID)
CompletionRec = namedtuple('CompletionRec',
                           ['completed_on',
                            'points_earned',
                            'recorded_on',
                            'days_late',
                            ])

class EarlyCompletionException(Exception):
    '''Thrown when a task is completed ahead of its due date and allow_early is
    False'''
    pass

class FutureCompletionException(Exception):
    '''Thrown when a task is completed with a completion date that is in the
    future'''
    pass

def point_award(duedate, completed_on, decay_length, max_points):
    '''Calculates how many points a completion of a task on a certain date is
    worth, given the `duedate`, when it was `completed_on`, the `decay_length`
    and the `max_points` the task is worth'''
    if duedate >= completed_on:
        return max_points
    elif completed_on >= duedate + decay_length:
        return 0
    else:
        days_late = (completed_on - duedate).days
        points_per_day = max_points / float(decay_length.days)
        return max_points - int(ceil(points_per_day * days_late))
        
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
