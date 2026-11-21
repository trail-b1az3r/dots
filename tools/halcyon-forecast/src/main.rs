//! Summit's forecast window (the weather in the top bar opens it): where you are, now, the next hours and the week,
//! in the active theme's colours. It only reads files: halcyon_weather.py fetches the forecast into
//! ~/.cache/halcyon/weather.json, and halcyon-theme writes Summit's colours to ~/.local/state/halcyon/summit.json.
//! Both are read again every half minute, so the window follows a new forecast or theme while it is open.
//!
//! Escape or Q closes it; R asks for a fresh forecast (systemctl --user start halcyon-weather.service).

use std::path::PathBuf;
use std::time::Duration;

use iced::alignment::{Horizontal, Vertical};
use iced::font::Weight;
use iced::widget::{column, container, row, space, text, Column, Row};
use iced::{keyboard, time, window, Border, Color, Element, Font, Length, Size, Subscription, Task, Theme};
use serde::Deserialize;

const UI: Font = Font::with_name("Inter");
// The ten weather icons this window draws, from Google's Material Symbols Rounded (Apache License 2.0), cut to its
// Regular weight and to just these glyphs (assets/README.md), so they look the same on every system.
const ICONS: Font = Font::with_name("Halcyon Weather Icons");
const ICON_FONT: &[u8] = include_bytes!("../assets/weather-icons.ttf");

// The forecast (halcyon_weather.py's cache) --------------------------------------------------------------------------

#[derive(Debug, Default, Clone, Deserialize)]
#[serde(default)]
struct Forecast {
    updated: String,
    place: Place,
    current: Current,
    daily: Vec<Day>,
    hourly: Vec<Hour>,
}

#[derive(Debug, Default, Clone, Deserialize)]
#[serde(default)]
struct Place {
    name: String,
    source: String,
}

#[derive(Debug, Default, Clone, Deserialize)]
#[serde(default)]
struct Current {
    temperature: Option<f64>,
    feels_like: Option<f64>,
    weather_code: Option<i64>,
    is_day: Option<i64>,
}

#[derive(Debug, Default, Clone, Deserialize)]
#[serde(default)]
struct Day {
    date: String,
    max: Option<f64>,
    min: Option<f64>,
    weather_code: Option<i64>,
    rain: Option<f64>,
}

#[derive(Debug, Default, Clone, Deserialize)]
#[serde(default)]
struct Hour {
    time: String,
    temperature: Option<f64>,
    weather_code: Option<i64>,
}

// The colours (Summit's settings) ------------------------------------------------------------------------------------

#[derive(Debug, Clone, Copy)]
struct Palette {
    background: Color,
    surface: Color,
    track: Color,
    text: Color,
    muted: Color,
    accent: Color,
    warm: Color,
}

impl Default for Palette {
    // HyperNeo v2's, as in Summit's Theme.qml.
    fn default() -> Self {
        Palette {
            background: rgb(0x0B1322),
            surface: rgb(0x101A2C),
            track: rgb(0x18243A),
            text: rgb(0xE8EDF6),
            muted: rgb(0x93A0B6),
            accent: rgb(0x9CC0FF),
            warm: rgb(0xE8C79A),
        }
    }
}

fn rgb(n: u32) -> Color {
    Color::from_rgb8((n >> 16) as u8, (n >> 8) as u8, n as u8)
}

fn hex(value: &str) -> Option<Color> {
    let v = value.strip_prefix('#')?;
    (v.len() == 6).then(|| u32::from_str_radix(v, 16).ok().map(rgb)).flatten()
}

fn read_palette(path: &PathBuf) -> Palette {
    let mut palette = Palette::default();
    let Ok(raw) = std::fs::read_to_string(path) else { return palette };
    let Ok(json) = serde_json::from_str::<serde_json::Value>(&raw) else { return palette };
    let colours = &json["colors"];
    for (key, slot) in [
        ("background", &mut palette.background),
        ("surface", &mut palette.surface),
        ("surface_high", &mut palette.track),
        ("text", &mut palette.text),
        ("muted", &mut palette.muted),
        ("accent", &mut palette.accent),
        ("warm", &mut palette.warm),
    ] {
        if let Some(c) = colours[key].as_str().and_then(hex) {
            *slot = c;
        }
    }
    palette
}

