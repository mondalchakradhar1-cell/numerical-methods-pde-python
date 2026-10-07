#!/usr/bin/env python3
"""Set the frame delay of a GIF in place, without re-encoding (frames stay bit-identical).

    python set_gif_delay.py <file.gif> <delay_ms> [last_frame_ms]
"""
import sys


def set_delay(path, ms, last_ms=None):
    """Every frame gets a graphic-control block with the delay; frames without one get a neutral block
    (no transparency, disposal unspecified: same rendering as before). Image data is untouched."""
    b = bytes(open(path, "rb").read())
    flags = b[10]
    i = 13 + (3 * 2 ** ((flags & 7) + 1) if flags & 0x80 else 0)
    out = bytearray(b[:i])
    frames = []                       # (index in out of the GCE delay bytes)
    pending = None
    while i < len(b):
        t = b[i]
        if t == 0x3B:
            out += b[i:]
            break
        j = i
        if t == 0x21:
            j += 2
            while b[j]:
                j += b[j] + 1
            j += 1
            if b[i + 1] == 0xF9:
                pending = len(out) + 4
            out += b[i:j]
        elif t == 0x2C:
            if pending is None:
                pending = len(out) + 4
                out += bytes([0x21, 0xF9, 0x04, 0x00, 0, 0, 0x00, 0x00])
            frames.append(pending); pending = None
            pf = b[i + 9]
            j += 10 + (3 * 2 ** ((pf & 7) + 1) if pf & 0x80 else 0) + 1
            while b[j]:
                j += b[j] + 1
            j += 1
            out += b[i:j]
        else:
            raise ValueError(f"bad block {t:#x} at {i}")
        i = j
    for k, q in enumerate(frames):
        cs = (last_ms if (last_ms and k == len(frames) - 1) else ms) // 10
        out[q:q + 2] = int(cs).to_bytes(2, "little")
    open(path, "wb").write(out)
    return len(frames)


if __name__ == "__main__":
    print(sys.argv[1], set_delay(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else None), "frames")
