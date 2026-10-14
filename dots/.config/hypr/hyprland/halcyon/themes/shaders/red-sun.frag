#version 300 es
// Halcyon: Red Sun screen shader.
//
// The red ring of the Red Sun theme is the revolver. Spin it and, over about ten seconds:
//
//   0 s     the sun spins: the ring turns (its gaps go round with it), smeared by its own speed, and embers fly
//           off it. Cracks run out from it and the screen breaks into shards that sink towards it, bevelled and
//           lit like thick glass, with a deep red glow in the gaps and light raying out through them.
//   2 s     inside the ring, where the glass is gone, an eye opens. It looks round, blinks, and then fixes on the
//           car on the road; its pupil narrows to a slit and a red ring closes on the car.
//   6.1 s   the picture turns to videotape: scanlines, colour bleeding sideways, tracking noise, jitter, and a
//           VCR's "PLAY" with a running counter.
//   6.9 s   "REW": everything runs backwards at speed through the tape's rewind noise. The eye closes, the shards
//           fly back together and the ring turns back.
//   ~10 s   "PLAY" again, the tape look fades, and the desktop is as it was.
//
// The shader does nothing until the revolver arms it (`halcyon-theme collapse arm`), and then only for the
// episode after a press on the ring. The pointer's press list is how it knows when: Hyprland (0.56+) gives screen
// shaders the position and age of the last 32 presses, which only update with debug:damage_tracking off.
// halcyon-theme sets both together, at the "full" effects level only.
//
// halcyon-theme rewrites the #define lines below: the ring's and the car's places from the revolver, ARM_AGE
// when the spin starts, and STRENGTH from Settings > Halcyon (config.json: halcyon.glass.strength). Don't edit
// the installed copy.

precision highp float;

#define FLIP_POINTER_Y 0
#define COLLAPSE_ARMED 0
#define ARM_AGE 0.000
#define RING_X 0.4907
#define RING_Y 0.4312
#define RING_R 0.0656
#define CAR_X 0.6485
#define CAR_Y 0.7084
#define STRENGTH 0.5

in vec2 v_texcoord;
uniform sampler2D tex;

uniform vec2 screen_size;
uniform float time;                          // seconds
uniform vec2 pointer_pressed_positions[32];  // 0..1, top-left origin, most recent first
uniform float pointer_pressed_times[32];     // seconds since each press; negative when unused

layout(location = 0) out vec4 fragColor;

const float TAU = 6.28318531;
const float DURATION = 10.6;      // s, the whole episode, counted from the press
const float T_VHS = 6.1;          // the picture turns to tape
const float T_REW = 6.9;          // and rewinds
const float REW_SPEED = 2.7;      // times faster than it happened
const float T_BACK = T_REW + T_REW / REW_SPEED;   // when the rewind reaches the start (~9.46 s)
const float T_LOCK = 5.2;         // the eye fixes on the car
const float ANGULAR_CELLS = 15.0; // shards round the ring
const float JITTER = 0.85;        // how irregular the shards are
const vec2 LIGHT = vec2(-0.62, -0.78);    // towards the light, screen y down
const vec3 EMBER = vec3(1.0, 0.16, 0.10); // the glow inside the cracks
const vec3 HOT = vec3(1.0, 0.82, 0.70);   // its hottest line

float hash11(float p) {
    return fract(sin(p * 127.1) * 43758.5453123);
}

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

// ── The clock ───────────────────────────────────────────────────────────────────────────────────────────────────
// Scene time runs forward to the rewind, then back to 0 at REW_SPEED: everything below is a function of it, so the
// rewind is the same film played backwards.
float sceneTime(float age) {
    return age < T_REW ? age : max(0.0, T_REW - (age - T_REW) * REW_SPEED);
}

float spinAngle(float st) {             // how far the sun has turned: fast, then slowing
    return 7.5 * (1.0 - exp(-1.5 * st));
}

float spinRate(float st) {
    return 11.25 * exp(-1.5 * st);
}

float collapseAt(float st) {
    return smoothstep(0.35, 2.2, st);
}

// ── Sampling the screen ─────────────────────────────────────────────────────────────────────────────────────────

