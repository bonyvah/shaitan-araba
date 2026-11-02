"""Product illustrations as standalone SVG files.

Every product gets a flat line drawing tinted with its `color`, so the
site needs no photos and the build stays reproducible.
"""

from html import escape

INK = "#1d232a"
METAL = "#9aa3ad"
SOFT = "#d7dce1"


def _svg(body: str, label: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 320" role="img" '
        f'aria-label="{escape(label)}">{body}</svg>\n'
    )


def _wheel(cx: float, cy: float, r: float, tire: float) -> str:
    spokes = "".join(
        f'<line x1="{cx}" y1="{cy}" x2="{cx + (r - tire) * c:.1f}" y2="{cy + (r - tire) * s:.1f}"/>'
        for c, s in [(1, 0), (0.5, 0.866), (-0.5, 0.866), (-1, 0), (-0.5, -0.866), (0.5, -0.866),
                     (0.866, 0.5), (0, 1), (-0.866, 0.5), (-0.866, -0.5), (0, -1), (0.866, -0.5)]
    )
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{INK}" stroke-width="{tire}"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r - tire / 2 - 3}" fill="none" stroke="{METAL}" stroke-width="3"/>'
        f'<g stroke="{METAL}" stroke-width="1.2">{spokes}</g>'
        f'<circle cx="{cx}" cy="{cy}" r="7" fill="{INK}"/>'
    )


