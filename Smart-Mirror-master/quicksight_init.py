#	Product name: QuickSight
#	File name: quicksight_init.py
#	Authors: Mustafa S. Hamada, Christoffer Palm & Marie Sahiti
#	
#	Original Tk interface code template:
#       https://github.com/HackerShackOfficial/Smart-Mirror
#	Original serial-read code template:
#       https://www.piddlerintheroot.com/voice-recognition/
#
#	Date of completion: 2018-09-14
#	
#	Program description:
#	Voice-controlled Python(3) program that displays widgets with
#   information snippets for every day use


#################### IMPORT LIBRARIES ####################
from __future__ import print_function
from tkinter import *
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from PIL import Image, ImageTk
from contextlib import contextmanager

import locale
import threading
import time
import serial
import requests
import json
import traceback
import feedparser
import subprocess
import urllib.request
import datetime
import xmltodict

#################### SCOPES OF ACCESS FOR CALENDAR ####################
SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
LOCALE_LOCK = threading.Lock()


################### COUNTRY AND METRIC SETTINGS FOR WIDGETS ###################
ui_locale = '' # e.g. 'fr_FR' fro French, '' as default
#changed to 24 for 24 hour format
time_format = 24 # 12 or 24
#changed to %d %b %Y
date_format = "%d %b, %Y" # check python doc for strftime() for options
# changed from 'us' country code to none
news_country_code = None #'se'
# Account created at darksky.net, max 1000 requests a day
weather_api_token = 'a87515b394e6cc671e762fe2f47cbede'
# weather lang and unit format set after darksky parameters
# see https://darksky.net/dev/docs/forecast for list of parameters values
weather_lang = 'sv'
weather_unit = 'si'
# latitude and longitude not read from IP correctly and is currently hard coded
# Currently set for Linkoping,Sweden
latitude = '58'
longitude = '16'

#################### FONT AND WIDGET PADDING- SETTINGS ####################
xlarge_text_size = 94
large_text_size = 48
medium_text_size = 28
small_text_size = 18
minimal_text_size = 12
# vertical widget padding (distance from top)
y_pad = 20
# horizontal widget padding (distance from side)
x_pad = 20
# global variable set to '0' for news feed fetch
num_headlines = 0


#################### CONSTRUCT ####################
@contextmanager
# thread proof function to work with locale
def setlocale(name):
    with LOCALE_LOCK:
        saved = locale.setlocale(locale.LC_ALL)
        try:
            yield locale.setlocale(locale.LC_ALL, name)
        finally:
            locale.setlocale(locale.LC_ALL, saved)

# dictionary of weather icons, reading is not impacted by the 'lang' parameter
icon_lookup = {
    'clear-day': "assets/Sun.png",  # clear sky day
    'wind': "assets/Wind.png",   # wind
    'cloudy': "assets/Cloud.png",  # cloudy day
    'partly-cloudy-day': "assets/PartlySunny.png",  # partly cloudy day
    'rain': "assets/Rain.png",  # rain day
    'snow': "assets/Snow.png",  # snow day
    'snow-thin': "assets/Snow.png",  # sleet day
    'fog': "assets/Haze.png",  # fog day
    'clear-night': "assets/Moon.png",  # clear sky night
    'partly-cloudy-night': "assets/PartlyMoon.png",  # scattered clouds night
    'thunderstorm': "assets/Storm.png",  # thunderstorm
    'tornado': "assests/Tornado.png",    # tornado
    'hail': "assests/Hail.png"  # hail
}

