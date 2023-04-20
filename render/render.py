"""
This script essentially generates a HTML file of the calendar I wish to display. It then fires up a headless Chrome
instance, sized to the resolution of the eInk display and takes a screenshot.

This might sound like a convoluted way to generate the calendar, but I'm doing so mainly because (i) it's easier to
format the calendar exactly the way I want it using HTML/CSS, and (ii) I can delink the generation of the
calendar and refreshing of the eInk display.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from time import sleep
import sys
from datetime import timedelta
import pathlib
import string
from PIL import Image
import logging
from selenium.webdriver.common.by import By


class RenderHelper:

    def __init__(self, width, height, angle):
        self.logger = logging.getLogger('maginkdash')
        self.currPath = str(pathlib.Path(__file__).parent.absolute())
        self.htmlFile = 'file://' + self.currPath + '/dashboard.html'
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

    def get_screenshot(self, path_to_server_image):
        opts = Options()
        opts.add_argument("--headless")
        opts.add_argument("--hide-scrollbars");
        opts.add_argument('--force-device-scale-factor=1')
        driver = webdriver.Chrome(options=opts)
        self.set_viewport_size(driver)
        driver.get(self.htmlFile)
        sleep(1)
        driver.get_screenshot_as_file(self.currPath + '/dashboard.png')
        driver.save_screenshot(path_to_server_image)
        self.logger.info('Screenshot captured and saved to file.')

    def get_german_day(self, en):

        if en == "Monday":
            return "Montag"
        elif en == "Tuesday":
            return "Dienstag"
        elif en == "Wednesday":
            return "Mittwoch"
        elif en == "Thursday":
            return "Donnerstag"
        elif en == "Friday":
            return "Freitag"
        elif en == "Saturday":
            return "Samstag"
        elif en == "Sunday":
            return "Sonntag"

        return en

    def get_german_month(self, en):
        month_dict = {
            "January": "Januar",
            "February": "Februar",
            "March": "März",
            "April": "April",
            "May": "Mai",
            "June": "Juni",
            "July": "Juli",
            "August": "August",
            "September": "September",
            "October": "Oktober",
            "November": "November",
            "December": "Dezember"
        }
        return month_dict.get(en, en)

    def get_short_time(self, datetimeObj, is24hour=True):
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

    def process_inputs(self, current_date, current_weather, hourly_forecast, daily_forecast, event_list, num_cal_days, path_to_server_image, calender_details, max_lines):

        # Read html template
        with open(self.currPath + '/dashboard_template.html', 'r') as file:
            dashboard_template = file.read()

        # Populate the date and events

        lines = 0
        max_lines -= 1
        calender_text = u""

        for i in range(num_cal_days):

            if lines >= max_lines:
                break

            day = self.get_german_day((current_date + timedelta(days=i)).strftime("%A"))
            if i == 0:
                day = 'Heute'

            if len(event_list[i]) > 0:
                calender_text += f'<div class="row align-items-start"><div class="col-md-12"><h2>{day}</h2>'
            else:
                calender_text += f'<div class="row align-items-start"><div class="col-md-12"><h2 class="event-time">{day}</h2>'

            calender_text += '</h2><ol class="list-unstyled">'

            lines += 1


            for event in event_list[i]:
                cal_events_text = '<div class="event">'
                if event["isMultiday"] or event["allday"]:
                    cal_events_text += event['summary']
                else:

                    time = self.get_short_time(event['startDatetime'])

                    if event['summary'] in calender_details:

                        time += " - " + self.get_short_time(event['endDatetime'])

                    cal_events_text += '<span class="event-time">' + time + '</span> ' + event['summary']

                cal_events_text += '</div>'

                calender_text += cal_events_text

                lines += 1

                if lines >= max_lines:
                    break

            calender_text += '</ol></div></div><div class="row align-items-start"><div class="col-md-12"  style="height: 1px"></div></div>'


        # Append the bottom and write the file
        htmlFile = open(self.currPath + '/dashboard.html', "w", encoding='utf-8')
        htmlFile.write(dashboard_template.format(
            day=current_date.strftime("%d"),
            month=self.get_german_month(current_date.strftime("%B")),
            weekday=self.get_german_day(current_date.strftime("%A")),
            day0=self.get_german_day((current_date + timedelta(days=0)).strftime("%A")),
            day1=self.get_german_day((current_date + timedelta(days=1)).strftime("%A")),
            day2=self.get_german_day((current_date + timedelta(days=2)).strftime("%A")),
            day3=self.get_german_day((current_date + timedelta(days=3)).strftime("%A")),
            day4=self.get_german_day((current_date + timedelta(days=4)).strftime("%A")),
            events=calender_text,
            # I'm choosing to show the forecast for the next hour instead of the current weather
            current_weather_text=string.capwords(current_weather["weather"][0]["description"]),
            current_weather_id=current_weather["weather"][0]["id"],
            current_weather_temp=round(current_weather["temp"]),
            #current_weather_text=string.capwords(hourly_forecast[1]["weather"][0]["description"]),
            #current_weather_id=hourly_forecast[1]["weather"][0]["id"],
            #current_weather_temp=round(hourly_forecast[1]["temp"]),
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
        htmlFile.close()

        self.get_screenshot(path_to_server_image)
