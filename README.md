Spotify GNOME Integration
=========================

This is a python script which adds GNOME integration to Spotify. Specifically
the following features are supported:

* Notification display with cover art when changing tracks
* Use media keys to control playback (patch by Mathieu Virbel)
* Notification tray icon for current track
* DBUS integration (Media Player Indicator gnome-shell extension displays what Spotify is playing)
* Launch spotify:// URL's (playlists etc.) from other applications such as a browser.

Has been tested to work with Spotify 0.9.4.183

## Usage

Instead of launching `spotify` directly launch `spotify-dbus.py`.

## Credits

This script was created by David Martinez (http://code.google.com/p/gnome-integration-spotify/)
I've also incorporated Mathieu Virbel's media keys patch. I'm planning on
continuing to maintain this script with newer Spotify versions and perhaps add
more features to integrate tighter with future GNOME releases.

## Licensing

This script is licensed under the GPLv3.