#################### WIDGET CLASS DEFINITIONS ####################
class Clock(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, bg='black')
        # initialize time label
        self.time1 = ''
        self.timeLbl = Label(self, font=('Helvetica', large_text_size),
                             fg="white", bg="black")
        self.timeLbl.pack(side=TOP, anchor=E)
        # initialize day of week
        self.day_of_week1 = ''
        self.dayOWLbl = Label(self, text=self.day_of_week1,
                    font=('Helvetica', small_text_size), fg="white", bg="black")
        self.dayOWLbl.pack(side=TOP, anchor=E)
        # initialize date label
        self.date1 = ''
        self.dateLbl = Label(self, text=self.date1,
                    font=('Helvetica', small_text_size), fg="white", bg="black")
        self.dateLbl.pack(side=TOP, anchor=E)
        self.tick()

    def tick(self):
        with setlocale(ui_locale):
            if time_format == 12:
                # hour in 12h format
                time2 = time.strftime('%I:%M %p')
            else:
                # hour in 24h format
                time2 = time.strftime('%H:%M')
            day_of_week2 = time.strftime('%A')
            date2 = time.strftime(date_format)
            # if time string has changed, update it
            if time2 != self.time1:
                self.time1 = time2
                self.timeLbl.config(text=time2)
            if day_of_week2 != self.day_of_week1:
                self.day_of_week1 = day_of_week2
                day_of_week2 = day_of_week2.capitalize()
                self.dayOWLbl.config(text=day_of_week2)
            if date2 != self.date1:
                self.date1 = date2
                self.dateLbl.config(text=date2)

            # calls itself every 200 milliseconds
            self.timeLbl.after(200, self.tick)


class Weather(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, bg='black')
        self.temperature = ''
        self.forecast = ''
        self.location = ''
        self.currently = ''
        self.icon = ''
        self.degreeFrm = Frame(self, bg="black")
        self.degreeFrm.pack(side=TOP, anchor=W)
        self.temperatureLbl = Label(self.degreeFrm,
                    font=('Helvetica', large_text_size), fg="white", bg="black")
        self.temperatureLbl.pack(side=LEFT, anchor=N)
        self.iconLbl = Label(self.degreeFrm, bg="black")
        self.iconLbl.pack(side=LEFT, anchor=N, padx=20)
        self.currentlyLbl = Label(self, font=('Helvetica', medium_text_size),
                    fg="white", bg="black")
        self.currentlyLbl.pack(side=TOP, anchor=W)
        self.forecastLbl = Label(self, font=('Helvetica', small_text_size),
                    fg="white", bg="black")
        self.forecastLbl.pack(side=TOP, anchor=W)
        self.locationLbl = Label(self, font=('Helvetica', small_text_size),
                    fg="white", bg="black")
        self.locationLbl.pack(side=TOP, anchor=W)
        self.get_weather()

    def get_ip(self):
        try:
            ip_url = "http://jsonip.com/"
            req = requests.get(ip_url)
            ip_json = json.loads(req.text)
            return ip_json['ip']
        except Exception as e:
            traceback.print_exc()
            return "Error: %s. Cannot get ip." % e

    def get_weather(self):
        try:

            if latitude is None and longitude is None:
                # get location
                location_req_url = "http://freegeoip.net/json/%s" % self.get_ip()
                r = requests.get(location_req_url)
                location_obj = json.loads(r.text)

                lat = location_obj['latitude']
                lon = location_obj['longitude']

                location2 = "%s, %s" % (location_obj['city'],
                                        location_obj['region_code'])

                # get weather
                weather_req_url =("https://api.darksky.net/forecast/%s/%s,"
                        "%s?lang=%s&units=%s" % (weather_api_token, lat,lon,
                        weather_lang,weather_unit))
            else:
                location2 = ""
                # get weather
                weather_req_url = ("https://api.darksky.net/forecast/%s/%s,"
                        "%s?lang=%s&units=%s" % (weather_api_token, latitude,
                        longitude, weather_lang, weather_unit))

            r = requests.get(weather_req_url)
            weather_obj = json.loads(r.text)

            degree_sign= u'\N{DEGREE SIGN}'
            temperature2 =("%s%s" % (str(int(weather_obj['currently']
                        ['temperature'])), degree_sign))
            currently2 = weather_obj['currently']['summary']
            # forecast2 is left intentionally empty for optional use by end-user
            forecast2 = ''

            icon_id = weather_obj['currently']['icon']
            icon2 = None

            if icon_id in icon_lookup:
                icon2 = icon_lookup[icon_id]

            if icon2 is not None:
                if self.icon != icon2:
                    self.icon = icon2
                    image = Image.open(icon2)
                    image = image.resize((75, 70), Image.ANTIALIAS)
                    image = image.convert('RGB')
                    photo = ImageTk.PhotoImage(image)

                    self.iconLbl.config(image=photo)
                    self.iconLbl.image = photo
            else:
                # remove image
                self.iconLbl.config(image='')

            if self.currently != currently2:
                self.currently = currently2
                self.currentlyLbl.config(text=currently2)
            if self.forecast != forecast2:
                self.forecast = forecast2
                self.forecastLbl.config(text=forecast2)
            if self.temperature != temperature2:
                self.temperature = temperature2
                self.temperatureLbl.config(text=temperature2)
            if self.location != location2:
                if location2 == ", ":
                    self.location = "Cannot Pinpoint Location"
                    self.locationLbl.config(text="Cannot Pinpoint Location")
                else:
                    self.location = location2
                    self.locationLbl.config(text=location2)
        except Exception as e:
            traceback.print_exc()
            print("Error: %s. Cannot get weather." % e)

        self.after(600000, self.get_weather)

    @staticmethod
    def convert_kelvin_to_fahrenheit(kelvin_temp):
        return 1.8 * (kelvin_temp - 273) + 32


