"""Write the Got a Talent troupe "Duck Choir": eight ducks sing Beethoven's Ode to Joy (public domain)
in four parts, sitting and rising in a wave, heads swaying in mirror, a quack to end.

    uv run --frozen --group workshop python scripts/talent_choir.py      # -> got_a_talent/choir.json

Every duck is this entry's own policy ("self"). Each duck's commands stay inside what training saw
(see got_a_talent/AGENTS.md): sit flag 0 or 1, postures held at least 3.5 s, head targets at least
2 s apart and within 40 % of the trained ranges.
"""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "src/microduck_challenges/got_a_talent/choir.json"
BEAT = 0.5          # 120 bpm
SONG_T0 = 2.0       # the choir starts singing
DURATION = 20.0

# Ode to Joy, 8 bars of 4 beats: (note, beats). The melody, then three parts on the I-V harmony.
SOPRANO = [("E5", 1), ("E5", 1), ("F5", 1), ("G5", 1), ("G5", 1), ("F5", 1), ("E5", 1), ("D5", 1),
           ("C5", 1), ("C5", 1), ("D5", 1), ("E5", 1), ("E5", 1.5), ("D5", 0.5), ("D5", 2),
           ("E5", 1), ("E5", 1), ("F5", 1), ("G5", 1), ("G5", 1), ("F5", 1), ("E5", 1), ("D5", 1),
           ("C5", 1), ("C5", 1), ("D5", 1), ("E5", 1), ("D5", 1.5), ("C5", 0.5), ("C5", 2)]
ALTO = [("C5", 4), ("B4", 4), ("G4", 4), ("B4", 4), ("C5", 4), ("B4", 4), ("G4", 4), ("B4", 2), ("G4", 2)]
TENOR = [("G4", 4), ("G4", 4), ("E4", 4), ("G4", 4), ("G4", 4), ("G4", 4), ("E4", 4), ("F4", 2), ("E4", 2)]
BASS = [("C4", 4), ("G3", 4), ("C4", 4), ("G3", 4), ("C4", 4), ("G3", 4), ("C4", 4), ("G3", 2), ("C3", 2)]
PARTS = {"S": SOPRANO, "A": ALTO, "T": TENOR, "B": BASS}
VOICE = {"S": 0.85, "A": 0.65, "T": 0.4, "B": 0.15}   # pitch knob
VOWEL = {"S": "ah", "A": "oh", "T": "oh", "B": "oo"}

# Two rows facing the audience (+x). Front: A S S A, back: B T T B. y left to right.
SEATS = [("A", 0.35, -1.05), ("S", 0.35, -0.35), ("S", 0.35, 0.35), ("A", 0.35, 1.05),
         ("B", -0.35, -1.05), ("T", -0.35, -0.35), ("T", -0.35, 0.35), ("B", -0.35, 1.05)]

WAVE = 0.2          # s between neighbours' sits, left to right
YAW, ROLL, NOD = 0.45, 0.10, 0.35


def song(part: str) -> list[dict]:
    t, notes = SONG_T0, []
    for i, (note, beats) in enumerate(PARTS[part]):
        dur = beats * BEAT
        last = i == len(PARTS[part]) - 1
        dyn = "f" if part == "S" else "mf"
        notes.append({"t": round(t, 3), "note": note, "for": round(dur * 0.92, 3),
                      "dynamic": "ff" if last else dyn, "vowel": VOWEL[part]})
        t += dur
    return notes


def keyframes(column: int, side: int) -> list[dict]:
    """side: -1 left half, +1 right half (heads sway in mirror, towards the centre first)."""
    w = column * WAVE
    sit = [(0.0, 0), (3.0 + w, 1), (7.0 + w, 0), (11.0 + w, 1), (15.0 + w, 0)]
    # Heads every 2 s, the same for all: sway in mirror, a nod with the last note, then look up.
    head = [(0.0, [0, 0, 0, 0])]
    for k, t in enumerate(range(2, 16, 2)):
        s = -side if k % 2 == 0 else side
        head.append((float(t), [0, 0, s * YAW, s * ROLL]))
    head += [(16.0, [0, NOD, 0, 0]), (18.0, [0, 0, 0, 0])]
    quack = [(19.0, [1, 0]), (19.4, [0, 0]), (19.6, [1, 0])]
    times = sorted({t for t, _ in sit} | {t for t, _ in head} | {t for t, _ in quack})

    def at(seq, t, default):
        cur = default
        for ts, v in seq:
            if ts <= t + 1e-9:
                cur = v
        return cur

    out = []
    for t in times:
        kf = {"t": round(t, 3), "twist": [at(sit, t, 0), 0, 0], "head": at(head, t, [0, 0, 0, 0])}
        trig = at(quack, t, [0, 0])
        if any(trig):
            kf["triggers"] = trig
        out.append(kf)
    return out


def main() -> None:
    ducks = []
    for part, x, y in SEATS:
        column = [-1.05, -0.35, 0.35, 1.05].index(y)
        side = -1 if y < 0 else 1
        ducks.append({
            "policy": "self",
            "start": {"x": x, "y": y, "yaw": 0},
            "keyframes": keyframes(column, side),
            "voice": {"pitch": VOICE[part], "vibrato": 0.5},
            "song": song(part),
        })
    OUT.write_text(json.dumps({"timeline_version": 2, "duration_s": DURATION, "ducks": ducks}, indent=1))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
