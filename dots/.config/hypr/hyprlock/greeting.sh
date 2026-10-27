#!/usr/bin/env bash
# The lock screen's greeting: the time of day and your name (the full name if the account has one).
hour=$(date +%-H)
if (( hour < 5 )); then greeting="Good night"
elif (( hour < 12 )); then greeting="Good morning"
elif (( hour < 18 )); then greeting="Good afternoon"
else greeting="Good evening"; fi
name=$(getent passwd "$USER" | cut -d: -f5 | cut -d, -f1)
echo "$greeting, ${name:-${USER:-$(id -un)}}"
