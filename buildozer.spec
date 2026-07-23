[app]

title = openNavy
package.name = opennavy
package.domain = org.opennavy

source.dir = .
source.include_exts = py,png,jpg,kv,ttc,ttf

version = 1.0.0

requirements = python3, pygame, sdl2, sdl2_image, sdl2_mixer, sdl2_ttf

orientation = landscape

osx.python_version = 3
osx.kivy_version = 2.2.0

fullscreen = 1

android.wakelock = 1
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.gradle_dependencies = org.libsdl.android:Sdl:1.0.0

presplash.color = #0a0f28

[buildozer]

log_level = 2
warn_on_root = 1
