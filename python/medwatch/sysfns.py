#!/usr/bin/env python3

import os
import sys
import time
import math
from datetime import datetime, timedelta


# SYSTEM FUNCTIONS

def now_hms():
    """
    Get current time in HH:MM:SS format
    **Plan to add timezones with pytz package

    e.g. now_hms()
         returns '11:00:00'

    Parameters:
    -------------
    n/a

    Returns:
    -------------
    current_time: str - Current time in HH:MM:SS
    """

    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    return current_time


def is_na(subject):
    """
    Checks if input is NaN which may be in multiple formats including a string
    ('n/a', or 'NaN'), float, or boolean.

    e.g. is_na('n/a')        returns True
         is_na(nan)          returns True
         is_na(False)        returns True
         is_na(1234)         returns False
         is_na('google.com') returns False

    Parameters:
    -------------
    subject: - Not type specific

    Returns:
    -------------
    True/False
    """

    if isinstance(subject, str):
        na_versions = ["n/a", "nan"]
        if subject.lower() in na_versions:
            return True
        else:
            return False
    elif isinstance(subject, float):
        if math.isnan(subject):
            return True
    elif isinstance(subject, bool):
        return not subject
    else:
        return False


def gen_start_end_times(start_time=[6, 0, 0], end_time=[23, 0, 0]):
    """
    Determines what the next start and end times should be based of current time.
    """

    now = datetime.now()
    year = now.year
    month = now.month
    day = now.day

    start_time = datetime(
        year, month, day, start_time[0], start_time[1], start_time[2], 0
    )

    end_time = datetime(year, month, day, end_time[0], end_time[1], end_time[2], 0)

    if end_time < now:
        end_time += timedelta(days=1)
        start_time += timedelta(days=1)

    return start_time, end_time


def gen_next_time(intervals, start_time=[6, 0, 0], end_time=[23, 0, 0]):
    """
    Function that generates the next datetime based off a specified
    interval

    Parameters:
    -------------
    interval: float - number of seconds between start of next datetime
    start_time: tuple of length 3 - (H, M, S)
    end_time: tuple of length 3 - (H, M, S)

    Yields:
    -------------
    next_datetime: datetime - 
    """
    now = datetime.now()
    year = now.year
    month = now.month
    day = now.day

    starttime, endtime = mw.gen_start_end_times(
        start_time=start_time, end_time=end_time
    )

    next_datetime = start_time

    while next_datetime < end_time:

        if next_datetime < now:
            while next_datetime < now:
                next_datetime += timedelta(seconds=intervals)
        else:
            next_datetime += timedelta(seconds=intervals)

        yield next_datetime
