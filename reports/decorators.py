from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden


def moderator_required(view_func):
    """Require the user to be logged in and have moderator or admin role."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if request.user.role not in ("moderator", "admin"):
            return HttpResponseForbidden("You do not have permission to access this page.")
        return view_func(request, *args, **kwargs)

    return _wrapped
