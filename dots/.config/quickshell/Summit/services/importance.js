.pragma library

// Summit's notification importance model: which notifications are worth a banner under the clock, and a one-line
// summary of them. A tiny logistic regression over hashed words and word pairs of the app name, title and body, plus
// a few signals (urgency, actions, a code, a time "in 5 minutes"). Its weights are assets/model/importance.json,
// trained by tools/summit-importance/train.py, which reads this same file for the features, so training and Summit
// can never disagree about them. Everything runs here, offline: nothing leaves the computer.

var BUCKETS = 4096;

// FNV-1a, 32 bits, over the characters (always ASCII here: normalize keeps nothing else).
function hash(text) {
    var h = 0x811c9dc5;
    for (var i = 0; i < text.length; i++) {
        h ^= text.charCodeAt(i);
        h = Math.imul(h, 0x01000193) >>> 0;
    }
    return h >>> 0;
}

function stripMarkup(text) {
    return String(text || "").replace(/<[^>]*>/g, " ").replace(/&[a-z]+;/g, " ");
}

// Lower case words of letters and digits; links become "url", 4 to 8 digits "numcode" (a code), other numbers "num".
function normalize(text) {
    var t = stripMarkup(text).toLowerCase();
    t = t.replace(/https?:\/\/\S+|www\.\S+/g, " url ");
    t = t.replace(/\b\d{4,8}\b/g, " numcode ");
    t = t.replace(/\d+([.,:]\d+)*/g, " num ");
    t = t.replace(/[^a-z' ]+/g, " ").replace(/'/g, "");
    return t.split(/\s+/).filter(function (w) { return w.length > 0; });
}

function features(n) {
    var app = normalize(n.appName);
    var title = normalize(n.summary);
    var body = normalize(n.body);
    var raw = (n.summary || "") + " " + stripMarkup(n.body);
    var out = {};
    function add(f) { out[f] = 1; }
    if (app.length)
        add("a=" + app.join("_"));
    function words(prefix, list) {
        for (var i = 0; i < list.length; i++) {
            add(prefix + ":" + list[i]);
            add("w:" + list[i]);
            if (i + 1 < list.length)
                add(prefix + "2:" + list[i] + "_" + list[i + 1]);
        }
    }
    words("t", title);
    words("b", body);
    add("u=" + (n.urgency === 2 ? "critical" : n.urgency === 0 ? "low" : "normal"));
    if (n.hasActions)
        add("has_actions");
    var length = body.length;
    add("len=" + (length === 0 ? "0" : length <= 5 ? "short" : length <= 20 ? "mid" : "long"));
    if (raw.indexOf("!") >= 0)
        add("excl");
    if (raw.indexOf("?") >= 0)
        add("question");
    if (/\b(in|within) \d+ ?(min|mins|minutes|m|sec|seconds|s)\b|\bstarts? (now|soon)\b|\bnow\b/i.test(raw))
        add("soon");
    if (/\b\d{4,8}\b/.test(raw))
        add("code");
    return Object.keys(out);
}

// Each feature as [bucket, sign]: the sign is another bit of the hash, so features that share a bucket mostly cancel
// out instead of adding up.
function hashed(list) {
    var out = [];
    for (var i = 0; i < list.length; i++) {
        var h = hash(list[i]);
        out.push([h % BUCKETS, ((h >>> 16) & 1) ? 1 : -1]);
    }
    return out;
}

function linear(model, list) {
    var z = model.bias;
    var hs = hashed(list);
    for (var i = 0; i < hs.length; i++)
        z += hs[i][1] * model.w[hs[i][0]];
    return z;
}

function probability(model, n) {
    return 1 / (1 + Math.exp(-linear(model, features(n))));
}

function clip(text, limit) {
    text = text.replace(/\s+/g, " ").trim();
    if (text.length <= limit)
        return text;
    var cut = text.slice(0, limit - 1);
    var space = cut.lastIndexOf(" ");
    return (space > limit * 0.6 ? cut.slice(0, space) : cut).replace(/[ ,;:.-]+$/, "") + "…";
}

// The summary: the title, and the body's sentence the model finds most telling (by the weights of its words).
function summarize(model, n, limit) {
    limit = limit || 96;
    var title = stripMarkup(n.summary).replace(/\s+/g, " ").trim();
    var body = stripMarkup(n.body).replace(/https?:\/\/\S+/g, "").trim();
    var sentences = body.replace(/([.!?])\s+/g, "$1\n").split(/\n+/).map(function (s) { return s.trim(); }).filter(function (s) { return s.length > 0; });
    var best = "", bestScore = -Infinity;
    for (var i = 0; i < sentences.length; i++) {
        var ws = normalize(sentences[i]);
        if (!ws.length)
            continue;
        var list = ws.map(function (w) { return "w:" + w; });
        var score = (linear(model, list) - model.bias) / Math.sqrt(ws.length) - i * 0.05;   // earlier wins ties
        if (score > bestScore) {
            bestScore = score;
            best = sentences[i];
        }
    }
    if (!title)
        return clip(best, limit);
    if (!best || best.toLowerCase() === title.toLowerCase() || title.length > limit * 0.75)
        return clip(title, limit);
    return clip(title + " — " + best, limit);
}

// What Summit asks: {important, score, summary}. Critical urgency is always important; low urgency never is.
function judge(model, n, threshold) {
    var score = model ? probability(model, n) : (n.urgency === 2 ? 1 : 0);
    var important = n.urgency === 2 || (n.urgency !== 0 && score >= (threshold || model.threshold || 0.5));
    return { important: important, score: score, summary: model ? summarize(model, n) : clip(stripMarkup(n.summary), 96) };
}

if (typeof module !== "undefined")
    module.exports = { BUCKETS: BUCKETS, hash: hash, normalize: normalize, features: features, hashed: hashed,
                       probability: probability, summarize: summarize, judge: judge };
