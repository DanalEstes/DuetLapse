#!/usr/bin/env python3
# Python Script to take Time Lapse photographs during a print on 
#   a Duet based 3D printer and convert them into a video. 
#
# Copyright (C) 2020 Danal Estes all rights reserved.
# Released under The MIT License. Full text available via https://opensource.org/licenses/MIT
#
# Implemented to run on Raspbian on a Raspberry Pi.  May be adaptable to other platforms. 
# For USB or Pi camera, must run on a Raspberry Pi that is attached to camera.
# For dlsr USB cameras, must run on a Raspberry Pi that owns the interface to the camera.  
# For Webcam, the camera must be network reachable and via a defined URL for a still image.
# 
# The Duet printer must be RepRap firmware V2 or V3 and must be network reachable. 
#

import subprocess
import sys
import argparse
import time
try: 
    import DuetWebAPI as DWA
except ImportError:
    print("Python Library Module 'DuetWebAPI.py' is required. ")
    print("Obtain from https://github.com/DanalEstes/DuetWebAPI ")
    print("Place in same directory as script, or in Python libpath.")
    exit(2)

try: 
    import numpy as np
except ImportError:
    print("Python Library Module 'numpy' is required. ")
    print("Obtain via 'sudo python3 -m pip install numpy'")
    exit(2)


# Globals.
zo = 0                  # Z coordinate old
frame = 0               # Frame counter for file names
printerState  = 0       # State machine for print idle before print, printing, idle after print. 
timePriorPhoto = 0      # Time of last interval based photo, in time.time() format. 
alreadyPaused  = False  # If printer is paused, have we taken our actions yet? 

###########################
# Methods begin here
###########################


