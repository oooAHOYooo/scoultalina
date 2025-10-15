[app]
title = ScoutAlina
package.name = scoutalina
package.domain = com.scoutalina
source.dir = .
version = 0.1.0
requirements = python3,kivy,plyer,requests
orientation = portrait
fullscreen = 0
icon.filename = ../server/static/images/logo.png

# Android permissions
android.permissions = ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# Target SDK and min SDK (optional; adjust as needed)
# android.minapi = 24
# android.api = 33

[buildozer]
log_level = 2


