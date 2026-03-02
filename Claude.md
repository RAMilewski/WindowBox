Write a python program to display images on the screen.

The program must be cross platform and run on MacOS, Debian, Ubuntu and RaspberryPi OS.

Image files should be taken from an images subdirectory and be .png .jpg, or .gif. Animated PNGs and GIFs should be supported.

The program must be calendar aware to enable scheduling events on specific days of the week and days of the month.  eg.  "Wed", "first Tue", etc.

A file named playlist.txt should control which image is displayed, when and for how long.
the file format should be:

        duration, days, timespan,  filename, 

where:

duration is the time the image is on the screen measured in seconds.

days is a | delimited list of days the image should appear (see "Calendar Aware" above.) This should be case insensitive.

timespan is a of the form "start-time,stop-time" using a 24 hour clock listing the times the image should be displayed.

filename is the name of the file in the images directory.




The program should cycle through the playlist displaying any image that fits the day and time restrictions.

All this should live in a directory named Windowbox.