def init():
    # parse command line arguments
    parser = argparse.ArgumentParser(description='Program to create time lapse video from camera pointed at Duet3D based printer.', allow_abbrev=False)
    parser.add_argument('-duet',type=str,nargs=1,help='Name or IP address of Duet printer.',required=True)
    parser.add_argument('-camera',type=str,nargs=1,choices=['usb','pi','web','dslr'],default=['usb'])
    parser.add_argument('-seconds',type=float,nargs=1,default=[0])
    parser.add_argument('-detect',type=str,nargs=1,choices= ['layer', 'pause', 'none'],default=['layer'])
    parser.add_argument('-pause',type=str,nargs=1,choices= ['yes', 'no'],default=['no'])
    parser.add_argument('-movehead',type=float,nargs=2,default=[0.0,0.0])
    parser.add_argument('-weburl',type=str,nargs=1,default=[''])
    #parser.add_argument('--', '-camparm',type=str,nargs=argparse.REMAINDER,default=[''], dest='camparm', help='Extra parms to pass to fswebcam, raspistill, or wget.  Must come last. ')
    parser.add_argument('-dontwait',action='store_true',help='Capture images immediately.')
    subparsers = parser.add_subparsers(title='subcommands',help='DuetLapse camparms -h  or vidparms -h for more help')
    pcamparm   = subparsers.add_parser('camparms',description='camparm -parms xxx where xxx is passed to fswebcam, raspistill, or wget.')
    pcamparm.add_argument('--','-parms', type=str,nargs=argparse.REMAINDER,default=[''], dest='camparms', help='Extra parms to pass to fswebcam, raspistill, or wget.')
    pcamparm   = subparsers.add_parser('vidparms',description='vidparms -parms xxx where xxx is passed to ffmpeg.')
    pcamparm.add_argument('--','-parms', type=str,nargs=argparse.REMAINDER,default=[''], dest='vidparms', help='Extra parms to pass to fswebcam, raspistill, or wget.')
    args=vars(parser.parse_args())

    global duet, camera, seconds, detect, pause, movehead, weburl, dontwait, camparms, vidparms
    duet     = args['duet'][0]
    camera   = args['camera'][0]
    seconds  = args['seconds'][0]
    detect   = args['detect'][0]
    pause    = args['pause'][0]
    movehead = args['movehead']
    weburl   = args['weburl'][0]
    dontwait = args['dontwait']
    camparms = ['']
    if ('camparms' in args.keys()): camparms = args['camparms']
    camparms = ' '.join(camparms)
    vidparms = ['']
    if ('vidparms' in args.keys()): vidparms = args['vidparms']
    vidparms = ' '.join(vidparms)

    # Warn user if we havent' implemented something yet. 
    if ('dlsr' in camera):
        print('DuetLapse.py: error: Camera type '+camera+' not yet supported.')
        exit(2)

    # Inform regarding valid and invalid combinations
    if ((seconds > 0) and (not 'none' in detect)):
        print('Warning: -seconds '+str(seconds)+' and -detect '+detect+' will trigger on both.')
        print('Specify "-detect none" with "-seconds" to trigger on seconds alone.')

    if ((not movehead == [0.0,0.0]) and ((not 'yes' in pause) and (not 'pause' in detect))):
        print('Invalid Combination: "-movehead {0:1.2f} {1:1.2f}" requires either "-pause yes" or "-detect pause".'.format(movehead[0],movehead[1]))
        exit(2)

    if (('yes' in pause) and ('pause' in detect)):
        print('Invalid Combination: "-pause yes" causes this script to pause printer when')
        print('other events are detected, and "-detect pause" requires the gcode on the printer')
        print('contain its own pauses.  These are fundamentally incompatible.')
        exit(2)

    if ('pause' in detect):
        print('************************************************************************************')
        print('* Note "-detect pause" means that the G-Code on the printer already contains pauses,')
        print('* and that this script will detect them, take a photo, and issue a resume.')
        print('* Head position during those pauses is can be controlled by the pause.g macro ')
        print('* on the duet, or by specifying "-movehead nnn nnn".')
        print('*')
        print('* If instead, it is desired that this script force the printer to pause with no')
        print('* pauses in the gcode, specify either:')
        print('* "-pause yes -detect layer" or "-pause yes -seconds nnn".')
        print('************************************************************************************')


    if ('yes' in pause):
        print('************************************************************************************')
        print('* Note "-pause yes" means this script will pause the printer when the -detect or ')
        print('* -seconds flags trigger.')
        print('*')
        print('* If instead, it is desired that this script detect pauses that are already in')
        print('* in the gcode, specify:')
        print('* "-detect pause"')
        print('************************************************************************************')


    # Check for requsite commands
    if ('usb' in camera):
        if (20 > len(subprocess.check_output('whereis fswebcam', shell=True))):
            print("Module 'fswebcam' is required. ")
            print("Obtain via 'sudo apt install fswebcam'")
            exit(2)

    if ('pi' in camera):
        if (20 > len(subprocess.check_output('whereis raspistill', shell=True))):
            print("Module 'raspistill' is required. ")
            print("Obtain via 'sudo apt install raspistill'")
            exit(2)

    if ('web' in camera):
        if (20 > len(subprocess.check_output('whereis wget', shell=True))):
            print("Module 'wget' is required. ")
            print("Obtain via 'sudo apt install wget'")
            exit(2)

    if (20 > len(subprocess.check_output('whereis ffmpeg', shell=True))):
        print("Module 'ffmpeg' is required. ")
        print("Obtain via 'sudo apt install ffmpeg'")
        exit(2)

    # Get connected to the printer.

    print('Attempting to connect to printer at '+duet)
    global printer
    printer = DWA.DuetWebAPI('http://'+duet)
    if (not printer.printerType()):
        print('Device at '+duet+' either did not respond or is not a Duet V2 or V3 printer.')
        exit(2)
    printer = DWA.DuetWebAPI('http://'+duet)

    print("Connected to a Duet V"+str(printer.printerType())+" printer at "+printer.baseURL())

    # Tell user options in use. 
    print()
    print("##################################")
    print("# Options in force for this run: #")
    print("# camera   = {0:20s}#".format(camera))
    print("# printer  = {0:20s}#".format(duet))
    print("# seconds  = {0:20s}#".format(str(seconds)))
    print("# detect   = {0:20s}#".format(detect))
    print("# pause    = {0:20s}#".format(pause))
    print("# camparms = {0:20s}#".format(camparms))
    print("# vidparms = {0:20s}#".format(vidparms))
    print("# movehead = {0:6.2f} {1:6.2f}       #".format(movehead[0],movehead[1]))
    print("# dontwait = {0:20s}#".format(str(dontwait)))
    print("##################################")
    print()

    # Clean up directory from past runs.  Be silent if it does not exist. 
    subprocess.call('rm -r /tmp/DuetLapse > /dev/null 2>&1', shell=True)
    subprocess.call('mkdir /tmp/DuetLapse', shell=True)



