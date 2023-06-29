# -*- coding: utf-8 -*-
import time

from django.conf import settings
from django.contrib import auth


class AutoLogoutMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_last_touch = True

        # can't log out if not logged in
        if not request.user.is_authenticated:
            # do nothing
            set_last_touch = False
        # check if auto logout is activated
        elif not settings.AUTO_LOGOUT_MINUTES:
            # do nothing
            set_last_touch = False
        else:
            try:
                delta = time.time() - request.session['last_touch']
            except (KeyError, TypeError):
                pass
            else:
                seconds = settings.AUTO_LOGOUT_MINUTES * 60
                if delta > seconds:
                    del request.session['last_touch']
                    auth.logout(request)
                    set_last_touch = False

        if set_last_touch:
            request.session['last_touch'] = time.time()

        response = self.get_response(request)
        return response
