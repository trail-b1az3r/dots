# Browsers

## USB devices in the browser

Sites that talk to hardware (flashing a keyboard or a microcontroller, updating a controller, a serial console) use
WebUSB, WebHID or Web Serial. When Chromium's device picker comes up empty, or a device is listed but "access denied",
the browser is fine: it isn't allowed to open the device.

```sh
halcyon usb                       # every device, whether the browser can open it, and what to do
halcyon usb allow 2341:0043       # let the browser open this one (ids as `halcyon usb` lists them)
halcyon usb allow --all           # every USB, HID and USB-serial device except keyboards and mice
halcyon usb remove                # undo
```

Why it happens on Arch:

| Cause | What `halcyon usb` says |
| --- | --- |
| USB device nodes (`/dev/bus/usb/…`) and `/dev/hidraw*` belong to root. systemd lets the person at the screen use only kinds of device it knows: sound, cameras, game controllers, security keys. | Which devices can't be opened, and the `allow` line for them. `allow` writes `/etc/udev/rules.d/70-halcyon-usb.rules`, which tags them `uaccess`: you get access while you're logged in at the screen, and nobody else does. |
| USB-serial adapters (`/dev/ttyUSB*`, `/dev/ttyACM*`) belong to the `uucp` group. | Join `uucp`, or `allow` the adapter. |
| A Flatpak browser sees no devices at all. | `flatpak override --user --device=all org.chromium.Chromium` |
| Your session isn't the active one on a seat (started over SSH, or with `su`). | Says so first: no device access is given then. |
| WebUSB never opens keyboards, mice and other HID, storage, sound, video or smart cards, on any system. | Names the device; sites reach HID devices through WebHID instead. |

`allow --all` leaves keyboards and mice out on purpose: raw access to them would let any program you run read what
you type. If a site still finds nothing, `chrome://device-log` in the browser says why it left a device out.
