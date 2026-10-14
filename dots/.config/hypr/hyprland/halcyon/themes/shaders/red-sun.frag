#version 300 es
// Halcyon: Red Sun screen shader.
//
// The red ring of the Red Sun theme is the revolver. Spin it and the screen
// behaves as if the glass inside the computer is failing:
//   * cracks run out from the ring, round it and away from it, and the
//     screen breaks into shards that sit at different depths;
//   * the shards sink towards the ring, tilt and shrink, and the gaps between
//     them open onto a deep red glow. Each edge is bevelled, lit from above
//     left, so the cracks read as thick glass rather than lines;
//   * the picture is pulled in towards the ring and darkens at the edges;
//   * then it comes back together and the cracks heal.
//
// The shader does nothing until the revolver arms it (`halcyon-theme collapse
// arm`), and then only for a few seconds after a press on the ring. The
// pointer's press list is how it knows when: Hyprland (0.56+) gives screen
// shaders the position and age of the last 32 presses, which only update with
// debug:damage_tracking off. halcyon-theme sets both together, at the "full"
// effects level only.
//
// halcyon-theme rewrites the #define lines below: the ring's place from the
// revolver, ARM_AGE when the spin starts, and STRENGTH from Settings > Halcyon
// (config.json: halcyon.glass.strength). Don't edit the installed copy.

precision highp float;

#define FLIP_POINTER_Y 0
#define COLLAPSE_ARMED 0
#define ARM_AGE 0.000
#define RING_X 0.4907
#define RING_Y 0.4312
#define RING_R 0.0656
#define STRENGTH 0.5

in vec2 v_texcoord;
uniform sampler2D tex;

uniform vec2 screen_size;
uniform float time;                          // seconds
uniform vec2 pointer_pressed_positions[32];  // 0..1, top-left origin, most recent first
uniform float pointer_pressed_times[32];     // seconds since each press; negative when unused

layout(location = 0) out vec4 fragColor;

const float TAU = 6.28318531;
const float DURATION = 6.2;       // s, the whole episode, counted from the press
const float ANGULAR_CELLS = 15.0; // shards round the ring
const float JITTER = 0.85;        // how irregular the shards are
const vec2 LIGHT = vec2(-0.62, -0.78);    // towards the light, screen y down
const vec3 EMBER = vec3(1.0, 0.16, 0.10); // the glow inside the cracks
const vec3 HOT = vec3(1.0, 0.82, 0.70);   // its hottest line

float hash21(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
}

vec2 hash22(vec2 p) {
    return vec2(hash21(p), hash21(p + vec2(19.19, 7.77)));
}

float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash21(i), hash21(i + vec2(1.0, 0.0)), u.x),
               mix(hash21(i + vec2(0.0, 1.0)), hash21(i + vec2(1.0, 1.0)), u.x), u.y);
}

vec2 rotate(vec2 v, float a) {
    float c = cos(a), s = sin(a);
    return vec2(c * v.x - s * v.y, s * v.x + c * v.y);
}

// A cell's feature point in log-polar space. The angular index wraps, so the
// shards meet up all the way round the ring.
vec2 featurePoint(vec2 cell) {
    vec2 id = vec2(cell.x, mod(cell.y, ANGULAR_CELLS));
    return cell + 0.5 + (hash22(id) - 0.5) * JITTER;
}

vec2 cellHash(vec2 cell) {
    return hash22(vec2(cell.x, mod(cell.y, ANGULAR_CELLS)) + 41.0);
}

// Mirrored at the screen edges, so a shard that moves never drags a smeared edge in.
vec3 sampleScreen(vec2 hu, vec2 ringUV, float aspect) {
    vec2 uv = ringUV + hu / vec2(aspect, 1.0);
    uv = 1.0 - abs(1.0 - mod(uv, 2.0));
    return texture(tex, uv).rgb;
}