vec3 sampleTex(vec2 uv) {
    uv = 1.0 - abs(1.0 - mod(uv, 2.0));   // mirrored at the edges, so nothing smears in
    return texture(tex, uv).rgb;
}

// The picture, with the ring's neighbourhood turned with the sun, smeared along its turn while it is fast.
vec3 sampleScreen(vec2 hu, vec2 ringUV, float aspect, float st) {
    float r = length(hu);
    float w = exp(-pow((r - RING_R) / (RING_R * 0.55), 2.0)) + (1.0 - smoothstep(0.0, RING_R, r));
    w = clamp(w, 0.0, 1.0);
    float angle = spinAngle(st) * w;
    if (angle < 1e-4)
        return sampleTex(ringUV + hu / vec2(aspect, 1.0));
    float smear = min(spinRate(st) * 0.035, 0.45) * w;
    vec3 sum = vec3(0.0);
    for (int i = 0; i < 5; i++) {
        float a = angle - smear * float(i) / 4.0;
        sum += sampleTex(ringUV + rotate(hu, -a) / vec2(aspect, 1.0));
    }
    return sum / 5.0;
}

// A cell's feature point in log-polar space. The angular index wraps, so the shards meet up all the way round.
vec2 featurePoint(vec2 cell) {
    vec2 id = vec2(cell.x, mod(cell.y, ANGULAR_CELLS));
    return cell + 0.5 + (hash22(id) - 0.5) * JITTER;
}

vec2 cellHash(vec2 cell) {
    return hash22(vec2(cell.x, mod(cell.y, ANGULAR_CELLS)) + 41.0);
}

// ── The eye ─────────────────────────────────────────────────────────────────────────────────────────────────────

// Where it looks (eye units, y down): a few glances, then the car.
vec2 gazeAt(float st, vec2 carDir) {
    vec2 g = vec2(0.0);
    g = mix(g, vec2(-0.30, -0.08), smoothstep(2.85, 2.95, st));
    g = mix(g, vec2(0.30, 0.04), smoothstep(3.45, 3.55, st));
    g = mix(g, vec2(-0.12, 0.24), smoothstep(3.95, 4.04, st));
    g = mix(g, vec2(0.24, -0.22), smoothstep(4.62, 4.71, st));
    g = mix(g, carDir * 0.36, smoothstep(T_LOCK - 0.06, T_LOCK + 0.06, st));
    // A living eye is never quite still, until it has found what it wants.
    float settle = 1.0 - smoothstep(T_LOCK, T_LOCK + 0.4, st);
    g += (vec2(noise(vec2(st * 7.0, 1.3)), noise(vec2(st * 7.0, 8.1))) - 0.5) * 0.035 * settle;
    return g;
}

float eyeOpenAt(float st) {
    float open = smoothstep(2.0, 2.65, st);
    float blink = 1.0 - exp(-pow((st - 4.32) / 0.07, 2.0));
    return open * blink;
}

// How wide the hole inside the ring is: the ring's own size, then wider as the eye comes, so it can be seen.
float holeRadius(float st) {
    return RING_R * (1.0 + 1.35 * smoothstep(1.6, 2.5, st));
}

