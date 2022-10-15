# Concierge

This repository includes the Micropython code for a device that I use to unlock remotely the door of the building where I live.
It can unlock instantly or after a delay. The latter is used when I'm still in my car and I want to delay the unlock until I'm closer to the door.

The device uses a ESP8266 with a small relay with the relay connected to the building's intercom handset.

The device provides a very basic web interface where it is possible to trigger the relay and also change the Wifi settings.

The code uses a small "web server" library taken from https://github.com/codemee/ESP8266WebServer.
This library was changed to include a very rudimentary support for POST method and form parameters. 



## Notes to self ##

Connect rshell to the ESP8266 via serial

`rshell -p /dev/ttyUSB0`

Rsync the files in the current directory to the ESP8266 flash

`rsync . /pyboard/`

Launch the program in the ESP8266
```
repl ~ import main~main.main()
(Press Ctrl-X to exit)
```

Replace the config.cfg file in the ESP8266 where the settings are kept.

`cp config.cfg /pyboard/config.cfg`

Replace the boot script. Useful to prevent the main program from executing after a reset

`cp boot.py /pyboard/boot.py`

Alternative ways when rshell is unable to connect
```
ampy -p /dev/ttyUSB0 put boot.py
ampy -p /dev/ttyUSB0 put config.cfg
```
