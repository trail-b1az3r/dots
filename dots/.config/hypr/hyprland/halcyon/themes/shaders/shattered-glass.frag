#version 300 es
// Halcyon: Shattered Glass screen shader.
//
// Treats the screen as a pane of liquid glass:
//   * a glass lens follows the pointer. Its middle stays clear and flat;
//     light bends in its rounded rim, which catches a soft highlight on top
//     and a faint shadow below, like a drop of water on a window. It fades
//     away when the pointer rests;
//   * a click sends a gentle ripple through the glass, with faint cracks
//     around the click that heal as it passes;
//   * optionally, the screen edges split colour slightly, like thick glass.
//
// Uses Hyprland's pointer uniforms (0.56+), which only update with
// debug:damage_tracking off; halcyon-theme sets both together, at the
// "full" effects level only.
//
// halcyon-theme rewrites the #define lines below from Settings > Halcyon
// (config.json: halcyon.glass.*). Don't edit the installed copy.

precision highp float;

#define FLIP_POINTER_Y 0
#define LENS_ENABLED 1
#define RIPPLES_ENABLED 1
#define EDGE_ENABLED 0
#define STRENGTH 0.5
#define LENS_RADIUS 90.0
#define BOUNCE 0.6

in vec2 v_texcoord;
uniform sampler2D tex;

uniform vec2 screen_size;
uniform float time;                 // seconds, for the quiver
uniform vec2 pointer_position;               // 0..1, top-left origin
uniform vec2 pointer_pressed_positions[32];  // most recent first
uniform float pointer_pressed_times[32];     // seconds since each press
uniform float pointer_last_active;           // seconds since the pointer moved
uniform int pointer_hidden;

layout(location = 0) out vec4 fragColor;

const float PI = 3.14159265;
const float TAU = 6.28318531;

// Everything below is at STRENGTH 1; STRENGTH scales it down.
const float LENS_RIM = 0.34;          // rim width, as a fraction of the radius
const float LENS_BEND = 14.0;         // px of refraction in the rim
const float LENS_MAGNIFY = 0.05;      // gentle magnification in the middle
const float LENS_ABERRATION = 1.2;    // px of colour split in the rim
const float LENS_IDLE_START = 1.0;    // s before the lens starts to fade
const float LENS_IDLE_END = 2.2;      // s when it is gone

const float RIPPLE_DURATION = 0.75;   // s
const float RIPPLE_SPEED = 900.0;     // px/s
const float RIPPLE_WIDTH = 60.0;      // px
const float RIPPLE_PUSH = 7.0;        // px of refraction in the wave
const float CRACK_REACH = 170.0;      // px
const float CRACK_SECTORS = 9.0;
const float CRACK_RING_BASE = 26.0;   // px

const float EDGE_ABERRATION = 0.8;    // px at the corners

const vec3 GLASS_TINT = vec3(0.62, 0.85, 1.0);

float hash(float n) {
    return fract(sin(n) * 43758.5453123);
}

vec2 toPixels(vec2 normalised, vec2 size) {
#if FLIP_POINTER_Y
    normalised.y = 1.0 - normalised.y;
#endif
    return normalised * size;
}

// Jelly bounce. Screen shaders get no pointer velocity, only the time since
// it last moved (t), so the bounce keys off that: while the pointer moves
// (t near 0) the lens is pressed a little flatter and quivers; when it
// stops, it springs back past its rest shape, trading width for height a
// couple of times, and settles in about half a second.
vec2 bounceScale(float t, float amount) {
    float spring = exp(-6.5 * t) * cos(17.0 * t);
    float moving = 1.0 - smoothstep(0.0, 0.12, t);
    float quiver = sin(time * 21.0) * moving;
    float size = -0.09 * spring;
    float squash = 0.08 * spring + 0.03 * quiver;
    return vec2(1.0 + (size + squash) * amount, 1.0 + (size - squash) * amount);
}

