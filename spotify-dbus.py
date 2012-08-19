#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# **** BEGIN LICENSE BLOCK ****
# Version: GPL 3.0
#
# The contents of this file are subject to the GNU General Public License Version
# 3.0 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.gnu.org/licenses/gpl.txt
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# **** END LICENSE BLOCK ****
#
# Gnome Integration for Spotify by David Martínez <gnomeintegration@davidmartinez.net>
#
# Requirements:
#
#		Mandatory	: python, python-dbus
#		Recommended	: imagemagick
#		Optional	: wmctrl, x11-utils, xautomation, xdotool
#
# To allow Firefox/Chrome open playlists:
#
#		gconftool-2 -t string -s /desktop/gnome/url-handlers/spotify/command "/path/to/this/script"
#		gconftool-2 -t bool -s /desktop/gnome/url-handlers/spotify/needs_terminal false
#		gconftool-2 -t bool -s /desktop/gnome/url-handlers/spotify/enabled true
#
# References:
#
#		http://www.galago-project.org/specs/notification/0.9/index.html
#
import re
import os
import sys
import dbus
import time
import gobject
import hashlib
import commands

from dbus import Interface
from dbus.mainloop.glib import DBusGMainLoop

class Spotify:
	nid = False
	pid = False
	size = '48x48'
	loop = False
	dloop = False
	debug = True
	cache = os.environ['HOME'] + '/.cache/spotify/Covers/'
	locale = 'en_US'
	player = False
	playing = False
	pidfile = '/tmp/spotify-daemon.pid'
	timeout = 5000
	linktotray = False
	
	translations = {
		'es_ES': {
			'detail_by'			: 'por',
			'detail_album'		: 'del disco',
			'action_next'		: 'Siguiente',
			'action_oause'		: 'Pausar',
			'action_prev'		: 'Anterior',
			'playback_paused'	: 'Reproducción pausada'
		},
		
		'en_US': {
			'detail_by'			: 'by',
			'detail_album'		: 'from',
			'action_next'		: 'Next',
			'action_pause'		: 'Pause',			
			'action_prev'		: 'Previous',
			'playback_paused'	: 'Playback paused'
		}
	}
	
	# Notifier
	def show_playing(self, track = False, interactive = True):
		# Debug info
		if self.debug == True and interactive == True:
			print "Show track data interactively..."
		elif self.debug == True:
			print "Show track data..."
	
		# Define actions in notification
		if interactive == True:
			actions = [ '2', self.translate('action_next') ]
		else:
			actions = []
	
		# If track not specified in parameter, read from D-Bus
		if not track:
			track = self.get_metadata()
	
		# If there's a song playing
		if track:
			# Get Spotify tray icon coordinates
			coords = self.get_tray_coords()
	
			# Configure notification hints
			if coords['x'] > 0:
				hints = { 'x': coords['x'], 'y': coords['y'] }
			else:
				hints = {}
	
			# Generate notification content
			text = self.translate('detail_by') + ' <i>' + self.get_info(track, 'artist')
			text = text + '</i> ' + self.translate('detail_album') + ' <i>' + self.get_info(track, 'album') + '</i>'
			text = text.replace('&', '&amp;')
	
			# Get interface for call notification daemon
			proxy = self.bus.get_object('org.freedesktop.Notifications', '/org/freedesktop/Notifications')
			interface = Interface(proxy, dbus_interface='org.freedesktop.Notifications')
	
			# Closes active notification
			if self.nid != False:
				if self.debug == True:
					print "Closing existing notification..."
				
				interface.CloseNotification(self.nid)
	
			# Shows notification
			self.nid = interface.Notify('Spotify', 0, self.get_cover(), self.get_info(track, 'title'), text, actions, hints, self.timeout)
	
			# Connects to actions signals
			if self.nid > 0:
				if interactive == True:
					interface.connect_to_signal('ActionInvoked', self.action_listener)
	
				interface.connect_to_signal('NotificationClosed', self.action_dismisser)
				gobject.threads_init()
				gobject.timeout_add(self.timeout * 10, self.action_listener)
	
		return self.nid
		
	# Paused notifier
	def show_paused(self):
		# Debug info
		if self.debug == True:
			print "Show paused..."
	
		# Get Spotify tray icon coordinates
		coords = self.get_tray_coords()
	
		# Configure notification hints
		if coords['x'] > 0:
			hints = { 'x': coords['x'], 'y': coords['y'] }
		else:
			hints = {}
	
		# Get interface for call notification daemon
		proxy = bus.get_object('org.freedesktop.Notifications', '/org/freedesktop/Notifications')
		interface = Interface(proxy, dbus_interface='org.freedesktop.Notifications')
	
		# Closes active notification
		if self.nid != False:
			if self.debug == True:
				print "Closing existing notification..."
			
			interface.CloseNotification(self.nid)
	
		# Shows notification
		self.nid = interface.Notify('Spotify', 0, '/usr/share/pixmaps/spotify.png', 'Spotify', self.translate('playback_paused'), [], hints, self.timeout)
	
	# Hides current notification
	def close_notification(self):
		# Get interface for call notification daemon
		proxy = self.bus.get_object('org.freedesktop.Notifications', '/org/freedesktop/Notifications')
		interface = Interface(proxy, dbus_interface='org.freedesktop.Notifications')

		# Closes active notification
		if self.nid != False:
			if self.debug == True:
				print "Closing existing notification..."
			
			interface.CloseNotification(self.nid)		
		
	# Execute an action
	def action_trigger(self, action, param = False):
		if self.debug == True:
			print "Action '" + action + "' invoked..."
	
		if action == 'info':
			self.show_playing()
	
		elif action == 'next':
			self.player.Next()
	
		elif action == 'prev':
			self.player.Previous()
	
		elif action == 'playpause':
			self.player.PlayPause()
	
		elif action == 'play' or action == 'pause':
			if not self.get_metadata():
				self.player.Play()
			else:
				self.player.Pause()
	
		elif action == 'stop':
			if self.get_metadata():
				self.player.Pause()
	
		elif action == 'quit':
			self.player.Quit()
	
		elif action == 'uri':
			if self.debug == True:
				print "Opening " + param + "..."
	
			window = self.get_window()
			window.openLink(param)
	
	# Action listener
	def action_listener(self, id = 0, action = ''):
		if id > 0 and id == self.nid:
			if self.debug == True and action == 'default':
				print "Notification closed by user..."
			elif self.debug == True:
				print "Listener received action '" + action + "', invoking action..."
	
			if action == '0':
				self.action_trigger('stop')
			elif action == '1':
				self.action_trigger('play')
			elif action == '2':
				self.action_trigger('next')
			elif action == '3':
				self.action_trigger('prev')
				time.sleep(1)
				self.action_trigger('prev')
	
			self.nid = False
	
	# Action dismissed, quits loop
	def action_dismisser(self, id = 0, reason = ''):
		if id > 0 and id == self.nid:
			if self.debug == True:
				if reason == 1:
					print "Notification expired..."
				elif reason == 2:
					print "Notification dismissed..."
				elif reason == 3:
					print "Notification closed..."
				else:
					print "Notification closed unexpectedly..."
	
			self.nid = False
	
	# Track change
	def change_listener(self):	
		# Gets current song data
		track = self.get_metadata()
	
		# Check if Spotify is running
		if self.pid and not track:
			if int(commands.getoutput("ps ax | awk '{print $1}' | grep -c " + str(self.pid))) == 0:
				if self.debug == True:
					print "Spotify not running, exiting..."
	
				os.system('rm -f ' + self.pidfile)
				sys.exit()
	
		# Start playing
		if not self.playing and track:
			self.show_playing()
			if self.debug == True:
				print "Start playing..."
	
		# Track info changed
		elif self.playing and track != self.playing:
			# Paused
			if not track:
				# show_paused()
				if self.debug == True:
					print "Track paused..."
			
			# Changed
			else:
				self.show_playing()
				if self.debug == True:
					info = self.get_info(track, 'artist') + ' - ' + self.get_info(track, 'title')
					print "Track changed to " + info + ", show info..."
	
		# Saves current playing song
		self.playing = track;
	
		# Returns true to continue with loop
		return True
	
	# Get formatted info
	def get_info(self, track, item):
		mapped = 'xesam:' + item;
		if item == 'artist':
			for item in track[mapped]:
				info = item
				break
		else:
			info = track[mapped]
	
		return info.encode('utf-8', 'ignore')
	
	# Get the player object
	def get_player(self):
		try:
			proxyobj = self.bus.get_object('org.mpris.MediaPlayer2.spotify', '/')
			pl = dbus.Interface(proxyobj, 'org.freedesktop.MediaPlayer2')
		except dbus.DBusException:
			pl = False
	
		return pl
	
	# Get the window object
	def get_window(self, interface = 'local.sp.SpotifyApplicationLinux'):
		try:
			proxyobj = self.bus.get_object('org.mpris.MediaPlayer2.spotify', '/MainWindow')
			pl = dbus.Interface(proxyobj, interface)
		except dbus.DBusException:
			pl = False
	
		return pl
	
	# Get the current track info
	def get_metadata(self):
		try:
			if self.player != False:
				track = self.player.GetMetadata()
			else:
				track = False
		except dbus.DBusException:
			track = False
	
		return track
	
	# Get in-screen coords of tray Spotify icon
	def get_tray_coords(self):
		tray_coords = { 'x': 0, 'y': 0 }
		
		if self.linktotray == True:
			wmctrl = self.which('wmctrl')
			xwininfo = self.which('xwininfo')
			
			if wmctrl != False and xwininfo != False:
				tray = commands.getoutput(wmctrl + ' -l -p | grep "lateral superior" | awk \'{print $1}\'')
				sptfp = commands.getoutput(xwininfo + ' -id ' + tray + ' -tree | grep "spotify" | awk \'{print $6}\'')
				sptfx = commands.getoutput('echo ' + sptfp + ' | awk -F "+" \'{print $2+=10}\'')
				sptfy = commands.getoutput('echo ' + sptfp + ' | awk -F "+" \'{print $3+=13}\'')
			
				tray_coords = { 'x': int(sptfx), 'y': int(sptfy) }
	
		return tray_coords
	
	# Get current mouse coords
	def get_mouse_coords(self):
		xdotool = self.which('xdotool')
		mouse_coords = { 'x': 0, 'y': 0 }
		
		if xdotool != False:
			mousex = commands.getoutput("xdotool getmouselocation | awk '{print $1}' | sed -e 's/^x://'")
			mousey = commands.getoutput("xdotool getmouselocation | awk '{print $2}' | sed -e 's/^y://'")
			
			mouse_coords = { 'x': int(mousex), 'y': int(mousey) }
	
		return mouse_coords
	
	# Gets the album cover based on a track
	def get_cover(self):
		# Gets track info
		track = self.get_metadata()
	
		# Check if cache path exists to create it
		if not os.path.exists(self.cache):
			os.system('mkdir "' + self.cache + '"')
			if self.debug == True:
				print "Created cache folder..."
		elif self.debug == True:
			print "Cache folder already exists..."
	
		# Generate title-based hash to store album cover
		# base = get_info(track, 'artist') + ' - ' + get_info(track, 'album') + ' (' + str(track['year']) + ')'
		base = self.get_info(track, 'artist') + ' - ' + self.get_info(track, 'album')
		if self.debug == True:
			print 'Generating album hash for "' + base + '"'
	
		h = hashlib.new('md5')
		h.update(base + self.size)
		hash = h.hexdigest()
	
		# Check if cover is already downloaded
		path = self.cache + hash
		if not os.path.exists(path) and self.which('convert'):
			# Generate cover URL
			id = track['xesam:url'].split(':')
			url = 'http://open.spotify.com/track/' + id[2]
			output = commands.getoutput('curl -v ' + url + '| grep \'id="cover-art"\'')
			match = re.search('http(.+)image\/(\w+)', output)
	
			# Download the cover
			if self.debug == True:
				print "Downloading cover " + url + "..."
	
			os.system('wget -q -O ' + path + ' ' + match.group(0))
			os.system('convert -quiet -resize ' + self.size + ' ' + path + ' ' + path)
	
			# If download fails uses default Spotify icon
			if not os.path.exists(path):
				path = '/usr/share/pixmaps/spotify.png'
				if self.debug == True:
					print "Download cover failed..."
			elif self.debug == True:
				print "Download cover success..."
	
		elif self.debug == True:
			print "Cover is already downloaded..."
	
		return path
	
	# Shows Spotify window
	def show_window(self):
		os.system('touch /tmp/spotify-window.toggle')
	
		if player.CanRaise():
			if self.debug == True:
				print "Showing Spotify window..."
	
			player.Raise()
		elif self.debug == True:
			print "Cound't show Spotify window..."
	
	# Hides Spotify window
	def hide_window(self):
		os.system('rm -f /tmp/spotify-window.toggle')
	
		#window = get_window('com.trolltech.Qt.QApplication')
		#window.closeAllWindows()
	
		#if self.debug == True:
		#	print "Hiding Spotify window..."
	
		xte = self.which('xte')
		tray = self.get_tray_coords()
		mouse = self.get_mouse_coords()
	
		if xte != False and tray['x'] > 0 and mouse['x'] > 0:
			if self.debug == True:
				print "Hiding Spotify window..."
	
			commands.getoutput(xte + ' "mousemove ' + str(tray['x']) + ' ' + str(tray['y']) + '" "mousedown 3" "mouseup 3" && sleep 0.01')
			commands.getoutput(xte + ' "mousemove ' + str(tray['x'] + 50) + ' ' + str(tray['y'] + 60) + '" "mousedown 1" "mouseup 1"')
			commands.getoutput(xte + ' "mousemove ' + str(mouse['x']) + ' ' + str(mouse['y']) + '"')
		elif self.debug == True:
			print "Cound't hide Spotify window..."
			
	# Translates a string
	def translate(self, string):
		if string in self.translations[self.locale]:
			string = self.translations[self.locale][string]
			
		return string
			
	# Detects if a command exists
	def which(self, cmd):
		path = False
		
		if os.path.exists("/usr/bin/" + cmd): path = "/usr/bin/" + cmd
		elif os.path.exists("/usr/local/bin/" + cmd): path = "/usr/local/bin/" + cmd
		
		return path
	
	# Just launch Spotify in background
	def launch(self):
		spotify = self.which('spotify')
			
		if spotify != False:
			os.system(spotify + ' > /dev/null 2>&1 &')
			time.sleep(1);
			
			return commands.getoutput('pidof ' + spotify).strip()
		else:
			print 'Spotify cannot be found'
			sys.exit()
	
	# init
	def __init__(self):
		# detects current locale
		locale = commands.getoutput('locale | grep LANG')[5:10];
		if locale in self.translations:
			self.locale = locale
		
		# loop must be global to can quit from listener
		self.loop = gobject.MainLoop()
		
		# Prepare loop for interactive notifications or daemon mode
		self.dloop = DBusGMainLoop()
		bus = dbus.SessionBus(mainloop=self.dloop)
		
		# Container of active notification
		self.nid = False
		
		# Container of current playing song
		self.playing = False
		
		# These are defined incorrectly in dbus.dbus_bindings
		DBUS_START_REPLY_SUCCESS = 1
		DBUS_START_REPLY_ALREADY_RUNNING = 2
		
		# Get the current session bus
		self.bus = dbus.SessionBus()
		
		# Get player object
		self.player = self.get_player()
		
		# Get notification object
		proxy = bus.get_object('org.freedesktop.Notifications', '/org/freedesktop/Notifications')
		interface = Interface(proxy, dbus_interface='org.freedesktop.Notifications')
		
		# Daemon to listen track change
		if '--daemon' in sys.argv or 'daemon' in sys.argv or len(sys.argv) == 1:
			# Get the current PID
			daemon_pid = str(os.getpid())
			
			# Check if daemon is running now
			if not os.path.exists(self.pidfile):
				if self.debug == True:
					print 'Daemon not running, starting...'
				
				os.system('echo ' + daemon_pid + ' > ' + self.pidfile)
			else:
				old_daemon_pid = open(self.pidfile).read().strip();
				
				running = 'ps ax | awk \'{print $1}\' | egrep -c "^' + old_daemon_pid + '$"'
				running = int(commands.getoutput(running).strip())				
				
				if(running == 0):
					if self.debug == True:
						print 'Previous daemon exited unexpectly, starting...'
					
					os.system('rm -f ' + self.pidfile)
					os.system('echo ' + daemon_pid + ' > ' + self.pidfile)
				else:
					if self.debug == True:
						print 'Daemon already running, exiting...'
					
					sys.exit()
			
			# Launch Spotify and wait for it
			if self.player == False:
				if self.debug == True:
					print 'Launching Spotify...'
		
				self.pid = self.launch()
				time.sleep(3)
				self.player = self.get_player()
		
			os.system('touch /tmp/spotify-window.toggle')
		
			if self.debug == True:
				print 'Launching daemon...'
		
			# Start loop listening for track changes
			try:
				gobject.timeout_add(100, self.change_listener)
				self.loop.run()
			except KeyboardInterrupt:
				print 'Stopping daemon...'
		
		# Info
		elif '--info' in sys.argv or 'info' in sys.argv:
			self.action_trigger('info')
		
		# Next song
		elif '--next' in sys.argv or 'next' in sys.argv:
			self.action_trigger('next')
		
		# Previous song
		elif '--prev' in sys.argv or 'prev' in sys.argv:
			self.action_trigger('prev')
		
		# Play/pause
		elif '--play' in sys.argv or '--pause' in sys.argv or 'play' in sys.argv or 'pause' in sys.argv:
			self.action_trigger('play')
		
		# Play/pause (0.6)
		elif '--playpause' or 'playpause' in sys.argv:
			self.action_trigger('playpause')
		
		# Stop
		elif '--stop' in sys.argv or 'stop' in sys.argv:
			self.action_trigger('stop')
		
		# Quit
		elif '--quit' in sys.argv or 'quit' in sys.argv:
			self.action_trigger('quit')
		
		# Show window
		elif '--show' in sys.argv or 'show' in sys.argv:
			self.show_window()
		
		# Hide window
		elif '--hide' in sys.argv or 'hide' in sys.argv:
			self.hide_window()
		
		# Toggle window
		elif '--toggle' in sys.argv or 'toggle' in sys.argv:
			if not os.path.exists('/tmp/spotify-window.toggle'):
				self.show_window()
		
			else:
				self.hide_window()
		
		# Open URI
		elif sys.argv[1][0:8] == 'spotify:':
			self.action_trigger('uri', sys.argv[1])
		
		# Other parameters, error
		else:
			if self.debug == True:
				print "Unknown " + sys.argv[1] + " command..."

s = Spotify()