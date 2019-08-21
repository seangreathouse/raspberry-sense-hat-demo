#!/usr/bin/python

## Controls:
## Left: Display Message
## Right: Rotate through color sets
## Up: Pause display (will wait until message is done)
## Down: Start pattern display
## Middle: Display IP address, wired if present, wifi otherwise

from sense_hat import SenseHat
sense = SenseHat()
import threading
from threading import Thread
import time
import sys
import signal
from subprocess import check_output
import re

#sense.rotation = 180
sense.low_light = False

# Set custom display message
display_message = "Hello World"

# Define colors
black = (0, 0, 0)
white = (255, 255, 255)
green = (0, 255, 0)
red = (255, 0, 0)
red_med = (170, 0, 0)
red_dark = (100, 0, 0)
blue = (0, 0, 255)
blue_med = (0, 0, 170)
blue_dark = (0, 0, 100)
violet = (102, 0 ,204)
purple = (153, 51, 255)
orange = (255, 102, 0)
# Define color sets
# (head, trail1, trail2,trail3/clean, center, background, set_number)
color_sets = ((blue, blue_med, blue_dark, black, purple, black, 0),
			 (red, red_med, red_dark, black, orange, black, 1),
			 (violet, violet, blue_dark, black, orange, black, 2))
# Set the active color set
color_set = color_sets[0]

# Set the length of each segment of the trail
# The offsets are cumulative, so a trail with 3 segments of 4 pixels each
# would have offsets of 4, 8 & 12
trail_offset_1 = 4
trail_offset_2 = 6
trail_offset_3 = 8

# Set the time in seconds for the trail to complete a circle
rotation_time = 3
sleep_time = float(rotation_time)/28

# Set the timing for center animation
start_sleep_time = .03
center_sleep_time = .01

# For message display mode:
default_display_message = display_message
draw_message_in_progress = False
start_routine_in_progress = False

# Set info for IP display
wifi_interface = "wlan0"
wired_interface = "eth0"

# Set one time special start position
position = -1
# Start counter
counter = 0

## Define start state
draw_message_pause = True
draw_trail_pause = False
draw_center_pause = False

# If true, pauses before executing joystick action 
film_mode = False
film_mode_pause_time = 5

## We are working in terms of positions around the perimeter
## of the sense hat led grid.
## our 8x8 grid has 28 positions numbered 0-27

## We are drawing a 2 pixel wide trail clockwise around the perimeter
## So we have an inner and outer pixel for each position

## Calculate the pixels to draw for each position
## Takes position as input, then returns xy coordinates
## to draw the inner and outer pixels of our trail
def position_calc(position):
	# First run draw
	if position == -1:
		out_x = 0
		out_y = 0
		in_x = 0
		in_y = 1
	# Top Row + Top Corners		
	if position >= 0 and position <= 7:
		out_x = position
		out_y = 0
		if position == 0:
			in_x = 1
			in_y = 1
		elif position == 7:
			in_x = 6
			in_y = 1
		else:
			in_x = out_x
			in_y = out_y+1
	# Right Edge
	if position >= 8 and position <= 13:
		out_x = 7
		out_y = position-7
		in_x = 6
		in_y = position-7
	# Bottom Row + Bottom Corners
	if position >= 14 and position <= 21:
		out_x = 21-position
		out_y = 7
		if position == 14:
			in_x = 6
			in_y = 6
		elif position == 21:
			in_x = 1
			in_y = 6 
		else:
			in_x = out_x
			in_y = out_y-1
	# Left Edge
	if position >= 22 and position <= 27:
		out_x = 0
		out_y = 28-position
		in_x = 1
		in_y = 28-position
	return((out_x, out_y, in_x, in_y))

