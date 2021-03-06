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

"""This module includes much of the core functionality of Cyclence."""

from __future__ import print_function

from datetime import date, timedelta, datetime
from itertools import count
from math import ceil
from uuid import uuid4
from hashlib import md5

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.dialects.postgresql import UUID, INTERVAL
from sqlalchemy.orm import relationship, column_property
from sqlalchemy.orm.session import object_session
from sqlalchemy import (Column, Integer, String, Boolean, Date, DateTime,
                        ForeignKey, Table, select, func)

from cyclence import utils

CyclenceBase = declarative_base()

DUE = 'due'
OVERDUE = 'overdue'
NOT_DUE = 'not due'

class Notification(CyclenceBase):
    r'''Represents a notification in the system'''
    __tablename__ = 'notifications'

    notification_id = Column(UUID, primary_key=True)
    email = Column(String, ForeignKey('users.email'))
    timestamp = Column(DateTime)
    message = Column(String)
    noti_type = Column(String)
    sender = Column(String, ForeignKey('users.email'), nullable=True)
    task_id = Column(UUID, ForeignKey('tasks.task_id'), nullable=True)

class Tag(CyclenceBase):
    r'''Represents a tag attached to a specific Task'''
    __tablename__ = 'tasktags'

    task_id = Column(UUID, ForeignKey('tasks.task_id'),
                     primary_key=True)
    tag_name = Column(String, primary_key=True)

    def __init__(self, task_id, tag_name):
        self.task_id = task_id
        self.tag_name = tag_name

    def __str__(self):
        return self.tag_name

    def __repr__(self):
        return 'Tag({}, {})'.format(self.task_id, self.tag_name)

class Completion(CyclenceBase):
    r'''Represents a completion of a task'''
    __tablename__ = 'completions'

    task_id = Column(UUID, ForeignKey('tasks.task_id'), primary_key=True)
    completed_on = Column(Date, primary_key=True)
    points_earned = Column(Integer)
    recorded_on = Column(DateTime)
    days_late = Column(Integer)
    email = Column(String, ForeignKey('users.email'), nullable=False,
                   index=True)

    completer = relationship('User')


usertasks = Table('taskuser', CyclenceBase.metadata,
    Column('task_id', UUID, ForeignKey('tasks.task_id'), primary_key=True),
    Column('email', String, ForeignKey('users.email'), primary_key=True)
)

class Task(CyclenceBase):
    "Represents a recurring task."

    __tablename__ = "tasks"
    task_id = Column(UUID, primary_key=True)
    name = Column(String)
    length = Column(INTERVAL)
    first_due = Column(Date, nullable=True)
    allow_early = Column(Boolean)
    points = Column(Integer)
    decay_length = Column(INTERVAL)
    notes = Column(String)

    last_completed = column_property(
        select([func.max(Completion.completed_on)])
        .where(Completion.task_id == task_id))

    users = relationship('User', secondary=usertasks,
                         backref='tasks')
    _tags = relationship('Tag', collection_class=set,
                         cascade="all, delete, delete-orphan")
    completions = relationship("Completion", lazy="dynamic", backref="task",
                               cascade="all, delete, delete-orphan")

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

        if tags:
            self.add_tags(tags)
        self.notes = notes

    @property
    def tags(self):
        '''Tags on this task'''
        return {t.tag_name for t in self._tags}

    @tags.setter
    def tags(self, new_tags):
        '''Set tags'''
        self._tags.clear()
        self.add_tags(new_tags)

    def add_tags(self, tags):
        '''Allows adding tags'''
        for tag in tags:
            t = Tag(self.task_id, tag.strip())
            self._tags.add(t)

    def remove_tag(self, tag_name):
        '''Removes a tag from the task'''
        t = s.query(Tag).get((self.task_id, tag_name))
        self._tags.remove(t)

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


    def complete(self, completer, completed_on=None):
        '''Complete the recurring task.'''
        today = date.today()
        completed_on = completed_on or today

        if completed_on > today:
            raise FutureCompletionException('The completion date cannot be in '
                                            'the future.')
        if self.last_completed == completed_on:
            raise AlreadyCompletedException(
                'This is already recorded as being completed on {}'
                .format(completed_on))
        # calculate days_late, calculate points
        self.completions.append(
            Completion(completed_on = completed_on,
                       points_earned = self.point_worth(completed_on),
                       days_late = (completed_on - self.duedate).days,
                       recorded_on = today,
                       email=completer.email))


    def __repr__(self):
        return '{name} starts on {date} and recurs every {length}'\
            .format(name = self.name,
                    date = utils.date_str(self.first_due),
                    length = utils.time_str(self.length.days))


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
        if self.duedate > completed_on and not self.allow_early:
            return 0
        days_off = abs((self.duedate - completed_on).days)
        points_per_day = self.points / float(self.decay_length.days)
        return max(0, self.points - int(ceil(points_per_day * days_off)))

    @property
    def sort_value(self):
        r'''A single number that represents the priority of this task.'''
        if self.is_not_due and not self.allow_early:
            return 0
        today = date.today()
        zero = self.duedate - self.decay_length
        mult = max(0, (today - zero).days)
        days_late = max(0, (today - self.duedate).days)
        return self.points * (mult + days_late) # double count late days


friendships = Table('friendships', CyclenceBase.metadata,
    Column('email_1', String, ForeignKey('users.email'), primary_key=True),
    Column('email_2', String, ForeignKey('users.email'), primary_key=True)
)

class User(CyclenceBase):
    r'''Represents a user in the system'''
    __tablename__ = 'users'

    email = Column(String, primary_key=True)
    name = Column(String)
    firstname = Column(String)
    lastname = Column(String)

    _followers = relationship('User', secondary=friendships,
                              primaryjoin=friendships.c.email_1==email,
                              secondaryjoin=friendships.c.email_2==email,
                              backref='_followees')

    notifications = relationship(Notification, order_by=Notification.timestamp.desc(),
                                 backref='user',
                                 primaryjoin='User.email == Notification.email',
                                 cascade='all, delete, delete-orphan')
    @property
    def total_points(self):
        r'''Returns the total number of points earned by this user'''
        return object_session(self).query(func.sum(Completion.points_earned))\
                                              .filter_by(email=self.email).one()[0]

    def share_task(self, task, sharer):
        r'''Share a task with this user'''
        self.notify('share', '{.name} has shared the task "{.name}" with you'
                    .format(sharer, task), sender=sharer.email,
                    task_id=task.task_id)

    def befriend(self, sender):
        self.notify('befriend', '{.name} wants to be friends!'.format(sender),
                    sender=sender.email)

    def notify(self, noti_type, msg, task_id=None, sender=None):
        self.notifications.append(Notification(notification_id=str(uuid4()),
                                               email=self.email,
                                               timestamp=datetime.now(),
                                               message=msg,
                                               noti_type=noti_type,
                                               task_id=task_id,
                                               sender=sender,
                                               ))

    @property
    def friends(self):
        return self._followers + self._followees

    @property
    def gravatar_url(self):
        return 'http://www.gravatar.com/avatar/{hash}'.format(
            hash = md5(self.email).hexdigest())

class AlreadyCompletedException(Exception):
    '''Thrown when a task is completed on a date it has already been completed
    on'''
    pass

class FutureCompletionException(Exception):
    '''Thrown when a task is completed with a completion date that is in the
    future'''
    pass
