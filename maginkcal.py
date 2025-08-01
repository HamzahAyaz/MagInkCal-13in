#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This project is designed for the WaveShare 12.48" eInk display. Modifications will be needed for other displays,
especially the display drivers and how the image is being rendered on the display. Also, this is the first project that
I posted on GitHub so please go easy on me. There are still many parts of the code (especially with timezone
conversions) that are not tested comprehensively, since my calendar/events are largely based on the timezone I'm in.
There will also be work needed to adjust the calendar rendering for different screen sizes, such as modifying of the
CSS stylesheets in the "render" folder.
"""

import os
import sys
import subprocess
import time
import datetime
from datetime import datetime as dt
import json
import logging
from time import sleep

from pytz import timezone
from gcal.gcal import GcalHelper
# from gcal.gcal import GcalModule
from owm.owm import OWMModule
from render.render import RenderHelper
from power.power import PowerHelper

def main():
    # Basic configuration settings (user replaceable)
    config_file = open('config.json')
    config = json.load(config_file)

    display_tz = timezone(config['displayTZ']) # list of timezones - print(pytz.all_timezones)
    day_view_display_time_in_sec = config['dayViewDisplayTimeInSec']  # list of timezones - print(pytz.all_timezones)
    threshold_hours = config['thresholdHours']  # considers events updated within last 12 hours as recently updated
    max_events_per_day = config['maxEventsPerDay']  # limits number of events to display (remainder displayed as '+X more')
    is_display_to_screen = config['isDisplayToScreen']  # set to true when debugging rendering without displaying to screen
    is_shutdown_on_complete = config['isShutdownOnComplete']  # set to true to conserve power, false if in debugging mode
    auto_shutdown_delay_time_in_sec = config['autoShutdownDelayTimeInSec']
    battery_display_mode = config['batteryDisplayMode']  # 0: do not show / 1: always show / 2: show when battery is low
    week_start_day = config['weekStartDay']  # Monday = 0, Sunday = 6
    day_of_week_text = config['dayOfWeekText'] # Monday as first item in list
    screen_width = config['screenWidth']  # Width of E-Ink display. Default is landscape. Need to rotate image to fit.
    screen_height = config['screenHeight']  # Height of E-Ink display. Default is landscape. Need to rotate image to fit.
    image_width = config['imageWidth']  # Width of image to be generated for display.
    image_height = config['imageHeight'] # Height of image to be generated for display.
    rotate_angle = config['rotateAngle']  # If image is rendered in portrait orientation, angle to rotate to fit screen
    calendars = config['calendars']  # Google calendar ids
    is24hour = config['is24h']  # set 24 hour time
    day_view_day_to_fetch = config['maxDayFetchForDayView'] # Number of days to retrieve from gcal, keep to 3 unless other parts of the code are changed too
    day_view_cal_days_to_show = config['maxEventsForDayView']
    lat = config["lat"] # Latitude in decimal of the location to retrieve weather forecast for
    lon = config["lon"] # Longitude in decimal of the location to retrieve weather forecast for
    owm_api_key = config["owm_api_key"]  # OpenWeatherMap API key. Required to retrieve weather forecast.

    # Create and configure logger
    logging.basicConfig(filename="logfile.log", format='%(asctime)s %(levelname)s - %(message)s', filemode='a')
    logger = logging.getLogger('maginkcal')
    logger.addHandler(logging.StreamHandler(sys.stdout))  # print logger to stdout
    logger.setLevel(logging.INFO)
    logger.info("Starting daily calendar update")

    # Establish current date and time information
    # Note: For Python dt.weekday() - Monday = 0, Sunday = 6
    curr_datetime = dt.now(display_tz)
    curr_date = curr_datetime.date()
    logger.info("Time synchronised to {}".format(curr_datetime))

    # Retrieve Battery Data
    power_service = PowerHelper()
    power_service.sync_time()
    curr_battery_level = power_service.get_battery()
    logger.info('Battery level at start: {:.3f}'.format(curr_battery_level))

    # For this implementation, each week starts on a Sunday and the calendar begins on the nearest elapsed Sunday
    # The calendar will also display 5 weeks of events to cover the upcoming month, ending on a Saturday
    cal_view_start_date = curr_date - datetime.timedelta(days=((curr_date.weekday() + (7 - week_start_day)) % 7))
    cal_view_end_date = cal_view_start_date + datetime.timedelta(days=(5 * 7 - 1))
    cal_view_start_datetime = display_tz.localize(dt.combine(cal_view_start_date, dt.min.time()))
    cal_view_end_datetime = display_tz.localize(dt.combine(cal_view_end_date, dt.max.time()))

    # Using Google Calendar to retrieve all events within start and end date (inclusive)
    start = dt.now()
    gcal_service = GcalHelper()
    month_cal_event_list = gcal_service.retrieve_events(calendars, cal_view_start_datetime, cal_view_end_datetime, display_tz, threshold_hours)
    logger.info("Month View Calendar events retrieved in " + str(dt.now() - start))

    # Populate dictionary with information to be rendered on e-ink display
    cal_month_view_dict = {
        'eventsMonthCal': month_cal_event_list,
        'calStartDate': cal_view_start_date,
        'today': curr_date,
        'lastRefresh': curr_datetime,
        'batteryLevel': curr_battery_level,
        'batteryDisplayMode': battery_display_mode,
        'dayOfWeekText': day_of_week_text,
        'weekStartDay': week_start_day,
        'maxEventsPerDay': max_events_per_day,
        'is24hour': is24hour
    }

    # Generate Month View
    render_service = RenderHelper(image_width, image_height, rotate_angle)
    month_calendar_image = render_service.generateMonthCal(cal_month_view_dict)

    try:
        # Retrieve Weather Data
        owm_module = OWMModule()
        current_weather, hourly_forecast, daily_forecast = owm_module.get_weather(lat, lon, owm_api_key)

        # Get next 6 hours  in 12hr format
        weather_forecast_times = []
        for i in range(7):  # current + 6 = 7 total
            future_time = curr_datetime + datetime.timedelta(hours=i)
            hour_str = future_time.strftime("%-I %p")  # %I = 12-hour, %p = AM/PM
            weather_forecast_times.append(hour_str)

        logger.info('Retrieved Weather Data')


        # Retrieve Events for Day View
        day_view_start_datetime = display_tz.localize(dt.combine(curr_date, dt.min.time()))
        day_view_end_datetime = display_tz.localize(dt.combine(curr_date + datetime.timedelta(days=day_view_day_to_fetch - 1), dt.max.time()))
        day_cal_event_list = gcal_service.get_events(curr_date, calendars, day_view_start_datetime, day_view_end_datetime, display_tz, day_view_day_to_fetch, threshold_hours)
        logger.info("Day View Calendar events retrieved in " + str(dt.now() - start))

        # bundle battery data
        battery_status = {
            'batteryLevel': curr_battery_level,
            'batteryDisplayMode': battery_display_mode,
        }

        # Generate Day View
        daily_calendar_image = render_service.generateDailyCal(curr_date, current_weather, hourly_forecast, daily_forecast, weather_forecast_times, day_cal_event_list, day_view_day_to_fetch, day_view_cal_days_to_show,battery_status)

        # Display Day View
        if is_display_to_screen:
            from display.display import DisplayHelper
            display_service = DisplayHelper(screen_width, screen_height)
            display_service.update(daily_calendar_image)
            display_service.sleep()

            display_time_in_min = day_view_display_time_in_sec / 60
            logger.info("Day View displayed, waiting {} min to redisplay Month View... ".format(display_time_in_min))
            time.sleep(day_view_display_time_in_sec) # Wait 5min before displaying Month view again

    except Exception as e:
        logger.error(e)

    # Display Month View
    if is_display_to_screen:
        from display.display import DisplayHelper
        display_service = DisplayHelper(screen_width, screen_height)

        if curr_date.weekday() == week_start_day:
            # calibrate display once a week to prevent ghosting
            display_service.calibrate(cycles=1)  # to calibrate in production

        display_service.update(month_calendar_image)
        display_service.sleep()

    curr_battery_level = power_service.get_battery()
    logger.info('Battery level at end: {:.3f}'.format(curr_battery_level))

    logger.info("Completed calendar update")

    if is_shutdown_on_complete:
        # Perform Smart Shutdown:
        # - Wait some min (defined in config) before initiating shutdown
        # - After some min (defined in config) check if any user is logged in, if so then delay shutdown
        # - Recheck and delay shutdown until user is no longer logged in.

        perform_smart_shutdown(logger, auto_shutdown_delay_time_in_sec)

def is_user_logged_in():
    result = subprocess.run(['who'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return bool(result.stdout.strip())  # True if anyone is logged in

def perform_smart_shutdown(logger, check_interval):
    logger.info("Waiting {} min before safely shutting down...".format(check_interval/60))
    while True:
        time.sleep(check_interval)
        if not is_user_logged_in():
            logger.info("No user session detected — shutting down safely.")
            os.system("sudo shutdown -h now")
            break
        else:
            logger.info("User session detected. Postponing shutdown for {} min".format(check_interval/60))


if __name__ == "__main__":
    main()