def draw_start_routine(center_color, background_color):
	global start_routine_in_progress
	sense.clear()
	start_routine_in_progress = True
	## Draw vertical lines
	for column_x in range(0, 8):
		time.sleep(start_sleep_time)
		for row_y in range(0, 8):
			sense.set_pixel(column_x, row_y, center_color)
	for column_x in range(0, 8):
		time.sleep(start_sleep_time)
		for row_y in range(0, 8):
			sense.set_pixel(column_x, row_y, background_color)
	for column_x in reversed(range(0, 8)):
		time.sleep(start_sleep_time)
		for row_y in range(0, 8):
			sense.set_pixel(column_x, row_y, center_color)
	for column_x in reversed(range(0, 8)):
		time.sleep(start_sleep_time)
		for row_y in range(0, 8):
			sense.set_pixel(column_x, row_y, background_color)
	## Draw Horizontal Lines
	for row_y in range(0, 8):
		time.sleep(start_sleep_time)
		for column_x in range(0, 8):
			sense.set_pixel(column_x, row_y, center_color)
	for row_y in range(0, 8):
		time.sleep(start_sleep_time)
		for column_x in range(0, 8):
			sense.set_pixel(column_x, row_y, background_color)
	for row_y in reversed(range(0, 8)):
		time.sleep(start_sleep_time)
		for column_x in range(0, 8):
			sense.set_pixel(column_x, row_y, center_color)
	for row_y in reversed(range(0, 8)):
		time.sleep(start_sleep_time)
		for column_x in range(0, 8):
			sense.set_pixel(column_x, row_y, background_color)
	start_routine_in_progress = False

def draw_trail(trail_offset, trail_color):
	if counter >= trail_offset: # don't clean/draw tail until head has been drawn
		if counter == trail_offset: #Exception to clean initial step
			trail_position = -1
		elif position < trail_offset:
			trail_position = position - trail_offset + 28
		else:
			trail_position = position - trail_offset
		trail_draw = position_calc(trail_position)
		sense.set_pixel(trail_draw[0], trail_draw[1], trail_color)
		sense.set_pixel(trail_draw[2], trail_draw[3], trail_color)

def draw_center_routine():
	this_thread = threading.currentThread()
	while getattr(this_thread, "continue_thread", True):
		while (draw_center_pause == True) and (getattr(this_thread, "continue_thread", True)):
			time.sleep(.01)
			pass
		time.sleep(center_sleep_time)
		for row_y in range(2, 6):
			for column_x in range(2, 6):
				sense.set_pixel(column_x, row_y, color_set[4])

def draw_trail_routine():
	global position
	global counter
	this_thread = threading.currentThread()
	while getattr(this_thread, "continue_thread", True):	
		while (draw_trail_pause == True) and (getattr(this_thread, "continue_thread", True)):
			time.sleep(.01)
			pass
		## Pause at start if time in second is not evenly divisible by rotation time
		if (position == -1): #or (position == 0):
			while True:
				my_time = time.time()
				time_head, sep, time_tail = str(my_time).partition('.')
				time_check = float(time_head)/rotation_time
				time_head, sep, time_even = str(time_check).partition('.')
				if int(time_even) > 0 :
					second_correction = True
				if int(time_even) == 0 :
					break 
		#Reset as there are only positions 0-27
		if position == 28:  
			position = 0	
		draw_trail(0, color_set[0])
		draw_trail(trail_offset_1, color_set[1])
		draw_trail(trail_offset_2, color_set[2])
		draw_trail(trail_offset_3, color_set[3])
		time.sleep(sleep_time)
		if position == -1: # Exception for initial step
			position = 0
		position += 1
		counter += 1

def draw_message():
	global display_message
	global draw_message_pause
	global draw_message_in_progress
	this_thread = threading.currentThread()
	while getattr(this_thread, "continue_thread", True):
		while draw_message_pause == True and (getattr(this_thread, "continue_thread", True)):
			time.sleep(.1)
			pass
		if draw_message_pause == False:
			draw_message_in_progress = True
			sense.show_message(display_message, text_colour=orange, scroll_speed=0.075)
			draw_message_in_progress = False
		
def change_color_set():
	global color_set
	global color_sets
	if color_set[6] != (len(color_sets)-1):
		color_set = color_sets[(color_set[6]+1)]
		sense.clear()
	else:
		color_set = color_sets[0]
		sense.clear()