def bike(kind: str, color: str, label: str) -> str:
    small = kind in ("kids", "folding")
    r = 56 if small else 76
    tire = {"mtb": 11, "road": 5, "city": 7, "kids": 9, "ebike": 9, "folding": 7}[kind]
    rear, front = (140, 236 - (76 - r)), (342, 236 - (76 - r))
    ry = rear[1]
    bb = (232, ry + 4)
    seat = (210, ry - (112 if small else 122))
    head_top = (318, ry - (118 if small else 128))
    head_bot = (326, ry - (86 if small else 92))

    tubes = []
    t = 9 if kind in ("mtb", "ebike") else 7
    tubes.append((rear, bb))  # chainstay
    tubes.append((rear, seat))  # seatstay
    tubes.append((bb, seat))  # seat tube
    tubes.append((bb, head_bot))  # down tube
    if kind != "city":
        tubes.append((seat, head_top))  # top tube
    frame = "".join(
        f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}"/>' for a, b in tubes
    )
    if kind == "city":
        # step-through: a low curved tube instead of a top tube
        frame += (
            f'<path d="M{bb[0] - 6} {bb[1] - 30} Q {bb[0] + 30} {bb[1] - 70} {head_top[0] + 2} {head_top[1] + 12}" fill="none"/>'
        )
    frame += f'<line x1="{head_top[0]}" y1="{head_top[1]}" x2="{head_bot[0]}" y2="{head_bot[1]}" stroke-width="{t + 3}"/>'

    fork_w = 8 if kind in ("mtb", "ebike") else 5
    fork = f'<line x1="{head_bot[0]}" y1="{head_bot[1]}" x2="{front[0]}" y2="{front[1]}" stroke="{INK if kind == "mtb" else color}" stroke-width="{fork_w}" stroke-linecap="round"/>'
    if kind == "mtb":
        fork += f'<line x1="{head_bot[0]}" y1="{head_bot[1]}" x2="{head_bot[0] + 7}" y2="{head_bot[1] + 46}" stroke="{METAL}" stroke-width="11" stroke-linecap="round"/>'

    sx, sy = seat
    post = f'<line x1="{sx}" y1="{sy}" x2="{sx - 6}" y2="{sy - 18}" stroke="{METAL}" stroke-width="6"/>'
    saddle = f'<path d="M{sx - 34} {sy - 22} Q {sx - 6} {sy - 34} {sx + 22} {sy - 22} L {sx + 14} {sy - 16} L {sx - 30} {sy - 16} Z" fill="{INK}"/>'

    hx, hy = head_top
    stem_top = (hx - 2, hy - 18)
    stem = f'<line x1="{hx}" y1="{hy}" x2="{stem_top[0]}" y2="{stem_top[1]}" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'
    if kind == "road":
        bar = f'<path d="M{stem_top[0]} {stem_top[1]} L {stem_top[0] + 22} {stem_top[1]} Q {stem_top[0] + 40} {stem_top[1] + 4} {stem_top[0] + 34} {stem_top[1] + 24} Q {stem_top[0] + 28} {stem_top[1] + 36} {stem_top[0] + 14} {stem_top[1] + 32}" fill="none" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>'
    elif kind == "city":
        bar = f'<path d="M{stem_top[0]} {stem_top[1]} Q {stem_top[0] - 6} {stem_top[1] - 12} {stem_top[0] - 30} {stem_top[1] - 8}" fill="none" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>'
    else:
        bar = f'<line x1="{stem_top[0] - 6}" y1="{stem_top[1]}" x2="{stem_top[0] + 18}" y2="{stem_top[1] - 2}" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'

    bx, by = bb
    drive = (
        f'<circle cx="{bx}" cy="{by}" r="17" fill="none" stroke="{INK}" stroke-width="4"/>'
        f'<line x1="{bx}" y1="{by}" x2="{bx + 14}" y2="{by + 26}" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>'
        f'<rect x="{bx + 4}" y="{by + 24}" width="22" height="6" rx="3" fill="{INK}"/>'
        f'<line x1="{bx}" y1="{by - 17}" x2="{rear[0]}" y2="{rear[1] - 8}" stroke="{METAL}" stroke-width="2"/>'
        f'<line x1="{bx}" y1="{by + 17}" x2="{rear[0]}" y2="{rear[1] + 8}" stroke="{METAL}" stroke-width="2"/>'
    )

    extras = ""
    if kind == "ebike":
        # battery along the down tube
        extras += (
            f'<g transform="rotate(-38 {bx + 46} {by - 34})"><rect x="{bx + 6}" y="{by - 46}" width="84" height="22" rx="6" fill="{INK}"/>'
            f'<rect x="{bx + 14}" y="{by - 40}" width="10" height="10" rx="2" fill="#4cd964"/></g>'
        )
    if kind == "city":
        extras += (
            f'<path d="M{rear[0] - r + 6} {ry - 8} A {r + 4} {r + 4} 0 0 1 {rear[0] + 40} {ry - r - 2}" fill="none" stroke="{color}" stroke-width="5" stroke-linecap="round"/>'
            f'<path d="M{front[0] - 40} {ry - r - 2} A {r + 4} {r + 4} 0 0 1 {front[0] + r - 6} {ry - 8}" fill="none" stroke="{color}" stroke-width="5" stroke-linecap="round"/>'
            f'<line x1="{seat[0] - 10}" y1="{seat[1] + 10}" x2="{rear[0] - 20}" y2="{seat[1] + 18}" stroke="{INK}" stroke-width="5"/>'
            f'<path d="M{stem_top[0] + 6} {stem_top[1] + 8} h 44 l -6 34 h -32 Z" fill="none" stroke="{METAL}" stroke-width="4" stroke-linejoin="round"/>'
        )
    if kind == "folding":
        mid = ((seat[0] + head_top[0]) / 2, (seat[1] + head_top[1]) / 2)
        extras += f'<circle cx="{mid[0]}" cy="{mid[1]}" r="9" fill="{INK}"/><circle cx="{mid[0]}" cy="{mid[1]}" r="3" fill="{METAL}"/>'
    if kind == "kids" and "беговел" not in label.lower():
        extras += _wheel(rear[0] - 10, ry + r - 18, 16, 4).replace(METAL, SOFT)

    if kind == "kids" and "беговел" in label.lower():
        drive = ""

    body = (
        '<ellipse cx="240" cy="300" rx="190" ry="8" fill="#000" opacity=".06"/>'
        + _wheel(*rear, r, tire)
        + _wheel(*front, r, tire)
        + drive
        + f'<g stroke="{color}" stroke-width="{t}" stroke-linecap="round" fill="none">{frame}</g>'
        + fork
        + extras
        + post
        + saddle
        + stem
        + bar
    )
    return _svg(body, label)


