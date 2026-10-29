# What Halcyon and illogical-impulse run, as NixOS packages. The system module (halcyon.nix) installs these; the
# list follows sdata/dist-arch (the PKGBUILDs) and sdata/deps-info.md, with Halcyon's own needs at the end.
pkgs: with pkgs; [
  # Basics
  inetutils libnotify dbus xorg.xlsclients bc coreutils cliphist cmake curlFull wget ripgrep jq yq-go rsync
  xdg-user-dirs foot alacritty kitty fish starship eza fontconfig kdePackages.kconfig python3 git gnumake

  # Audio
  cava pavucontrol playerctl libdbusmenu-gtk3 easyeffects

  # Backlight and displays
  brightnessctl ddcutil hyprsunset

  # Look: cursor, GTK and Qt themes, icons
  bibata-cursors adw-gtk3 kdePackages.breeze kdePackages.breeze-icons papirus-icon-theme darkly darkly-qt5 matugen

  # Hyprland's companions
  wl-clipboard hypridle hyprlock hyprpicker hyprshot

  # KDE parts the shell uses
  kdePackages.bluedevil python3Packages.dbus-next libsecret kdePackages.dolphin kdePackages.systemsettings
  kdePackages.polkit-kde-agent-1 networkmanager

  # Python for the shell's helpers (uv makes their environment; nix-ld lets its Python run)
  uv gtk4 libadwaita libsoup_3 libportal-gtk4 gobject-introspection

  # Screenshots and recording
  slurp grim swappy tesseract wf-recorder

  # Toolkit
  upower wtype ydotool

  # Widgets
  fuzzel glib imagemagick songrec translate-shell wlogout libqalculate

  # Halcyon: video wallpapers and their previews, the icon packs, the popups, the lock and sound fixes
  ffmpeg mpvpaper avizo power-profiles-daemon pciutils usbutils v4l-utils pulseaudio
]
