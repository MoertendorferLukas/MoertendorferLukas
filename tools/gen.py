# =====================================================================
#  Baut alle animierten SVGs fuer das GitHub-Profil-README.
#
#  GitHub erlaubt im README kein JavaScript, also auch kein three.js.
#  Darum rechnet dieses Skript die 3D-Szenen selbst: Modelle aus Boxen,
#  Zylindern und Kegeln (wie in welt3d.js), Perspektive, Rueckseiten
#  weglassen, nach Tiefe sortieren, flach beleuchten. Jedes Einzelbild
#  landet als Gruppe im SVG, CSS blendet sie nacheinander ein.
#
#  Aufruf:  python tools/gen.py      (braucht: pip install fonttools)
# =====================================================================
import math, os
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

HIER = os.path.dirname(os.path.abspath(__file__))
ZIEL = os.path.join(HIER, '..', 'assets')
os.makedirs(ZIEL, exist_ok=True)

# ---------- Anpassen ----------
SPIELE = 29   # Zahl auf dem Sticker im Hero

# ---------- Farben (dieselben wie auf der Website) ----------
SONNE, TINTE, TINTE2, NACHT = '#ffc61a', '#16193b', '#3b3f6b', '#0e1029'
WEISS, ROT, ROT_D, BLAU, BLAU_D, GRUEN = '#fffdf5', '#d6311f', '#9c1d0f', '#1f5fd0', '#16449a', '#2f9e58'
SANS = "system-ui,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"

class F:
    gras = 0x4cb963; grasD = 0x2f9e58; sand = 0xf4d58d; sandD = 0xe0b86a; erde = 0xa9714b; erdeD = 0x7d5238
    fels = 0x9da0b8; felsD = 0x6f7290; wasser = 0x36b1e6; wasserD = 0x1f7fc4
    dino = 0x4cb963; dinoD = 0x2a8a4a; bauch = 0xc9efb0; rot = 0xe23d28; rotD = 0xa82112; gelb = 0xffc61a
    weiss = 0xfffdf5; tinte = 0x16193b; blau = 0x1f5fd0; holz = 0xc08a55; holzD = 0x7d5330; lava = 0xff7a1a
    filz = 0x1f8a55; stahl = 0xdfe6f2; lila = 0x8a63d2; lilaD = 0x6846ad; gold = 0xf5b301
    nachtblau = 0x2a3170; rauch = 0xe9e6dc

PI, sin, cos = math.pi, math.sin, math.cos

# =====================================================================
#  Schrift: Bagel Fat One als Pfade (SVGs in <img> duerfen keine Fonts laden)
# =====================================================================
_font = TTFont(os.path.join(HIER, 'fonts', 'BagelFatOne-Latin.ttf'))
_gs, _cmap, _upm = _font.getGlyphSet(), _font.getBestCmap(), _font['head'].unitsPerEm
_ntos = lambda v: ('%.1f' % v).rstrip('0').rstrip('.')

def bagel_breite(text, size):
    return sum(_gs[_cmap[ord(c)]].width for c in text) * size / _upm

def bagel(text, size, x, y, anker='start', einzeln=False):
    """Text als SVG-Pfad. einzeln=True liefert einen Pfad pro Buchstabe."""
    s = size / _upm
    b = bagel_breite(text, size)
    if anker == 'middle': x -= b / 2
    if anker == 'end': x -= b
    teile = []
    for c in text:
        g = _gs[_cmap[ord(c)]]
        pen = SVGPathPen(_gs, ntos=_ntos)
        g.draw(TransformPen(pen, (s, 0, 0, -s, x, y)))
        d = pen.getCommands()
        if d: teile.append(d)
        x += g.width * s
    return teile if einzeln else ''.join(teile)

def passend(text, breite, maxsize):
    return min(maxsize, maxsize * breite / bagel_breite(text, maxsize))

def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;')

# =====================================================================
#  3D: Flaechen sind [Eckpunkte, Farbe]. Eckpunkte gegen den Uhrzeigersinn
#  von aussen gesehen, damit Rueckseiten erkannt werden.
# =====================================================================
def normale(vs):
    nx = ny = nz = 0.0
    for i in range(len(vs)):
        a, b = vs[i], vs[(i + 1) % len(vs)]
        nx += (a[1] - b[1]) * (a[2] + b[2]); ny += (a[2] - b[2]) * (a[0] + b[0]); nz += (a[0] - b[0]) * (a[1] + b[1])
    l = math.sqrt(nx * nx + ny * ny + nz * nz) or 1
    return nx / l, ny / l, nz / l

def mitte(vs):
    n = len(vs)
    return sum(v[0] for v in vs) / n, sum(v[1] for v in vs) / n, sum(v[2] for v in vs) / n

def _aussen(faces, c):
    """Dreht Flaechen so, dass die Normale vom Mittelpunkt c wegzeigt."""
    out = []
    for f in faces:
        vs = f[0]
        n, m = normale(vs), mitte(vs)
        if n[0] * (m[0] - c[0]) + n[1] * (m[1] - c[1]) + n[2] * (m[2] - c[2]) < 0: vs = vs[::-1]
        out.append([vs, *f[1:]])
    return out

# Jeder Baustein (Box, Zylinder) ist ein "Teil". Sortiert wird erst nach Teilen, dann nach
# Flaechen: das haelt Figuren aus vielen Boxen sauber. Die Ebene erzwingt eine Reihenfolge
# (z. B. Spielbrett vor den Figuren, die darauf stehen).
_teilnr = [0]
def _teil(faces, ebene=1):
    _teilnr[0] += 1
    return [[f[0], f[1], (ebene, _teilnr[0])] for f in faces]
def ebene(faces, n):
    return [[f[0], f[1], (n, f[2][1] if len(f) > 2 else _neu())] for f in faces]
def _neu():
    _teilnr[0] += 1
    return _teilnr[0]

def _map(faces, fn): return [[[fn(v) for v in f[0]], *f[1:]] for f in faces]
def T(faces, x=0, y=0, z=0): return _map(faces, lambda v: (v[0] + x, v[1] + y, v[2] + z))
def SC(faces, s, sy=None, sz=None):
    sy = s if sy is None else sy; sz = s if sz is None else sz
    return _map(faces, lambda v: (v[0] * s, v[1] * sy, v[2] * sz))
