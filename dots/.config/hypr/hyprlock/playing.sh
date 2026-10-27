#!/usr/bin/env bash
# What is playing, for the lock screen: "♪  title  ·  artist", or nothing.
command -v playerctl >/dev/null || exit 0
title=$(playerctl metadata title 2>/dev/null) || exit 0
[ -n "$title" ] || exit 0
artist=$(playerctl metadata artist 2>/dev/null)
line="♪  $title${artist:+  ·  $artist}"
echo "${line:0:70}"
