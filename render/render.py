#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script essentially generates a HTML file of the calendar I wish to display. It then fires up a headless Chrome
instance, sized to the resolution of the eInk display and takes a screenshot. This screenshot will then be processed
to extract the grayscale and red portions, which are then sent to the eInk display for updating.

This might sound like a convoluted way to generate the calendar, but I'm doing so mainly because (i) it's easier to
format the calendar exactly the way I want it using HTML/CSS, and (ii) I can better delink the generation of the
calendar and refreshing of the eInk display. In the future, I might choose to generate the calendar on a separate
RPi device, while using a ESP32 or PiZero purely to just retrieve the image from a file host and update the screen.
"""

import string
import pathlib
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from time import sleep
from datetime import timedelta
from PIL import Image

class RenderHelper:

    def __init__(self, width, height, angle):
        self.logger = logging.getLogger('maginkcal')
        self.currPath = str(pathlib.Path(__file__).parent.absolute())
        self.imageWidth = width
        self.imageHeight = height
        self.rotateAngle = angle

    def set_viewport_size(self, driver):

        # Extract the current window size from the driver
        current_window_size = driver.get_window_size()

        # Extract the client window size from the html tag
        html = driver.find_element(By.TAG_NAME,'html')
        inner_width = int(html.get_attribute("clientWidth"))
        inner_height = int(html.get_attribute("clientHeight"))

        # "Internal width you want to set+Set "outer frame width" to window size
        target_width = self.imageWidth + (current_window_size["width"] - inner_width)
        target_height = self.imageHeight + (current_window_size["height"] - inner_height)

        driver.set_window_rect(
            width=target_width,
            height=target_height)

    def get_screenshot(self, name="calendar"):
        opts = Options()
        opts.add_argument("--headless")
        opts.add_argument("--hide-scrollbars")
        opts.add_argument('--force-device-scale-factor=1')
        driver = webdriver.Chrome(options=opts)

        self.set_viewport_size(driver)
        driver.get('file://' + self.currPath + '/' + name + '.html')
        sleep(1)
        screenshot_path = self.currPath + '/' + name + ".png"
        driver.get_screenshot_as_file(screenshot_path)
        driver.quit()

        self.logger.info('Screenshot captured and saved to file.')

        # Load full-color image and rotate it
        color_img = Image.open(screenshot_path).convert("RGB")
        color_img = color_img.rotate(self.rotateAngle, expand=True)

        self.logger.info('Full-color image processed.')
        return color_img

    def get_day_in_cal(self, startDate, eventDate):
        delta = eventDate - startDate
        return delta.days

    def get_short_time(self, datetimeObj, is24hour=False):
        datetime_str = ''
        if is24hour:
            datetime_str = '{}:{:02d}'.format(datetimeObj.hour, datetimeObj.minute)
        else:
            if datetimeObj.minute > 0:
                datetime_str = '.{:02d}'.format(datetimeObj.minute)

            if datetimeObj.hour == 0:
                datetime_str = '12{}am'.format(datetime_str)
            elif datetimeObj.hour == 12:
                datetime_str = '12{}pm'.format(datetime_str)
            elif datetimeObj.hour > 12:
                datetime_str = '{}{}pm'.format(str(datetimeObj.hour % 12), datetime_str)
            else:
                datetime_str = '{}{}am'.format(str(datetimeObj.hour), datetime_str)
        return datetime_str

    def generateMonthCal(self, cal_dict):
        # calDict = {'eventsMonthCal': eventList, 'calStartDate': calStartDate, 'today': currDate, 'lastRefresh': currDatetime, 'batteryLevel': batteryLevel}
        # first setup list to represent the 5 weeks in our calendar
        cal_list = []
        for i in range(35):
            cal_list.append([])

        # retrieve calendar configuration
        max_events_per_day = cal_dict['maxEventsPerDay']
        battery_display_mode = cal_dict['batteryDisplayMode']
        day_of_week_text = cal_dict['dayOfWeekText']
        week_start_day = cal_dict['weekStartDay']
        is24hour = cal_dict['is24hour']

        # for each item in the eventList, add them to the relevant day in our calendar list
        for event in cal_dict['eventsMonthCal']:
            idx = self.get_day_in_cal(cal_dict['calStartDate'], event['startDatetime'].date())
            if idx >= 0:
                cal_list[idx].append(event)
            if event['isMultiday']:
                idx = self.get_day_in_cal(cal_dict['calStartDate'], event['endDatetime'].date())
                if idx < len(cal_list):
                    cal_list[idx].append(event)

        # Read html template
        with open(self.currPath + '/calendar_template.html', 'r') as file:
            calendar_template = file.read()

        # Insert month header
        month_name = str(cal_dict['today'].month)

        # Insert battery icon
        # batteryDisplayMode - 0: do not show / 1: always show / 2: show when battery is low
        batt_level = cal_dict['batteryLevel']

        if battery_display_mode == 0:
            batt_text = 'batteryHide'
        elif battery_display_mode == 1:
            if batt_level >= 80:
                batt_text = 'battery80'
            elif batt_level >= 60:
                batt_text = 'battery60'
            elif batt_level >= 40:
                batt_text = 'battery40'
            elif batt_level >= 20:
                batt_text = 'battery20'
            else:
                batt_text = 'battery0'

        elif battery_display_mode == 2 and batt_level < 20.0:
            batt_text = 'battery0'
        elif battery_display_mode == 2 and batt_level >= 20.0:
            batt_text = 'batteryHide'

        # Populate the day of week row
        cal_days_of_week = ''
        for i in range(0, 7):
            cal_days_of_week += '<li class="font-weight-bold text-uppercase">' + day_of_week_text[
                (i + week_start_day) % 7] + "</li>\n"

        # Populate the date and events
        cal_events_text = ''
        for i in range(len(cal_list)):
            curr_date = cal_dict['calStartDate'] + timedelta(days=i)
            day_of_month = curr_date.day
            if curr_date == cal_dict['today']:
                cal_events_text += '<li><div class="datecircle">' + str(day_of_month) + '</div>\n'
            elif curr_date.month != cal_dict['today'].month:
                cal_events_text += '<li><div class="date text-muted">' + str(day_of_month) + '</div>\n'
            else:
                cal_events_text += '<li><div class="date">' + str(day_of_month) + '</div>\n'

            for j in range(min(len(cal_list[i]), max_events_per_day)):
                event = cal_list[i][j]
                cal_events_text += '<div class="event'
                if event['isUpdated']:
                    cal_events_text += ' text-danger'
                elif curr_date.month != cal_dict['today'].month:
                    cal_events_text += ' text-muted'
                if event['isMultiday']:
                    if event['startDatetime'].date() == curr_date:
                        cal_events_text += '">►' + event['summary']
                    else:
                        # calHtmlList.append(' text-multiday">')
                        cal_events_text += '">◄' + event['summary']
                elif event['allday']:
                    cal_events_text += '">' + event['summary']
                else:
                    cal_events_text += '">' + self.get_short_time(event['startDatetime'], is24hour) + ' ' + event[
                        'summary']
                cal_events_text += '</div>\n'
            if len(cal_list[i]) > max_events_per_day:
                cal_events_text += '<div class="event text-muted">' + str(len(cal_list[i]) - max_events_per_day) + ' more'

            cal_events_text += '</li>\n'

        # Append the bottom and write the file
        html_file = open(self.currPath + '/calendar.html', "w")
        html_file.write(calendar_template.format(month=month_name, battText=batt_text, dayOfWeek=cal_days_of_week,
                                                events=cal_events_text))
        html_file.close()

        calendar_image = self.get_screenshot("calendar")
        return calendar_image

    def generateDailyCal(self, current_date, current_weather, hourly_forecast, daily_forecast, event_list, num_cal_days):

        # Read html template
        with open(self.currPath + '/dashboard_template.html', 'r') as file:
            dashboard_template = file.read()

        # Populate the date and events
        cal_events_list = []
        for i in range(num_cal_days):
            cal_events_text = ""

            if len(event_list[i]) == 0:
                cal_events_text = '<div class="event"><span class="event-time">None</span></div>'
            elif i == 0:  # TODAY — detailed format, only once
                # cal_events_text += '<ul class="event-today-list">'
                for event in event_list[i]:
                    cal_events_text += f"""
                        <li class="event">
                            <strong>{event['summary']}</strong><br>
                            <span class="event-today">Time: {self.get_short_time(event['startDatetime'])}</span><br>
                            <span class="event-today">Location: {event['location']}</span><br>
                            <span class="event-today">Notes: {event['description']}</span><br><br>
                        </li>
                    """
                # cal_events_text += '</ul>'
            else:  # FUTURE DAYS — condensed format
                for event in event_list[i]:
                    cal_events_text += '<div class="event">'
                    if event["isMultiday"] or event["allday"]:
                        cal_events_text += event['summary']
                    else:
                        cal_events_text += f'<span class="event-time">{self.get_short_time(event["startDatetime"])}</span> {event["summary"]}'
                    cal_events_text += '</div>\n'

            cal_events_list.append(cal_events_text)

        # Append the bottom and write the file
        html_file = open(self.currPath + '/dashboard.html', "w")
        html_file.write(dashboard_template.format(
            day=current_date.strftime("%-d"),
            month=current_date.strftime("%B"),
            weekday=current_date.strftime("%A"),
            tomorrow=(current_date + timedelta(days=1)).strftime("%A"),
            dayafter=(current_date + timedelta(days=2)).strftime("%A"),
            events_today=cal_events_list[0],
            events_tomorrow=cal_events_list[1],
            events_dayafter=cal_events_list[2],
            # I'm choosing to show the forecast for the next hour instead of the current weather
            # current_weather_text=day_of_month.capwords(current_weather["weather"][0]["description"]),
            # current_weather_id=current_weather["weather"][0]["id"],
            # current_weather_temp=round(current_weather["temp"]),
            current_weather_text=string.capwords(hourly_forecast[1]["weather"][0]["description"]),
            current_weather_id=hourly_forecast[1]["weather"][0]["id"],
            current_weather_temp=round(hourly_forecast[1]["temp"]),
            today_weather_id=daily_forecast[0]["weather"][0]["id"],
            tomorrow_weather_id=daily_forecast[1]["weather"][0]["id"],
            dayafter_weather_id=daily_forecast[2]["weather"][0]["id"],
            today_weather_pop=str(round(daily_forecast[0]["pop"] * 100)),
            tomorrow_weather_pop=str(round(daily_forecast[1]["pop"] * 100)),
            dayafter_weather_pop=str(round(daily_forecast[2]["pop"] * 100)),
            today_weather_min=str(round(daily_forecast[0]["temp"]["min"])),
            tomorrow_weather_min=str(round(daily_forecast[1]["temp"]["min"])),
            dayafter_weather_min=str(round(daily_forecast[2]["temp"]["min"])),
            today_weather_max=str(round(daily_forecast[0]["temp"]["max"])),
            tomorrow_weather_max=str(round(daily_forecast[1]["temp"]["max"])),
            dayafter_weather_max=str(round(daily_forecast[2]["temp"]["max"])),
        ))
        html_file.close()

        calendar_image = self.get_screenshot("dashboard")
        return calendar_image

