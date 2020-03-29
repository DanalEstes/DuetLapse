#!/usr/bin/env python3
# Python Script to take Time Lapse pictures during a print
#   using images from a USB camera and a network
#   interface to a Duet based printer. 
#
# Copyright (C) 2020 Danal Estes all rights reserved.
# Released under The MIT License. Full text available via https://opensource.org/licenses/MIT
#
# Must run on the computer that owns the USB camera.  This is usually
#   a Raspberry Pi.  It may be possible to adapt to other OS platforms. 
#
# Requires network connection to Duet based printer running Duet/RepRap V2 or V3
# Requires ffmpeg (sudo apt-get install ffmpeg)
#
#
# This version of the script DOES NOT move the print head out of the way
#   while taking pictures.  The print head will be in a random location. 
#

import os
import subprocess
import sys
import datetime
import time
import numpy as np
import DuetWebAPI as DWA


# Globals.
zn = 0  # Z coordinate Now
zo = 0  # Z coordiante Old
frame = 0

# Get connected to the printer.  First, see if we are running on the Pi in a Duet3.
print("Attempting to connect to printer.")
printer = DWA.DuetWebAPI('http://127.0.0.1')
while (not printer.printerType()):
    ip = input("\nPlease Enter IP or name of printer\n")
    print("Attempting to connect to printer.")
    printer = DWA.DuetWebAPI('http://'+ip)

print("Connected to a Duet V"+str(printer.printerType())+" printer at "+printer.baseURL())

try:
    subprocess.call('rm -r /tmp/DuetLapse', shell=True)
except: 
    next

subprocess.call('mkdir /tmp/DuetLapse', shell=True)

print("A frame will be captured at each Z change.")
print("Press Ctl+C when ready to make frames into video.")

try:
    while(1):
        time.sleep(1.001) 
        zn=printer.getCoords()['Z']
        if (not zn == zo):
            # Z changed, take a picture. 
            s="{0:08d}".format(int(np.around(frame)))
            frame += 1
            cmd = 'fswebcam --quiet -d v4l2:/dev/video0 -i 0 -r 800x600 -p YUYV --no-banner '
            cmd += '/tmp/DuetLapse/IMG'+s+'.jpeg'
            print("Capturing frame {0:5d} at Z {1:7.2f} .".format(int(np.around(frame)),zn ))
            subprocess.call(cmd, shell=True)
        zo = zn
except KeyboardInterrupt:
    print()
    print("Now making {0:d} frames into a video at 10 frames per second.".format(int(np.around(frame))))
    print("This can take a while...")
    cmd='ffmpeg -r 10 -i /tmp/DuetLapse/IMG%08d.jpeg -vcodec libx264 -crf 25 -s 800x600 -pix_fmt yuv420p -y -v 8 ~/DuetLapse.mp4'
    subprocess.call(cmd, shell=True)
    print("Video processing complete.")
    print("Video file is in home directory, named DuetLapse.mp4")
    exit()

except:
    raise