def RX(faces, a):
    c, s = cos(a), sin(a); return _map(faces, lambda v: (v[0], v[1] * c - v[2] * s, v[1] * s + v[2] * c))
def RY(faces, a):
    c, s = cos(a), sin(a); return _map(faces, lambda v: (v[0] * c + v[2] * s, v[1], -v[0] * s + v[2] * c))
def RZ(faces, a):
    c, s = cos(a), sin(a); return _map(faces, lambda v: (v[0] * c - v[1] * s, v[0] * s + v[1] * c, v[2]))

def box(w, h, d, col, x=0, y=0, z=0, rx=0, ry=0, rz=0):
    a, b, c = w / 2, h / 2, d / 2
    P = [(-a, -b, -c), (a, -b, -c), (a, b, -c), (-a, b, -c), (-a, -b, c), (a, -b, c), (a, b, c), (-a, b, c)]
    idx = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (3, 2, 6, 7), (0, 3, 7, 4), (1, 2, 6, 5)]
    f = _aussen([[[P[i] for i in q], col] for q in idx], (0, 0, 0))
    if rz: f = RZ(f, rz)
    if rx: f = RX(f, rx)
    if ry: f = RY(f, ry)
    return _teil(T(f, x, y, z))

def zyl(ro, ru, h, seg, col, x=0, y=0, z=0, oben=None, unten=None, dreh=0, deckel=True):
    """Zylinder/Kegelstumpf wie THREE.CylinderGeometry: ro = Radius oben, ru = unten."""
    f = []
    ring = lambda r, yy: [(r * cos(dreh + i * 2 * PI / seg), yy, r * sin(dreh + i * 2 * PI / seg)) for i in range(seg)]
    o, u = ring(ro, h / 2), ring(ru, -h / 2)
    for i in range(seg):
        j = (i + 1) % seg
        if ro < 1e-6: f.append([[(0, h / 2, 0), u[i], u[j]], col])
        elif ru < 1e-6: f.append([[o[i], o[j], (0, -h / 2, 0)], col])
        else: f.append([[o[i], o[j], u[j], u[i]], col])
    f = _aussen(f, (0, 0, 0))
    if deckel:
        if ro > 1e-6: f += _aussen([[o, col if oben is None else oben]], (0, 0, 0))
        if ru > 1e-6: f += _aussen([[u, col if unten is None else unten]], (0, 0, 0))
    return _teil(T(f, x, y, z))

def kegel(r, h, seg, col, x=0, y=0, z=0, dreh=0): return zyl(0, r, h, seg, col, x, y, z, dreh=dreh)

def platte(pts, col, y=0.0):
    """Flaches Vieleck, das nach oben zeigt."""
    vs = [(p[0], y, p[1]) for p in pts]
    if normale(vs)[1] < 0: vs = vs[::-1]
    return [[vs, col]]

def beidseitig(vs, col): return [[vs, col], [vs[::-1], col]]

def oval(rx, rz, seg, x=0, z=0, dreh=0):
    return [(x + rx * cos(dreh + i * 2 * PI / seg), z + rz * sin(dreh + i * 2 * PI / seg)) for i in range(seg)]

# ---------- Kamera und Zeichnen ----------
class Kamera:
    def __init__(s, cx, cy, S, neig=24, D=26, licht=(-.45, .8, .55), amb=.66, dif=.44):
        s.cx, s.cy, s.S, s.D = cx, cy, S, D
        s.sn, s.cs = sin(math.radians(neig)), cos(math.radians(neig))
        l = math.sqrt(sum(v * v for v in licht)); s.licht = tuple(v / l for v in licht)
        s.amb, s.dif = amb, dif
        s.pos = (0, D * s.sn, D * s.cs)

    def tiefe(s, p): return p[1] * s.sn + p[2] * s.cs
    def punkt(s, p):
        k = s.D / (s.D - s.tiefe(p))
        return s.cx + s.S * p[0] * k, s.cy - s.S * (p[1] * s.cs - p[2] * s.sn) * k

STELLEN = 1   # Nachkommastellen der Koordinaten

def _z(v):
    t = ('%.*f' % (STELLEN, v)).rstrip('0').rstrip('.') if STELLEN else '%d' % round(v)
    return '0' if t in ('-0', '') else t

def _pfad(pts):
    r = [(round(x, STELLEN), round(y, STELLEN)) for x, y in pts]
    d = 'M' + _z(r[0][0]) + ' ' + _z(r[0][1]) + 'l'
    teile = []
    for i in range(1, len(r)):
        teile.append(_z(r[i][0] - r[i - 1][0])); teile.append(_z(r[i][1] - r[i - 1][1]))
    s = ''
    for t in teile: s += t if (not s or t.startswith('-')) else ' ' + t
    return d + s + 'z'

def _farbe(col, i):
    r, g, b = (col >> 16) & 255, (col >> 8) & 255, col & 255
    return '#%02x%02x%02x' % tuple(max(0, min(255, int(c * i + .5))) for c in (r, g, b))

MINFLAECHE = 1.0   # kleinere Flaechen (in Pixeln) werden weggelassen

def zeichne(faces, kam, sortieren=True, keulen=True):
    """Liefert [(Tiefe, '<path .../>')] fuer eine Flaechenliste (bereits gedreht)."""
    out = []
    teile = {}
    for f in faces:
        if len(f) < 3: f.append((1, _neu()))
        teile.setdefault(f[2], []).extend(f[0])
    teiltiefe = {k: kam.tiefe(mitte(v)) for k, v in teile.items()}
    for vs, col, teil in faces:
        n, m = normale(vs), mitte(vs)
        if keulen and n[0] * (kam.pos[0] - m[0]) + n[1] * (kam.pos[1] - m[1]) + n[2] * (kam.pos[2] - m[2]) <= 0: continue
        pts = [kam.punkt(v) for v in vs]
        fl = abs(sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))) / 2
        if fl < MINFLAECHE: continue
        hell = kam.amb + kam.dif * max(0, n[0] * kam.licht[0] + n[1] * kam.licht[1] + n[2] * kam.licht[2])
        out.append(((teil[0], teiltiefe[teil], kam.tiefe(m)), '<path fill="%s" d="%s"/>' % (_farbe(col, hell), _pfad(pts))))
    if sortieren: out.sort(key=lambda t: t[0])
    return out