void main() {
    vec2 size = max(screen_size, vec2(1.0));
    vec2 px = v_texcoord * size;
    float strength = clamp(STRENGTH, 0.0, 1.0);

    vec2 offset = vec2(0.0);     // where to sample from, relative to here (px)
    vec2 splitDir = vec2(0.0);   // direction of colour split
    float split = 0.0;           // amount of colour split (px)
    float light = 0.0;           // added (or, negative, removed) light
    float tint = 0.0;            // added glass tint

#if EDGE_ENABLED
    vec2 fromCentre = v_texcoord - 0.5;
    float edge = pow(clamp(length(fromCentre) * 1.4142, 0.0, 1.0), 3.0);
    split += edge * EDGE_ABERRATION * strength;
    splitDir += fromCentre;
#endif

#if LENS_ENABLED
    float awake = (1.0 - smoothstep(LENS_IDLE_START, LENS_IDLE_END, pointer_last_active)) * strength;
    if (pointer_hidden == 0 && awake > 0.0) {
        vec2 d = px - toPixels(pointer_position, size);
        float r = length(d / (LENS_RADIUS * bounceScale(pointer_last_active, clamp(BOUNCE, 0.0, 1.0))));
        if (r < 1.0) {
            vec2 dir = d / max(length(d), 1e-3);
            // 0 in the flat middle, rising to 1 at the outer edge of the rim.
            float rimT = smoothstep(1.0 - LENS_RIM, 1.0, r);
            // Light bends inwards across the rim, most in its middle, as it
            // would through the rounded edge of a drop; none at the very edge,
            // so the lens meets the screen without a seam.
            float bend = sin(rimT * PI);
            offset -= dir * bend * LENS_BEND * awake;
            offset -= d * LENS_MAGNIFY * (1.0 - rimT) * awake;
            split += bend * LENS_ABERRATION * awake;
            splitDir += dir * bend;
            // Lit from above: highlight along the top of the rim, a faint
            // shadow along the bottom, and a whisper of frost inside.
            float facing = dot(dir, vec2(0.0, -1.0));
            float rimLine = smoothstep(0.55, 0.9, rimT) * (1.0 - smoothstep(0.9, 1.0, rimT));
            light += rimLine * max(facing, 0.0) * 0.14 * awake;
            light -= rimLine * max(-facing, 0.0) * 0.06 * awake;
            tint += (0.025 + rimLine * 0.04) * awake;
        }
    }
#endif

#if RIPPLES_ENABLED
    for (int i = 0; i < 32; i++) {
        float t = pointer_pressed_times[i];
        if (t < 0.0 || t > RIPPLE_DURATION)
            continue;

        vec2 d = px - toPixels(pointer_pressed_positions[i], size);
        float dist = length(d);
        float life = (1.0 - t / RIPPLE_DURATION) * strength;
        vec2 dir = d / max(dist, 1e-3);

        // A soft refraction wave running outwards.
        float band = (dist - t * RIPPLE_SPEED) / RIPPLE_WIDTH;
        if (abs(band) < 2.0) {
            float wave = sin(band * PI) * exp(-band * band * 1.6);
            offset += dir * wave * RIPPLE_PUSH * life;
            split += abs(wave) * 0.8 * life;
            splitDir += dir * abs(wave);
        }

        // Faint cracks around the click, healing as the wave passes.
        float reach = CRACK_REACH * (1.0 - exp(-t * 10.0));
        if (dist < reach && dist > 1.0) {
            float seed = hash(float(i) * 7.13 + pointer_pressed_positions[i].x * 101.0);
            float angle = atan(d.y, d.x) + PI;
            float warped = angle + 0.35 * sin(angle * 2.0 + seed * TAU) + 0.18 * sin(angle * 5.0 + seed * 17.0);
            float sectorBase = warped / TAU * CRACK_SECTORS + seed * 5.0;
            float ringF = log2(dist / CRACK_RING_BASE + 1.0) * 1.6
                        + (hash(floor(sectorBase) + seed * 13.0) - 0.5) * 0.7;
            float sectorF = sectorBase + (hash(floor(ringF) * 3.7 + seed * 29.0) - 0.5) * 0.45;

            float fall = 1.0 - smoothstep(0.5, 1.0, dist / CRACK_REACH);
            float heal = life * life * fall;
            float sf = fract(sectorF);
            float rf = fract(ringF);
            float toRadial = min(sf, 1.0 - sf) * TAU / CRACK_SECTORS * dist;
            float toRing = min(rf, 1.0 - rf) * (dist + CRACK_RING_BASE) * 0.4332; // ln2 / 1.6
            float crack = 1.0 - smoothstep(0.3, 1.2, min(toRadial, toRing));
            light += crack * 0.22 * heal;
            tint += crack * 0.18 * heal;
        }
    }
#endif

    vec4 base;
    vec3 colour;
    if (offset == vec2(0.0) && split < 0.05 && light == 0.0 && tint == 0.0) {
        // Nothing happening here: one plain sample.
        base = texture(tex, v_texcoord);
        colour = base.rgb;
    } else {
        vec2 uv = clamp((px + offset) / size, 0.0, 1.0);
        float dirLength = length(splitDir);
        vec2 splitUV = (dirLength > 1e-4 ? splitDir / dirLength : vec2(1.0, 0.0)) * split / size;
        base = texture(tex, uv);
        colour = vec3(
            texture(tex, clamp(uv + splitUV, 0.0, 1.0)).r,
            base.g,
            texture(tex, clamp(uv - splitUV, 0.0, 1.0)).b
        );
        // Tint mixes towards the glass colour rather than adding light, so
        // it never glares on bright content.
        colour = mix(colour, GLASS_TINT, clamp(tint, 0.0, 0.3)) + vec3(light);
    }

    fragColor = vec4(clamp(colour, 0.0, 1.0), base.a);
}