// WMO weather codes (Open-Meteo's) as words and icons ----------------------------------------------------------------

fn words(code: Option<i64>) -> &'static str {
    match code {
        Some(0) => "Clear",
        Some(1) => "Mostly clear",
        Some(2) => "Partly cloudy",
        Some(3) => "Overcast",
        Some(45 | 48) => "Fog",
        Some(51 | 53 | 55) => "Drizzle",
        Some(56 | 57) => "Freezing drizzle",
        Some(61) => "Light rain",
        Some(63) => "Rain",
        Some(65) => "Heavy rain",
        Some(66 | 67) => "Freezing rain",
        Some(71) => "Light snow",
        Some(73) => "Snow",
        Some(75) => "Heavy snow",
        Some(77) => "Snow grains",
        Some(80 | 81) => "Showers",
        Some(82) => "Heavy showers",
        Some(85 | 86) => "Snow showers",
        Some(95) => "Thunderstorm",
        Some(96 | 99) => "Thunderstorm with hail",
        _ => "",
    }
}

/// The icon for a weather code (its Material Symbols codepoint).
fn glyph(code: Option<i64>, day: bool) -> char {
    match code {
        Some(0) if day => '\u{f157}',                // clear_day
        Some(0) => '\u{f159}',                       // bedtime (a clear night)
        Some(1 | 2) if day => '\u{f172}',            // partly_cloudy_day
        Some(1 | 2) => '\u{f174}',                   // partly_cloudy_night
        Some(45 | 48) => '\u{e818}',                 // foggy
        Some(51..=67) | Some(80..=82) => '\u{f176}', // rainy
        Some(71..=77) | Some(85 | 86) => '\u{e2cd}', // weather_snowy
        Some(95..) => '\u{ebdb}',                    // thunderstorm
        _ => '\u{e2bd}',                             // cloud
    }
}

const NEAR_ME: char = '\u{e569}';

fn degrees(value: Option<f64>) -> String {
    value.map(|v| format!("{}°", v.round() as i64)).unwrap_or_else(|| "–".into())
}

/// "2026-11-21" as "Sat"; the first day is "Today".
fn weekday(date: &str, index: usize) -> String {
    if index == 0 {
        return "Today".into();
    }
    let parts: Vec<i64> = date.split('-').filter_map(|p| p.parse().ok()).collect();
    if parts.len() != 3 {
        return date.into();
    }
    // Sakamoto's method: 0 is Sunday.
    let (mut y, m, d) = (parts[0], parts[1].clamp(1, 12), parts[2]);
    let t = [0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4];
    if m < 3 {
        y -= 1;
    }
    let dow = (y + y / 4 - y / 100 + y / 400 + t[(m - 1) as usize] + d).rem_euclid(7);
    ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][dow as usize].into()
}

fn hour_of(time: &str) -> Option<u32> {
    time.get(11..13)?.parse().ok()
}

// The window ---------------------------------------------------------------------------------------------------------

struct App {
    cache: PathBuf,
    settings: PathBuf,
    forecast: Option<Forecast>,
    palette: Palette,
}

#[derive(Debug, Clone)]
enum Message {
    Reload,
    Refresh,
    Close,
}

fn xdg(var: &str, fallback: &str) -> PathBuf {
    std::env::var_os(var).filter(|v| !v.is_empty()).map(PathBuf::from).unwrap_or_else(|| {
        std::env::var_os("HOME").map(PathBuf::from).unwrap_or_else(|| PathBuf::from("/")).join(fallback)
    })
}

impl App {
    fn new() -> Self {
        let mut app = App {
            cache: xdg("XDG_CACHE_HOME", ".cache").join("halcyon/weather.json"),
            settings: xdg("XDG_STATE_HOME", ".local/state").join("halcyon/summit.json"),
            forecast: None,
            palette: Palette::default(),
        };
        app.reload();
        app
    }

    fn reload(&mut self) {
        self.palette = read_palette(&self.settings);
        self.forecast =
            std::fs::read_to_string(&self.cache).ok().and_then(|raw| serde_json::from_str::<Forecast>(&raw).ok());
    }