def checkForcePause():
    # Called when some other trigger has already happend, like layer or seconds.
    # Checks to see if we should pause; if so, returns after pause and head movement complete.
    global alreadyPaused
    if (alreadyPaused): return
    if (not 'yes' in pause): return
    print('Requesting pause via M25')
    printer.gCode('M25')    # Ask for a pause
    printer.gCode('M400')   # Make sure the pause finishes
    alreadyPaused = True 
    if(not movehead == [0.0,0.0]):
        print('Moving print head to X{0:4.2f} Y{1:4.2f}'.format(movehead[0],movehead[1]))
        printer.gCode('G1 X{0:4.2f} Y{1:4.2f}'.format(movehead[0],movehead[1]))
        printer.gCode('M400')   # Make sure the move finishes

def unPause():
    global alreadyPaused
    if (alreadyPaused):
        print('Requesting un pause via M24')
        printer.gCode('M24')
        alreadyPaused = False

def onePhoto():
    global frame
    frame += 1
    s="{0:08d}".format(int(np.around(frame)))
    fn = '/tmp/DuetLapse/IMG'+s+'.jpeg'

    if ('usb' in camera): 
        if (camparms == ''):
            cmd = 'fswebcam --quiet --no-banner '+fn
        else:
            cmd = 'fswebcam '+camparms+' '+fn
    if ('pi' in camera): 
        if (camparms == ''):
            cmd = 'raspistill -o '+fn
        else:
            cmd = 'raspistill  '+camparms+' -o '+fn
    if ('web' in camera): 
        if (camparms == ''):
            cmd = 'wget --auth-no-challenge -nv -O '+fn+' "'+weburl+'" '
        else:
            cmd = 'wget '+camparms+' -O '+fn+' "'+weburl+'" '

    subprocess.call(cmd, shell=True)
    global timePriorPhoto
    timePriorPhoto = time.time()


def oneInterval():
    global frame
    if ('layer' in detect):
        global zo
        zn=printer.getLayer()
        if (not zn == zo):
            # Z changed, take a picture.
            checkForcePause()
            print('Capturing frame {0:5d} at X{1:4.2f} Y{2:4.2f} Z{3:4.2f} Layer {4:d}'.format(int(np.around(frame)),printer.getCoords()['X'],printer.getCoords()['Y'],printer.getCoords()['Z'],zn))
            onePhoto()
        zo = zn
    global timePriorPhoto
    elap = (time.time() - timePriorPhoto)
    if ((seconds) and (seconds < elap)):
        checkForcePause()
        print('Capturing frame {0:5d} after {1:4.2f} seconds elapsed.'.format(int(np.around(frame)),elap))
        onePhoto()
    if ('pause' in detect):
        if ('paused' in printer.getStatus()):
            global alreadyPaused
            alreadyPaused = True
            print('Pause Detected, capturing frame {0:5d}'.format(int(np.around(frame)),elap))
            onePhoto()
        unPause()            

def postProcess():
    print()
    print("Now making {0:d} frames into a video at 10 frames per second.".format(int(np.around(frame))))
    if (250 < frame): print("This can take a while...")
    fn ='~/DuetLapse'+time.strftime('%m%d%y%H%M',time.localtime())+'.mp4'
    if (vidparms == ''):
        cmd  = 'ffmpeg -r 10 -i /tmp/DuetLapse/IMG%08d.jpeg -vcodec libx264 -y -v 8 '+fn
    else:
        cmd  = 'ffmpeg '+vidparms+' -i /tmp/DuetLapse/IMG%08d.jpeg '+fn
    subprocess.call(cmd, shell=True)
    print('Video processing complete.')
    print('Video file is in home directory, named '+fn)
    exit()    


###########################
# Main begins here
###########################
init()
    
if (dontwait):
    print('Not Waiting for print to start on printer '+duet)
    print('Will take pictures from now until a print starts, ')
    print('  continue to take pictures throughout printing, ')
else:
    print('Waiting for print to start on printer '+duet)
    print('Will take pictures when printing starts, ')
print('  and make video when printing ends.')
print('Or, press Ctrl+C one time to move directly to conversion step.')
print('')


timePriorPhoto = time.time()

try: 
    while(1):
        time.sleep(.77)            # Intentionally not evenly divisible into one second. 
        status=printer.getStatus()

        if (printerState == 0):     # Idle before print started. 
            if (dontwait):
                oneInterval()
            if ('processing' in status):
                print('Print start sensed.')
                print('End of print will be sensed, and frames will be converted into video.')
                print('Or, press Ctrl+C one time to move directly to conversion step.')
                print('')
                printerState = 1

        elif (printerState == 1):   # Actually printing
            oneInterval()
            if ('idle' in status):
                printerState = 2

        elif (printerState == 2): 
            postProcess()
except KeyboardInterrupt:
    postProcess()    
