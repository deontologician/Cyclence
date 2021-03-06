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

from __future__ import print_function

import os
import os.path
from os.path import join as ojoin
from base64 import urlsafe_b64decode as b64decode
from uuid import uuid4
from datetime import date, datetime, timedelta
from functools import wraps

from tornado import ioloop, web, auth, escape
from tornado.httpclient import HTTPError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import cyclence.Calendaring as orm
from cyclence.utils import date_str

UUID_REGEX = r'[\dA-Fa-f]{8}-[\dA-Fa-f]{4}-[\dA-Fa-f]{4}'\
          '-[\dA-Fa-f]{4}-[\dA-Fa-f]{12}'

DATE_REGEX = r'[\d]{4}-[\d]{2}-[\d]{2}'

def rollback_on_failure(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        try:
            method(self, *args, **kwargs)
        except:
            self.session.rollback()
            raise
    return wrapped

def parsedate(datestr):
    'Parses a date in ISO8601 format'
    if not datestr:
        return None
    return datetime.strptime(datestr, '%Y-%m-%d').date()

class BaseHandler(web.RequestHandler):

    def initialize(self, *args, **kwargs):
        self.session = sessionmaker(bind=self.application.engine)()

    def on_finish(self):
        self.session.close()

    @property
    def json(self):
        if not hasattr(self, '_json'):
            self._json = escape.json_decode(self.request.body)
        return self._json


    def get_current_user(self):
        if not hasattr(self, '_user'):
            email = self.get_secure_cookie('user')
            if not email:
                return None
            self._user = self.session.query(orm.User).filter(orm.User.email == email).first()
        return self._user

    def redirect(self, url, permanent=False, status=303):
        try:
            web.RequestHandler.redirect(self, url.url, permanent, status)
        except AttributeError:
            web.RequestHandler.redirect(self, url, permanent, status)

def build_handlers(*args):
    return [(h.url, h) for h in args]

class CyclenceApp(web.Application):
    r'''Customized application for Cyclence that includes database
    initialization'''
    def __init__(self, debug=False):
        handlers = build_handlers(Main,
                                  Login,
                                  Logout,
                                  Google,
                                  Tasks,
                                  Task,
                                  NewTask,
                                  EditTasks,
                                  EditTask,
                                  ShareTask,
                                  DeleteTask,
                                  Completion,
                                  Notifications,
                                  Notification,
                                  Friends,
                                  Invite,
                                  )
        settings = dict(
            cookie_secret=os.getenv('CYCLENCE_COOKIE_SECRET'),
            login_url='/login',
            template_path=os.path.join(os.path.dirname(__file__), 'tpl'),
            debug=True if os.getenv('CYCLENCE_DEBUG') == 'true' else False,
            static_path=os.path.join(os.path.dirname(__file__), "../../static"),
            )
        self.engine = create_engine(self.connection_string, echo=debug)

        web.Application.__init__(self, handlers, **settings)

    @property
    def connection_string(self):
        try:
            return self._connection_string
        except AttributeError:
            self._connection_string = os.getenv('CYCLENCE_DB_CONNECTION_STRING')
            return self._connection_string

class Main(BaseHandler):
    url = "/"

    @web.authenticated
    def get(self):
        self.session.refresh(self.current_user)
        self.render('tasklist.html')

class Login(BaseHandler):
    url = ojoin(Main.url, "login")

    def get(self):
        self.render('login.html')

class Logout(BaseHandler):
    url = ojoin(Main.url, 'logout')

    @web.authenticated
    def get(self):
        self.clear_cookie('user')
        self.redirect(Login)

class Google(BaseHandler, auth.GoogleMixin):
    url = ojoin(Main.url, "auth", "google")

    @web.asynchronous
    def get(self):
        if self.get_argument("openid.mode", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authenticate_redirect()

    def _on_auth(self, user):
        if not user:
            raise web.HTTPError(500, "Google auth failed")
        self.set_secure_cookie('user', user['email'])
        if not self.session.query(orm.User).filter_by(email=user['email']).first():
            usr = orm.User(email=user['email'],
                       name=user.get('name'),
                       firstname=user.get('first_name'),
                       lastname=user.get('last_name'))
            self.session.add(usr)
            self.session.commit()
        self.redirect(Main)

class Tasks(BaseHandler):
    '''Allows creation of tasks'''

    url = ojoin(Main.url, "tasks")

    @web.authenticated
    def get(self):
        '''Renders the task list'''
        self.render('tasklist.html')

    @web.authenticated
    @rollback_on_failure
    def post(self):
        '''Adds a task to the current user'''
        t = orm.Task(self.get_argument('taskname'),
                 int(self.get_argument('length')),
                 self.get_argument('firstdue'),
                 self.get_argument('allowearly', 'off') == 'on',
                 int(self.get_argument('points', 100)),
                 int(self.get_argument('decay_length', self.get_argument('length'))),
                 set(self.get_argument('tags', '').replace(',',' ').split()),
                 self.get_argument('notes', None))
        t.user_email = self.current_user.email
        self.current_user.tasks.append(t)
        self.session.commit()
        self.redirect(Tasks)

class Task(BaseHandler):
    r'''Handles updates to a task'''

    url = ojoin(Tasks.url, "({})".format(UUID_REGEX))

    #currently no methods

class NewTask(BaseHandler):
    r'''Allows creating a new task'''

    url = ojoin(Tasks.url, 'new')

    def get(self):
        self.render('newtask.html')


class ShareTask(BaseHandler):
    r'''Handles sharing tasks'''

    url = ojoin(Task.url, "share")

    @web.authenticated
    @rollback_on_failure
    def post(self, task_id):
        try:
            task = self.session.query(orm.Task).filter_by(task_id=task_id).one()
            if task not in self.current_user.tasks:
                raise Exception('User does not own this task')
            email = self.get_argument('friend', None)
            if email is None:
                raise Exception('Email argument not given')
            friend = self.session.query(orm.User).filter_by(email=email).one()
            if friend not in self.current_user.friends:
                raise Exception('Cannot share a task with someone who is not a friend.')
            friend.share_task(task=task, sharer=self.current_user)
            self.session.commit()
        except Exception as e:
            print(str(e))
        finally:
            self.redirect(Tasks)

class EditTasks(BaseHandler):
    r'''Lists tasks to be edited'''

    url = ojoin(Tasks.url, "edit")

    @web.authenticated
    @rollback_on_failure
    def get(self):
        '''Shows the task edit selection screen'''
        try:
            self.render('edittasks.html')
        except Exception as e:
            print(str(e))

class EditTask(BaseHandler):
    r'''Handles editing a task'''

    url = ojoin(Task.url, "edit")

    @web.authenticated
    @rollback_on_failure
    def get(self, task_id):
        '''Shows the form for editing a particular task'''
        try:
             task = next(task for task in self.current_user.tasks
                          if str(task.task_id) == task_id)
        except Exception as e:
            self.set_status(404)
        else:
            try:
                self.render('edittask.html', task=task)
            except Exception as e:
                print(str(e))


    @web.authenticated
    @rollback_on_failure
    def post(self, task_id):
        '''Actually updates the task with the edits'''
        try:
            task = self.session.query(orm.Task).filter(orm.Task.task_id == task_id).one()
        except Exception as e:
            self.set_status(404)
        task.name = self.get_argument('taskname', task.name)
        task.length = timedelta(days=int(self.get_argument('length', task.length)))
        task.allow_early = self.get_argument('allowearly',
                                             'on' if task.allow_early else 'off') == 'on'
        task.points = int(self.get_argument('points', task.points))
        task.tags = self.get_argument('tags', ', '.join(task.tags)).split(',')
        notes = self.get_argument('notes', task.notes)
        self.current_user.notify('message', 'The task {.name} has been updated'.format(task))
        self.session.commit()
        self.redirect(Tasks)


class DeleteTask(BaseHandler):

    url = ojoin(Task.url, "delete")

    @web.authenticated
    def get(self, task_id):
        self.redirect(Tasks)

    @web.authenticated
    @rollback_on_failure
    def post(self, task_id):
        if self.get_argument('delete', 'false') == 'true':
            task = self.session.query(orm.Task).filter(orm.Task.task_id == task_id).one()
            if len(task.users) > 1 and self.current_user in task.users:
                task.users.remove(self.current_user)
                self.current_user.notify('message',
                                         "You have been removed from the task '{.name}'"
                                         .format(task))
            elif len(task.users) == 1 and self.current_user in task.users:
                self.session.delete(task)
                self.current_user.notify('message',
                                         "The task '{.name}' has been deleted.".format(task))
            self.session.commit()
        else:
            print("Didn't get the expected argument delete=true. Hacking?")
        self.redirect(Tasks)

class Completion(BaseHandler):

    url = ojoin(Task.url, "completions", "({})".format(DATE_REGEX))

    @web.authenticated
    @rollback_on_failure
    def post(self, task_id, completed_on):
        completion_date = parsedate(completed_on)
        task = self.session.query(orm.Task).filter(orm.Task.task_id == task_id).one()
        if task.last_completed is None or completion_date > task.last_completed:
            task.complete(self.current_user, parsedate(completed_on))
            self.session.commit()
        else:
            self.current_user.notify('error',
                                     "You already completed '{}' on {}"
                                     .format(task.name,
                                             date_str(completion_date)),
                                     task.task_id)
            self.session.commit()
        self.redirect(Main)


class Notifications(BaseHandler):
    '''Displays all notifications for a user'''

    url = ojoin(Main.url, 'notifications')

    @web.authenticated
    def get(self):
        self.render('notifications.html')

class Notification(BaseHandler):

    url = ojoin(Notifications.url, "({})".format(UUID_REGEX))

    @web.authenticated
    @rollback_on_failure
    def post(self, notification_id):
        note = self.session.query(orm.Notification)\
            .filter_by(notification_id=notification_id).one()
        if note not in self.current_user.notifications:
            pass # will just redirect
        elif self.get_argument('delete', None) == 'true':
            self.current_user.notifications.remove(note)
            self.session.commit()
        elif note.noti_type == 'befriend' and self.get_argument('accept', 'false') == 'true':
            friend = self.session.query(orm.User).filter_by(email=note.sender).one()
            self.current_user._followers.append(friend)
            friend.notify('message', '{.name} has accepted your friend request'
                          .format(self.current_user))
            self.current_user.notifications.remove(note)
            self.session.commit()
        elif note.noti_type == 'share' and self.get_argument('accept', 'false') == 'true':
            task = self.session.query(orm.Task).filter_by(task_id=note.task_id).one()
            sender = self.session.query(orm.User).filter_by(email=note.sender).one()
            self.current_user.tasks.append(task)
            self.current_user.notify('message', "You have accepted the task '{.name}'".
                                     format(task))
            sender.notify('message', "{.name} has accepted the task '{.name}'"
                          .format(self.current_user, task))
            self.current_user.notifications.remove(note)
            self.session.commit()
        self.redirect(Notifications)

class Friends(BaseHandler):
    '''Handles the list of friends'''
    url = ojoin(Main.url, "friends")

    @web.authenticated
    def get(self):
        self.render('friendlist.html')

class Invite(BaseHandler):
    '''Handles an invitation to become friends'''
    url = ojoin(Main.url, "invite")

    @web.authenticated
    @rollback_on_failure
    def post(self):
        email = self.get_argument('email')
        if email is None:
            redirect(Friends)
            return
        potential_friend = self.session.query(orm.User).filter_by(email=email).one()
        if potential_friend == self.current_user:
            self.current_user.notify('error',
                                     'Forever Alone: you tried to befriend yourself')
        else:
            potential_friend.befriend(self.current_user)
        self.session.commit()
        self.redirect(Friends)

if __name__ == '__main__':
    from tornado.options import define, options
    define("worker_id", default=None, help="Worker id, used to determine port "
           "to listen on")
    define("debug", default=None, help="debug mode")
    options.parse_command_line()

    if options.debug is not None:
        DEBUG = options.debug
    else:
        DEBUG = os.getenv('CYCLENCE_DEBUG', 'false').lower() == 'true'

    env_port = os.getenv('CYCLENCE_TORNADO_PORT')
    if options.worker_id is not None:
        if env_port is not None:
            PORT = int(env_port) + int(options.worker_id)
        else:
            PORT = 8800 + int(options.worker_id)
    elif env_port is not None:
        PORT = int(env_port)
    else:
        PORT = 8801
    CyclenceApp(debug=DEBUG).listen(PORT)
    ioloop.IOLoop.instance().start()