def bild(szene, gier, kam):
    """Ein Einzelbild. szene = Liste aus ('stapel'|'flach'|'dinge', [Flaechenlisten])."""
    s = []
    for art, listen in szene:
        gedreht = [RY(f, gier) for f in listen]
        if art == 'stapel':
            for f in gedreht: s += [p for _, p in zeichne(f, kam)]
        elif art == 'flach':
            for f in gedreht: s += [p for _, p in zeichne(f, kam, sortieren=False, keulen=False)]
        else:
            dinge = []
            for f in gedreht:
                pk = [v for fl in f for v in fl[0]]
                dinge.append((kam.tiefe(mitte(pk)), zeichne(f, kam)))
            dinge.sort(key=lambda t: t[0])
            for _, ps in dinge: s += [p for _, p in ps]
    return ''.join(s)

def film(bilder, fps=12, halten=0.0, klasse='f'):
    """Bilder nacheinander einblenden. halten = Sekunden, die das letzte Bild stehen bleibt."""
    n = len(bilder); dt = 1 / fps; dauer = n * dt + halten
    css = ('.%s{visibility:hidden;animation:%sk %.3fs steps(1,end) infinite}'
           '@keyframes %sk{0%%{visibility:visible}%.4f%%{visibility:hidden}}') % (klasse, klasse, dauer, klasse, 100 * dt / dauer)
    if halten:
        css += ('.%sl{visibility:hidden;animation:%skl %.3fs steps(1,end) infinite}'
                '@keyframes %skl{0%%{visibility:hidden}%.4f%%{visibility:visible}}') % (klasse, klasse, dauer, klasse, 100 * (n - 1) * dt / dauer)
    css += '@media (prefers-reduced-motion:reduce){.%s,.%sl{animation:none}.%s0{visibility:visible}}' % (klasse, klasse, klasse)
    g = []
    for i, b in enumerate(bilder):
        if halten and i == n - 1: g.append('<g class="%sl %s0">%s</g>' % (klasse, klasse, b))
        else: g.append('<g class="%s%s" style="animation-delay:%.3fs">%s</g>' % (klasse, (' %s0' % klasse) if (i == 0 and not halten) else '', i * dt, b))
    return css, ''.join(g)

# =====================================================================
#  Modelle (nach welt3d.js)
# =====================================================================
def m_dino(s=1.0, hut='kappe', wink=None):
    g = []
    g += box(.5, .54, .74, F.dino, 0, .58, 0, rx=-.16)
    g += box(.4, .36, .1, F.bauch, 0, .52, .36, rx=-.16)
    k = []
    k += box(.46, .4, .5, F.dino, 0, .1, .08) + box(.4, .2, .34, F.dino, 0, .02, .44)
    k += box(.36, .08, .46, F.dinoD, 0, -.1, .4)
    for sx in (-1, 1):
        k += box(.03, .13, .13, F.weiss, sx * .232, .17, .16) + box(.03, .07, .07, F.tinte, sx * .245, .17, .19)
    if hut == 'kappe': k += box(.5, .13, .54, F.rot, 0, .36, .08) + box(.42, .045, .24, F.rotD, 0, .31, .46)
    g += T(k, 0, .96, .32)
    g += T(RX(kegel(.2, .8, 5, F.dino), -1.4), 0, .56, -.7)
    for sx in (-1, 1):
        g += T(box(.17, .36, .22, F.dinoD, 0, -.18, 0) + box(.17, .08, .1, F.dinoD, 0, -.32, .14), sx * .16, .36, -.04)
    for sx in (-1, 1):
        arm = box(.09, .22, .09, F.dinoD, 0, -.09, 0)
        if wink is not None and sx == 1: arm = T(RZ(box(.11, .44, .11, F.dinoD, 0, .2, 0), wink), .06, 0, -.1)   # Arm nach oben, winkt
        else: arm = RX(arm, -.7)
        g += T(arm, sx * .28, .68, .26)
    for i in range(3): g += kegel(.07, .17, 4, F.bauch, 0, .9 - i * .08, -.1 - i * .19)
    return SC(g, s)

def m_tanne(s=1.0):
    return SC(zyl(.08, .1, .3, 5, F.holzD, 0, .15, 0) + kegel(.42, .7, 6, F.grasD, 0, .6, 0) + kegel(.32, .6, 6, 0x3aa85a, 0, 1.0, 0), s)

def m_palme(s=1.0):
    g = RZ(zyl(.06, .09, 1.1, 5, F.holz, 0, .55, 0), .12)
    for i in range(5):
        g += T(RY(RX(box(.16, .04, .62, F.grasD, 0, 0, .3), .45), i * PI * .4), -.13, 1.1, 0)
    return SC(g, s)

def m_kaktus(s=1.0):
    return SC(box(.16, .56, .16, F.grasD, 0, .28, 0) + box(.1, .1, .1, F.grasD, .13, .3, 0) + box(.1, .24, .1, F.grasD, .2, .4, 0)
              + box(.1, .1, .1, F.grasD, -.13, .22, 0) + box(.1, .18, .1, F.grasD, -.2, .3, 0), s)

def m_vulkan():
    g = zyl(.42, 1.25, 1.3, 8, 0x8f6f62, 0, .65, 0, oben=F.lava)
    g += zyl(.3, .3, .02, 8, 0xffd23f, 0, 1.31, 0, deckel=True)
    g += box(.22, .22, .22, F.rauch, .1, 1.75, 0, rx=.5, ry=.6) + box(.3, .3, .3, F.rauch, -.12, 2.15, .08, rx=.3, ry=.2)
    return g

def m_turm():
    """Dungeon Fighters: Verliesturm mit Zinnen, Dach und Fahne."""
    g = zyl(.5, .58, 1.5, 8, F.fels, 0, .75, 0)
    g += zyl(.62, .62, .16, 8, F.felsD, 0, 1.58, 0)
    for i in range(4): g += box(.2, .16, .2, F.fels, .5 * cos(i * PI / 2 + .4), 1.74, .5 * sin(i * PI / 2 + .4), ry=-(i * PI / 2 + .4))
    g += kegel(.46, .7, 8, F.lila, 0, 2.0, 0)
    g += box(.03, .4, .03, F.tinte, 0, 2.5, 0) + box(.24, .14, .02, F.rot, .13, 2.6, 0)
    g += box(.26, .42, .06, F.tinte, 0, .21, .57)
    return g

