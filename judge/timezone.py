import logging

import pytz
from django.conf import settings
from django.db import connection
from django.utils import timezone
from django.utils.timezone import make_aware, make_naive

logger = logging.getLogger('judge.timezone')


class TimezoneMiddleware(object):
    def __init__(self, get_response=None):
        self.get_response = get_response

    @staticmethod
    def canonicalize_timezone(tzname):
        """
        Normalize a timezone name to its canonical IANA form.

        pytz accepts deprecated names like 'Asia/Saigon', but MySQL
        CONVERT_TZ only recognizes current IANA names ('Asia/Ho_Chi_Minh').
        Using a deprecated name causes CONVERT_TZ to return NULL, which
        crashes QuerySet.datetimes() and date_hierarchy in the admin.

        We validate against pytz.common_timezones, which contains only
        canonical IANA names (not deprecated aliases). If the user's
        timezone is a deprecated name, we fall back to DEFAULT_USER_TIME_ZONE
        and log a warning so the profile data can be corrected.
        """
        if tzname in pytz.common_timezones:
            return tzname

        logger.warning(
            'User timezone %r is not a canonical IANA name. '
            'Falling back to %r. Update the profile timezone to a '
            'canonical name to fix this.',
            tzname,
            settings.DEFAULT_USER_TIME_ZONE,
        )
        return settings.DEFAULT_USER_TIME_ZONE

    def get_timezone(self, request):
        tzname = settings.DEFAULT_USER_TIME_ZONE
        if request.profile:
            tzname = request.profile.timezone
        tzname = self.canonicalize_timezone(tzname)
        return pytz.timezone(tzname)

    def __call__(self, request):
        with timezone.override(self.get_timezone(request)):
            return self.get_response(request)


def from_database_time(datetime):
    tz = connection.timezone
    if tz is None:
        return datetime
    return make_aware(datetime, tz)


def to_database_time(datetime):
    tz = connection.timezone
    if tz is None:
        return datetime
    return make_naive(datetime, tz)
