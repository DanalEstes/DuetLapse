# DuetLapse
Time Lapse camera support for Duet based 3D printers.

Designed to run on a Raspberry Pi, may be adaptable to other platforms. Supports cameras via USB, Pi (ribbon cable), and Webcam.  May support DSLR triggering in the future. Produces a video with H.264 encoding in an MP4 container. Does not, at this time, manage a library of videos, it simply drops the vid in home directory. 

Triggers images based on time, layer change, or pause.  Works with existing pauses in G-Code, or can force pauses at other trigger events. Optionally moves head to a specified position before capturing paused images. 

## Status

As of April 2, 2020, ready for Alpha testing. Feedback via issues on Github or at Duet forum https://forum.duet3d.com/

## Installation
* Either:
  * git clone https://github.com/DanalEstes/DuetLapse
  * Right click and "Save as" https://github.com/DanalEstes/DuetLapse/blob/master/DuetLapse.py 
* Copy included module https://github.com/DanalEstes/DuetWebAPI/blob/master/DuetWebAPI.py to the same directory, or to anywhere in python's libpath. 
* chmod 744 DuetLapse.py


## Corequisites 

* Python3
* Duet printer must be reachable via network
* ffmpeg
* Depending on camera type, one of
  * fswebcam (for USB cameras)
  * raspistill (for Pi cam or Ardu cam)
  * wget (for Web cameras)
  
## Usage

Start the script, usually *./DuetLapse \[options\]*, before starting a print.  It will connect to the printer and wait for the printer to change status from "Idle" to "Processing" and then begin capturing still images per the flag settings.  When the printer then goes "idle" again (i.e. end of print), it will process the still images into a video. 

```
usage: DuetLapse.py -duet DUET 
                    \[-camera {usb,pi,web,dslr}\]
                    \[-seconds SECONDS] 
                    \[-detect {layer,pause,none}\]
                    \[-pause {yes,no}] 
                    \[-movehead X Y\]
                    \[-weburl WEBURL]
                    \[-h\]
```

## Usage Notes

The only required flag is -duet to specify the printer to which the script will connect.  This assumes defaults of "USB" camera and "layer" detection. Example:
```
./DuetLapse.py -duet 192.168.7.101 
```

Many options can be combined.  For example, the script can trigger on every few seconds and when detecting layer changes. It will inform you if you select conflicting options. 

Example: Use a webcam that requires a UserId and Password, trigger every 30 seconds, do not detect any other triggers:
```
./DuetLapse.py -camera web -weburl http://userid:password@192.168.7.140/cgi-bin/currentpic.cgi -duet 192.168.7.101 -seconds 20 -detect none
```




  