def m_brett():
    """2 Spieler Spiele: Spielbrett mit zwei Figuren und einem Wuerfel."""
    g = ebene(box(1.5, .14, 1.5, F.tinte, 0, .07, 0), -2)
    g += ebene(platte([(-.66, -.66), (.66, -.66), (.66, .66), (-.66, .66)], F.weiss, .143), -1)
    for i in range(3):
        for j in range(3):
            if (i + j) % 2 == 0: continue
            x, z = (i - 1) * .44, (j - 1) * .44
            g += ebene(platte([(x - .22, z - .22), (x + .22, z - .22), (x + .22, z + .22), (x - .22, z + .22)], F.gelb, .146), 0)
    for x, z, c in ((-.44, .44, F.rot), (.44, -.44, F.blau)):
        g += zyl(.06, .17, .42, 6, c, x, .36, z) + box(.2, .2, .2, c, x, .66, z, ry=.6)
    g += box(.26, .26, .26, F.weiss, .42, .29, .4, ry=.5)
    return g

def m_karten():
    """BlackJacKing: Filztisch, zwei Karten und Jetons."""
    g = ebene(zyl(.95, .95, .12, 10, F.filz, 0, .06, 0, oben=0x26a366), 0)
    def karte(col):
        k = box(.56, .8, .05, F.weiss, 0, .4, 0)
        raute = [(0, .58, 0), (.14, .4, 0), (0, .22, 0), (-.14, .4, 0)]
        k += [[[(x, y, .03) for x, y, _ in raute], col], [[(x, y, -.03) for x, y, _ in raute][::-1], col]]
        return k
    g += T(RY(RX(karte(F.rot), -.22), .35), -.22, .12, -.05)
    g += T(RY(RX(karte(F.tinte), -.22), -.3), .3, .12, .12)
    g += zyl(.17, .17, .22, 8, F.rot, -.45, .23, .55, oben=F.weiss) + zyl(.17, .17, .14, 8, F.gold, -.05, .19, .68, oben=F.weiss)
    g += zyl(.17, .17, .08, 8, F.blau, .5, .16, -.55, oben=F.weiss)
    return g

def m_boot():
    g = box(.9, .2, .4, F.holz, 0, .1, 0) + box(.24, .12, .3, F.holzD, .5, .14, 0) + box(.24, .12, .3, F.holzD, -.5, .14, 0)
    g += box(.05, .9, .05, F.holzD, 0, .6, 0)
    g += beidseitig([(.04, 1.02, 0), (.04, .32, 0), (.5, .32, 0)], F.weiss)
    g += beidseitig([(-.04, .95, 0), (-.04, .32, 0), (-.36, .32, 0)], F.rot)
    return g

def m_hochhaus():
    """Spider-Rex: Hochhaus mit leuchtenden Fenstern."""
    g = box(.74, 1.9, .74, F.nachtblau, 0, .95, 0) + box(.5, .16, .5, F.tinte, 0, 1.98, 0)
    for r in range(3):
        for sp in (-1, 1):
            y, o = .4 + r * .5, sp * .17
            g += [[[(o - .09, y, .375), (o + .09, y, .375), (o + .09, y + .3, .375), (o - .09, y + .3, .375)], F.gelb]]
            g += [[[(o + .09, y, -.375), (o - .09, y, -.375), (o - .09, y + .3, -.375), (o + .09, y + .3, -.375)], F.gelb]]
            g += [[[(.375, y, o + .09), (.375, y, o - .09), (.375, y + .3, o - .09), (.375, y + .3, o + .09)], F.gelb]]
            g += [[[(-.375, y, o - .09), (-.375, y, o + .09), (-.375, y + .3, o + .09), (-.375, y + .3, o - .09)], F.gelb]]
    return g

def m_truhe():
    return box(.5, .26, .34, F.holz, 0, .13, 0) + box(.54, .12, .38, F.holzD, 0, .32, 0) + box(.1, .12, .04, F.gold, 0, .26, .18)

def m_stein(r, col=F.fels):
    return box(r * 1.5, r, r * 1.3, col, 0, r * .4, 0, rx=.3, ry=.7, rz=.2)

def m_schwert():
    g = box(.12, 1.25, .04, F.stahl, 0, 1.0, 0) + box(.5, .1, .1, F.gold, 0, .36, 0) + box(.1, .3, .1, F.holzD, 0, .18, 0)
    g += box(.16, .12, .12, F.gold, 0, .02, 0)
    return g

# =====================================================================
#  Die Insel
# =====================================================================
def insel_szene():
    R = 4.3
    stapel = [
        zyl(1.7, .35, 1.5, 9, F.erdeD, 0, -2.95, 0, dreh=.3),
        zyl(3.1, 1.7, 1.2, 10, 0x8f5d40, 0, -1.6, 0, dreh=.1),
        zyl(4.05, 3.1, .65, 10, F.erde, 0, -.675, 0),
        zyl(R, R, .35, 10, F.grasD, 0, -.175, 0, oben=F.gras),
    ]
    ort = lambda grad, r: (r * cos(math.radians(grad)), r * sin(math.radians(grad)))
    flach, dinge = [], []
    schatten = lambda x, z, r: flach.append(platte(oval(r, r, 8, x, z), 0x40a957, .012))
    def stelle(m, grad, r, dreh=0, sch=0):
        x, z = ort(grad, r)
        if sch: schatten(x, z, sch)
        dinge.append(T(RY(m, dreh), x, 0, z))

    # Teich mit Boot (Dinoangler)
    tx, tz = ort(270, 2.7)
    flach.append(platte(oval(1.45, 1.05, 10, tx, tz), F.sand, .012))
    flach.append(platte(oval(1.22, .84, 10, tx, tz), F.wasser, .02))
    flach.append(platte(oval(.7, .4, 8, tx - .2, tz + .1), 0x5cc4f0, .025))
    dinge.append(T(RY(m_boot(), .3), tx, .02, tz))
    # Sandplatz fuer Kaktus und Palme (Dino-Runner)
    sx, sz = ort(95, 3.1)
    flach.append(platte(oval(1.1, .8, 9, sx, sz), F.sand, .012))

    schatten(0, .2, 1.05)
    dinge.append(T(RY(m_dino(1.75), .5), 0, 0, .2))
    stelle(m_hochhaus(), 5, 3.0, .4, .75)
    stelle(m_brett(), 48, 2.75, .5)
    stelle(m_palme(1.15), 82, 3.25, .2)
    stelle(m_kaktus(1.2), 108, 3.2, .3)
    stelle(m_karten(), 145, 2.8, 2.4)
    stelle(m_tanne(1.15), 180, 3.5, 0, .5)
    stelle(m_tanne(.85), 193, 2.75, 1, .4)
    stelle(m_vulkan(), 222, 2.55, .2)
    stelle(m_truhe(), 250, 1.55, -.4, .4)
    stelle(m_turm(), 318, 2.85, -2.3, .8)
    stelle(m_tanne(1.0), 345, 3.75, 2, .45)
    stelle(m_stein(.34), 25, 1.9, 1, 0)
    stelle(m_stein(.26, F.felsD), 165, 1.7, 2, 0)
    return [('stapel', stapel), ('flach', flach), ('dinge', dinge)]

