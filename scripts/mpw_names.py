"""mapwright place names from a sound pattern (standard library only).

A language is a small phonology: onset consonants, vowels, codas, syllable
shapes and a syllable count range. Names are seeded by (language seed, kind,
key, attempt), so the same world always gets the same names and a child map
reuses its parent's language.
"""
import re

M64 = (1 << 64) - 1


def h64(*k):
    x = 0x9E3779B97F4A7C15
    for v in k:
        x = (x ^ (v & M64)) * 0xBF58476D1CE4E5B9 & M64
        x ^= x >> 31
        x = x * 0x94D049BB133111EB & M64
        x ^= x >> 29
    return x


def _kid(s):
    """Stable integer for a short string (no Python hash randomisation)."""
    v = 0
    for ch in s:
        v = h64(v, ord(ch))
    return v


# onsets / vowels / codas are space separated; shapes use C (onset), V (vowel), F (coda)
STYLES = {
    "soft": dict(C="l m n r s v th h f y w", V="a e i o u ae ei ia", F="n l s r th",
                 S="CV CVF V CV", N="2-3", desc="flowing, vowel rich"),
    "harsh": dict(C="k g d t r z kr gr dr th b", V="a o u i", F="k g r z rk th d",
                  S="CVF CV CVF CCVF", N="1-2", desc="clustered stops, closed syllables"),
    "nordic": dict(C="b d f g h k l m n r s t v sk st", V="a e i o u y aa ei", F="n r d k ll rd nd st",
                   S="CVF CV CVF", N="1-2", desc="short, consonant final"),
    "latinate": dict(C="b c d f l m n p r s t v qu", V="a e i o u ia io", F="n s r m",
                     S="CV CV CVF V", N="2-4", desc="open syllables, -a/-um/-is feel"),
    "desert": dict(C="b d h j k m n q r s sh t z kh", V="a i u aa", F="r n m d sh",
                   S="CV CVF CV", N="2-3", desc="long vowels, sh/kh/q"),
    "isle": dict(C="h k l m n p w", V="a e i o u", F="",
                 S="CV V CV", N="2-4", desc="no codas, small inventory"),
}

# Site words per style: a settlement on that site ends in the root, and names.json glosses it.
# Invented roots, each fitted to its style's sounds. A custom pattern has none, so its names get no site word.
SITES = ("river mouth", "ford", "coast", "hill")
ROOTS = {
    "soft": {"river mouth": "sael", "ford": "wen", "coast": "thea", "hill": "lin"},
    "harsh": {"river mouth": "kruz", "ford": "dak", "coast": "zar", "hill": "gor"},
    "nordic": {"river mouth": "osk", "ford": "vad", "coast": "stren", "hill": "kold"},
    "latinate": {"river mouth": "ostra", "ford": "vira", "coast": "lita", "hill": "colla"},
    "desert": {"river mouth": "shat", "ford": "makh", "coast": "sahr", "hill": "tul"},
    "isle": {"river mouth": "wana", "ford": "kawa", "coast": "kai", "hill": "pali"},
}
GLOSS = {"ocean": "open ocean", "sea": "sea", "land": "landmass", "range": "mountain range", "lake": "lake",
         "river": "river", "settlement": "settlement, no site word"}

DEFAULT_STYLE = "soft"
BAD = ("fuck", "shit", "cunt", "nigg", "fag", "rape", "kkk", "nazi", "piss", "slut", "whore", "dick",
       "cock", "anus", "porn")
VOWELS = set("aeiouy")


def parse_pattern(p):
    """'C=p t k;V=a i u;F=n;S=CV CVF;N=2-3' -> language fields."""
    out = {}
    for part in p.split(";"):
        if not part.strip():
            continue
        if "=" not in part:
            raise ValueError("pattern part %r needs KEY=values (keys C V F S N)" % part)
        k, v = part.split("=", 1)
        k = k.strip().upper()
        if k not in ("C", "V", "F", "S", "N"):
            raise ValueError("unknown pattern key %r (use C V F S N)" % k)
        out[k] = " ".join(v.replace(",", " ").split())
    for k in ("C", "V", "S"):
        if not out.get(k):
            raise ValueError("pattern needs %s=..." % k)
    out.setdefault("F", "")
    out.setdefault("N", "2-3")
    if not re.fullmatch(r"\d+-\d+|\d+", out["N"]):
        raise ValueError("N wants a range like 2-3")
    for sh in out["S"].split():
        if not re.fullmatch(r"C*VF*", sh):
            raise ValueError("syllable shape %r: use C, V, F like CVF" % sh)
        if "F" in sh and not out["F"]:
            raise ValueError("shape %r uses F but no codas given" % sh)
    return out