// The eye, drawn over `under` in the void inside the ring. p is in height units from the ring's centre.
vec3 drawEye(vec3 under, vec2 p, float st, vec2 carDir, float present) {
    float open = eyeOpenAt(st) * present;
    if (open < 0.002)
        return under;
    float E = holeRadius(st) * 0.84;
    vec2 q = p / E;
    float ax = clamp(1.0 - q.x * q.x, 0.0, 1.0);
    float upper = open * 0.60 * pow(ax, 0.75);
    float lower = open * 0.46 * pow(ax, 0.9);
    float inside = min(q.y + upper, lower - q.y);    // > 0 between the lids
    float aa = 2.0 / (E * screen_size.y);
    float mask = smoothstep(-aa, aa, inside) * step(abs(q.x), 1.0);

    vec2 g = gazeAt(st, carDir);
    float lock = smoothstep(T_LOCK, T_LOCK + 0.45, st);

    // The white of the eye: dark, hot, veined, in shadow under the lids.
    float veins = smoothstep(0.62, 0.95, noise(q * 9.0 + 3.0)) * smoothstep(0.35, 1.0, length(q));
    vec3 col = mix(vec3(0.20, 0.03, 0.04), vec3(0.55, 0.16, 0.12), 0.5 + 0.5 * q.y);
    col += EMBER * veins * 0.55;
    col *= smoothstep(0.0, 0.32, inside / max(open, 0.05));

    // The iris: molten gold to ember, in fibres round the pupil, darker at its rim.
    vec2 iq = q - g;
    float IR = 0.40;
    float d = length(iq) / IR;
    float ang = atan(iq.y, iq.x);
    float fibres = noise(vec2(ang * 9.0, d * 3.0)) * 0.6 + noise(vec2(ang * 23.0, d * 7.0)) * 0.4;
    vec3 iris = mix(HOT * vec3(1.0, 0.86, 0.45), EMBER, smoothstep(0.15, 0.95, d));
    iris *= 0.55 + 0.75 * fibres;
    iris *= 1.0 - 0.75 * smoothstep(0.78, 1.0, d);                // the dark limbal ring
    iris += HOT * exp(-pow((d - 0.42) / 0.07, 2.0)) * 0.35;       // the bright ring round the pupil
    iris *= 1.0 + 0.6 * lock;                                     // it burns brighter once it has the car
    float irisMask = 1.0 - smoothstep(0.97, 1.03, d);
    col = mix(col, iris, irisMask);

    // The pupil: round while it looks, a slit once it has found the car.
    vec2 pr = vec2(mix(0.16, 0.055, lock), mix(0.16, 0.30, lock));
    float pd = length(iq / pr);
    col = mix(col, vec3(0.01, 0.0, 0.0), 1.0 - smoothstep(0.92, 1.08, pd));
    col += EMBER * exp(-pow((pd - 1.0) / 0.12, 2.0)) * 0.3 * lock;

    // A wet highlight, and the lids' own shadow.
    vec2 hl = iq - vec2(-0.13, -0.15);
    col += vec3(1.0, 0.92, 0.88) * (1.0 - smoothstep(0.035, 0.06, length(hl))) * 0.85;
    col *= 0.55 + 0.45 * smoothstep(0.0, 0.18, inside);

    // The lids' edges glow like the ring.
    float rim = exp(-pow(inside / 0.035, 2.0)) * step(abs(q.x), 1.02);
    vec3 outCol = mix(under, col, mask);
    outCol += EMBER * rim * 0.9 * open + HOT * rim * rim * 0.35 * open;
    return outCol;
}

// ── Embers ──────────────────────────────────────────────────────────────────────────────────────────────────────

vec3 embers(vec2 p, float st) {
    vec3 sum = vec3(0.0);
    for (int i = 0; i < 22; i++) {
        float fi = float(i);
        float t0 = 0.35 + 2.4 * hash11(fi + 0.5);
        float life = 1.2 + 1.4 * hash11(fi + 7.3);
        float a = st - t0;
        if (a < 0.0 || a > life)
            continue;
        float k = a / life;
        float ang = TAU * hash11(fi + 3.1);
        vec2 dir = vec2(cos(ang), sin(ang));
        vec2 vel = dir * (0.10 + 0.22 * hash11(fi + 11.7)) + vec2(0.0, -0.05);
        vec2 pos = dir * holeRadius(t0) * 1.02 + vel * a + vec2(sin(a * 5.0 + fi) * 0.006, -0.05 * a * a);
        vec2 back = pos - normalize(vel + vec2(0.0, -0.1 * a)) * 0.012;    // a short streak behind it
        vec2 pa = p - back, ba = pos - back;
        float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
        float dist = length(pa - ba * h);
        float size = 0.002 + 0.003 * hash11(fi + 5.9);
        float glow = exp(-dist * dist / (size * size)) * (0.4 + 0.6 * h);
        sum += mix(HOT, EMBER, k) * glow * (1.0 - k) * 1.4;
    }
    return sum;
}

// ── The scene at scene time st ──────────────────────────────────────────────────────────────────────────────────

