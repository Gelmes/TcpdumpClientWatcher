#!/usr/bin/python
import subprocess as sub
import shlex
import sys
import time
import threading
import argparse
from os import system, name 

def clear(): 
  
    # for windows 
    if name == 'nt': 
        _ = system('cls') 
  
    # for mac and linux(here, os.name is 'posix') 
    else: 
        _ = system('clear') 

def printDevices(devices):
    # clear()
    # for key in devices:
    #     if(devices[key].getRuntime() > 0):
    #         print( key + " " + str(round(devices[key].getRuntime(),2))+ " seconds")
    output = ""
    for key in devices:
        if(devices[key].getRuntime() > 5):
            output += ( "[" + key + ":" + str(round(devices[key].getRuntime(),2))+ "] ")
        if(output != ""):
            print(output)



class TcpThread(threading.Thread):
    def __init__(self, devices, lock, mode, port):
        threading.Thread.__init__(self)
        self.devices = devices
        self.lock = lock
        self.mode = mode
        self.port = port
        if(mode == "tcp"):
            self.cmd = 'sudo tcpdump -l -i eno1 -n "tcp[tcpflags] & (tcp-syn|tcp-fin|tcp-ack) != 0" and port ' + port
        elif(mode == "udp"):
            self.cmd = 'sudo tcpdump -l -i eno1 -n udp and port ' + port
        elif(mode == "tcp/udp"):
            self.cmd = 'sudo tcpdump -l -i eno1 -n "tcp[tcpflags] & (tcp-syn|tcp-fin|tcp-ack) != 0" or udp and port ' + port
        else:
            self.cmd = "exit"

    def run(self):
        args = shlex.split(self.cmd)
        process = sub.Popen( args, stdout=sub.PIPE )
        for row in iter(process.stdout.readline, b''):
            device = Device(row)
            self.lock.acquire()

            source_found = device.source in devices
            destination_found = device.destination in devices
            if( not source_found ):
                # if(device.flag_init):
                # print("Connected client " + device.source)
                printDevices(devices)
                device.type = "client"
                self.devices[device.source] = device
                
            if( not destination_found ):
                # if(device.flag_init or device.flag_accept):
                # print("Connected server " + device.destination)
                printDevices(devices)
                device.type = "client"
                self.devices[device.destination] = device

            if( source_found ):
                self.devices[device.source].updateTimer()
            if( destination_found ):
                self.devices[device.destination].updateTimer()

            self.lock.release()


class TimeoutThread(threading.Thread):
    def __init__(self, name, lock, timeout):
        threading.Thread.__init__(self)
        self.devices = devices
        self.lock = lock
        self.timeout = timeout

    def run(self):
        while True:
            self.lock.acquire()
            epoch = time.time()
            deleteList = []
            for key in devices:
                delta = epoch - devices[key].timerLastTick
                if( delta > self.timeout):
                    # print("Disconnected " + devices[key].source + " connected for " + str(round(devices[key].getRuntime(),2)) + " seconds")
                    printDevices(devices)
                    deleteList.append(key)
            for device in deleteList:
                del self.devices[device]

            self.lock.release()
            time.sleep(1)

class Device:
    def __init__(self, raw):
        output = raw.rstrip().decode("utf-8") 
        aps = output.split()[2].split('.')
        apd = output.split()[4].split('.')
        # print(output)
        self.source = aps[0] + "." + aps[1] + "."  + aps[2] + "."  + aps[3]
        self.destination = apd[0] + "." + apd[1] + "."  + apd[2] + "."  + apd[3]

        self.flag_init   = ( "[S]" in output )
        self.flag_accept = ( "[S.]" in output )
        self.flag_end    = ( "[F.]" in output )
        self.timerStart = time.time()
        self.timerLastTick = time.time()
        self.type = "none"

    def updateTimer(self):
        self.timerLastTick = time.time()

    def getRuntime(self):
        return self.timerLastTick - self.timerStart

def monitorPackets(port="80"):
    CMD = 'sudo tcpdump -l -i eno1 -n "tcp[tcpflags] & (tcp-syn|tcp-fin|tcp-ack) != 0" and port ' + port
    args = shlex.split(CMD)
    process = sub.Popen( args, stdout=sub.PIPE )
    devices = {}
    for row in iter(process.stdout.readline, b''):
        device = Device(row)
        
        source_found = device.source in devices
        destination_found = device.destination in devices
        if( not source_found ):
            if(device.flag_init):
                print("Connected client" + device.source)
                device.type = "client"
                devices[device.source] = device
        if( not destination_found ):
            if(device.flag_init or device.flag_accept):
                device.type = "server"
                print("Connected server" + device.source)
                devices[device.source] = device
        
        if( source_found ):
            devices[device.source].updateTime()
        if( destination_found ):
            devices[device.destination].updateTime()

        # if(device.flag_init):
        #     if( not device.source in devices ):
        #         print("Connected " + device.source)
        #         devices[device.source] = device
        #     else:
        #         devices[device.source].updateTime()
        #         devices[device.destination].updateTime()
        # if(device.flag_end):
        #     if( device.source in devices ):
        #         print("Disconnected " + device.source)
        #         del devices[device.source]
        #     elif( device.destination in devices ):
        #         print("Disconnected " + device.destination)
        #         del devices[device.source]

# def monitorPackets(port="80"):
#     CMD = 'sudo tcpdump -l -i eno1 -n "tcp[tcpflags] & (tcp-syn|tcp-fin) != 0" and port ' + port
#     args = shlex.split(CMD)
#     process = sub.Popen( args, stdout=sub.PIPE )
#     devices = {}
#     for row in iter(process.stdout.readline, b''):
#         device = Device(row)

#         if(device.flag_init):
#             if( not device.source in devices.keys() ):
#                 print("Connected " + device.source)
#                 devices[device.source] = device
#         if(device.flag_end):
#             if( device.source in devices.keys()):
#                 print("Disconnected " + device.source)
#                 devices.remove(device.source)
#             elif( device.destination in devices.keys() ):
#                 print("Disconnected " + device.destination)
#                 devices.remove(device.destination)

if __name__ == "__main__":
    timeout = 10 # Seconds
    parser = argparse.ArgumentParser(prog='PROG')
    parser.add_argument('-p','--port', default='80', help='Port to watch client connections on')
    parser.add_argument('-u','--udp', action='store_true', help='Watch udp packets')
    parser.add_argument('-t','--tcp', action='store_true', help='Watch tcp packets')
    args = parser.parse_args()

    mode = "tcp"
    if(args.udp and args.tcp):
        mode = "tcp/udp"
    elif(args.udp):
        mode = "udp"

    print("Watching devices on port " + args.port + " in mode " + mode)
    
    # Build locks and device list
    deviceLock = threading.Condition()
    devices = {}

    # Initialize threads
    tcpThread = TcpThread(devices, deviceLock, mode, args.port)
    timeoutThread = TimeoutThread(devices, deviceLock, timeout)

    # Start
    tcpThread.start()
    timeoutThread.start()

    # Wait
    tcpThread.join()
    timeoutThread.join()