def make_language(seed, style=None, pattern=None):
    """Resolved language dict stored in recipe.json and names.json."""
    if pattern:
        f = parse_pattern(pattern)
        name = "custom"
    else:
        if style in (None, "auto"):
            keys = sorted(STYLES)
            style = keys[h64(seed, 4242) % len(keys)]
        if style not in STYLES:
            raise ValueError("unknown style %r; styles: %s" % (style, ", ".join(sorted(STYLES))))
        f = {k: STYLES[style][k] for k in ("C", "V", "F", "S", "N")}
        name = style
    return dict(style=name, seed=int(seed) & M64, C=f["C"], V=f["V"], F=f["F"], S=f["S"], N=f["N"])


def _pick(lst, x):
    return lst[x % len(lst)]


def _raw(lang, key):
    C, V, F = lang["C"].split(), lang["V"].split(), lang["F"].split()
    S = lang["S"].split()
    lo, _, hi = lang["N"].partition("-")
    lo = int(lo)
    hi = int(hi or lo)
    x = h64(lang["seed"], *key)
    n = lo + x % (hi - lo + 1)
    parts = []
    for i in range(n):
        sh = _pick(S, h64(x, i, 1))
        for j, ch in enumerate(sh):
            r = h64(x, i, j, 2)
            if ch == "C":
                parts.append(_pick(C, r))
            elif ch == "V":
                parts.append(_pick(V, r))
            else:
                parts.append(_pick(F, r))
    return "".join(parts)


def ok_name(s):
    """Reject obvious bad strings: too short or long, triple letters, vowel or consonant runs, slurs."""
    if not 3 <= len(s) <= 10 or not s.isalpha():
        return False
    if re.search(r"(.)\1\1", s):
        return False
    run_v = run_c = 0
    for ch in s:
        if ch in VOWELS:
            run_v += 1
            run_c = 0
        else:
            run_c += 1
            run_v = 0
        if run_v > 2 or run_c > 3:
            return False
    if not any(ch in VOWELS for ch in s) or (len(s) > 1 and s[0] == s[1] and s[0] not in VOWELS):
        return False
    return not any(b in s for b in BAD)


class Namer:
    """Hands out unique names for one world (a parent's names count as used)."""

    def __init__(self, lang, used=()):
        self.lang = lang
        self.used = set(n.lower() for n in used)

    def name(self, kind, key):
        """key: tuple of ints that identifies the feature in world terms."""
        kid = _kid(kind)
        for attempt in range(200):
            s = _raw(self.lang, (kid,) + tuple(int(k) & M64 for k in key) + (attempt,))
            if ok_name(s) and s not in self.used:
                self.used.add(s)
                return s[0].upper() + s[1:]
        # fall back: append a syllable count suffix until unique (practically never reached)
        base = _raw(self.lang, (kid,) + tuple(key))[:10] or "nameless"
        i = 2
        while (base + str(i)).lower() in self.used:
            i += 1
        self.used.add((base + str(i)).lower())
        return base.capitalize() + str(i)


def site_name(namer, key, site):
    """A settlement name: a base name plus the style's root for the site. Returns (name, generic, gloss)."""
    roots = ROOTS.get(namer.lang.get("style"), {})
    root = roots.get(site) if site else None
    base = namer.name("settlement", key)
    if root and h64(namer.lang["seed"], 7177, *key) % 5 >= 3:      # two in five keep a bare name
        root = None
    if not root:
        return base, None, GLOSS["settlement"]
    full = base + root
    if full.lower() in namer.used or any(b in full.lower() for b in BAD):
        return base, None, GLOSS["settlement"]
    namer.used.add(full.lower())
    return full, site, "%s + -%s '%s'" % (base, root, site)


def sample(n, seed=0, style=None, pattern=None):
    lang = make_language(seed, style, pattern)
    nm = Namer(lang)
    return lang, [nm.name("sample", (i,)) for i in range(n)]
