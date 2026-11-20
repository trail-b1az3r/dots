#version 440
// Halcyon Neumorphism: a soft surface pressed out of (or into) the same material as what is around it.
//
// Raised: a light shadow towards the light (top-left) and a dark one away from it (bottom-right), both soft, so
// the shape seems to rise out of the page. Inset: the same two shadows inside the shape, so it seems pressed into
// it. `inset` blends between them (0 raised, 1 pressed), so a button sinks smoothly when pressed. `convex` lights
// the face itself, brighter towards the light (a dome; negative: a dish).
//
// The item is the shape plus a margin round it for the shadows. The outline is a rounded rectangle with
// superellipse corners, like the glass panes'.

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 itemSize;
    vec4 base;          // the material
    vec4 lightTone;     // the lit shadow
    vec4 darkTone;      // the dark shadow
    vec4 accent;        // a fill drawn into the face (a lit toggle, a gauge), with its own alpha
    vec2 lightDir;      // where the light comes from (unit vector)
    float margin;
    float radius;
    float corner;
    float distance;     // px the shadows are thrown
    float blur;         // px of softness
    float strength;     // 0..1
    float inset;        // 0: raised, 1: pressed in
    float convex;       // -1..1
};

float shapeSdf(vec2 p, vec2 b, float r, float n) {
    vec2 q = abs(p) - b + r;
    if (q.x > 0.0 && q.y > 0.0) {
        vec2 a = q / r;
        return (pow(pow(a.x, n) + pow(a.y, n), 1.0 / n) - 1.0) * r;
    }
    return max(q.x, q.y) - r;
}

void main() {
    vec2 px = qt_TexCoord0 * itemSize;
    vec2 halfSize = max(itemSize * 0.5 - margin, vec2(1.0));
    float r = min(radius, min(halfSize.x, halfSize.y));
    vec2 p = px - itemSize * 0.5;
    vec2 throw_ = -lightDir * distance;              // away from the light
    float d = shapeSdf(p, halfSize, r, corner);
    float raised = 1.0 - inset;

    // Outside: the two shadows of a raised shape (each is the shape moved, blurred).
    float dDark = shapeSdf(p - throw_, halfSize, r, corner);
    float dLight = shapeSdf(p + throw_, halfSize, r, corner);
    float darkOut = (1.0 - smoothstep(-blur, blur, dDark)) * raised;
    float lightOut = (1.0 - smoothstep(-blur, blur, dLight)) * raised;

    // The lit shadow over the dark one (as CSS draws them), so the light side stays bright where they meet.
    float da = darkTone.a * darkOut * strength;
    float la = lightTone.a * lightOut * strength;
    vec4 outside = vec4(darkTone.rgb, 1.0) * da;
    outside = vec4(lightTone.rgb, 1.0) * la + outside * (1.0 - la);

    // Inside: the face, and when pressed, shadows falling inside its edges.
    vec3 face = base.rgb;
    float tilt = dot(p / max(halfSize, vec2(1.0)), lightDir) * -0.5;        // +0.5 towards the light
    face += convex * tilt * 0.10;
    face = mix(face, accent.rgb, accent.a);
    // Pressed: dark along the edges facing the light, lit along the far ones.
    float darkIn = smoothstep(-blur, blur * 0.6, shapeSdf(p + throw_ * 0.9, halfSize, r, corner)) * inset;
    float lightIn = smoothstep(-blur, blur * 0.6, shapeSdf(p - throw_ * 0.9, halfSize, r, corner)) * inset;
    face = mix(face, darkTone.rgb, darkIn * darkTone.a * strength * 0.9);
    face = mix(face, lightTone.rgb, lightIn * lightTone.a * strength * 0.9);
    // A hairline lit edge on the light side keeps a raised shape crisp.
    vec2 e = vec2(0.75, 0.0);
    vec2 n = normalize(vec2(shapeSdf(p + e.xy, halfSize, r, corner) - shapeSdf(p - e.xy, halfSize, r, corner),
                            shapeSdf(p + e.yx, halfSize, r, corner) - shapeSdf(p - e.yx, halfSize, r, corner)) + 1e-6);
    float rim = exp(-abs(d + 0.6) / 0.8) * max(dot(n, lightDir) * -1.0, 0.0) * raised;
    face = mix(face, lightTone.rgb, rim * 0.6 * strength);

    float cover = clamp(0.5 - d, 0.0, 1.0);
    vec4 shape = vec4(clamp(face, 0.0, 1.0), 1.0) * cover;
    fragColor = (shape + outside * (1.0 - shape.a)) * qt_Opacity;
}
