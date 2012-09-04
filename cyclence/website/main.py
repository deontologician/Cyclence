from __future__ import print_function

import os
import os.path

from tornado import ioloop, web, auth, escape
from base64 import urlsafe_b64decode as b64decode


class BaseHandler(web.RequestHandler):
    def get_current_user(self):
        user_json = self.get_secure_cookie('user')
        if not user_json:
            return None
        return escape.json_decode(user_json)


class MainHandler(BaseHandler):
    
    def get(self):
        if not self.current_user:
            self.write('<p>Oh no, you arent logged in. Sorry brah!</p>'
                       '<p><a href="/auth/google">Login with Google!</a></p>')
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
        self.set_secure_cookie('user', escape.json_encode(user))
        self.redirect('/')
        
class LogoutHandler(BaseHandler):
    @web.authenticated
    @web.asynchronous
    def get(self):
        self.clear_cookie('user')
        self.redirect('/')
        return
        self.write('You are now logged out!')
        self.write('<p><a href="/auth/google">Log in again</a></p>')


application = web.Application([
        (r"/", MainHandler),
        (r"/auth/google", GoogleHandler),
        (r"/logout", LogoutHandler),
        ],
        cookie_secret=os.getenv('CYCLENCE_COOKIE_SECRET'),
        login_url='/',
        template_path='tpl',
        debug=True,
        static_path=os.path.join(os.path.dirname(__file__), "static"),)

if __name__ == '__main__':
    application.listen(os.getenv('CYCLENCE_TORNADO_PORT'))
    ioloop.IOLoop.instance().start()
