#version 300 es
// Halcyon: Shattered Glass screen shader.
//
// Makes the whole screen behave like a pane of liquid glass:
//   * a refracting glass lens follows the pointer, with chromatic fringes
//     and a highlight on its rim; it fades away when the pointer rests;
//   * every click cracks the glass: a refraction wave runs outwards, and
//     the pane behind it splits into shards along glinting cracks that
//     then heal;
//   * the edges of the screen split colour very slightly, as thick glass
//     does.
//
// Uses Hyprland's pointer uniforms (0.56+), which only update with
// debug:damage_tracking off. halcyon-theme sets both together; the
// "effects" level controls this: `halcyon-theme effects light` drops the
// shader and restores damage tracking.

precision highp float;

// halcyon-theme sets this to 1 if pointer effects appear mirrored.
#define FLIP_POINTER_Y 0

in vec2 v_texcoord;
uniform sampler2D tex;

uniform vec2 screen_size;
uniform vec2 pointer_position;               // 0..1, top-left origin
uniform vec2 pointer_pressed_positions[32];  // most recent first
uniform float pointer_pressed_times[32];     // seconds since each press
uniform float pointer_last_active;           // seconds since the pointer moved
uniform int pointer_hidden;

layout(location = 0) out vec4 fragColor;

const float PI = 3.14159265;
const float TAU = 6.28318531;

// Pointer lens
const float LENS_RADIUS = 110.0;      // px
const float LENS_MAGNIFY = 0.22;      // pull towards the centre, at the centre
const float LENS_ABERRATION = 2.4;    // px of colour split at the rim
const float LENS_IDLE_START = 1.2;    // s before the lens starts to fade
const float LENS_IDLE_END = 2.6;      // s when it is gone

// Click crack
const float CRACK_DURATION = 1.1;     // s
const float CRACK_SPEED = 1100.0;     // px/s of the wave front
const float CRACK_WAVE_WIDTH = 55.0;  // px
const float CRACK_WAVE_PUSH = 12.0;   // px of refraction in the wave
const float CRACK_REACH = 280.0;      // px, how far the cracks spread
const float CRACK_SECTORS = 9.0;      // radial cracks
const float CRACK_RING_BASE = 26.0;   // px, first concentric crack
const float CRACK_SHARD_SHIFT = 6.0;  // px each shard is knocked out of place

// Screen edges
const float EDGE_ABERRATION = 1.1;    // px at the corners

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

void main() {
    vec2 size = max(screen_size, vec2(1.0));
    vec2 px = v_texcoord * size;

    vec2 offset = vec2(0.0);     // where to sample from, relative to here (px)
    vec2 splitDir = vec2(0.0);   // direction of colour split
    float split = 0.0;           // amount of colour split (px)
    float glint = 0.0;           // added white light
    float tint = 0.0;            // added glass tint

    // Edge aberration, radial from the centre of the screen.
    vec2 fromCentre = v_texcoord - 0.5;
    float edge = pow(clamp(length(fromCentre) * 1.4142, 0.0, 1.0), 3.0);
    split += edge * EDGE_ABERRATION;
    splitDir += fromCentre;

    // Pointer lens.
    float awake = 1.0 - smoothstep(LENS_IDLE_START, LENS_IDLE_END, pointer_last_active);
    if (pointer_hidden == 0 && awake > 0.0) {
        vec2 d = px - toPixels(pointer_position, size);
        float r = length(d) / LENS_RADIUS;
        if (r < 1.0) {
            vec2 dir = d / max(length(d), 1e-3);
            // A dome: strongest in the middle and rolling to nothing at the
            // rim, so the lens meets the screen without a seam.
            float dome = sqrt(1.0 - r * r);
            offset -= d * LENS_MAGNIFY * dome * awake;
            // Real droplets bend hardest near their edge.
            float rim = smoothstep(0.62, 0.97, r) * (1.0 - smoothstep(0.97, 1.0, r));
            split += LENS_ABERRATION * rim * awake;
            splitDir += dir * rim * 4.0;
            float light = max(dot(dir, normalize(vec2(-0.55, -0.83))), 0.0);
            glint += pow(light, 5.0) * rim * 0.32 * awake;
            tint += rim * 0.06 * awake;
        }
    }

    // Click cracks.
    for (int i = 0; i < 32; i++) {
        float t = pointer_pressed_times[i];
        if (t < 0.0 || t > CRACK_DURATION)
            continue;

        vec2 d = px - toPixels(pointer_pressed_positions[i], size);
        float dist = length(d);
        float front = t * CRACK_SPEED;
        float life = 1.0 - t / CRACK_DURATION;
        vec2 dir = d / max(dist, 1e-3);

        // The refraction wave at the front.
        float band = (dist - front) / CRACK_WAVE_WIDTH;
        if (abs(band) < 2.0) {
            float wave = sin(band * PI) * exp(-band * band * 1.6);
            offset += dir * wave * CRACK_WAVE_PUSH * life;
            split += abs(wave) * 2.5 * life;
            splitDir += dir * abs(wave);
        }

        // Around the impact, the pane is in shards. The cracks race out to
        // their full reach in a fraction of a second, then heal.
        float reach = CRACK_REACH * (1.0 - exp(-t * 9.0));
        if (dist < reach && dist > 1.0) {
            float seed = hash(float(i) * 7.13 + pointer_pressed_positions[i].x * 101.0);
            float angle = atan(d.y, d.x) + PI;
            // Uneven radial cracks: warp the angle so sectors differ in size.
            float warped = angle + 0.35 * sin(angle * 2.0 + seed * TAU) + 0.18 * sin(angle * 5.0 + seed * 17.0);
            float sectorBase = warped / TAU * CRACK_SECTORS + seed * 5.0;
            // Rings grow geometrically, and each sector puts its crack at a
            // slightly different radius, so they come out as broken polygons.
            float ringF = log2(dist / CRACK_RING_BASE + 1.0) * 1.6
                        + (hash(floor(sectorBase) + seed * 13.0) - 0.5) * 0.7;
            // Radial cracks kink where they cross a ring.
            float sectorF = sectorBase + (hash(floor(ringF) * 3.7 + seed * 29.0) - 0.5) * 0.45;
            float shard = floor(sectorF) * 31.0 + floor(ringF) * 7.0 + seed * 977.0;

            float fall = 1.0 - smoothstep(0.55, 1.0, dist / CRACK_REACH);
            float heal = life * life * fall;
            vec2 knock = vec2(hash(shard), hash(shard + 1.7)) - 0.5;
            offset += knock * CRACK_SHARD_SHIFT * heal;
            glint += (hash(shard + 3.3) - 0.5) * 0.10 * heal;

            // Distance to the nearest crack, in pixels.
            float sf = fract(sectorF);
            float rf = fract(ringF);
            float toRadial = min(sf, 1.0 - sf) * TAU / CRACK_SECTORS * dist;
            float toRing = min(rf, 1.0 - rf) * (dist + CRACK_RING_BASE) * 0.4332; // ln2 / 1.6
            float crack = 1.0 - smoothstep(0.35, 1.4, min(toRadial, toRing));
            glint += crack * 0.6 * heal;
            tint += crack * 0.4 * heal;
            // A bright bruise at the point of impact.
            glint += exp(-dist / 14.0) * 0.8 * life;
        }
    }

    vec4 base;
    vec3 colour;
    if (offset == vec2(0.0) && split < 0.05 && glint == 0.0 && tint == 0.0) {
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
        colour += GLASS_TINT * tint + vec3(glint);
    }

    fragColor = vec4(clamp(colour, 0.0, 1.0), base.a);
}