vec3 scene(vec2 uv, float st, float strength, vec2 ringUV, vec2 carP, float aspect) {
    float collapse = collapseAt(st);
    float front = RING_R * 1.1 + 2.6 * (1.0 - exp(-st * 3.4));
    float bump = exp(-pow((st - 0.45) / 0.35, 2.0));

    vec2 p = (uv - ringUV) * vec2(aspect, 1.0);   // height units from the ring
    // A short shudder as the glass gives way.
    p += vec2(sin(time * 53.0), cos(time * 67.0)) * 0.0016 * bump * strength;
    float r = max(length(p), 1e-4);
    float theta = atan(p.y, p.x);
    float K = ANGULAR_CELLS / TAU;
    float rBase = RING_R * 1.1;

    // Near the screen's edges things move less, so nothing from beyond the edge is pulled into view.
    float edgeRoom = min(min(uv.x, 1.0 - uv.x), min(uv.y, 1.0 - uv.y));
    float freedom = smoothstep(0.0, 0.14, edgeRoom);

    float pinch = collapse * strength * 0.22 * exp(-r / 0.5) * freedom;
    vec2 pulled = p * (1.0 + pinch);

    // Shards: Voronoi cells in log-polar space, small near the ring and larger away from it.
    vec2 q = vec2(log(max(r, rBase * 0.92) / rBase) * K, theta * K);
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

    vec2 h = cellHash(bestCell);
    float depth = h.x;
    float rC = rBase * exp(bestPoint.x / K);
    float thetaC = bestPoint.y / K;
    vec2 radialC = vec2(cos(thetaC), sin(thetaC));
    vec2 centre = radialC * rC;
    float cracked = 1.0 - smoothstep(front - 0.08, front, rC);
    float own = clamp(collapse * 1.3 - 0.3 * h.y, 0.0, 1.0) * cracked * strength * freedom;
    float funnel = exp(-(rC - RING_R) / 0.35);

    float sink = min(rC * 0.5, 0.06 + 0.08 * funnel) * (0.35 + 0.65 * depth);
    vec2 move = -radialC * sink * own;
    float shrink = 1.0 - (0.06 + 0.16 * funnel) * own * (0.4 + 0.6 * depth);
    float turn = (h.y - 0.5) * 0.35 * own;
    vec2 tilt = (h - 0.5) * 0.02 * depth * own;
    vec2 source = centre + rotate(pulled - centre - move, -turn) / shrink + tilt;

    vec2 split = radialC * (0.0012 + 0.003 * depth) * own;
    vec3 colour = vec3(
        sampleScreen(source + split, ringUV, aspect, st).r,
        sampleScreen(source, ringUV, aspect, st).g,
        sampleScreen(source - split, ringUV, aspect, st).b
    );

    float facet = dot(normalize(h - 0.5 + 1e-4), LIGHT) * own * (0.4 + 0.6 * depth);
    colour *= 1.0 + facet * 0.16 + (h.x - 0.5) * 0.08 * own;
    colour *= 1.0 - 0.55 * own * (0.35 + 0.65 * depth) * funnel;

    float perQ = r * TAU / ANGULAR_CELLS;
    float edgePx = max(edgeQ, 0.0) * perQ * screen_size.y;
    vec2 radial = vec2(cos(theta), sin(theta));
    vec2 tangent = vec2(-radial.y, radial.x);
    vec2 edgeFacing = normalize(radial * edgeDir.x + tangent * edgeDir.y);

    float live = (1.0 - smoothstep(front - 0.06, front, r)) * smoothstep(0.02, 0.25, st)
               * smoothstep(RING_R * 0.82, RING_R * 1.0, r);
    float gap = (0.9 + 7.5 * collapse * strength) * live;
    float halfGap = gap * 0.5;
    float aa = 0.9;

    float bevelWidth = 2.5 + 5.0 * depth;
    float t = clamp((edgePx - halfGap) / bevelWidth, 0.0, 1.0);
    float lit = dot(edgeFacing, LIGHT);
    float bevel = (1.0 - t) * (1.0 - t);
    colour += HOT * max(lit, 0.0) * bevel * 0.55 * live * (0.5 + 0.5 * strength);
    colour *= 1.0 - max(-lit, 0.0) * bevel * 0.5 * live;
    colour += vec3(1.0) * (1.0 - smoothstep(halfGap, halfGap + 1.3, edgePx)) * max(lit, 0.0) * 0.5 * live;
    colour *= 1.0 - 0.38 * exp(-(edgePx - halfGap) / (6.0 + 6.0 * depth)) * live * own;

    float inGap = 1.0 - smoothstep(halfGap - aa, halfGap + aa, edgePx);
    float core = exp(-edgePx * edgePx / (gap * 0.08 + 0.35));
    float heat = (0.3 + 0.7 * exp(-r * 1.7)) * (0.35 + 0.65 * collapse) * strength;
    vec3 abyss = mix(vec3(0.02, 0.0, 0.012), EMBER * (0.45 + 1.5 * heat), 0.12 + 0.88 * core);
    abyss = mix(abyss, HOT, core * core * 0.55 * heat);
    colour = mix(colour, abyss, inGap * live);

    // Light rays out through the cracks, turning slowly.
    vec2 dir = p / r;
    float rays = pow(noise(dir * 6.0 + vec2(st * 0.12, -st * 0.07)), 3.0) * 2.2;
    colour += EMBER * rays * collapse * strength * 0.32 * exp(-max(r - RING_R, 0.0) * 2.6) * step(RING_R, r);

    // Inside the ring the glass is gone: a dark core with the ring's light pouring in from its rim.
    float holeR = holeRadius(st);
    float core01 = 1.0 - smoothstep(holeR * 0.80, holeR * 0.96, r);
    float coreDepth = smoothstep(0.0, holeR * 0.96, r);
    vec3 voidColour = mix(vec3(0.01, 0.0, 0.005), EMBER * 0.9, pow(coreDepth, 3.0));
    voidColour += HOT * pow(coreDepth, 10.0) * 0.6;
    float voidAmount = core01 * collapse * strength * 0.92;
    colour = mix(colour, voidColour, voidAmount);

    // The eye, in the void.
    vec2 carDir = normalize(carP + vec2(1e-5));
    colour = drawEye(colour, p, st, carDir, clamp(voidAmount / max(strength * 0.92, 1e-3), 0.0, 1.0));

    // Once it has the car: a red ring closes on it, and a faint line runs from the eye to it.
    float lockVis = smoothstep(T_LOCK, T_LOCK + 0.15, st) * (1.0 - smoothstep(T_LOCK + 1.2, T_LOCK + 2.4, st));
    if (lockVis > 0.0) {
        float dc = length(p - carP);
        float rad = mix(0.09, 0.024, smoothstep(T_LOCK, T_LOCK + 0.5, st));
        float reticle = exp(-pow((dc - rad) / 0.0016, 2.0));
        float ticks = step(0.7, abs(cos(atan(p.y - carP.y, p.x - carP.x) * 2.0)));
        colour += EMBER * reticle * (0.6 + 0.4 * ticks) * lockVis * 1.4;
        colour += EMBER * exp(-dc * dc / 0.0003) * 0.35 * lockVis;
        vec2 seg = carP;
        float hseg = clamp(dot(p, seg) / dot(seg, seg), 0.0, 1.0);
        float beam = exp(-pow(length(p - seg * hseg) / 0.0012, 2.0)) * step(RING_R * 0.5, length(p));
        colour += EMBER * beam * 0.35 * lockVis * (0.6 + 0.4 * sin(time * 30.0 - hseg * 40.0));
    }

    colour += embers(p, st) * strength;

    // The whole screen darkens towards its edges, and the middle burns.
    float vignette = collapse * strength * 0.5 * smoothstep(0.25, 1.35, r);
    colour *= 1.0 - vignette;
    colour += EMBER * collapse * strength * 0.2 * exp(-r * r / 0.02);
    return clamp(colour, 0.0, 1.0);
}