def accessory(kind: str, color: str, label: str) -> str:
    shadow = '<ellipse cx="240" cy="292" rx="130" ry="8" fill="#000" opacity=".06"/>'
    shapes = {
        "helmet": (
            f'<path d="M110 220 Q 110 96 250 90 Q 372 92 378 210 Q 380 232 356 232 L 136 232 Q 110 232 110 220 Z" fill="{color}"/>'
            f'<path d="M150 228 Q 160 150 250 118 M210 230 Q 214 150 270 112 M270 230 Q 290 160 320 124 M330 228 Q 350 180 352 150" stroke="{INK}" stroke-opacity=".35" stroke-width="10" fill="none" stroke-linecap="round"/>'
            f'<path d="M120 232 L 368 232 Q 372 252 350 254 L 140 254 Q 116 252 120 232 Z" fill="{INK}"/>'
        ),
        "lock": (
            f'<path d="M168 190 L 168 120 A 72 72 0 0 1 312 120 L 312 190" fill="none" stroke="{METAL}" stroke-width="22" stroke-linecap="round"/>'
            f'<rect x="132" y="176" width="216" height="80" rx="18" fill="{color}"/>'
            f'<rect x="132" y="176" width="216" height="80" rx="18" fill="none" stroke="{INK}" stroke-width="4"/>'
            f'<circle cx="300" cy="216" r="12" fill="{INK}"/><rect x="296" y="214" width="8" height="18" rx="3" fill="{INK}"/>'
        ),
        "light": (
            f'<path d="M300 150 L 420 100 M300 170 L 430 170 M300 190 L 420 240" stroke="#f5c542" stroke-width="10" stroke-linecap="round" opacity=".7"/>'
            f'<rect x="120" y="128" width="190" height="84" rx="30" fill="{INK}"/>'
            f'<rect x="268" y="138" width="34" height="64" rx="14" fill="#fff6d5" stroke="{color}" stroke-width="6"/>'
            f'<rect x="150" y="212" width="40" height="40" rx="8" fill="{METAL}"/>'
            f'<circle cx="170" cy="170" r="10" fill="{color}"/>'
        ),
        "pump": (
            f'<rect x="216" y="70" width="48" height="190" rx="14" fill="{color}"/>'
            f'<line x1="240" y1="70" x2="240" y2="40" stroke="{METAL}" stroke-width="10"/>'
            f'<rect x="170" y="26" width="140" height="20" rx="10" fill="{INK}"/>'
            f'<rect x="150" y="256" width="180" height="18" rx="9" fill="{INK}"/>'
            f'<circle cx="240" cy="200" r="22" fill="#fff" stroke="{INK}" stroke-width="5"/>'
            f'<line x1="240" y1="200" x2="252" y2="188" stroke="{INK}" stroke-width="4"/>'
            f'<path d="M264 120 Q 340 130 330 220 Q 326 250 350 252" fill="none" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'
        ),
        "bag": (
            f'<path d="M110 120 L 370 120 Q 386 120 380 140 L 330 244 Q 324 256 310 256 L 170 256 Q 156 256 150 244 L 100 140 Q 94 120 110 120 Z" fill="{color}"/>'
            f'<path d="M120 150 L 360 150" stroke="{INK}" stroke-width="5" stroke-dasharray="10 8"/>'
            f'<rect x="150" y="100" width="34" height="28" rx="6" fill="{INK}"/><rect x="296" y="100" width="34" height="28" rx="6" fill="{INK}"/>'
            f'<rect x="210" y="180" width="60" height="10" rx="5" fill="#fff" opacity=".6"/>'
        ),
        "bottle": (
            f'<rect x="196" y="78" width="88" height="190" rx="30" fill="{color}"/>'
            f'<rect x="214" y="48" width="52" height="36" rx="10" fill="{INK}"/>'
            f'<rect x="230" y="28" width="20" height="24" rx="6" fill="{METAL}"/>'
            f'<path d="M196 150 h 88 M196 190 h 88" stroke="#fff" stroke-opacity=".45" stroke-width="8"/>'
            f'<path d="M180 120 L 180 250 Q 180 270 200 270 L 280 270 Q 300 270 300 250 L 300 120" fill="none" stroke="{METAL}" stroke-width="7"/>'
        ),
        "tool": (
            f'<g stroke-linecap="round"><line x1="240" y1="200" x2="150" y2="90" stroke="{METAL}" stroke-width="16"/>'
            f'<line x1="240" y1="200" x2="200" y2="70" stroke="{METAL}" stroke-width="14"/>'
            f'<line x1="240" y1="200" x2="260" y2="66" stroke="{METAL}" stroke-width="12"/>'
            f'<line x1="240" y1="200" x2="318" y2="80" stroke="{METAL}" stroke-width="10"/></g>'
            f'<rect x="130" y="176" width="220" height="70" rx="35" fill="{color}"/>'
            f'<rect x="130" y="176" width="220" height="70" rx="35" fill="none" stroke="{INK}" stroke-width="4"/>'
            f'<circle cx="166" cy="211" r="10" fill="{INK}"/><circle cx="314" cy="211" r="10" fill="{INK}"/>'
        ),
        "tire": (
            f'<circle cx="240" cy="160" r="112" fill="none" stroke="{INK}" stroke-width="28"/>'
            f'<circle cx="240" cy="160" r="112" fill="none" stroke="{color}" stroke-width="28" stroke-dasharray="6 14" opacity=".5"/>'
            f'<circle cx="240" cy="160" r="88" fill="none" stroke="{METAL}" stroke-width="4"/>'
        ),
        "gloves": (
            f'<path d="M170 270 L 160 160 Q 156 140 172 138 Q 186 138 188 156 L 192 112 Q 194 92 212 94 Q 228 96 226 116 L 228 100 Q 232 80 250 84 Q 266 88 262 108 L 264 110 Q 270 92 286 96 Q 300 102 296 122 L 290 190 L 306 166 Q 318 150 332 160 Q 342 170 332 186 L 290 262 Q 280 276 262 276 L 190 276 Q 172 276 170 270 Z" fill="{color}"/>'
            f'<path d="M180 236 L 290 236" stroke="{INK}" stroke-width="12"/>'
            f'<path d="M196 200 Q 240 186 280 200" stroke="{INK}" stroke-opacity=".3" stroke-width="8" fill="none" stroke-linecap="round"/>'
        ),
        "glasses": (
            f'<path d="M96 140 Q 100 120 130 120 L 220 124 Q 236 126 240 140 Q 244 126 260 124 L 350 120 Q 380 120 384 140 L 376 188 Q 370 214 340 212 L 280 206 Q 252 202 240 172 Q 228 202 200 206 L 140 212 Q 110 214 104 188 Z" fill="{color}" opacity=".85"/>'
            f'<path d="M96 140 L 60 150 M384 140 L 420 150" stroke="{INK}" stroke-width="8" stroke-linecap="round"/>'
            f'<path d="M96 140 Q 100 120 130 120 L 350 120 Q 380 120 384 140" fill="none" stroke="{INK}" stroke-width="8"/>'
        ),
    }
    return _svg(shadow + shapes[kind], label)


BIKE_KINDS = {"mtb", "road", "city", "kids", "ebike", "folding"}


def render(kind: str, color: str, label: str) -> str:
    return bike(kind, color, label) if kind in BIKE_KINDS else accessory(kind, color, label)
