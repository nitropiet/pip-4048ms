#!/usr/bin/python

import urllib2
import serial, time

import sqlite3
import datetime
import os
import sys

os_env = os.environ

APP_DIR = os.path.abspath(os.path.dirname(__file__))  # This directory
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))

#Commands with CRC cheats
QPGS0 = '\x51\x50\x47\x53\x30\x3f\xda\x0d'
QPGS1 = '\x51\x50\x47\x53\x31\x2f\xfb\x0d'
QPIGS = '\x51\x50\x49\x47\x53\xB7\xA9\x0d' #valid?
QMCHGCR ='\x51\x4D\x43\x48\x47\x43\x52\xD8\x55\x0D' #?
QMUCHGCR='\x51\x4D\x55\x43\x48\x47\x43\x52\x26\x34\x0D' #?
QPIWS = '\x51\x50\x49\x57\x53\xB4\xDA\x0D' #valid?
POP02 = '\x50\x4F\x50\x30\x32\xE2\x0B\x0D' # set to SBU
POP00 = '\x50\x4F\x50\x30\x30\xC2\x48\x0D' #Set to UTILITY

dbpath="/opt/db/inverter/inverter.db"

#check DB
conn=sqlite3.connect(dbpath)
conn.close()

#initialization and open the port
#possible timeout values:
#	1. None: wait forever, block call
#	2. 0: non-blocking mode, return immediately
#	3. x, x is bigger than 0, float allowed, timeout block call

ser = serial.Serial()
ser.port = "/dev/ttyAMA0"
ser.baudrate = 2400
ser.bytesize = serial.EIGHTBITS	 #number of bits per bytes
ser.parity = serial.PARITY_NONE	 #set parity check: no parity
ser.stopbits = serial.STOPBITS_ONE  #number of stop bits
#ser.timeout = None				 #block read
ser.timeout = 1					 #non-block read
#ser.timeout = 2					#timeout block read
ser.xonxoff = False				 #disable software flow control
ser.rtscts = False				  #disable hardware (RTS/CTS) flow control
ser.dsrdtr = False				  #disable hardware (DSR/DTR) flow control
ser.writeTimeout = 2				#timeout for write


def print_nums(nums_data):
	if nums_data != ['']:
		#print nums_data
		print "SerialNo: " + nums_data[1]
		print "PV input (V): " + nums_data[14]
		print "PV input (A): " + nums_data[25]
		print "Bat in  (A): " + nums_data[12]
		print "Bat out (A): " + nums_data[26][:3]
		print "Load (A): " + nums_data[9]
		print "Load (%): " + nums_data[10]
		print ""

		print "Battery Voltage: " + nums_data[11]
		print "Total Charging (A): " + nums_data[15]
		print "Total usage (W): " + nums_data[17]
		print "Total usage (%): " + nums_data[18]
		print ""
		print ""

def save_data(_capture_datetime, nums_data, save_totals = False):
	conn=sqlite3.connect(dbpath)
	curs=conn.cursor()
	
	#serial no
	#pv_in_V
	#pv_in_A
	#bat_in_A
	#bat_out_A
	#load_W
	#load_perc	
	curs.execute("""INSERT INTO inverter_data values(datetime((?)),
	(?), (?), (?), (?), (?), (?), (?))""", (
	_capture_datetime,
	nums_data[1], 
	nums_data[14], 
	nums_data[25], 
	nums_data[12], 
	nums_data[26][:3], 
	nums_data[9], 
	nums_data[10]))

	if save_totals:
		#datetime

		#bat_V
		#bat_in_A
		#bat_out_A
		#load_W
		#load_perc
		curs.execute("""INSERT INTO total_data values(datetime((?)),
		(?), (?), (?), (?), (?))""", (
		_capture_datetime,
		nums_data[11], 
		nums_data[15], 
		nums_data[26][:3], 
		nums_data[17], 
		nums_data[18]))
	
	conn.commit()
	conn.close()
  
def get_data():

	conn=sqlite3.connect(dbpath)
	curs=conn.cursor()
	
	#datetime
	curs.execute("SELECT datetime('now') ")
	capture_datetime=curs.fetchone()[0]

	conn.close

	#get inverter data from axpert inverter

	if not ser.isOpen():
		try: 
			ser.open()
		except Exception, e:
			print "error open serial port: " + str(e)
			return

	try:
		ser.flushInput()			#flush input buffer, discarding all its contents
		ser.flushOutput()		   #flush output buffer, aborting current output and discard all that is in buffer

		ser.write(QPGS0)
		time.sleep(0.2)			 #give the serial port sometime to receive the data
		response = ser.readline()

		nums = response.split(' ', 99)

		print_nums(nums) 
		save_data(capture_datetime, nums, True)   
	
		ser.write(QPGS1)
		time.sleep(0.2)			 #give the serial port sometime to receive the data
		response = ser.readline()

		nums = response.split(' ', 99)
		print_nums(nums)	
		save_data(capture_datetime, nums)   


	except Exception, e1:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
		print(exc_type, fname, exc_tb.tb_lineno)
		
		print "error communicating...: " + str(e1)
		ser.close()
	conn.close()

	return


 
def main():
	while True:
		get_data()
		time.sleep(120)	
		
if __name__ == '__main__':
	main()