// ── The VCR's on-screen display ─────────────────────────────────────────────────────────────────────────────────

// 5×7 glyphs, one row of five bits each, left pixel first.
// 0-9 digits, 10 P, 11 L, 12 A, 13 Y, 14 R, 15 E, 16 W, 17 :, 18 S, 19 T, 20 O, 21 space, 22 play, 23 rewind
const int FONT[168] = int[](14, 17, 19, 21, 25, 17, 14, 4, 12, 4, 4, 4, 4, 14, 14, 17, 1, 2, 4, 8, 31, 31, 2, 4,
    2, 1, 17, 14, 2, 6, 10, 18, 31, 2, 2, 31, 16, 30, 1, 1, 17, 14, 6, 8, 16, 30, 17, 17, 14, 31, 1, 2, 4, 8, 8, 8,
    14, 17, 17, 14, 17, 17, 14, 14, 17, 17, 15, 1, 2, 12, 30, 17, 17, 30, 16, 16, 16, 16, 16, 16, 16, 16, 16, 31,
    14, 17, 17, 31, 17, 17, 17, 17, 17, 10, 4, 4, 4, 4, 30, 17, 17, 30, 20, 18, 17, 31, 16, 16, 30, 16, 16, 31, 17,
    17, 17, 21, 21, 21, 10, 0, 12, 12, 0, 12, 12, 0, 15, 16, 16, 14, 1, 1, 30, 31, 4, 4, 4, 4, 4, 4, 14, 17, 17,
    17, 17, 17, 14, 0, 0, 0, 0, 0, 0, 0, 16, 24, 28, 30, 28, 24, 16, 1, 3, 7, 15, 7, 3, 1);

