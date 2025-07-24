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
import time
import datetime as dt
import os
import sys
import subprocess

from pytz import timezone
from gcal.gcal import GcalHelper
from render.render import RenderHelper
from power.power import PowerHelper
import json
import logging


def main():
    # Basic configuration settings (user replaceable)
    configFile = open('config.json')
    config = json.load(configFile)

    displayTZ = timezone(config['displayTZ']) # list of timezones - print(pytz.all_timezones)
    thresholdHours = config['thresholdHours']  # considers events updated within last 12 hours as recently updated
    maxEventsPerDay = config['maxEventsPerDay']  # limits number of events to display (remainder displayed as '+X more')
    isDisplayToScreen = config['isDisplayToScreen']  # set to true when debugging rendering without displaying to screen
    isShutdownOnComplete = config['isShutdownOnComplete']  # set to true to conserve power, false if in debugging mode
    batteryDisplayMode = config['batteryDisplayMode']  # 0: do not show / 1: always show / 2: show when battery is low
    weekStartDay = config['weekStartDay']  # Monday = 0, Sunday = 6
    dayOfWeekText = config['dayOfWeekText'] # Monday as first item in list
    screenWidth = config['screenWidth']  # Width of E-Ink display. Default is landscape. Need to rotate image to fit.
    screenHeight = config['screenHeight']  # Height of E-Ink display. Default is landscape. Need to rotate image to fit.
    imageWidth = config['imageWidth']  # Width of image to be generated for display.
    imageHeight = config['imageHeight'] # Height of image to be generated for display.
    rotateAngle = config['rotateAngle']  # If image is rendered in portrait orientation, angle to rotate to fit screen
    calendars = config['calendars']  # Google calendar ids
    is24hour = config['is24h']  # set 24 hour time

    # Create and configure logger
    logging.basicConfig(filename="logfile.log", format='%(asctime)s %(levelname)s - %(message)s', filemode='a')
    logger = logging.getLogger('maginkcal')
    logger.addHandler(logging.StreamHandler(sys.stdout))  # print logger to stdout
    logger.setLevel(logging.INFO)
    logger.info("Starting daily calendar update")

    try:
        # Establish current date and time information
        # Note: For Python datetime.weekday() - Monday = 0, Sunday = 6
        # For this implementation, each week starts on a Sunday and the calendar begins on the nearest elapsed Sunday
        # The calendar will also display 5 weeks of events to cover the upcoming month, ending on a Saturday
        powerService = PowerHelper()
        powerService.sync_time()
        currBatteryLevel = powerService.get_battery()
        logger.info('Battery level at start: {:.3f}'.format(currBatteryLevel))

        currDatetime = dt.datetime.now(displayTZ)
        logger.info("Time synchronised to {}".format(currDatetime))
        currDate = currDatetime.date()
        calStartDate = currDate - dt.timedelta(days=((currDate.weekday() + (7 - weekStartDay)) % 7))
        calEndDate = calStartDate + dt.timedelta(days=(5 * 7 - 1))
        calStartDatetime = displayTZ.localize(dt.datetime.combine(calStartDate, dt.datetime.min.time()))
        calEndDatetime = displayTZ.localize(dt.datetime.combine(calEndDate, dt.datetime.max.time()))

        # Using Google Calendar to retrieve all events within start and end date (inclusive)
        start = dt.datetime.now()
        gcalService = GcalHelper()
        eventList = gcalService.retrieve_events(calendars, calStartDatetime, calEndDatetime, displayTZ, thresholdHours)
        logger.info("Calendar events retrieved in " + str(dt.datetime.now() - start))

        # Populate dictionary with information to be rendered on e-ink display
        calDict = {'events': eventList, 'calStartDate': calStartDate, 'today': currDate, 'lastRefresh': currDatetime,
                   'batteryLevel': currBatteryLevel, 'batteryDisplayMode': batteryDisplayMode,
                   'dayOfWeekText': dayOfWeekText, 'weekStartDay': weekStartDay, 'maxEventsPerDay': maxEventsPerDay,
                   'is24hour': is24hour}

        renderService = RenderHelper(imageWidth, imageHeight, rotateAngle)
        calendarImage = renderService.process_inputs(calDict)

        if isDisplayToScreen:
            from display.display import DisplayHelper
            displayService = DisplayHelper(screenWidth, screenHeight)

            if currDate.weekday() == weekStartDay:
                # calibrate display once a week to prevent ghosting
                displayService.calibrate(cycles=1)  # to calibrate in production

            displayService.update(calendarImage)
            displayService.sleep()

        currBatteryLevel = powerService.get_battery()
        logger.info('Battery level at end: {:.3f}'.format(currBatteryLevel))

    except Exception as e:
        logger.error(e)

    logger.info("Completed daily calendar update")

    logger.info("Checking if configured to shutdown safely - Current hour: {}".format(currDatetime.hour))
    if isShutdownOnComplete:
        # Perform Smart Shutdown:
        # - Wait 5min before initiating shutdown
        # - After 5min check if any user is logged in, if so then delay shutdown by 5min
        # - Recheck and delay shutdown until user is no longer logged in.

        perform_smart_shutdown(logger, 300)

def is_user_logged_in():
    result = subprocess.run(['who'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return bool(result.stdout.strip())  # True if anyone is logged in

def perform_smart_shutdown(logger, check_interval=300):
    while True:
        time.sleep(check_interval)
        if not is_user_logged_in():
            logger.info("No user session detected — shutting down safely.")
            os.system("sudo shutdown -h now")
            break
        else:
            logger.info("User session detected. Postponing shutdown.")

def perform_clocked_shutdown(logger, curr_date_time, hour_to_shutdown=11):
    if curr_date_time.hour == hour_to_shutdown:
        logger.info("Shutting down safely.")
        os.system("sudo shutdown -h now")

if __name__ == "__main__":
    main()