def wolke(x, y, s, klasse):
    return ('<g class="%s"><g transform="translate(%s %s) scale(%s)" fill="%s">'
            '<circle cx="0" cy="0" r="26"/><circle cx="30" cy="-12" r="32"/><circle cx="66" cy="0" r="24"/>'
            '<rect x="-26" y="-2" width="118" height="28" rx="14"/></g></g>') % (klasse, x, y, s, WEISS)

def svg(w, h, css, inhalt, titel):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="%s">'
            '<title>%s</title><style>%s</style>%s</svg>') % (w, h, w, h, esc(titel), esc(titel), css, inhalt)

def schreibe(name, text):
    with open(os.path.join(ZIEL, name), 'w', encoding='utf-8', newline='\n') as f: f.write(text)
    print('%-22s %7.1f kB' % (name, len(text.encode('utf-8')) / 1024))

# =====================================================================
#  hero.svg
# =====================================================================
def hero():
    global STELLEN, MINFLAECHE
    W, H, N = 1200, 600, 72
    kam = Kamera(905, 318, 51)
    szene = insel_szene()
    STELLEN, MINFLAECHE = 0, 5.0   # ganze Pixel und keine Kruemel: haelt die Datei klein
    fcss, frames = film([bild(szene, i * 2 * PI / N, kam) for i in range(N)], fps=9)
    STELLEN, MINFLAECHE = 1, 1.0
    css = fcss + (
        '.bob{animation:bob 5s ease-in-out infinite alternate}@keyframes bob{from{transform:translateY(-9px)}to{transform:translateY(9px)}}'
        '.sch{transform-origin:905px 566px;animation:sch 5s ease-in-out infinite alternate}@keyframes sch{from{transform:scale(.9);opacity:.13}to{transform:scale(1.06);opacity:.22}}'
        '.w1{animation:w 19s ease-in-out infinite alternate}.w2{animation:w 26s ease-in-out -8s infinite alternate-reverse}.w3{animation:w 31s ease-in-out -15s infinite alternate}'
        '@keyframes w{from{transform:translateX(-46px)}to{transform:translateX(46px)}}'
        '.g{transform-box:fill-box;transform-origin:50% 100%;animation:pop .7s cubic-bezier(.2,1.5,.4,1) both}'
        '@keyframes pop{from{opacity:0;transform:translateY(-46px) scale(.5) rotate(-12deg)}}'
        '.rein{animation:rein .8s cubic-bezier(.16,1,.3,1) both}@keyframes rein{from{opacity:0;transform:translateY(22px)}}'
        '.st{transform-box:fill-box;transform-origin:50% 50%;animation:st 3.2s ease-in-out infinite alternate}@keyframes st{from{transform:rotate(-13deg)}to{transform:rotate(-5deg) scale(1.05)}}'
        '.fu{transform-box:fill-box;transform-origin:50% 50%;animation:fu 2.4s ease-in-out infinite}@keyframes fu{0%,100%{transform:scale(.4);opacity:.2}50%{transform:scale(1);opacity:1}}'
        '.pf{animation:pf 1.2s ease-in-out infinite alternate}@keyframes pf{to{transform:translateX(7px)}}'
        '@media (prefers-reduced-motion:reduce){.bob,.sch,.w1,.w2,.w3,.g,.rein,.st,.fu,.pf{animation:none}}')
    o = ['<defs><clipPath id="c"><rect width="%d" height="%d" rx="44"/></clipPath></defs><g clip-path="url(#c)">' % (W, H)]
    o.append('<rect width="%d" height="%d" fill="%s"/>' % (W, H, SONNE))
    o.append('<circle cx="905" cy="318" r="292" fill="#ffd54a"/><circle cx="905" cy="318" r="214" fill="#ffe07a"/>')
    o.append('<circle cx="-40" cy="640" r="210" fill="#ffd54a"/>')
    o.append(wolke(640, 92, 1.0, 'w1') + wolke(1035, 138, .72, 'w2') + wolke(1010, 470, .6, 'w3'))
    stern = lambda x, y, r, d: '<path class="fu" style="animation-delay:%ss" fill="%s" d="M%s %sl%s %s %s %s %s %s %s %sz"/>' % (
        d, WEISS, x, y - r, _z(r * .28), _z(r * .72), _z(r * .72), _z(r * .28), _z(-r * .72), _z(r * .28), _z(-r * .28), _z(r * .72))
    star = lambda x, y, r, d: ('<g class="fu" style="animation-delay:%ss" fill="%s"><path d="M%s %sQ%s %s %s %sQ%s %s %s %sQ%s %s %s %sQ%s %s %s %sz"/></g>'
                               % (d, WEISS, x, y - r, x, y, x + r, y, x, y, x, y + r, x, y, x - r, y, x, y, x, y - r))
    o.append(star(690, 250, 15, 0) + star(1128, 300, 12, .8) + star(770, 500, 10, 1.5) + star(1090, 520, 14, .4))
    o.append('<ellipse class="sch" cx="905" cy="566" rx="150" ry="13" opacity=".18" fill="%s"/>' % TINTE)
    o.append('<g class="bob">%s</g>' % frames)

    # Name, Buchstabe fuer Buchstabe
    x0, i = 64, 0
    for text, breite, maxs, y in (('Lukas', 420, 150, 196), ('Mörtendorfer', 566, 150, 304)):
        for d in bagel(text, passend(text, breite, maxs), x0, y, einzeln=True):
            o.append('<path class="g" style="animation-delay:%.2fs" fill="%s" d="%s"/>' % (.1 + i * .05, TINTE, d)); i += 1
    o.append('<g class="rein" style="animation-delay:1s" font-family="%s" font-size="23" fill="%s">' % (SANS, TINTE))
    o.append('<text x="66" y="362"><tspan font-weight="700">19</tspan> · computer science student at <tspan font-weight="700">HTL Leonding</tspan></text>')
    o.append('<text x="66" y="394">Everything I’ve built stands on this island.</text></g>')
    # Knopf
    kt = 'Visit the island'
    kb = bagel_breite(kt, 27)
    o.append('<g class="rein" style="animation-delay:1.25s"><rect x="64" y="440" width="%.0f" height="66" rx="33" fill="%s"/>' % (kb + 104, ROT_D))
    o.append('<rect x="64" y="434" width="%.0f" height="66" rx="33" fill="%s"/>' % (kb + 104, ROT))
    o.append('<path fill="#fff" d="%s"/>' % bagel(kt, 27, 96, 477))
    o.append('<path class="pf" fill="#fff" d="M%.0f 456l18 11-18 11z"/></g>' % (96 + kb + 16))
    o.append('<text class="rein" style="animation-delay:1.5s" x="66" y="548" font-family="%s" font-size="16" font-weight="600" fill="%s" opacity=".75">On the real one you can spin it and tap a model to play.</text>' % (SANS, TINTE))
    # Sticker
    o.append('<g class="st"><circle cx="672" cy="398" r="62" fill="%s"/><circle cx="672" cy="392" r="62" fill="%s"/>' % (ROT_D, ROT))
    o.append('<path fill="#fff" d="%s"/><path fill="%s" d="%s"/></g>' % (bagel(str(SPIELE), 62, 672, 404, 'middle'), SONNE, bagel('games', 21, 672, 430, 'middle')))
    o.append('</g>')
    schreibe('hero.svg', svg(W, H, css, ''.join(o), 'Lukas Mörtendorfer: a rotating 3D island carrying every game and app he has built'))

