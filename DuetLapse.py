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
import argparse
import datetime
import time
import numpy as np
import DuetWebAPI as DWA


# Globals.
zn = 0  # Z coordinate Now
zo = 0  # Z coordiante Old
frame = 0
printerip = ''
cameratype = ''
printerState = 0 # State machine for print idle before print, printing, idle after print. 

# parse command line arguments
parser = argparse.ArgumentParser(description='Program to create time lapse video from camera pointed at Duet3D based printer.')
parser.add_argument('-duet',type=str,nargs=1,help='Name or IP address of Duet printer.',required=True)
parser.add_argument('-camera',type=str,nargs=1,help='Camera type',choices=['usb','pi','web','dlsr'],default=['usb'])
parser.add_argument('-interval',type=str,nargs=1,help='Interval in seconds, or trigger [nnn|layer|layerPause]',default=['layer'])
args=vars(parser.parse_args())
duet     = args['duet'][0]
camera   = args['camera'][0]
interval = args['interval'][0]

if(not 'usb' in camera):
    print('DuetLapse.py: error: Camera type '+camera+' not yet supported.')
    sys.exit(2)

# Get connected to the printer.

print('Attempting to connect to printer at '+duet)
printer = DWA.DuetWebAPI('http://'+duet)
if (not printer.printerType()):
    print('Device at '+duet+' either did not respond or is not a Duet V2 or V3 printer.')
    exit(2)
printer = DWA.DuetWebAPI('http://'+duet)

print("Connected to a Duet V"+str(printer.printerType())+" printer at "+printer.baseURL())

# Clean up directory from past runs.
try:
    subprocess.call('rm -r /tmp/DuetLapse', shell=True)
except: 
    next

subprocess.call('mkdir /tmp/DuetLapse', shell=True)

print('Interval selected = '+interval)
print('Waiting for print to start.')

while(1):
    time.sleep(1.001) 
    status=printer.getStatus()
    #print(printerState, status)

    if (printerState == 0):  # Idle before print started. 
        if ('processing' in status):
            print('Print start sensed.')
            print('End of print will be sensed, and frames will be converted into video.')
            printerState = 1
            continue

    elif (printerState == 1):
        if ('idle' in status):
            printerState = 2
            continue

        if ('layer' in interval):
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

    elif (printerState == 2):
        print()
        print("Now making {0:d} frames into a video at 10 frames per second.".format(int(np.around(frame))))
        print("This can take a while...")
        cmd='ffmpeg -r 10 -i /tmp/DuetLapse/IMG%08d.jpeg -vcodec libx264 -crf 25 -s 800x600 -pix_fmt yuv420p -y -v 8 ~/DuetLapse.mp4'
        subprocess.call(cmd, shell=True)
        print("Video processing complete.")
        print("Video file is in home directory, named DuetLapse.mp4")
        exit()
