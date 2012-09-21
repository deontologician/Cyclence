from __future__ import print_function

import os
import os.path
from base64 import urlsafe_b64decode as b64decode

from tornado import ioloop, web, auth, escape
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from cyclence.Calendaring import User, Task, Completion

class CyclenceApp(web.Application):
    r'''Customized application for Cyclence that includes database
    initialization'''
    def __init__(self):
        handlers = [(r"/", MainHandler),
                    (r'/tasks', TaskHandler),
                    (r"/auth/google", GoogleHandler),
                    (r"/logout", LogoutHandler),
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
        self.session = sessionmaker(bind=create_engine(connstr))()

class BaseHandler(web.RequestHandler):

    @property
    def session(self):
        return self.application.session

    def get_current_user(self):
        email = self.get_secure_cookie('user')
        if not email:
            return None
        return self.session.query(User).filter(User.email == email).one()


class MainHandler(BaseHandler):
    def get(self):
        if not self.current_user:
            self.render('logged_out.html')
        else:
            self.render('main_page.html', user=self.current_user)

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
        if not self.session.query(User).filter_by(email=user['email']).one():
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
        return
        self.write('You are now logged out!')
        self.write('<p><a href="/auth/google">Log in again</a></p>')

class TaskHandler(BaseHandler):
    @web.authenticated
    def get(self):
        self.render('tasks.html', user=self.current_user)

    @web.authenticated
    def post(self):
        pass

if __name__ == '__main__':
    CyclenceApp().listen(int(os.getenv('CYCLENCE_TORNADO_PORT')))
    ioloop.IOLoop.instance().start()
