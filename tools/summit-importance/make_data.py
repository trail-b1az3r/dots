#!/usr/bin/env python3
"""The training examples for Summit's notification importance model: make_data.py > data.jsonl.

Notifications as a desktop gets them, each labelled important (1: worth a banner under the clock) or not (0), from
templates filled with apps, people, places and numbers. Seeded, so the same file comes out every time. The examples
in holdout.jsonl are written by hand instead and never trained on: train.py measures the model on them.

Important: things to act on now or soon. Security (sign-ins, codes, password changes), calls, a person writing to you
directly about something that needs you, meetings and alarms about to start, failures (builds, backups, payments,
deliveries that need you), the computer itself in trouble (battery critical, disk full, overheating).
Not important: chatter. Likes and follows, promotions and digests, now playing, connected/disconnected, saved,
copied, finished downloads and updates, successes, group-chat banter, achievements.
"""

from __future__ import annotations

import json
import random
import sys

R = random.Random(20261126)

PEOPLE = ["Ana", "Ben", "Chloé", "Dev", "Emma", "Farah", "Gus", "Hana", "Ivan", "Jules", "Kofi", "Lena", "Mateo",
          "Nia", "Omar", "Priya", "Quinn", "Rosa", "Sam", "Tariq", "Uma", "Viktor", "Wen", "Yusuf", "Zoe", "Mum", "Dad",
          "Grandma", "Alex Chen", "Maria Lopez", "the landlord", "your manager"]
CHAT_APPS = ["Signal", "Telegram", "Discord", "Slack", "WhatsApp", "Element", "Messages", "KDE Connect"]
MAIL_APPS = ["Thunderbird", "Betterbird", "Evolution", "Geary"]
PLACES = ["Lagos", "São Paulo", "Moscow", "an unknown device", "Windows 11, Chrome", "a new iPhone", "Jakarta",
          "Frankfurt", "a browser in Ohio"]
SERVICES = ["Google", "GitHub", "Microsoft", "your bank", "Proton", "Steam", "Discord", "Apple ID", "PayPal",
            "Amazon", "Dropbox"]
EVENTS = ["Stand-up", "Design review", "Dentist", "1:1 with Priya", "Sprint planning", "Team sync", "Interview",
          "Doctor's appointment", "Parent-teacher meeting", "Flight check-in", "Client call", "Lecture: Linear Algebra"]
REPOS = ["halcyon", "frontline", "api-server", "web", "mobile-app", "infra", "docs", "payments"]
SONGS = [("Midnight City", "M83"), ("Holocene", "Bon Iver"), ("Teardrop", "Massive Attack"), ("Nights", "Frank Ocean"),
         ("Clair de Lune", "Debussy"), ("Pyramids", "Frank Ocean"), ("Windowlicker", "Aphex Twin")]
WIFI = ["Home", "Eduroam", "CoffeeShop_Guest", "Pixel 9", "Office-5G", "Library"]
DEVICES = ["WH-1000XM5", "AirPods Pro", "Keychron K2", "MX Master 3S", "Pixel Buds", "JBL Flip 6"]
FILES = ["report.pdf", "archlinux-2026.11.01-x86_64.iso", "holiday.zip", "invoice-1123.pdf", "setup.exe", "song.mp3"]
GROUPS = ["#random", "#general", "Family", "Climbing crew", "Book club", "#memes", "Gaming"]
STORES = ["Steam", "Epic Games", "Zalando", "IKEA", "Uber Eats", "Spotify", "Duolingo", "Humble Bundle"]
GAMES = ["Hades II", "Elden Ring", "Celeste", "Factorio", "Stardew Valley", "Baldur's Gate 3"]
HOSTS = ["db-01", "web-prod-2", "nas.local", "homeassistant", "vpn-gw", "minecraft-server"]


def n(app, summary, body="", label=0, urgency=1, actions=False):
    # Most apps send everything at normal urgency, chatter included, and many add buttons to it: an unimportant one
    # gets low urgency only sometimes and buttons now and then, so neither says "important" on its own.
    if label == 0:
        if urgency == 0 and R.random() < 0.6:
            urgency = 1
        if not actions and R.random() < 0.3:
            actions = True
    return {"appName": app, "summary": summary, "body": body, "urgency": urgency, "hasActions": actions, "label": label}


TASKS = ["Pick up the kids", "Take your medication", "Call the plumber", "Pay the rent", "Submit the assignment",
         "Leave for the airport", "Move the car", "Feed the cat", "Renew your passport", "Collect the prescription",
         "Doctor appointment", "Send the invoice"]
