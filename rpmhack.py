# rpm shift alert hack
# this is a hack and not advisable to actually use on the road - be warned!
# this script will send altered data to the cluster in order to trigger the engine overspeed alarm so it can be used as a shift alert
# be aware it will log a fault code everytime it goes off - the script will periodically clear the all fault codes in the PCM 
# this script assumes the mki fg falcon highspeed can interface is up on can0
# https://github.com/jakka351/FG-Falcon | https://github.com/jakka351/

# This is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this file.  If not, see <https://www.gnu.org/licenses/>.

#!/usr/bin/python3

############################
#import modules
############################
import can
import time
import os
import queue
from threading import Thread
import sys, traceback
############################
#Global Variables
############################

c                      = ''
count                  = 0  
RpmMessage             = 0x207
ShiftAlertByte0        = 0x0A #Set your rpm alarm threshold - this is set for 1001-1011 rpm - first two digits
ShiftAlertByte1        = (0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B) # last two digits of the RPM, set as a range to make it easier for python-can to catch it


def scroll():
    #prints logo to console
        print('  ')
        print('             ,777I77II??~++++=~::,,,,::::::::::~~~==+~                                        ')
        print('           ,IIIIII,IIII+~..,,:,,,,,:~:,,.....,~,,:::~+?+?=                                    ')
        print('         :=I7777I=IIIIII~...:===,:,=~:,,,,,,::=,,,:::~~:=?===                                 ')
        print('      ~=,?I?777II7IIIII=~,.,,,,,,,,,,,:,,,,,,::,,,,~:~~~~:~+:~:~                              ')
        print('      I=I?IIIIII~IIIIIII+:..,,,,,,,,,,,,.,.,,::.,,,,:::~~=~:=+~?~~                            ')
        print('      I77?+?IIIIIIIII7I7=~,.,,,..,,,,.,.,.......,.,.,.,..,,,:~=~:==~~                         ')
        print('     +=I7777I?+???IIIIII+=:..,,,,,,,,,,,...,,,,,,,,,,,,..,,,:..:?I7+...,,                     ')
        print('     +=+=I7777I=~~+~:~IIII~,..,,,,,,,,,,..,,,,,...~+II?I?+?III7IIII777I7=.....                ')
        print('      ==++++III=~~~::~+I:+?~:.........:+IIIIIIII+=?IIIIIII???????????III7II7I....             ')
        print('     ?+=======::,,,,...,,:=?==~?+?????????????+==~~~~~===+++++++++++++++???II?III....         ')
        print('     ?+=======+=~=I7III~:~~I??++??IIIIII??+??++++==~~~~:::~~~~============++?II?+7II.         ')
        print('     ??+=====~~~=~~~+III~~=III??++++=+++?II??+=+?+====~~~:::::~~~~~~~~~~======+???++II.       ')
        print('     ??+=?=~~~~~~~~~~=~I=77I7III??++==~++++=+I??+?~?+===~~~~::::::~~~~~~~~~~~===++++=II,      ')
        print('     I??+=++=~~~~~~~~~~~?I777IIII??++====~======????+==+==~~~~:::::::::~~~~~~~~~====+==I,     ')
        print('      ?I+=~~=++~~~~~~~~=?=:+IIIII??++++===~:~~~~~~~=???=?:=~~~~~::::::::~~~~~~~~~~=~=+?7~:    ')
        print('       ?+=~~~~=++~~~~~+???~=?7II??+++++++==~~:~~~~~~:~~???=+:~~~~~~:::::::::~~~~=++:,.,+=,,   ')
        print('        =?I+~~~==++~~:+??~====+I?+===+++++==~~~::::::::::~????~~~~~:::::~:~==+:,,,,?..::+=:   ')
        print('          =?I=~~~==++=+++~==:,~~=+====+++++:,,...:,::~:::::~~~~+~:~~:~~==,.,,.?I~,..::~~=,:   ')
        print('           ~=+I?=~~=~+++~~=...,~:=+====++?:~+=?I~,I=I??..~III7I:==~,.,,.,,.,,,...::~~++~:~:   ')
        print('              ~?I+=~~~~+~~~.:+,,,:=+===+++~+==~=+:III=?I?77777I~~~===,,,,.,.,,~~~~=+=~::,,:   ')
        print('                ~?I+=:~~~~~~,,+:,,+==~+++++,:~~:==,??,:,,=??I++,,,:~===,,,::~~=++=:::~=..,,   ')
        print('             ,,,,:=+?==~~~~.=:~~,..,=+++++=~:=+=~:.,:,,,,::?=I=:::::+~====++++=~:::?I+?,..,   ')
        print('              :,,,,~+====~:,,,:=,.,,,~~===~~~,:==~~~~~~:..,,,,,,..,,,~==+++~:,~++I++II?...    ')
        print('               :,,,,,,+==+,:..:==.:,,~:~~~~~:,,,,:~~~~~~~~=========~++++~,....II+II+?...,:    ')
        print('                 ,,,,,,,++.,,.,,,,=:,,~:::~:::,,,,,,,,,::~~~=====~====~.......?I=I.....,:~    ')
        print('                   ::,,,,,,:~::,~+I+,..~::::::,,,,,,,,,,,,,,,,,~==~~~.........+.......,:,,    ')        
        print('                        :,,,,,,:~::,~+I+RPM SHIFT ALERT HACK BY jakka351...+.......,:,,     ') 