# =====================================================================
#  Karten fuer die drei grossen Projekte
# =====================================================================
def karte(datei, titel, art, knopf, farbe, farbe2, modell, S, cy, neig=22):
    W, H, N = 400, 330, 60
    kam = Kamera(200, cy, S, neig=neig, D=14)
    fcss, frames = film([bild([('dinge', [modell])], i * 2 * PI / N, kam) for i in range(N)], fps=12)
    css = fcss + ('.bob{animation:bob 3s ease-in-out infinite alternate}@keyframes bob{from{transform:translateY(-4px)}to{transform:translateY(4px)}}'
                  '.pf{animation:pf 1.2s ease-in-out infinite alternate}@keyframes pf{to{transform:translateX(5px)}}'
                  '@media (prefers-reduced-motion:reduce){.bob,.pf{animation:none}}')
    o = ['<defs><clipPath id="c"><rect x="4" y="4" width="392" height="314" rx="30"/></clipPath></defs>']
    o.append('<rect x="4" y="12" width="392" height="314" rx="30" fill="%s"/>' % TINTE)
    o.append('<g clip-path="url(#c)"><rect width="400" height="330" fill="%s"/>' % farbe)
    o.append('<circle cx="200" cy="120" r="118" fill="%s"/><ellipse cx="200" cy="168" rx="92" ry="12" fill="%s" opacity=".22"/>' % (farbe2, NACHT))
    o.append('<g class="bob">%s</g><rect y="200" width="400" height="130" fill="%s"/></g>' % (frames, WEISS))
    o.append('<rect x="4" y="4" width="392" height="314" rx="30" fill="none" stroke="%s" stroke-width="5"/>' % TINTE)
    o.append('<path fill="%s" d="%s"/>' % (TINTE, bagel(titel, passend(titel, 250, 31), 26, 244)))
    o.append('<text x="27" y="272" font-family="%s" font-size="16.5" font-weight="600" fill="%s">%s</text>' % (SANS, TINTE2, esc(art)))
    kb = bagel_breite(knopf, 19)
    x = 374 - kb - 50
    o.append('<rect x="%.0f" y="279" width="%.0f" height="30" rx="15" fill="%s"/>' % (x, kb + 50, ROT))
    o.append('<path fill="#fff" d="%s"/><path class="pf" fill="#fff" d="M%.0f 287l12 7-12 7z"/>' % (bagel(knopf, 19, x + 15, 301), x + kb + 22))
    schreibe(datei, svg(W, H, css, ''.join(o), '%s: %s' % (titel, art)))

def karten():
    karte('app-2player.svg', '2-Player Games', '21 games for two · web app', 'Play', BLAU, '#3a78e4', T(m_brett(), 0, -.3, 0), 74, 150)
    karte('app-blackjacking.svg', 'BlackJacKing', 'Card counting trainer', 'Train', '#1f8a55', '#2aa468', T(m_karten(), 0, -.35, 0), 84, 152)
    df = m_turm() + T(RZ(m_schwert(), -.2), .95, 0, .35) + T(m_stein(.3), -.85, 0, .4)
    karte('app-dungeon.svg', 'Dungeon Fighters', 'Dungeon game · online', 'Play', '#6846ad', '#8a63d2', T(df, 0, -1.25, 0), 50, 128)