void main() {
    vec2 size = max(screen_size, vec2(1.0));
    float aspect = size.x / size.y;
    vec2 ringUV = vec2(RING_X, RING_Y);

    // Find the latest press that landed on the ring.
    float age = -1.0;
#if COLLAPSE_ARMED
    for (int i = 0; i < 32; i++) {
        float t = pointer_pressed_times[i];
        if (t < 0.0 || t > DURATION + ARM_AGE)
            continue;
        vec2 pp = pointer_pressed_positions[i];
#if FLIP_POINTER_Y
        pp.y = 1.0 - pp.y;
#endif
        if (length((pp - ringUV) * vec2(aspect, 1.0)) < RING_R * 1.35) {
            age = t - ARM_AGE;
            break;
        }
    }
#endif

    if (age < 0.0 || age > DURATION) {
        fragColor = texture(tex, v_texcoord);
        return;
    }

    float strength = 0.4 + 1.2 * clamp(STRENGTH, 0.0, 1.0);

    // Timeline. The cracks run out first, the glass gives way a moment later,
    // holds, and then comes back together.
    float front = RING_R * 1.1 + 2.6 * (1.0 - exp(-age * 3.4));
    float collapse = smoothstep(0.15, 2.1, age) * (1.0 - smoothstep(3.3, 5.7, age));
    float fade = 1.0 - smoothstep(4.9, 6.1, age);
    float bump = exp(-pow((age - 0.45) / 0.35, 2.0));

    vec2 p = (v_texcoord - ringUV) * vec2(aspect, 1.0);   // height units from the ring
    // A short shudder as the glass gives way.
    p += vec2(sin(time * 53.0), cos(time * 67.0)) * 0.0016 * bump * strength;
    float r = max(length(p), 1e-4);
    float theta = atan(p.y, p.x);
    float K = ANGULAR_CELLS / TAU;                         // log-polar units per radian
    float rBase = RING_R * 1.1;

    // Near the screen's edges things move less, so nothing from beyond the edge is pulled into view.
    float edgeRoom = min(min(v_texcoord.x, 1.0 - v_texcoord.x), min(v_texcoord.y, 1.0 - v_texcoord.y));
    float freedom = smoothstep(0.0, 0.14, edgeRoom);

    // The picture is pulled in towards the ring, most near it.
    float pinch = collapse * strength * 0.22 * exp(-r / 0.5) * freedom;
    vec2 pulled = p * (1.0 + pinch);

    // Shards: Voronoi cells in log-polar space, so they are small near the
    // ring and larger away from it, and the cracks run round it and out from
    // it. The coordinates are warped so the lines are not ruler-straight.
    vec2 q = vec2(log(max(r, rBase * 0.92) / rBase) * K, theta * K);
    // The warp comes from the screen position, not the angle, so there is no seam where the angle wraps.
    q += (vec2(noise(p * 5.0 + 3.1), noise(p * 5.0 + 17.7)) - 0.5) * 0.22;

    vec2 g = floor(q);
    float best = 1e9;
    vec2 bestCell = g;
    vec2 bestPoint = q;
    for (int j = -1; j <= 1; j++) {
        for (int i = -1; i <= 1; i++) {
            vec2 cell = g + vec2(float(i), float(j));
            vec2 pt = featurePoint(cell);
            float d = dot(q - pt, q - pt);
            if (d < best) {
                best = d;
                bestCell = cell;
                bestPoint = pt;
            }
        }
    }

    // Distance to the nearest shard edge, and which way that edge faces.
    float edgeQ = 1e9;
    vec2 edgeDir = vec2(1.0, 0.0);
    for (int j = -2; j <= 2; j++) {
        for (int i = -2; i <= 2; i++) {
            vec2 cell = bestCell + vec2(float(i), float(j));
            if (cell == bestCell)
                continue;
            vec2 pt = featurePoint(cell);
            vec2 across = pt - bestPoint;
            float len = length(across);
            if (len < 1e-4)
                continue;
            float dEdge = dot(0.5 * (bestPoint + pt) - q, across / len);
            if (dEdge < edgeQ) {
                edgeQ = dEdge;
                edgeDir = across / len;
            }
        }
    }

    // Per-shard character: depth, tilt, spin, and when it gives way.
    vec2 h = cellHash(bestCell);
    float depth = h.x;
    float rC = rBase * exp(bestPoint.x / K);
    float thetaC = bestPoint.y / K;
    vec2 radialC = vec2(cos(thetaC), sin(thetaC));
    vec2 centre = radialC * rC;
    float cracked = 1.0 - smoothstep(front - 0.08, front, rC);   // has the crack reached this shard?
    float own = clamp(collapse * 1.3 - 0.3 * h.y, 0.0, 1.0) * cracked * strength * freedom;
    // Shards near the ring fall furthest, so the screen caves in towards it like a funnel.
    float funnel = exp(-(rC - RING_R) / 0.35);

    // Where the shard has moved to: inwards, smaller, turned a little.
    float sink = min(rC * 0.5, 0.06 + 0.08 * funnel) * (0.35 + 0.65 * depth);
    vec2 move = -radialC * sink * own;
    float shrink = 1.0 - (0.06 + 0.16 * funnel) * own * (0.4 + 0.6 * depth);
    float turn = (h.y - 0.5) * 0.35 * own;
    vec2 tilt = (h - 0.5) * 0.02 * depth * own;
    vec2 source = centre + rotate(pulled - centre - move, -turn) / shrink + tilt;

    // Colour fringing, stronger on deeper shards.
    vec2 split = radialC * (0.0012 + 0.003 * depth) * own;
    vec3 colour = vec3(
        sampleScreen(source + split, ringUV, aspect).r,
        sampleScreen(source, ringUV, aspect).g,
        sampleScreen(source - split, ringUV, aspect).b
    );

    // Each face catches the light a little differently.
    float facet = dot(normalize(h - 0.5 + 1e-4), LIGHT) * own * (0.4 + 0.6 * depth);
    colour *= 1.0 + facet * 0.16 + (h.x - 0.5) * 0.08 * own;
    // Further down is darker: the shards that fell in are in the ring's shadow.
    colour *= 1.0 - 0.55 * own * (0.35 + 0.65 * depth) * funnel;

    // The edge, in pixels, and a physical direction for its bevel.
    float perQ = r * TAU / ANGULAR_CELLS;
    float edgePx = max(edgeQ, 0.0) * perQ * size.y;
    vec2 radial = vec2(cos(theta), sin(theta));
    vec2 tangent = vec2(-radial.y, radial.x);
    vec2 edgeFacing = normalize(radial * edgeDir.x + tangent * edgeDir.y);   // from this shard, across the edge

    // The gap opens as the glass gives way. Before then it is a hairline.
    float live = (1.0 - smoothstep(front - 0.06, front, r)) * fade * smoothstep(RING_R * 0.82, RING_R * 1.0, r);
    float gap = (0.9 + 7.5 * collapse * strength) * live;
    float halfGap = gap * 0.5;
    float aa = 0.9;

    // The shard's own edge: a bevel that is lit on the side facing the light,
    // dark on the other, with a thin bright line where the glass is cut.
    float bevelWidth = 2.5 + 5.0 * depth;
    float t = clamp((edgePx - halfGap) / bevelWidth, 0.0, 1.0);
    float lit = dot(edgeFacing, LIGHT);
    float bevel = (1.0 - t) * (1.0 - t) * (1.0 - smoothstep(0.0, 1.0, t) * 0.0);
    colour += HOT * max(lit, 0.0) * bevel * 0.55 * live * (0.5 + 0.5 * strength);
    colour *= 1.0 - max(-lit, 0.0) * bevel * 0.5 * live;
    colour += vec3(1.0) * (1.0 - smoothstep(halfGap, halfGap + 1.3, edgePx)) * max(lit, 0.0) * 0.5 * live;
    // A shadow where the shard sits above the one below it.
    colour *= 1.0 - 0.38 * exp(-(edgePx - halfGap) / (6.0 + 6.0 * depth)) * live * own;

    // Inside the gap: the dark inside of the machine, lit red from below.
    float inGap = 1.0 - smoothstep(halfGap - aa, halfGap + aa, edgePx);
    float core = exp(-edgePx * edgePx / (gap * 0.08 + 0.35));
    float heat = (0.3 + 0.7 * exp(-r * 1.7)) * (0.35 + 0.65 * collapse) * strength;
    vec3 abyss = mix(vec3(0.02, 0.0, 0.012), EMBER * (0.45 + 1.5 * heat), 0.12 + 0.88 * core);
    abyss = mix(abyss, HOT, core * core * 0.55 * heat);
    colour = mix(colour, abyss, inGap * live);

    // Inside the ring the glass is gone: a dark core with the ring's light pouring in from its rim.
    float core01 = 1.0 - smoothstep(RING_R * 0.78, RING_R * 0.95, r);
    float coreDepth = smoothstep(0.0, RING_R * 0.95, r);
    vec3 voidColour = mix(vec3(0.01, 0.0, 0.005), EMBER * 0.9, pow(coreDepth, 3.0));
    voidColour += HOT * pow(coreDepth, 10.0) * 0.6;
    colour = mix(colour, voidColour, core01 * collapse * strength * 0.92);

    // The whole screen darkens towards its edges, and the middle burns.
    float vignette = collapse * strength * 0.5 * smoothstep(0.25, 1.35, r);
    colour *= 1.0 - vignette;
    colour += EMBER * collapse * strength * 0.2 * exp(-r * r / 0.02) * fade;

    fragColor = vec4(clamp(colour, 0.0, 1.0), 1.0);
}
