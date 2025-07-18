# MagInkCal
This repo contains the code needed to drive an E-Ink Magic Calendar that uses a battery powered (PiSugar3) Raspberry Pi Zero 2W to retrieve events from a Google Calendar, format it into the desired layout, before pushing it to a Waveshare 13.3" full-color E-Ink display. Note that the code has only been tested on the specific hardware mentioned, and customization of the code is necessary for it to work with other E-Ink displays or Battery/RTC add-ons. That said, enjoy working on your project and hopefully this helps to jump-start your magic calendar journey.

![20210924_175459](https://user-images.githubusercontent.com/5581989/134661608-bac1f0bf-e7e3-41fe-b92e-37c26dad8fbe.jpg)

## Hardware Required
- Raspberry Pi Zero 2W - Header pins are needed to connect to the E-Ink display
- Waveshare 13.3" Full-color E-Ink Display
- PiSugar3 for Raspberry Pi Zero - Provides the RTC and battery for this project

## How It Works
Through PiSugar3's web interface, the onboard RTC can be set to wake and trigger the RPi to boot up daily at a time of your preference. Upon boot, a cronjob on the RPi is triggered to run a Python script that fetches calendar events from Google Calendar for the next few weeks, and formats them into the desired layout before displaying it on the E-Ink display. The RPi then shuts down to conserve battery. The calendar remains displayed on the E-Ink screen, because well, E-Ink...

## Setting Up Raspberry Pi Zero

1. Start by flashing [Raspberrypi OS Lite](https://www.raspberrypi.org/software/operating-systems/) to a MicroSD Card.

2. After setting up the OS, run the following commmand in the RPi Terminal, and use the [raspi-config](https://www.raspberrypi.org/documentation/computers/configuration.html) interface to setup Wifi connection, enable SSH, I2C, SPI, and set the timezone to your location.

```bash
sudo raspi-config
```
3. Run the following commands in the RPi Terminal to setup the environment to run the Python scripts.

```bash
sudo apt update
sudo apt-get install python3-pip
sudo apt-get install chromium-chromedriver
sudo apt-get install libopenjp2-7-dev
pip3 install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
pip3 install pytz
pip3 install selenium==4.6.0
pip3 install Pillow
```

4. Run the following commands in the RPi Terminal to install the libraries needed to drive the E-Ink display. See [this page]([https://www.waveshare.com/wiki/12.48inch_e-Paper_Module](https://www.waveshare.com/wiki/13.3inch_e-Paper_HAT+_(E)_Manual#Raspberry_Pi)) for more details.
```bash
sudo apt-get install python3-pil
sudo pip3 install RPi.GPIO
sudo pip3 install spidev
sudo apt-get install wiringpi
```

5. Run the following commands in the RPi Terminal to install the web interface for PiSugar3 display. See [this page](https://github.com/PiSugar/PiSugar/wiki/PiSugar3) for more details. After running the command, you would be able to access the web interface at http://your_raspberry_ip:8421 in your browser. From there you should be able to specify when you wish to schedule the PiSugar3 boot up your RPi.
```bash
curl http://cdn.pisugar.com/release/Pisugar-power-manager.sh | sudo bash
```

6. Download the over the files in this repo to a folder in your PC first. 

7. In order for you to access your Google Calendar events, it's necessary to first grant the access. Follow the [instructions here](https://developers.google.com/calendar/api/quickstart/python) on your PC to get the credentials.json file from your Google API. Don't worry, take your time. I'll be waiting here.

8. Once done, copy the credentials.json file to the "gcal" folder in this project. Run the following command on your PC. A web browser should appear, asking you to grant access to your calendar. Once done, you should see a "token.pickle" file in your "gcal" folder.

```bash
python3 quickstart.py
```

9. Copy all the files over to your RPi using your preferred means. 

10. Run the following command in the RPi Terminal to open crontab.
```bash
crontab -e
```
11. Specifically, add the following command to crontab so that the MagInkCal Python script runs each time the RPi is booted up.
```bash
@reboot cd /location/to/your/maginkcal && python3 maginkcal.py
```

12. That's all! Your Magic Calendar should now be refreshed at the time interval that you specified in the PiSugar3 web interface! 


## Acknowledgements
- [Original Repo](https://github.com/speedyg0nz/MagInkCal)
- [Quattrocento Font](https://fonts.google.com/specimen/Quattrocento): Font used for the calendar display
- [Bootstrap Calendar CSS](https://bootstrapious.com/p/bootstrap-calendar): Stylesheet that was adapted heavily for the calendar display
- [emagra](https://github.com/emagra): For adding in new features, such as 24hr display and multiple calendar selection. 
- [/u/aceisace](https://www.reddit.com/user/aceisace/): For the tips on E-Ink development and the [InkyCal](https://github.com/aceisace/Inkycal) repo (worth checking out even though I didn't use it for this project).   