REMINDER_APPS = ["Calendar", "Reminders", "gnome-calendar", "Korganizer", "Todo", "Planify", "Errands"]


def code():
    return str(R.randint(100000, 999999)) if R.random() < 0.8 else str(R.randint(1000, 9999))


def important():
    p, q = R.choice(PEOPLE), R.choice(PEOPLE)
    chat, mail = R.choice(CHAT_APPS), R.choice(MAIL_APPS)
    svc, ev, repo, host = R.choice(SERVICES), R.choice(EVENTS), R.choice(REPOS), R.choice(HOSTS)
    m = R.choice([1, 2, 3, 5, 10, 15])
    c = code()
    pct = R.randint(2, 9)
    return R.choice([
        lambda: n(svc, "New sign-in to your account", f"Someone signed in from {R.choice(PLACES)}. Was this you? If not, secure your account now.", 1, actions=True),
        lambda: n(svc, "Suspicious sign-in attempt blocked", f"We blocked a sign-in attempt from {R.choice(PLACES)}. Change your password.", 1),
        lambda: n(svc, "Your password was changed", "If you didn't do this, reset it immediately.", 1),
        lambda: n(chat, "Verification code", f"{c} is your {svc} verification code. Don't share it.", 1),
        lambda: n("Messages", f"{svc}", f"Your login code is {c}. It expires in 10 minutes.", 1),
        lambda: n(svc, "Approve sign-in request?", f"Tap to approve the sign-in from {R.choice(PLACES)}.", 1, actions=True),
        lambda: n("Power", "Battery critically low", f"{pct}% remaining. The computer will suspend soon. Plug in now.", 1, urgency=2),
        lambda: n("UPower", f"Battery low: {pct}%", "Connect the charger to keep working.", 1),
        lambda: n("Calendar", f"{ev} starts in {m} minutes", R.choice(["Room 4B", "Google Meet", "Zoom link in the invite", ""]), 1, actions=True),
        lambda: n("Calendar", f"Reminder: {ev}", f"Today at {R.randint(8, 18)}:{R.choice(['00', '15', '30', '45'])}, in {m} min", 1),
        lambda: n("Calendar", f"Now: {ev}", "Your event is starting now.", 1, actions=True),
        lambda: n(R.choice(REMINDER_APPS), R.choice(TASKS), R.choice([f"In {m} minutes", "Due now", f"Today at {R.randint(8, 20)}:00", f"in {m} min", "Overdue"]), 1, actions=R.random() < 0.5),
        lambda: n(R.choice(REMINDER_APPS), f"Reminder: {R.choice(TASKS).lower()}", R.choice(["", "Now", f"{m} minutes from now"]), 1),
        lambda: n("Clock", R.choice(["Alarm", "Timer finished", "Wake up"]), R.choice(["Time's up!", "Your timer has ended", "07:00"]), 1, urgency=2, actions=True),
        lambda: n(chat, f"Incoming call from {p}", "", 1, urgency=2, actions=True),
        lambda: n(chat, f"{p} is calling…", "Answer or decline", 1, urgency=2, actions=True),
        lambda: n(chat, f"Missed call from {p}", R.choice(["", "Call back?", "2 missed calls"]), 1),
        lambda: n(chat, p, R.choice(["Are you there? I need help with something urgent",
                                     "Can you call me asap?", "The server is down, can you look?",
                                     "Where are you? We're all waiting at the entrance",
                                     "Please send me the contract before 5pm today",
                                     "I'm outside, can you open the door?",
                                     "Did you lock the front door? Answer pls",
                                     "Emergency — call me back now",
                                     "Your car is blocking the driveway, can you move it?",
                                     f"@{q.lower().split()[0]} can you review my PR today? it's blocking the release"]), 1, actions=True),
        lambda: n("Slack", f"{p} mentioned you in #{repo}", R.choice(["can you take a look at this before the deploy?",
                                                                      "you're on call — prod alerts are firing",
                                                                      "need your approval on this"]), 1, actions=True),
        lambda: n(mail, f"From {p}: {R.choice(['Urgent: contract signature needed', 'Action required: invoice overdue', 'Your offer letter', 'Re: deadline today'])}",
                  "Please reply as soon as possible.", 1, actions=True),
        lambda: n("GitHub", f"Build failed: {repo}/main", f"CI failed on main: {R.randint(1, 12)} tests failing.", 1, actions=True),
        lambda: n("CI", f"Deployment to production failed", f"{repo}: rollback required. Check the logs.", 1),
        lambda: n("Monitoring", f"{host} is down", f"No response for {m} minutes.", 1, urgency=2),
        lambda: n("Monitoring", f"High error rate on {host}", f"5xx errors above threshold for {m} minutes", 1),
        lambda: n("Backup", "Backup failed", f"The backup to {host} could not finish: disk full.", 1),
        lambda: n("Disk usage", "Low disk space", f"Only {R.randint(50, 900)} MB left on /. Free some space.", 1),
        lambda: n("System", "Out of memory", f"{R.choice(['firefox', 'code', 'chromium', 'blender'])} was closed to free memory.", 1, urgency=2),
        lambda: n("Sensors", "CPU temperature critical", f"{R.randint(95, 105)}°C. The computer will shut down to protect itself.", 1, urgency=2),
        lambda: n(R.choice(["PayPal", "Bank", "Revolut", "Monzo"]), R.choice(["Payment failed", "Card declined", "Unusual card activity"]),
                  R.choice([f"A payment of €{R.randint(5, 900)} was declined.", "Please verify this transaction.", "Your card has been frozen."]), 1, actions=True),
        lambda: n(R.choice(["DHL", "UPS", "Royal Mail", "Amazon"]), R.choice(["Your courier is 2 stops away", "Delivery attempt failed", "Action needed for your parcel"]),
                  R.choice(["Someone needs to be home to sign.", "Rearrange delivery today or it goes back.", "Customs fee to pay."]), 1),
        lambda: n("Flights", R.choice(["Gate change", "Boarding now", "Your flight is delayed"]), f"Flight {R.choice(['LH', 'BA', 'KL'])}{R.randint(100, 999)}: gate {R.choice('ABCD')}{R.randint(1, 40)}", 1, urgency=2),
        lambda: n("Halcyon", "Update failed", "pacman could not finish: conflicting files. Your system may be partially updated.", 1),
        lambda: n("Screen locker", "Lock screen failed", "hyprlock could not start: your session is unlocked.", 1, urgency=2),
        lambda: n(chat, f"{p} (direct message)", R.choice(["hey, did you get my email? it's important", "need an answer from you by noon",
                                                           "your mum called, phone her back"]), 1),
    ])()