def setup():
    global bus
    try:
        bus = can.interface.Bus(channel='vcan0', bustype='socketcan_native')
                                                   # vcan0 is a virtual can interface, handy for testing
    except OSError:
        print("the can interface is not up...")
        sys.exit()
                                                   # quits if there is no canbus interface

    print("CANbus active on", bus)  
    print("waiting for engine to hit threshold RPM...")     
    print("")
    print("")

def cleanline():                      # cleans the last output line from the console
    sys.stdout.write('\x1b[1A')
    sys.stdout.write('\x1b[2K')

def msgbuffer():
    global message, q, RpmMessage                                        
    while True:
        message = bus.recv()          # if recieving can frames then put these can arb id's into a queue
        if message.arbitration_id == RpmMessage:                        
            q.put(message)

def main():

    try:
        while True:
            for i in range(8):
                while(q.empty() == True):                               # wait for messages to queue
                    pass
                message = q.get()
                       
                c = '{0:f},{1:d},'.format(message.timestamp,count)
                if message.arbitration_id == RpmMessage and message.data[0] == ShiftAlertByte0:
                    Data2 = message.data[2] 
                    Data3 = message.data[3]
                    Data4 = message.data[4]
                    Data5 = message.data[5]
                    Data6 = message.data[6]
                    Data7 = message.data[7]
                    trigger = can.Message(
                        arbitration_id=RpmMessage, data=[0x66, 0x66, Data2, Data3, Data4, Data5, Data6, Data7], is_extended_id=False
                    )

                    if message.arbitration_id == RpmMessage and message.data[0] >= ShiftAlertByte0 and message.data[1] in ShiftAlertByte1:
                       cleanline()
                       cleanline()
                       print(message)
                       print("shift!", time)

                       task = bus.send_periodic(trigger, 0.01)
                       assert isinstance(task, can.CyclicSendTaskABC)
                       time.sleep(1)
                       task.stop()
                       time.sleep(3)
                       pcm = 0x7E0        
                       cleardtc = can.Message(
                           arbitration_id=pcm, data=[0x03, 0x14, 0x00, 0xFF, 0x00, 0x00, 0x00, 0x00], is_extended_id=False
                       )
                       bus.send(cleardtc, timeout=None)
                       #flush_tx_buffer()

                    else:
                       pass
                   
                              
                else:
                    pass                                                                  
    except KeyboardInterrupt:
        sys.exit(0)                                              # quit if ctl + c is hit
    except Exception:
        traceback.print_exc(file=sys.stdout)                     # quit if there is a python problem
        sys.exit()
    except OSError:
        sys.exit()                                               # quit if there is a system issue

############################
# jakka351
############################
    

if __name__ == "__main__":                                       # run the program
    q                      = queue.Queue()                       #
    rx                     = Thread(target = msgbuffer)          #
    scroll()                                                     # scroll out fancy logo text
    setup()                                                      # set the can interface
    rx.start()                                                   # start the rx thread and queue msgs
    main()                                                       #