class News(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.config(bg='black')
        # self.title changed from 'News' to 'Nyheter'
        self.title = 'Nyheter' # 'News' is more internationally generic
        self.newsLbl = Label(self, text=self.title,
                    font=('Helvetica', small_text_size), fg="black", bg="black")
        self.newsLbl.pack(side=TOP, anchor=W)
        self.headlinesContainer = Frame(self, bg="black")
        self.headlinesContainer.pack(side=TOP)
        self.get_headlines()

    def get_headlines(self):
        try:
            # remove all children
            for widget in self.headlinesContainer.winfo_children():
                widget.destroy()
            if news_country_code == None:
                # Headline url changed to local rss feed, news_country_code is
                # not working since google changed rss handling
                # In order to work insert 'rss' after ...com/ in the url-link
                headlines_url = ("https://news.google.com/rss/?hl"
                                 "=sv&gl=SE&ceid=SE:sv&ned=sv_se")
            else:
                headlines_url = ("https://news.google.com/rss/%s?hl="
                                 "sv&gl=SE&ceid=SE:sv&ned=sv_se" % news_country_code)

            feed = feedparser.parse(headlines_url)

            for post in feed.entries[0:num_headlines]:
                headline = NewsHeadline(self.headlinesContainer, post.title)
                headline.pack(side=TOP, anchor=W)
        except Exception as e:
            traceback.print_exc()
            print("Error: %s. Cannot get news." % e)

        self.after(600000, self.get_headlines)


class NewsHeadline(Frame):
    def __init__(self, parent, event_name=""):
        Frame.__init__(self, parent, bg='black')

        image = Image.open("assets/Newspaper.png")
        image = image.resize((25, 25), Image.ANTIALIAS)
        image = image.convert('RGB')
        photo = ImageTk.PhotoImage(image)

        self.iconLbl = Label(self, bg='black', image=photo)
        self.iconLbl.image = photo
        self.iconLbl.pack(side=LEFT, anchor=N)

        self.eventName = event_name
        self.eventNameLbl = Label(self, text=self.eventName,
                    font=('Helvetica', minimal_text_size), fg="white", bg="black")
        self.eventNameLbl.pack(side=LEFT, anchor=N)


class Calendar(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, bg='black')
        self.start = ''
        self.start2 = ''
        self.title = 'Kalender'
        self.calendarLbl = Label(self, text=self.title,
                    font=('Helvetica', small_text_size), fg="black", bg="black")
        self.calendarLbl.pack(side=TOP, anchor=E)
        self.calendarEventContainer = Frame(self, bg='black')
        self.calendarEventContainer.pack(side=TOP, anchor=E)
        self.eventNameLbl = Label(self, text=self.start, anchor = W,
                    justify = LEFT, font=('Helvetica', minimal_text_size),
                    fg="black", bg="black")
        self.eventNameLbl.pack(side=TOP, anchor=E)
        self.get_events()

    def get_events(self):
        store = file.Storage('token.json')
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
            creds = tools.run_flow(flow, store)
        service = build('calendar', 'v3', http=creds.authorize(Http()))
        # Call the Calendar API, 'Z' indicates UTC time
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              maxResults=3, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            print('No upcoming events found.')
        for event in events:
            try: 
                self.start += (event['start'].get('dateTime')[0:10] + ' '
                + event['summary'] + ' '+ event['start'].get('dateTime')[11:16]
                +'\n')
            except:
                self.start += (event['start'].get('date')
                    + ' ' + event['summary'] + '\n')
     
        # Removes all children i.e. any interfering pop-windows
        for widget in self.calendarEventContainer.winfo_children():
            widget.destroy()

        if self.start != self.start2:
            self.start2 = self.start
            self.eventNameLbl.config(text=self.start)

        self.start = ''
            
        self.after(60000, self.get_events)

# Added in addition to the original widgets
class Message(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, bg='black')
        self.message_new = ''
        self.message_check = ''
        self.messageLbl = Label(self, text=self.message_new,
                font=('Helvetica', medium_text_size), fg="black", bg="black")
        self.messageLbl.pack(side=TOP, anchor=S)
        self.get_message()
        self.messageLbl.config(fg = 'black')

    def get_message(self):
        # Displayed message is read (200 characters) from a
        # text file (UTF-16) in the user Dropbox account
        self.message_new = (urllib.request.urlopen('https://www.dropbox.com/s/'
                        'gooevqruodwwakx/message_utf16.txt?raw=1').read(200))
        if self.message_new != self.message_check:
            self.messageLbl.config(text=self.message_new.decode('utf-16'))
            self.messageLbl.config(fg = 'white')
            self.message_check = self.message_new

        self.after(18000, self.get_message)

#Added in addition to the original widgets
class timeTable(Frame):
	def __init__(self, parent):
		Frame.__init__(self, parent, bg='black')
		self.time_title_string = 'Tidtabell'
		self.time_table_string = ''
		self.timeTitleLbl = Label(self, text=self.time_title_string,
                font=('Helvetica', medium_text_size), fg="white", bg="black")
		self.timeTitleLbl.pack(side=TOP, anchor=W)
		self.timeTableLbl = Label(self, text=self.time_table_string, anchor=W,
                justify=LEFT, font=('Helvetica', minimal_text_size),
                fg="white", bg="black")
		self.timeTableLbl.pack(side=TOP, anchor=W)
		self.get_timeTable()
		self.timeTableLbl.config(fg = 'black')
		self.timeTitleLbl.config(fg = 'black')
       
	def get_timeTable(self):
		get_api = (requests.get("https://api.resrobot.se/v2/departureBoard?key="
                "4deee6e8-978d-43ea-8564-2f6b0b405202&id=740054321&direction="
                "740000009&maxJourneys=3"))
		r = (get_api.text)
		r = xmltodict.parse(r)
		print(type(r))
		temp_string = r.get('DepartureBoard').get('Departure')
		print(type(temp_string))
		print(temp_string)
		try:
			for i in range (3):
				self.time_table_string += str(temp_string[i].get('@stop')[0:9]
                + ' ' + temp_string[i].get('@name')[13:]
                + ' ' + temp_string[i].get('@time') + '\n')

			self.timeTableLbl.config(text = self.time_table_string)

		finally:
			self.time_table_string = ''
			self.after(600000, self.get_timeTable)
        
# New class for Geeetech voice-recognition module set-up
class Voice(Frame):
	def __init__(self, parent):
		self.var_one = 0
		Frame.__init__(self, parent)
		# Dictionary of integers mapped to voice command functions
		self.commands = {11:self.one,
                         12:self.two,
                         13:self.three,
                         14:self.four,
                         15:self.five}
 
		# serial port settings for raspberry pi 3 B v.2
		self.ser = serial.Serial(
			port='/dev/ttyUSB0',
			baudrate=9600,
			parity=serial.PARITY_NONE,
			stopbits=serial.STOPBITS_ONE,
			bytesize=serial.EIGHTBITS,
			timeout=1
		)
		self.ser.flushInput()
 
		# For safety run twice to make sure it is in the correct mode
		for i in range(2):
            # set speech module to waiting state. See voice module data sheet.
			self.ser.write(serial.to_bytes([0xAA]))
			time.sleep(0.5)
            # import group 1 and await voice input
			self.ser.write(serial.to_bytes([0x21]))
			time.sleep(0.5)
		print('init complete')
		self.serial_read()

	def serial_read(self):
		control_string = 'Result:'
        # read serial data (11 bytes)
		data_byte = self.ser.read(11)
		if len(data_byte) == 11 and str(data_byte)[2:9] == control_string:
            # converts the last two 'bytes' of the incoming stream
            # to 'string' then to 'int'
			int_val = int(str(data_byte)[9:11])
            # checks if 'int_val' is an existing 'key' in the 'commands' dictionary
			if int_val in self.commands:
				self.commands[int_val]()

		self.after(5, self.serial_read)

	# Uses system screen saver function to turn on and off the monitor
	def one(self):
		print('command 1') # prints to console window
		if not self.var_one:
			subprocess.call('xset dpms force off', shell = True)
		elif self.var_one:
			subprocess.call('xset dpms force on', shell = True)
		self.var_one ^= 1

	# Alternates the calendar font colours upon incoming voice command
	def two(self):
		print('command 2')
		if w.calender.eventNameLbl.cget('fg') =='white':
			w.calender.eventNameLbl.config(fg='black')
			w.calender.calendarLbl.config(fg='black')
		elif w.calender.eventNameLbl.cget('fg') =='black':
			w.calender.eventNameLbl.config(fg='white')
			w.calender.calendarLbl.config(fg='white')

	# Alternates the news header label colour and number of news headlines
	def three(self):
		print('command 3')
		global num_headlines
		if num_headlines == 3:
			w.news.newsLbl.config(fg='black')
			num_headlines = 0
			w.news.get_headlines()
		elif num_headlines == 0:
			w.news.newsLbl.config(fg='white')
			num_headlines = 3
			w.news.get_headlines()

	# Alternates the calendar font colours upon incoming voice command
	def four(self):
		print('command 4')
		if w.message.messageLbl.cget('fg') =='white':
			w.message.messageLbl.config(fg='black')
		elif w.message.messageLbl.cget('fg') =='black':
			w.message.messageLbl.config(fg='white')

	# Alternates the calendar font colours upon incoming voice command
	def five(self):
		print('command 5')
		if w.timetable.timeTableLbl.cget('fg') =='white':
			w.timetable.timeTitleLbl.config(fg='black')
			w.timetable.timeTableLbl.config(fg='black')
		elif w.timetable.timeTableLbl.cget('fg') =='black':
			w.timetable.timeTitleLbl.config(fg='white')
			w.timetable.timeTableLbl.config(fg='white')
	
		  
class FullscreenWindow:
    def __init__(self):
        # Frame setup
        self.tk = Tk() # Creates an object of Tk()
        self.tk.configure(background='black')
        self.topFrame = Frame(self.tk, background = 'black')
        self.bottomFrame = Frame(self.tk, background = 'black')
        self.leftFrame = Frame(self.tk, background = 'black')
        self.topFrame.pack(side = TOP, fill=BOTH, expand = YES)
        self.bottomFrame.pack(side = BOTTOM, fill=BOTH, expand = YES)
        self.leftFrame.pack(side = LEFT)
        self.state = True
        self.tk.bind("<Return>", self.toggle_fullscreen)
        self.tk.bind("<Escape>", self.end_fullscreen)

        # Creates objects of each widget class
        # Clock
        self.clock = Clock(self.topFrame)
        self.clock.pack(side=RIGHT, anchor=N, padx=x_pad, pady=y_pad)
        # Weather
        self.weather = Weather(self.topFrame)
        self.weather.pack(side=LEFT, anchor=N, padx=x_pad, pady=y_pad)
        # News
        self.news = News(self.bottomFrame)
        self.news.pack(side=LEFT, anchor=S, padx=x_pad, pady=y_pad)
        # Calender
        self.calender = Calendar(self.bottomFrame)
        self.calender.pack(side = RIGHT, anchor=S, padx=x_pad, pady=y_pad)
        # sets the tkinter display window to fullscreen as default
        self.tk.attributes("-fullscreen", self.state)
        # Message
        self.message = Message(self.topFrame)
        self.message.pack(side=BOTTOM, anchor=SW)
        # Time Table
        self.timetable = timeTable(self.leftFrame)
        self.timetable.pack(side=LEFT, anchor=W)
        # Voice
        Voice(self.topFrame) 

    def toggle_fullscreen(self, event=None):
        self.state = not self.state  # Just toggling the boolean
        self.tk.attributes("-fullscreen", self.state)
        return "break"

    def end_fullscreen(self, event=None):
        self.state = False
        self.tk.attributes("-fullscreen", False)
        return "break"


# Creates an object of the FullscreenWindow class
# and run it in an endless loop until interrupted
if __name__ == '__main__':
    w = FullscreenWindow()
    w.tk.mainloop()
