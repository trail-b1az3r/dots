#version 300 es
// Halcyon: Fractured Glass screen shader. Refraction only.
//
// A lens of liquid glass follows the pointer, shaped and lit the way
// Apple's Liquid Glass controls are:
//   * a squircle, not a circle;
//   * the middle is nearly untouched, just very slightly magnified;
//   * a rounded bezel around it bends light more and more towards the
//     edge, so the content behind wraps around the rim;
//   * the rim catches light: bright where it faces the top-left, a dimmer
//     reflection opposite, with a little colour dispersion in the bezel;
//   * the glass lifts saturation slightly, and sits on a soft shadow.
// It fades when the pointer rests. Nothing reacts to clicks.
//
// Uses Hyprland's pointer uniforms (0.56+), which only update with
// debug:damage_tracking off; halcyon-theme sets both together, at the
// "full" effects level only. The #define lines are set from
// Settings > Halcyon > Glass; don't edit the installed copy.

precision highp float;

#define FLIP_POINTER_Y 0
#define LENS_ENABLED 1
#define STRENGTH 0.5
#define LENS_RADIUS 90.0

in vec2 v_texcoord;
uniform sampler2D tex;

uniform vec2 screen_size;
uniform vec2 pointer_position;      // 0..1, top-left origin
uniform float pointer_last_active;  // seconds since the pointer moved
uniform int pointer_hidden;

layout(location = 0) out vec4 fragColor;

// At STRENGTH 1; STRENGTH scales the optical effects, not the shape.
const float SQUIRCLE = 4.0;        // superellipse exponent (2 = circle)
const float BEZEL = 0.32;          // bezel width, as a fraction of the radius
const float BEND = 30.0;           // px of refraction at the outer rim
const float MAGNIFY = 0.07;        // in the flat middle
const float DISPERSION = 0.9;      // px of colour split in the bezel
const float SATURATE = 0.18;       // saturation lift inside the glass
const float RIM_LIGHT = 0.28;
const float SHADOW = 0.10;         // darkening just outside the rim
const float SHADOW_WIDTH = 0.22;   // as a fraction of the radius
const float IDLE_START = 1.2;      // s before the lens starts to fade
const float IDLE_END = 2.6;

void main() {
    vec2 size = max(screen_size, vec2(1.0));
    vec2 px = v_texcoord * size;
    vec4 base = texture(tex, v_texcoord);

#if LENS_ENABLED
    float awake = 1.0 - smoothstep(IDLE_START, IDLE_END, pointer_last_active);
    float strength = clamp(STRENGTH, 0.0, 1.0);
    if (pointer_hidden == 0 && awake > 0.0) {
        vec2 pointer = pointer_position;
#if FLIP_POINTER_Y
        pointer.y = 1.0 - pointer.y;
#endif
        vec2 q = (px - pointer * size) / LENS_RADIUS;  // lens space, rim at r = 1
        vec2 aq = abs(q);
        float r = pow(pow(aq.x, SQUIRCLE) + pow(aq.y, SQUIRCLE), 1.0 / SQUIRCLE);

        if (r < 1.0 + SHADOW_WIDTH) {
            // Outward normal of the squircle at this point.
            vec2 grad = sign(q) * pow(aq + 1e-5, vec2(SQUIRCLE - 1.0));
            vec2 normal = normalize(grad + 1e-6);

            if (r < 1.0) {
                float k = awake * strength;
                // 0 across the flat middle, 1 at the rim.
                float t = smoothstep(1.0 - BEZEL, 1.0, r);
                // A rounded bezel: refraction grows steeply towards the edge,
                // so what is just outside the lens wraps into it.
                float bend = t * t * (3.0 - 2.0 * t) * t;
                vec2 offset = -normal * bend * BEND * k - (px - pointer * size) * MAGNIFY * (1.0 - t) * k;
                vec2 uv = clamp((px + offset) / size, 0.0, 1.0);
                // Dispersion lives in the inner part of the bezel only. Further
                // out the bezel squeezes many pixels onto one, and even a
                // sub-pixel colour split there becomes a wide rainbow band.
                float spread = smoothstep(0.0, 0.35, t) * (1.0 - smoothstep(0.4, 0.7, t));
                vec2 split = normal * spread * DISPERSION * k / size;

                vec3 colour = vec3(
                    texture(tex, clamp(uv - split, 0.0, 1.0)).r,
                    texture(tex, uv).g,
                    texture(tex, clamp(uv + split, 0.0, 1.0)).b
                );
                float grey = dot(colour, vec3(0.299, 0.587, 0.114));
                colour = mix(vec3(grey), colour, 1.0 + SATURATE * k);

                // Rim light: a thin line just inside the edge, brightest
                // facing the light (top-left), a softer reflection opposite.
                float rim = smoothstep(0.86, 0.97, r) * (1.0 - smoothstep(0.985, 1.0, r));
                float facing = dot(normal, normalize(vec2(-0.6, -0.8)));
                float lit = max(facing, 0.0) + 0.35 * max(-facing, 0.0);
                colour += rim * lit * RIM_LIGHT * awake * (0.4 + 0.6 * strength);
                // A faint inner glow on the lit side of the bezel.
                colour += t * max(facing, 0.0) * 0.04 * k;

                base = vec4(colour, base.a);
            } else {
                // Soft contact shadow just outside the glass.
                float s = 1.0 - (r - 1.0) / SHADOW_WIDTH;
                base.rgb *= 1.0 - SHADOW * s * s * awake * (0.4 + 0.6 * strength);
            }
        }
    }
#endif

    fragColor = vec4(clamp(base.rgb, 0.0, 1.0), base.a);
}