float glyphPixel(int ch, ivec2 cell) {
    if (cell.x < 0 || cell.x > 4 || cell.y < 0 || cell.y > 6)
        return 0.0;
    int row = FONT[ch * 7 + cell.y];
    return float((row >> (4 - cell.x)) & 1);
}

// The messages: 0 "PLAY ▶", 1 "◀◀ REW", 2 "SP", 3 the counter "0:00:SS" (seconds of tape).
int messageChar(int msg, int i, float seconds) {
    if (msg == 0) {
        int m[6] = int[](10, 11, 12, 13, 21, 22);
        return i < 6 ? m[i] : -1;
    }
    if (msg == 1) {
        int m[6] = int[](23, 23, 21, 14, 15, 16);
        return i < 6 ? m[i] : -1;
    }
    if (msg == 2) {
        int m[2] = int[](18, 10);
        return i < 2 ? m[i] : -1;
    }
    int s = int(floor(seconds));
    int m[7] = int[](0, 17, 0, 0, 17, (s / 10) % 10, s % 10);
    return i < 7 ? m[i] : -1;
}

// 1 where message msg covers the screen pixel px, drawn from origin (top-left of its first glyph), in display
// pixels of `scale` screen pixels; cells are 6 × 9.
float message(int msg, vec2 px, vec2 origin, float scale, float seconds) {
    vec2 local = (px - origin) / scale;
    if (local.x < 0.0 || local.y < 0.0 || local.y >= 9.0)
        return 0.0;
    int index = int(floor(local.x / 6.0));
    int ch = messageChar(msg, index, seconds);
    if (ch < 0)
        return 0.0;
    ivec2 cell = ivec2(int(floor(local.x)) - index * 6, int(floor(local.y)) - 1);
    return glyphPixel(ch, cell);
}

float osd(int msg, vec2 px, vec2 origin, float scale, float seconds) {
    return message(msg, px, origin, scale, seconds);
}

