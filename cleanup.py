# Utilizes the following external libraries
# CiscoConfParse
#       Documentation: http://www.pennington.net/py/ciscoconfparse/
# Trigger
#       Documentation: http://trigger.rtfd.org
#       Source: https://github.com/trigger/trigger

import os, sys, getopt
from ciscoconfparse import CiscoConfParse
from trigger.cmds import Commando
from trigger.netdevices import NetDevices

# directory to store the change files
OUTPUT_DIRECTORY = 'audit-changes/'

# create a dictionary of the changes to push
commandFile= {}

# override the Commando class so I can implement custom logic
class CommandExecutor(Commando):
        vendors = ['cisco']

        # custom logic so I can customize the command list per device
        # pull out the commandList based on the commandFile (key is the deviceName)
        def to_cisco(self, dev, commands=None, extra=None):
                if self.verbose:
                        print dev.nodeName + '\n' + '\n'.join(commandFile[dev.nodeName]) + '\n\n'
                return commandFile[dev.nodeName]

# read in a file containing the devices to review
# if not specified then by default use the following
deviceListFile = "devicelist.txt"
if len(sys.argv) > 1:
        deviceListFile = sys.argv[1]

# read in the file and create an array of devices
deviceList = [line.strip() for line in open(deviceListFile, 'r')]

# commands to run to get into configuration mode
prefixList = ['conf t']
# commands to run to exit configuration mode and save the config
postList = ['end', 'wr mem']

nd = NetDevices()

for deviceName in deviceList:
        # commands to run in order to bring the device back to standard
        commandList = []

        # the current device configuration file is stored here, parse it
        p = CiscoConfParse("/home/ioswrite/network-configurations/" + deviceName)

        # ---------------------------------------------------------------------------------
        # STORM CONTROL: legacy switch configuration
        # ---------------------------------------------------------------------------------

        # give me a list of interfaces that contain " port storm-control unicast"
        interfaceList = p.find_parents_w_child('^interf', '^ port storm-control unicast')

        # create the commands so that I can remove this unwanted command
        for line in interfaceList:
                commandList.append(line)
                commandList.append(' no port storm-control unicast action filter')
                commandList.append(' no port storm-control unicast trap')

        # ---------------------------------------------------------------------------------
        # STORM CONTROL: modern switch configuration
        # ---------------------------------------------------------------------------------

        # give me a list of interfaces that contain "storm-control unicast level"
        interfaceList = p.find_parents_w_child('^interf', 'storm-control unicast level')

        # create the commands so that I can remove this unwanted command
        for line in interfaceList:
                commandList.append(line)
                commandList.append(' no storm-control unicast level')

        # ------------------------------------------------------------------------------------------
        # PORT SECURITY: legacy port security configuration (XL switches)
        # ------------------------------------------------------------------------------------------

        # give me a list of interfaces that are running port security
        interfaceList = p.find_parents_w_child('^interf', '^ port security$')

        # create the commands so that I can remove this unwanted command
        for line in interfaceList:
                commandList.append(line)
                commandList.append(' port security aging time 1')
                commandList.append(' port security max-mac-count 2')

        # ------------------------------------------------------------------------------------------
        # PORT SECURITY: port security configuration (3550, 3750, 2960, etc)
        # ------------------------------------------------------------------------------------------

        # give me a list of interfaces that are running port security and
        # that DO NOT have a max MAC address count
        interfaceList = p.find_parents_w_child('^interf', '(?=^ switchport port-security$)(?!^ switchport port-security maximum)')

        # create the commands so that I can remove this unwanted command
        for line in interfaceList:
                commandList.append(line)
                commandList.append(' switchport port-security maximum 2')
                commandList.append(' switchport port-security aging time 1')
                commandList.append(' switchport port-security aging type inactivity')
                commandList.append(' no switchport port-security violation restrict')

        # add the config changes the dictionary containing all the changes
        if len(commandList) > 0:
                commandFile[deviceName] = prefixList + commandList + postList

                # write changes to a file
                outfile = open(OUTPUT_DIRECTORY + deviceName, 'w')
                outfile.write("\n" . join(commandList))

# create my custom Commando class and run it against all the devices
#c = CommandExecutor(devices=commandFile.keys(), verbose=True)
#c.run()