def display_ip():
	global wired_interface
	global wifi_interface
	wifi_info = check_output(["/sbin/ifconfig", wifi_interface])
	wired_info = check_output(["/sbin/ifconfig", wired_interface])
	ip_pattern = re.compile(r'inet\ addr\:(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', re.MULTILINE)
	wifi_ip = re.findall(ip_pattern, wifi_info)
	wired_ip = re.findall(ip_pattern, wired_info)
	if len(wifi_ip) == 1:
		wifi_ip = str(wifi_ip[0])
		wifi_ip_first_octet = str(wifi_ip.split(".")[0])
	if len(wired_ip) == 1:
		wired_ip = str(wired_ip[0])
		wired_ip_first_octet = str(wired_ip.split(".")[0])
	if wired_ip and (wired_ip_first_octet != "169"):
		return(wired_ip)
	elif wifi_ip and (wifi_ip_first_octet != "169"):
		return(wifi_ip)
	else: 
		return("no valid ip")

def joystick_input():
	global draw_trail_thread
	global display_message
	global default_display_message
	global draw_message_pause
	global draw_trail_pause
	global draw_center_pause
	global film_mode
	global film_mode_pause_time
	this_thread = threading.currentThread()
	while getattr(this_thread, "continue_thread", True):
			for event in sense.stick.get_events():
				if ((event.action == "pressed") or (event.action == "held")):
					if film_mode == True:
						time.sleep(film_mode_pause_time)
				if ((event.action == "pressed") or (event.action == "held")) and (event.direction == "up"):
					draw_trail_pause = True
					draw_center_pause = True
					draw_message_pause = True
					sense.clear()
					time.sleep(.01)
					sense.clear()
				if ((event.action == "pressed") or (event.action == "held")) and (event.direction == "down"):
					draw_message_pause = True
					while draw_message_in_progress == True:
						time.sleep(.01)
					while start_routine_in_progress == True:
						time.sleep(.01)
					sense.clear()
					time.sleep(.01)
					sense.clear()
					draw_trail_pause = False
					draw_center_pause = False
				if ((event.action == "pressed") or (event.action == "held")) and ((event.direction == "left") or (event.direction == "middle")):
					if event.direction == "middle":
						display_message = display_ip()
					else:
						display_message = default_display_message
					draw_trail_pause = True
					time.sleep(.01)
					draw_center_pause = True
					time.sleep(.01)
					draw_message_pause = False
					sense.clear()
					time.sleep(.01)
					sense.clear()
				if ((event.action == "pressed") or (event.action == "held")) and (event.direction == "right"):
					change_color_set()
					sense.clear()
					time.sleep(.01)
					sense.clear()


def main():
	try:
		sense.clear()
		draw_trail_thread = Thread(target = draw_trail_routine, args = ())
		draw_center_thread = Thread(target = draw_center_routine, args = ())
		draw_message_thread = Thread(target = draw_message, args = ())
		draw_message_thread.continue_thread = True
		joystick_input_thread = Thread(target = joystick_input, args = ())
		draw_message_pause = True
		draw_trail_pause = False
		draw_center_pause = False
		draw_start_routine(color_set[4], color_set[5])
		draw_trail_thread.start()
		draw_center_thread.start()
		draw_message_thread.start()
		joystick_input_thread.start()
		draw_center_thread.join(99999999999999)
		draw_message_thread.join(99999999999999)
		draw_trail_thread.join(99999999999999)
		joystick_input_thread.join(99999999999999)
	except (KeyboardInterrupt, SystemExit):
		draw_message_thread.continue_thread = False
		while draw_message_in_progress == True:
			time.sleep(.01)
		draw_trail_thread.continue_thread = False
		draw_center_thread.continue_thread = False
		joystick_input_thread.continue_thread = False
		sense.clear()
		time.sleep(.01)
		draw_start_routine(color_set[4], color_set[5])
	 	sys.exit()

if __name__ == '__main__':
	main()