def unimportant():
    p = R.choice(PEOPLE)
    chat = R.choice(CHAT_APPS)
    store = R.choice(STORES)
    title, artist = R.choice(SONGS)
    k = R.randint(2, 40)
    m = R.choice([1, 2, 3, 5, 10, 15])
    return R.choice([
        lambda: n(R.choice(["Instagram", "Mastodon", "Bluesky", "YouTube"]), f"{p} liked your post", "", 0),
        lambda: n(R.choice(["Instagram", "Mastodon", "Bluesky", "GitHub"]), f"{p} started following you", "", 0),
        lambda: n(R.choice(["Mastodon", "Bluesky"]), f"{p} boosted your post", R.choice(["", "“Look at this sunset”"]), 0),
        lambda: n("YouTube", f"New video from {R.choice(['Linus Tech Tips', 'Veritasium', 'Kurzgesagt', 'Fireship'])}", R.choice(["I tried Linux for 30 days", "The fastest way to learn anything", ""]), 0),
        lambda: n(store, R.choice([f"{R.randint(10, 80)}% off this weekend", "Your weekly digest", "New arrivals you might like",
                                  "Don't miss out!", "Recommended for you", "Your wishlist item is on sale"]),
                  R.choice(["Shop now", "Offer ends Sunday", "Tap to see what's new", ""]), 0),
        lambda: n(R.choice(["Spotify", "Elisa", "mpv", "Firefox"]), title, artist, 0, urgency=0),
        lambda: n("Now playing", f"{title} — {artist}", "", 0, urgency=0),
        lambda: n("NetworkManager", R.choice(["Connection established", "Connected"]), f"You are now connected to “{R.choice(WIFI)}”.", 0, urgency=0),
        lambda: n("NetworkManager", "Disconnected", f"You are now disconnected from “{R.choice(WIFI)}”.", 0, urgency=0),
        lambda: n("Bluetooth", f"{R.choice(DEVICES)} connected", R.choice(["", "Battery 80%"]), 0, urgency=0),
        lambda: n("Screenshot", R.choice(["Screenshot saved", "Screenshot copied"]), R.choice(["~/Pictures/Screenshots/2026-11-26.png", "Copied to the clipboard"]), 0, urgency=0),
        lambda: n(R.choice(["Firefox", "Dolphin", "Downloads"]), "Download complete", R.choice(FILES), 0, urgency=0),
        lambda: n("Halcyon", R.choice(["Updates available", "System is up to date"]), f"{k} packages can be updated.", 0, urgency=0),
        lambda: n("Discover", f"{R.choice(['Firefox', 'Krita', 'Steam', 'kitty'])} was updated", "", 0, urgency=0),
        lambda: n("Halcyon", R.choice(["Theme applied", "Wallpaper changed", "Night light on"]), R.choice(["HyperNeo v2", "", "Until 06:30"]), 0, urgency=0),
        lambda: n("Power", R.choice(["Battery fully charged", "Charging", "Power saver off"]), R.choice(["100%", "Plugged in", ""]), 0, urgency=0),
        lambda: n("Backup", "Backup complete", f"{k} GB backed up to {R.choice(HOSTS)}.", 0, urgency=0),
        lambda: n("GitHub", f"Build passed: {R.choice(REPOS)}", "All checks have passed", 0),
        lambda: n("GitHub", f"{p} starred {R.choice(REPOS)}", "", 0),
        lambda: n(chat, f"{p} in {R.choice(GROUPS)}", R.choice(["lol", "haha nice", "👍", "anyone watching the game tonight?", "look at this meme",
                                                            "good morning everyone", "same", "that's hilarious", "brb"]), 0),
        lambda: n(chat, R.choice(GROUPS), f"{k} new messages", 0),
        lambda: n("Discord", f"{p} is now playing {R.choice(GAMES)}", "", 0, urgency=0),
        lambda: n("Steam", "Achievement unlocked", f"{R.choice(GAMES)}: {R.choice(['First Blood', 'Explorer', 'Completionist'])}", 0, urgency=0),
        lambda: n("Steam", f"{R.choice(GAMES)} is on sale", f"-{R.randint(20, 90)}% until Monday", 0, urgency=0),
        lambda: n("Duolingo", R.choice(["Time for your daily lesson!", "Don't lose your streak 🔥", "Your weekly progress"]), "Keep it up", 0),
        lambda: n(R.choice(MAIL_APPS), f"{k} new messages", R.choice(["Newsletter: November edition", "Your order has shipped", "Weekly summary"]), 0),
        lambda: n("Clipboard", "Copied", "", 0, urgency=0),
        lambda: n("KDE Connect", f"{p}'s phone", "Battery 45%", 0, urgency=0),
        lambda: n("Weather", R.choice(["Today: partly cloudy", "Tomorrow: rain", "Sunny, 21°"]), "High 12°, low 4°", 0, urgency=0),
        lambda: n("Calendar", f"Tomorrow: {R.choice(EVENTS)}", "All day", 0),
        lambda: n("Uber Eats", R.choice(["Your order was delivered", "Rate your order"]), "Enjoy your meal!", 0),
        lambda: n("Volume", f"Volume {R.randint(0, 100)}%", "", 0, urgency=0),
        # "Minutes" and buttons where nothing is urgent, so a time alone does not make it important.
        lambda: n(R.choice(["Duolingo", "Headspace", "Fitbit", "Strava", "Kindle"]),
                  R.choice(["Keep your streak going", "Time to stretch", "Ready for today's session?", "Your daily goal"]),
                  R.choice([f"Just {m} minutes a day", f"Practice for {m} minutes", f"A {m}-minute read", f"{m} min left in your goal"]), 0),
        lambda: n(R.choice(["Medium", "Reddit", "Hacker News", "Pocket"]), R.choice(["Trending now", "Recommended", "Top post today"]),
                  f"{R.choice(['Why Rust is eating the world', 'I quit my job to build a keyboard', 'The history of tabs'])} · {m} min read", 0),
        lambda: n(R.choice(["pamac", "Discover", "GNOME Software", "Halcyon", "Flatpak"]),
                  R.choice([f"{k} updates available", "Updates are ready", "Software updates"]),
                  R.choice(["Click to update", "Install now", "Restart to finish", ""]), 0, actions=True),
        lambda: n(R.choice(["Firefox", "Chromium", "Dolphin", "Transmission", "Motrix"]),
                  R.choice(["Download finished", "Download complete", "Torrent finished"]), R.choice(FILES), 0, actions=True),
        lambda: n(chat, p, R.choice(["haha ok", "sounds good", "thanks!", "see you tomorrow", "nice photo", "👍",
                                     "how was your weekend?", "I'll send the pics later", "lol same"]), 0),
    ])()


def main():
    rows = [important() for _ in range(900)] + [unimportant() for _ in range(1100)]
    R.shuffle(rows)
    for row in rows:
        sys.stdout.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
