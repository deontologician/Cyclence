from __future__ import print_function

import os
import os.path
from base64 import urlsafe_b64decode as b64decode
from uuid import uuid4
from datetime import date, datetime

from tornado import ioloop, web, auth, escape
from tornado.httpclient import HTTPError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from cyclence.Calendaring import User, Task, Completion, Notification
from cyclence.utils import date_str

uuidre = r'[\dA-Fa-f]{8}-[\dA-Fa-f]{4}-[\dA-Fa-f]{4}'\
          '-[\dA-Fa-f]{4}-[\dA-Fa-f]{12}'

datere = r'[\d]{4}-[\d]{2}-[\d]{2}'

def parsedate(datestr):
    'Parses a date in ISO8601 format'
    if not datestr:
        return None
    return datetime.strptime(datestr, '%Y-%m-%d').date()

class BaseHandler(web.RequestHandler):

    @property
    def json(self):
        if not hasattr(self, '_json'):
            self._json = escape.json_decode(self.request.body)
        return self._json
    
    @property
    def session(self):
        return self.application.session

    def get_current_user(self):
        if not hasattr(self, '_user'):
            email = self.get_secure_cookie('user')
            if not email:
                return None
            self._user = self.session.query(User).filter(User.email == email).first()
        return self._user

class CyclenceApp(web.Application):
    r'''Customized application for Cyclence that includes database
    initialization'''
    def __init__(self, debug=False):
        handlers = [(r"/", MainHandler),
                    (r"/auth/google", GoogleHandler),
                    (r"/logout", LogoutHandler),
                    (r"/tasks", TasksHandler),
                    (r"/tasks/({})".format(uuidre), TaskHandler),
                    (r"/tasks/({})/share".format(uuidre), TaskShareHandler),
                    (r"/tasks/({})/completions".format(uuidre),
                     CompletionsHandler),
                    (r"/tasks/({})/completions/({})".format(uuidre, datere),
                     CompletionHandler),
                    (r"/notifications/({})".format(uuidre), NotificationHandler),
                    (r"/invite", InviteHandler),
                    ]
        settings = dict(
            cookie_secret=os.getenv('CYCLENCE_COOKIE_SECRET'),
            login_url='/',
            template_path='tpl',
            debug=True if os.getenv('CYCLENCE_DEBUG') == 'true' else False,
            static_path=os.path.join(os.path.dirname(__file__), "../../static"),
            )
        web.Application.__init__(self, handlers, **settings)
        connstr = os.getenv('CYCLENCE_DB_CONNECTION_STRING')
        self.session = sessionmaker(bind=create_engine(connstr, echo=debug))()

class TasksHandler(BaseHandler):
    '''Allows creation of tasks'''

    @web.authenticated
    def post(self):
        '''Adds a task to the current user'''
        t = Task(self.get_argument('taskname'),
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
        self.redirect('/')

class TaskHandler(BaseHandler):
    r'''Handles updates to a task'''
    pass

class TaskShareHandler(BaseHandler):
    r'''Handles sharing tasks'''

    @web.authenticated
    def post(self, task_id):
        try:
            task = self.session.query(Task).filter_by(task_id=task_id).one()
            if task not in self.current_user.tasks:
                raise Exception('User does not own this task')
            email = self.get_argument('friend', None)
            if email is None:
                raise Exception('Email argument not given')
            friend = self.session.query(User).filter_by(email=email).one()
            if friend not in self.current_user.friends:
                raise Exception('Cannot share a task with someone who is not a friend.')
            friend.share_task(task=task, sharer=self.current_user)
            self.session.commit()
        except Exception as e:
            print(str(e))
        finally:
            self.redirect('/')

class CompletionsHandler(BaseHandler):
    @web.authenticated
    def get(self, task_id):
        task = filter(lambda t: t.task_id == task_id, self.current_user.tasks)
        if len(task) == 0:
            raise HTTPError(404, 'Non existant task or not authorized')
        self.write(escape.json_encode([
                    {'completed_on': c.completed_on.isoformat(),
                     'task_id': str(c.task_id),
                     'points_earned': c.points_earned,
                     'recorded_on': c.recorded_on.isoformat(),
                     'days_late': c.days_late} for c in task[0].completions]))


class CompletionHandler(BaseHandler):
    @web.authenticated
    def post(self, task_id, completed_on):
        completion_date = parsedate(completed_on)
        task = self.session.query(Task).filter(Task.task_id == task_id).one()
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
        self.redirect('/')

class MainHandler(BaseHandler):
    def get(self):
        if not self.current_user:
            self.render('logged_out.html')
        else:
            self.session.refresh(self.current_user)
            self.render('main_page.html',
                        user=self.current_user,
                        today=date.today())

class GoogleHandler(BaseHandler, auth.GoogleMixin):
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
        if not self.session.query(User).filter_by(email=user['email']).first():
            usr = User(email=user['email'],
                       name=user.get('name'),
                       firstname=user.get('first_name'),
                       lastname=user.get('last_name'))
            self.session.add(usr)
            self.session.commit()
        self.redirect('/')
        
class LogoutHandler(BaseHandler):
    @web.authenticated
    def get(self):
        self.clear_cookie('user')
        self.redirect('/')

class NotificationHandler(BaseHandler):
    @web.authenticated
    def post(self, notification_id): 
        note = self.session.query(Notification).filter_by(notification_id=notification_id).one()
        if note not in self.current_user.notifications:
            pass # will just redirect
        elif self.get_argument('delete', None) == 'true':
            self.current_user.notifications.remove(note)
            self.session.commit()
        elif note.noti_type == 'befriend' and self.get_argument('accept', 'false') == 'true':
            friend = self.session.query(User).filter_by(email=note.sender).one()
            self.current_user._followers.append(friend)
            friend.notify('message', '{.name} has accepted your friend request'
                          .format(self.current_user))
            self.current_user.notifications.remove(note)
            self.session.commit()
        elif note.noti_type == 'share' and self.get_argument('accept', 'false') == 'true':
            task = self.session.query(Task).filter_by(task_id=note.task_id).one()
            sender = self.session.query(User).filter_by(email=note.sender).one()
            self.current_user.tasks.append(task)
            self.current_user.notify('message', "You have accepted the task '{.name}'".
                                     format(task))
            sender.notify('message', "{.name} has accepted the task '{.name}'"
                          .format(self.current_user, task))
            self.current_user.notifications.remove(note)
            self.session.commit()
        self.redirect('/')

class InviteHandler(BaseHandler):
    @web.authenticated
    def post(self):
        email = self.get_argument('email')
        if email is None:
            redirect('/')
            return
        potential_friend = self.session.query(User).filter_by(email=email).one()
        if potential_friend == self.current_user:
            self.current_user.notify('error',
                                     'Forever Alone: you tried to befriend yourself')
        else:
            potential_friend.befriend(self.current_user)
        self.session.commit()
        self.redirect('/')

if __name__ == '__main__':
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    CyclenceApp(debug=debug).listen(int(os.getenv('CYCLENCE_TORNADO_PORT')))
    ioloop.IOLoop.instance().start()