// ── Main ────────────────────────────────────────────────────────────────────────────────────────────────────────

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
    vec2 carP = (vec2(CAR_X, CAR_Y) - ringUV) * vec2(aspect, 1.0);
    float st = sceneTime(age);
    vec2 uv = v_texcoord;

    // How much of a videotape it is: in at T_VHS, out at the end.
    float vhs = smoothstep(T_VHS, T_VHS + 0.45, age) * (1.0 - smoothstep(DURATION - 0.8, DURATION, age));
    if (vhs < 0.001) {
        fragColor = vec4(scene(uv, st, strength, ringUV, carP, aspect), 1.0);
        return;
    }
    float rew = smoothstep(T_REW - 0.05, T_REW + 0.12, age) * (1.0 - smoothstep(T_BACK, T_BACK + 0.25, age));

    // The tape: every line a little off sideways, more while it rewinds; a tracking band rolling through; the
    // head-switching tear along the bottom.
    vec2 px = uv * size;
    float line = floor(px.y / 2.0);
    float frame = floor(time * 30.0);
    float jitter = (hash21(vec2(line, frame)) - 0.5) * (0.0016 + 0.006 * rew);
    float bandY = fract(-age * (0.35 + 1.4 * rew));
    float band = exp(-pow((uv.y - bandY) / (0.025 + 0.03 * rew), 2.0));
    jitter += band * (noise(vec2(line * 0.3, frame)) - 0.5) * (0.03 + 0.05 * rew);
    float bottom = smoothstep(0.955, 0.985, uv.y);
    jitter += bottom * (0.02 + 0.03 * noise(vec2(line, frame)));
    // While it rewinds, the picture also rolls a little and its rows skew.
    uv.y += rew * 0.012 * sin(age * 9.0);
    uv.x += jitter * vhs + rew * 0.006 * sin(uv.y * 40.0 + age * 25.0);

    // Colour bleeds sideways, as tape's colour is soft next to its brightness.
    float bleed = (0.0025 + 0.004 * rew) * vhs;
    vec3 mid = scene(uv, st, strength, ringUV, carP, aspect);
    vec3 col = vec3(scene(uv + vec2(bleed, 0.0), st, strength, ringUV, carP, aspect).r, mid.g,
                    scene(uv - vec2(bleed, 0.0), st, strength, ringUV, carP, aspect).b);
    float luma = dot(col, vec3(0.299, 0.587, 0.114));
    vec3 tape = mix(vec3(luma), col, 0.78);                      // a little washed out
    tape = tape * vec3(1.04, 0.98, 0.94) + vec3(0.035, 0.025, 0.04);   // warm, with lifted blacks
    tape *= 0.86 + 0.14 * sin(px.y * 3.14159 / 1.5);              // scanlines
    tape += (hash21(px + frame) - 0.5) * (0.07 + 0.08 * rew);    // grain
    tape += band * (0.06 + 0.12 * rew) * hash21(vec2(px.x * 0.05, line + frame));   // the band's snow
    // Rewinding: thin bright streaks race across.
    float streak = step(0.985, hash21(vec2(floor(px.y / 3.0), floor(time * 24.0)))) * rew;
    tape += vec3(0.85) * streak * (0.4 + 0.6 * hash21(vec2(px.x * 0.02, frame)));
    tape = mix(tape, tape * 0.25 + vec3(0.05), bottom);
    vec2 vq = v_texcoord - 0.5;
    tape *= 1.0 - 0.35 * dot(vq, vq) * 2.0;
    col = mix(mid, clamp(tape, 0.0, 1.0), vhs);

    // The VCR's words, in white with a dark edge, top left and bottom right.
    float scale = max(2.0, floor(size.y / 180.0));
    vec2 tl = vec2(size.y * 0.07, size.y * 0.07);
    int msg = (age >= T_REW && age < T_BACK + 0.1) ? 1 : 0;
    float counter = st + 0.0;   // tape seconds: forwards, then back down while it rewinds
    vec2 tc = vec2(size.x - size.y * 0.07 - 7.0 * 6.0 * scale, size.y * 0.86);
    vec2 sp = vec2(size.y * 0.07, size.y * 0.86);
    float shadow = osd(msg, px - vec2(scale), tl, scale, counter) + osd(3, px - vec2(scale), tc, scale, counter)
                 + osd(2, px - vec2(scale), sp, scale, counter);
    float textMask = osd(msg, px, tl, scale, counter) + osd(3, px, tc, scale, counter) + osd(2, px, sp, scale, counter);
    float osdVis = smoothstep(T_VHS + 0.15, T_VHS + 0.3, age) * (1.0 - smoothstep(DURATION - 0.5, DURATION - 0.2, age));
    col = mix(col, vec3(0.0), clamp(shadow, 0.0, 1.0) * 0.7 * osdVis);
    col = mix(col, vec3(0.96, 0.98, 1.0), clamp(textMask, 0.0, 1.0) * osdVis);

    fragColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}