# =====================================================================
#  secret-map.svg: die geheimen Eingaenge zwischen den Dino-Spielen
# =====================================================================
def geheimkarte():
    W, H = 1200, 600
    css = ('.weg{fill:none;stroke:' + SONNE + ';stroke-width:5;stroke-linecap:round;stroke-dasharray:1 15;animation:weg 1.1s linear infinite}'
           '@keyframes weg{to{stroke-dashoffset:-16}}'
           '.kn{transform-box:fill-box;transform-origin:50% 50%;animation:kn 3s ease-in-out infinite alternate}@keyframes kn{from{transform:translateY(-3px)}to{transform:translateY(3px)}}'
           '.puls{transform-box:fill-box;transform-origin:50% 50%;animation:puls 1.8s ease-out infinite}@keyframes puls{from{transform:scale(1);opacity:.7}to{transform:scale(1.5);opacity:0}}'
           '.fu{animation:fu 2.6s ease-in-out infinite}@keyframes fu{0%,100%{opacity:.15}50%{opacity:.9}}'
           '@media (prefers-reduced-motion:reduce){.weg,.kn,.puls,.fu{animation:none}}')
    o = ['<rect width="%d" height="%d" rx="44" fill="%s"/>' % (W, H, NACHT)]
    import random
    rnd = random.Random(7)
    for _ in range(46):
        o.append('<circle class="fu" style="animation-delay:-%.1fs" cx="%d" cy="%d" r="%.1f" fill="#fff"/>' % (rnd.random() * 3, rnd.randint(20, W - 20), rnd.randint(20, H - 20), rnd.choice((1.2, 1.6, 2.2))))
    o.append('<path fill="%s" d="%s"/>' % (SONNE, bagel('Secret entrances', 50, 60, 92)))
    o.append('<text x="62" y="128" font-family="%s" font-size="20" fill="#c9cbe6">Every dino game hides a door to the next one. Here is where they are.</text>' % SANS)

    knoten = {  # name: (x, y, Farbe, Textfarbe, Unterzeile)
        'Dino Runner': (150, 372, SONNE, TINTE, 'start here'),
        'Dino Angler': (600, 222, '#36b1e6', TINTE, 'fishing game'),
        'Spider-Rex': (600, 372, ROT, '#fff', '3D game · three.js'),
        'Dino Toss': (600, 522, '#4cb963', TINTE, 'throwing game'),
        'Captain Rexbeard': (1050, 222, '#c08a55', TINTE, 'pirate game'),
        'Mampfosaurus': (1050, 522, '#8a63d2', '#fff', 'eating game'),
    }
    KB, KH = 220, 82
    wege = [('Dino Runner', 'Dino Angler', 'jump into the boat'), ('Dino Runner', 'Spider-Rex', 'grab the spider thread'),
            ('Dino Runner', 'Dino Toss', 'don’t jump over the mouth'), ('Dino Angler', 'Captain Rexbeard', 'fish up the chest'),
            ('Dino Toss', 'Mampfosaurus', 'fly 1000 m high')]
    for a, b, text in wege:
        ax, ay = knoten[a][0] + KB / 2, knoten[a][1]
        bx, by = knoten[b][0] - KB / 2, knoten[b][1]
        mx = (ax + bx) / 2
        o.append('<path class="weg" d="M%.0f %.0fC%.0f %.0f %.0f %.0f %.0f %.0f"/>' % (ax, ay, mx, ay, mx, by, bx - 14, by))
        o.append('<path fill="%s" d="M%.0f %.0fl-16-10v20z"/>' % (SONNE, bx - 2, by))
        ly = (ay + by) / 2
        tb = len(text) * 8.3 + 28
        o.append('<rect x="%.0f" y="%.0f" width="%.0f" height="32" rx="16" fill="%s" stroke="%s" stroke-width="2"/>' % (mx - tb / 2, ly - 16, tb, TINTE, TINTE2))
        o.append('<text x="%.0f" y="%.0f" text-anchor="middle" font-family="%s" font-size="16" font-weight="600" fill="%s">%s</text>' % (mx, ly + 5.5, SANS, WEISS, esc(text)))
    for i, (name, (x, y, col, tcol, unter)) in enumerate(knoten.items()):
        o.append('<g class="kn" style="animation-delay:-%.1fs">' % (i * .7))
        if name == 'Dino Runner':
            o.append('<rect class="puls" x="%.0f" y="%.0f" width="%d" height="%d" rx="41" fill="none" stroke="%s" stroke-width="4"/>' % (x - KB / 2, y - KH / 2, KB, KH, SONNE))
        o.append('<rect x="%.0f" y="%.0f" width="%d" height="%d" rx="41" fill="#000" opacity=".45"/>' % (x - KB / 2, y - KH / 2 + 7, KB, KH))
        o.append('<rect x="%.0f" y="%.0f" width="%d" height="%d" rx="41" fill="%s"/>' % (x - KB / 2, y - KH / 2, KB, KH, col))
        o.append('<path fill="%s" d="%s"/>' % (tcol, bagel(name, passend(name, KB - 44, 28), x, y + 2, 'middle')))
        o.append('<text x="%.0f" y="%.0f" text-anchor="middle" font-family="%s" font-size="14.5" font-weight="600" fill="%s" opacity=".8">%s</text></g>' % (x, y + 24, SANS, tcol, esc(unter)))
    schreibe('secret-map.svg', svg(W, H, css, ''.join(o), 'Map of the secret entrances that connect the dino games'))

