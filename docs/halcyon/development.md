# Development

```sh
./scripts/validate.sh
```

CI runs the same script. It checks that:

- every Lua file parses, and every shell script parses;
- all JSON is valid;
- the Halcyon layer is wired in, and the submodule and wallpapers are present;
- every theme is complete, has readable contrast, and renders to valid Lua
  at every effects level;
- every setting in the rendered Lua exists in Hyprland 0.56.2 with a value
  of the right type, using the option table in `scripts/data/`, which was
  extracted from Hyprland's source;
- every shell setting a theme changes exists in the shell, with the right type;
- screen shaders compile as GLSL ES 3.00, and the banner compositor runs;
- the cursor theme's XCursor files, hyprcursor zips and aliases are well formed and cover the essential names;
- the voice assistant's tests pass (`tests/`): end-of-speech detection, action validation, every provider's request and reply format, the tool loop, and settings.
- no Halcyon keybind reuses a key combination upstream already binds.

That last check exists because Hyprland runs *every* action bound to a
key combination. A clash would not replace upstream's action; both would
fire at once.

Two kinds of release are on the repository's Releases page. GitHub Actions builds both.

- **Stable** (`.github/workflows/stable.yml`): a normal release, numbered by the `VERSION` file. It is published
  when a `v` tag matching `VERSION` is pushed. You can also run it by hand from the Actions tab, with the tag.
- **Nightly** (`.github/workflows/nightly.yml`): a prerelease built from `main` each night. It replaces the previous
  nightly. If `main` has not changed since the last one, the run stops without building.

Each archive is `halcyon-<version>.tar.gz` with a `.sha256` file next to it. Check a download with
`sha256sum -c halcyon-<version>.tar.gz.sha256`.

To make a stable release:

```sh
echo 1.0.1 > VERSION
git commit -am "Release 1.0.1"
git tag v1.0.1
git push origin main v1.0.1
```

`scripts/release.sh <label> <outdir>` builds the same archive on your machine, if you want to look at it first.