    fn update(&mut self, message: Message) -> Task<Message> {
        match message {
            Message::Reload => self.reload(),
            Message::Refresh => {
                let _ = std::process::Command::new("systemctl")
                    .args(["--user", "start", "--no-block", "halcyon-weather.service"])
                    .spawn();
            }
            Message::Close => return iced::exit(),
        }
        Task::none()
    }

    fn subscription(&self) -> Subscription<Message> {
        Subscription::batch([
            time::every(Duration::from_secs(30)).map(|_| Message::Reload),
            keyboard::listen().filter_map(|event| match event {
                keyboard::Event::KeyPressed { key, .. } => match key.as_ref() {
                    keyboard::Key::Named(keyboard::key::Named::Escape) | keyboard::Key::Character("q") => {
                        Some(Message::Close)
                    }
                    keyboard::Key::Character("r") => Some(Message::Refresh),
                    _ => None,
                },
                _ => None,
            }),
        ])
    }

    // Pieces ---------------------------------------------------------------------------------------------------------

    fn icon<'a>(&self, code: Option<i64>, day: bool, size: f32, colour: Color) -> Element<'a, Message> {
        text(glyph(code, day).to_string()).font(ICONS).size(size).color(colour).into()
    }

    fn section<'a>(&self, title: &str, content: impl Into<Element<'a, Message>>) -> Element<'a, Message> {
        let surface = self.palette.surface;
        let label = text(title.to_uppercase())
            .size(11)
            .font(Font { weight: Weight::Semibold, ..UI })
            .color(self.palette.muted);
        container(column![label, content.into()].spacing(14))
            .padding([16, 18])
            .width(Length::Fill)
            .style(move |_| container::Style {
                background: Some(surface.into()),
                border: Border { radius: 18.0.into(), ..Border::default() },
                ..container::Style::default()
            })
            .into()
    }

    fn view(&self) -> Element<'_, Message> {
        let p = self.palette;
        let body: Element<Message> = match &self.forecast {
            Some(f) => self.forecast_view(f),
            None => column![
                self.icon(Some(2), true, 44.0, p.muted),
                text("No forecast yet").size(17).color(p.text),
                text("Press R to fetch it").size(13).color(p.muted),
            ]
            .spacing(10)
            .align_x(Horizontal::Center)
            .width(Length::Fill)
            .into(),
        };
        let background = p.background;
        container(body)
            .padding([22, 20])
            .center_x(Length::Fill)
            .height(Length::Fill)
            .style(move |_| container::Style { background: Some(background.into()), ..container::Style::default() })
            .into()
    }

    fn forecast_view<'a>(&self, f: &'a Forecast) -> Element<'a, Message> {
        let p = self.palette;
        let day = f.current.is_day.unwrap_or(1) == 1;
        let today = f.daily.first();

        // Now: the place, one big number, what it is like.
        let mut place = Row::new().spacing(6).align_y(Vertical::Center).push(
            text(if f.place.name.is_empty() { "Here".to_string() } else { f.place.name.clone() })
                .size(15)
                .font(Font { weight: Weight::Medium, ..UI })
                .color(p.text),
        );
        if f.place.source == "wifi" {
            place = place.push(text(NEAR_ME.to_string()).font(ICONS).size(13).color(p.muted));
        }
        let now = column![
            place,
            row![
                text(degrees(f.current.temperature)).size(68).font(Font { weight: Weight::Light, ..UI }).color(p.text),
                self.icon(f.current.weather_code, day, 40.0, p.warm),
            ]
            .spacing(14)
            .align_y(Vertical::Center),
            text(words(f.current.weather_code)).size(15).color(p.text),
            text(format!(
                "H {}   L {}   ·   Feels {}",
                degrees(today.and_then(|d| d.max)),
                degrees(today.and_then(|d| d.min)),
                degrees(f.current.feels_like)
            ))
            .size(13)
            .color(p.muted),
        ]
        .spacing(2)
        .align_x(Horizontal::Center)
        .width(Length::Fill);

        // The next hours: six, two hours apart.
        let hours = f.hourly.iter().step_by(2).take(6).enumerate().fold(Row::new(), |r, (i, h)| {
            let hh = hour_of(&h.time).unwrap_or(12);
            r.push(
                column![
                    text(if i == 0 { "Now".to_string() } else { format!("{hh:02}") }).size(12).color(p.muted),
                    self.icon(h.weather_code, (7..19).contains(&hh), 22.0, p.text),
                    text(degrees(h.temperature)).size(14).color(p.text),
                ]
                .spacing(8)
                .align_x(Horizontal::Center)
                .width(Length::Fill),
            )
        });

        // The week: each day's low to high as a bar on the week's own scale.
        let low = f.daily.iter().filter_map(|d| d.min).fold(f64::INFINITY, f64::min);
        let high = f.daily.iter().filter_map(|d| d.max).fold(f64::NEG_INFINITY, f64::max);
        let span = (high - low).max(1.0);
        let days = f.daily.iter().take(7).enumerate().fold(Column::new().spacing(12), |c, (i, d)| {
            let (lo, hi) = (d.min.unwrap_or(low), d.max.unwrap_or(high));
            let before = (((lo - low) / span) * 100.0).round().clamp(0.0, 100.0) as u16;
            let width = (((hi - lo) / span) * 100.0).round().clamp(6.0, 100.0) as u16;
            let after = 100u16.saturating_sub(before + width);
            let (accent, track) = (p.accent, p.track);
            let fill = container(space::horizontal()).width(Length::FillPortion(width)).height(4).style(move |_| {
                container::Style {
                    background: Some(accent.into()),
                    border: Border { radius: 2.0.into(), ..Border::default() },
                    ..container::Style::default()
                }
            });
            let mut bar = Row::new();
            if before > 0 {
                bar = bar.push(space::horizontal().width(Length::FillPortion(before)));
            }
            bar = bar.push(fill);
            if after > 0 {
                bar = bar.push(space::horizontal().width(Length::FillPortion(after)));
            }
            let bar = container(bar).height(4).width(Length::Fill).style(move |_| container::Style {
                background: Some(track.into()),
                border: Border { radius: 2.0.into(), ..Border::default() },
                ..container::Style::default()
            });
            let rain = match d.rain {
                Some(r) if r >= 30.0 => format!("{}%", r.round() as i64),
                _ => String::new(),
            };
            c.push(
                row![
                    text(weekday(&d.date, i)).size(14).color(p.text).width(Length::Fixed(54.0)),
                    container(self.icon(d.weather_code, true, 20.0, p.text)).width(Length::Fixed(26.0)),
                    text(rain).size(11).color(p.accent).width(Length::Fixed(34.0)),
                    text(degrees(d.min)).size(14).color(p.muted).width(Length::Fixed(34.0)).align_x(Horizontal::Right),
                    container(bar).padding([0, 10]).width(Length::Fill),
                    text(degrees(d.max)).size(14).color(p.text).width(Length::Fixed(34.0)),
                ]
                .align_y(Vertical::Center),
            )
        });

        // Where it is from, quietly, at the bottom.
        let source = match f.place.source.as_str() {
            "wifi" => "Located by nearby Wi-Fi",
            "ip" => "Located by your IP address",
            "fixed" => "The place you set",
            _ => "",
        };
        let updated = f.updated.get(11..16).map(|t| format!("Updated {t} UTC")).unwrap_or_default();
        let note: Vec<&str> = [source, updated.as_str()].into_iter().filter(|s| !s.is_empty()).collect();
        let footer = text(note.join("   ·   ")).size(11).color(p.muted).width(Length::Fill).align_x(Horizontal::Center);

        column![
            now,
            self.section("Next hours", hours),
            self.section("This week", days),
            space::vertical(),
            footer,
        ]
        .spacing(14)
        .max_width(440)
        .into()
    }
}

fn main() -> iced::Result {
    iced::application(App::new, App::update, App::view)
        .font(ICON_FONT)
        .title("Weather")
        .subscription(App::subscription)
        .theme(|_: &App| Theme::Dark)
        .default_font(UI)
        .window(window::Settings {
            size: Size::new(400.0, 720.0),
            min_size: Some(Size::new(360.0, 680.0)),
            platform_specific: window::settings::PlatformSpecific {
                application_id: "halcyon-forecast".into(),
                ..Default::default()
            },
            ..window::Settings::default()
        })
        .run()
}