# =====================================================================
#  skills.svg: Tuerme, die in 3D hochwachsen
# =====================================================================
def skills():
    W, H = 1200, 560
    werte = [('Java', 85, F.gelb), ('JavaScript', 80, F.rot), ('HTML & CSS', 85, F.weiss), ('C#', 70, 0x4cb963), ('SQL', 75, F.lila), ('Python', 65, F.lava)]
    kam = Kamera(372, 424, 62, neig=20, D=70, amb=.6, dif=.5)
    gier, HMAX, AB = .42, 4.3, 1.42
    xs = [(i - 2.5) * AB for i in range(len(werte))]
    NW = 30
    bilder = []
    for k in range(NW):
        t = (k + 1) / NW
        e = 1 - (1 - t) ** 3
        dinge = []
        for (name, w, col), x in zip(werte, xs):
            verz = max(0.0, min(1.0, e * 1.35 - (x - xs[0]) / (xs[-1] - xs[0]) * .35))
            h = max(.04, w / 100 * HMAX * verz)
            dinge.append(box(.92, h, .92, col, x, h / 2, 0))
        bilder.append(bild([('flach', [platte([(xs[0] - 1, -.95), (xs[-1] + 1, -.95), (xs[-1] + 1, .95), (xs[0] - 1, .95)], 0x16449a, 0)]), ('dinge', dinge)], gier, kam))
    fcss, frames = film(bilder, fps=15, halten=7.0)
    dauer = NW / 15 + 7
    ein = 100 * (NW / 15) / dauer
    css = fcss + ('.zahl{animation:zahl %.3fs linear infinite}@keyframes zahl{0%%,%.2f%%{opacity:0;transform:translateY(10px)}%.2f%%,97%%{opacity:1;transform:none}100%%{opacity:0}}'
                  '@media (prefers-reduced-motion:reduce){.zahl{animation:none}}') % (dauer, ein - 3, ein + 2)
    o = ['<rect width="%d" height="%d" rx="44" fill="%s"/>' % (W, H, BLAU)]
    o.append('<circle cx="1130" cy="60" r="190" fill="%s"/><circle cx="60" cy="560" r="150" fill="%s"/>' % ('#2a6ce0', '#2a6ce0'))
    o.append('<path fill="%s" d="%s"/>' % (WEISS, bagel('Stacked up', 50, 60, 92)))
    o.append('<text x="62" y="128" font-family="%s" font-size="20" fill="#d5e2fb">How confident I am in each language, in percent.</text>' % SANS)
    o.append(frames)
    rot = lambda p: (p[0] * cos(gier) + p[2] * sin(gier), p[1], -p[0] * sin(gier) + p[2] * cos(gier))
    for (name, w, col), x in zip(werte, xs):
        px, py = kam.punkt(rot((x, w / 100 * HMAX, 0)))
        o.append('<path class="zahl" fill="#fff" d="%s"/>' % bagel(str(w), 34, px, py - 30, 'middle'))
        bx, by = kam.punkt(rot((x, 0, .95)))
        o.append('<text x="%.0f" y="%.0f" text-anchor="middle" font-family="%s" font-size="17" font-weight="700" fill="#fff">%s</text>' % (bx + 4, by + 34, SANS, esc(name)))
    # Werkzeugkiste rechts
    o.append('<rect x="748" y="168" width="396" height="340" rx="30" fill="%s"/><rect x="748" y="160" width="396" height="340" rx="30" fill="%s"/>' % (BLAU_D, WEISS))
    o.append('<path fill="%s" d="%s"/>' % (TINTE, bagel('Also in the toolbox', 27, 776, 208)))
    chips = ['TypeScript', 'Node.js', 'C', 'three.js', 'PostgreSQL', 'MySQL', 'REST', 'Docker', 'Git', 'Linux', 'JDBC', 'Scrum', 'UML', 'TCP/IP', 'OOP']
    farben = [(SONNE, TINTE), (ROT, '#fff'), (BLAU, '#fff'), (TINTE, SONNE), ('#2f9e58', '#fff')]
    x, y = 776, 232
    for i, c in enumerate(chips):
        b = len(c) * 9.4 + 30
        if x + b > 1120: x, y = 776, y + 48
        bg, fg = farben[i % len(farben)]
        o.append('<rect x="%.0f" y="%d" width="%.0f" height="36" rx="18" fill="%s"/>' % (x, y, b, bg))
        o.append('<text x="%.0f" y="%d" text-anchor="middle" font-family="%s" font-size="16" font-weight="700" fill="%s">%s</text>' % (x + b / 2, y + 23.5, SANS, fg, esc(c)))
        x += b + 10
    schreibe('skills.svg', svg(W, H, css, ''.join(o), 'Skills: Java 85, JavaScript 80, HTML and CSS 85, C# 70, SQL 75, Python 65, plus TypeScript, Node.js, C, three.js, PostgreSQL, MySQL, REST, Docker, Git, Linux'))

# =====================================================================
#  contact.svg: der winkende Dino
# =====================================================================
def kontakt():
    W, H, N = 1200, 400, 48
    kam = Kamera(965, 338, 150, neig=12, D=16)
    bilder = []
    for i in range(N):
        t = i / N * 2 * PI
        m = m_dino(1.0, wink=-.95 + .45 * sin(t * 3))
        bilder.append(bild([('flach', [platte(oval(1.05, 1.05, 12), 0xb82a1a, 0)]), ('dinge', [m])], -.38 + .3 * sin(t), kam))
    fcss, frames = film(bilder, fps=12)
    css = fcss + ('.puls{transform-box:fill-box;transform-origin:50% 50%;animation:puls 1.6s ease-out infinite}@keyframes puls{from{transform:scale(1);opacity:.8}to{transform:scale(2.6);opacity:0}}'
                  '@media (prefers-reduced-motion:reduce){.puls{animation:none}}')
    o = ['<defs><clipPath id="c"><rect width="%d" height="%d" rx="44"/></clipPath></defs><g clip-path="url(#c)">' % (W, H)]
    o.append('<rect width="%d" height="%d" fill="%s"/><circle cx="960" cy="230" r="230" fill="#e04532"/><circle cx="80" cy="-40" r="170" fill="#e04532"/>' % (W, H, ROT))
    o.append(frames)
    o.append('<path fill="%s" d="%s"/>' % (WEISS, bagel('Let’s', 84, 62, 132)))
    o.append('<path fill="%s" d="%s"/>' % (SONNE, bagel('build something.', 84, 62, 216)))
    o.append('<text font-family="%s" font-size="22" fill="#fff"><tspan x="64" y="268">Got an internship, a project or just a question?</tspan><tspan x="64" dy="30">Write to me and I’ll get back to you quickly.</tspan></text>' % SANS)
    st = 'Open to internships & projects'
    o.append('<rect x="62" y="326" width="%.0f" height="42" rx="21" fill="%s"/>' % (len(st) * 9.3 + 62, TINTE))
    o.append('<circle class="puls" cx="86" cy="347" r="7" fill="#5ee08a"/><circle cx="86" cy="347" r="7" fill="#5ee08a"/>')
    o.append('<text x="104" y="353" font-family="%s" font-size="17" font-weight="700" fill="#fff">%s</text>' % (SANS, esc(st)))
    o.append('</g>')
    schreibe('contact.svg', svg(W, H, css, ''.join(o), 'Let’s build something. Open to internships and projects.'))

def knopf(datei, text, bg, kante, fg):
    b = bagel_breite(text, 24) + 64
    o = ('<rect x="0" y="6" width="%.0f" height="52" rx="26" fill="%s"/><rect width="%.0f" height="52" rx="26" fill="%s"/><path fill="%s" d="%s"/>'
         % (b, kante, b, bg, fg, bagel(text, 24, 32, 34.5)))
    schreibe(datei, svg(int(b + .99), 58, '', o, text))

if __name__ == '__main__':
    hero(); karten(); geheimkarte(); skills(); kontakt()
    knopf('btn-website.svg', 'Website', SONNE, '#d99a00', TINTE)
    knopf('btn-mail.svg', 'Send an email', TINTE, '#3b3f6b', SONNE)
