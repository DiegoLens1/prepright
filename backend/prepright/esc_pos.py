"""
ESC/POS printer data to plain text converter.

Thermal receipt printers send ESC/POS commands (binary control codes)
mixed with printable text. This module strips all ESC/POS commands and
extracts only the visible text for the receipt parser.

Usage:
    text = esc_pos_to_bytes(raw_bytes)
    lines = esc_pos_to_lines(raw_bytes)
"""

from typing import List


# ── ESC/POS command tables ──────────────────────────────────────────────────
#
# Each entry maps a command byte (the byte *after* the ESC/GS/FS prefix) to the
# number of fixed parameter bytes that follow it. ESC/POS parameters are binary
# and routinely fall in the printable-ASCII range (e.g. ESC ! 0x30), so the only
# reliable way to strip a command is to know exactly how many bytes it consumes.
#
# Commands whose length is data-dependent (cut, barcodes, bit images,
# length-prefixed GS( functions, NUL-terminated lists) are handled separately in
# _command_length() and are not listed here.

# ESC <cmd> [params...]
_ESC_PARAMS = {
    0x20: 1,  # SP  set right-side character spacing
    0x21: 1,  # !   select print mode
    0x24: 2,  # $   set absolute print position
    0x25: 1,  # %   select/cancel user-defined character set
    0x2D: 1,  # -   turn underline on/off
    0x32: 0,  # 2   select default line spacing
    0x33: 1,  # 3   set line spacing
    0x3D: 1,  # =   select peripheral device
    0x40: 0,  # @   initialize printer
    0x44: -1,  # D  set horizontal tab positions (NUL-terminated) — see below
    0x45: 1,  # E   turn emphasized (bold) on/off
    0x47: 1,  # G   turn double-strike on/off
    0x4A: 1,  # J   print and feed paper n dots
    0x4B: 1,  # K   print and reverse feed n dots
    0x4D: 1,  # M   select character font
    0x52: 1,  # R   select international character set
    0x53: 0,  # S   select standard mode
    0x54: 1,  # T   select print direction (page mode)
    0x56: 1,  # V   turn 90° rotation on/off
    0x5C: 2,  # \   set relative print position
    0x61: 1,  # a   select justification
    0x63: 2,  # c   panel/paper sensor commands (c3/c4/c5 n)
    0x64: 1,  # d   print and feed n lines
    0x65: 1,  # e   print and reverse feed n lines
    0x70: 3,  # p   generate pulse (m t1 t2)
    0x72: 1,  # r   select print color
    0x74: 1,  # t   select character code table
    0x7B: 1,  # {   turn upside-down printing on/off
}

# GS <cmd> [params...]
_GS_PARAMS = {
    0x21: 1,  # !   select character size
    0x24: 2,  # $   set absolute vertical print position (page mode)
    0x28: -1,  # (  length-prefixed function groups (A/B/C/D/E/...) — see below
    0x2A: -1,  # *  define downloaded bit image — see below
    0x2F: 1,  # /   print downloaded bit image
    0x3A: 0,  # :   start/end macro definition
    0x40: 0,  # @   (rarely GS @) — treat as no-param
    0x42: 1,  # B   turn white/black reverse on/off
    0x48: 1,  # H   select HRI character print position
    0x49: 1,  # I   transmit printer ID
    0x4C: 2,  # L   set left margin
    0x50: 2,  # P   set horizontal/vertical motion units
    0x56: -1,  # V  select cut mode and cut paper — see below
    0x57: 2,  # W   set print area width
    0x61: 1,  # a   enable/disable Automatic Status Back
    0x66: 1,  # f   select HRI character font
    0x68: 1,  # h   set barcode height
    0x6B: -1,  # k  print barcode — see below
    0x72: 1,  # r   transmit status
    0x76: -1,  # v  print raster bit image (GS v 0) — see below
    0x77: 1,  # w   set barcode width
}

# FS <cmd> [params...]
_FS_PARAMS = {
    0x21: 1,  # !   select print mode for Kanji
    0x26: 0,  # &   select Kanji character mode
    0x2D: 1,  # -   turn underline on/off for Kanji
    0x2E: 0,  # .   cancel Kanji character mode
    0x43: 1,  # C   select Kanji code system
    0x53: 2,  # S   set Kanji character spacing
    0x57: 1,  # W   turn quadruple-size Kanji on/off
}


def _u16(data: bytes, i: int) -> int:
    """Read a little-endian 16-bit value at offset i (0 if out of range)."""
    if i + 1 >= len(data):
        return 0
    return data[i] + (data[i + 1] << 8)


def _command_length(data: bytes, i: int) -> int:
    """Return the total number of bytes occupied by the command starting at data[i].

    data[i] is an ESC (0x1B), GS (0x1D) or FS (0x1C) prefix. The returned length
    includes the prefix, the command byte and all of its parameter/data bytes, so
    the caller can skip the whole command with ``i += _command_length(data, i)``.
    """
    length = len(data)
    prefix = data[i]

    # A lone prefix at end of buffer.
    if i + 1 >= length:
        return 1

    cmd = data[i + 1]
    table = {0x1B: _ESC_PARAMS, 0x1D: _GS_PARAMS, 0x1C: _FS_PARAMS}[prefix]
    params = table.get(cmd)

    # Fixed-length command: prefix + cmd + params.
    if params is not None and params >= 0:
        return 2 + params

    # ── Variable-length / data-bearing commands ──────────────────────────────

    # ESC D ... NUL  — horizontal tab positions, terminated by 0x00.
    if prefix == 0x1B and cmd == 0x44:
        j = i + 2
        while j < length and data[j] != 0x00:
            j += 1
        return (j - i) + 1  # include the terminating NUL

    # GS V — cut paper. m is 1 byte; m in {65,66,103,104} adds a feed byte n.
    if prefix == 0x1D and cmd == 0x56:
        m = data[i + 2] if i + 2 < length else 0
        return 4 if m in (65, 66, 103, 104) else 3

    # GS ( <fn> pL pH [params x (pL+pH*256)] — length-prefixed function groups.
    if prefix == 0x1D and cmd == 0x28:
        n = _u16(data, i + 3)  # pL pH at i+3, i+4
        return 5 + n  # prefix, cmd, fn, pL, pH, then n data bytes

    # GS * x y [x*y*8] — define downloaded bit image.
    if prefix == 0x1D and cmd == 0x2A:
        x = data[i + 2] if i + 2 < length else 0
        y = data[i + 3] if i + 3 < length else 0
        return 4 + (x * y * 8)

    # GS v 0 m xL xH yL yH [data] — print raster bit image.
    if prefix == 0x1D and cmd == 0x76:
        # data[i+2] is the sub-function (0 / '0'); m, then dimensions follow.
        x_bytes = _u16(data, i + 4)  # xL xH (width in bytes)
        y_dots = _u16(data, i + 6)   # yL yH (height in dots)
        return 8 + (x_bytes * y_dots)

    # GS k — print barcode. Two forms:
    #   m in 0..6 : GS k m d1..dk NUL   (NUL-terminated data)
    #   m in 65.. : GS k m n  d1..dn    (length byte n)
    if prefix == 0x1D and cmd == 0x6B:
        m = data[i + 2] if i + 2 < length else 0
        if m >= 65:
            n = data[i + 3] if i + 3 < length else 0
            return 4 + n
        j = i + 3
        while j < length and data[j] != 0x00:
            j += 1
        return (j - i) + 1  # include terminating NUL

    # ESC * m nL nH [data] — select bit image mode.
    if prefix == 0x1B and cmd == 0x2A:
        m = data[i + 2] if i + 2 < length else 0
        k = _u16(data, i + 3)
        per_col = 3 if m in (32, 33) else 1
        return 5 + (k * per_col)

    # Unknown command: skip just the prefix + command byte. We can't know its
    # parameter length, but consuming the command byte avoids re-entering this
    # branch and is safer than emitting it as text.
    return 2


def esc_pos_to_text(data: bytes) -> str:
    """Convert raw ESC/POS bytes to plain text.

    Strips ESC/POS control commands using a command-length table (so command
    parameter bytes that happen to be printable, e.g. ``ESC ! 0x30``, are not
    leaked into the output) and returns only the visible text and newlines.

    Args:
        data: Raw ESC/POS bytes from the printer.

    Returns:
        Plain text with only visible characters and newlines.
    """
    if not data:
        return ""

    result: List[str] = []
    i = 0
    length = len(data)

    while i < length:
        byte = data[i]

        # ESC / GS / FS command sequences — skip the whole command.
        if byte in (0x1B, 0x1D, 0x1C):
            i += _command_length(data, i)

        # Printable ASCII (0x20-0x7E)
        elif 0x20 <= byte <= 0x7E:
            result.append(chr(byte))
            i += 1

        # Line feed → newline
        elif byte == 0x0A:
            result.append("\n")
            i += 1

        # Carriage return → newline (collapse CRLF into a single newline)
        elif byte == 0x0D:
            result.append("\n")
            if i + 1 < length and data[i + 1] == 0x0A:
                i += 1
            i += 1

        # High bytes (0x80-0xFF): decode as cp437, fall back to latin-1
        elif byte >= 0x80:
            try:
                result.append(byte.to_bytes(1, "big").decode("cp437"))
            except (UnicodeDecodeError, ValueError):
                try:
                    result.append(byte.to_bytes(1, "big").decode("latin-1"))
                except (UnicodeDecodeError, ValueError):
                    pass
            i += 1

        # Other control bytes (NUL, HT, etc.): drop
        else:
            i += 1

    return "".join(result)


def esc_pos_to_lines(data: bytes) -> list[str]:
    """Convert raw ESC/POS bytes to a list of text lines.

    Returns lines ready for the receipt parser to process.
    Empty lines are preserved (they may be meaningful).

    Args:
        data: Raw ESC/POS bytes from the printer.

    Returns:
        List of text lines extracted from the ESC/POS data.
    """
    text = esc_pos_to_text(data)
    # Split on newlines, preserving the structure
    lines = text.split("\n")
    return lines


# ── Printing helpers (reverse direction: text → ESC/POS → USB) ──────


def text_to_escpos(
    text: str,
    bold: bool = False,
    width: int = 48,
    line_height: int = 32,
) -> bytes:
    """Convert plain text to ESC/POS byte stream.

    Args:
        text: Plain text to convert.
        bold: Whether to use bold font.
        width: Character column width (default 48 = 80mm).
        line_height: Line feed height in dots (default 32).

    Returns:
        ESC/POS byte sequence ready to send to printer.
    """
    cmd = b""

    # Initialize printer
    cmd += b"\x1B\x40"

    # Set line height
    cmd += b"\x1B\x33" + bytes([line_height])

    if bold:
        cmd += b"\x1B\x45\x01"  # Bold on

    for line in text.split("\n"):
        # Pad line to full width
        padded = line.ljust(width)
        cmd += padded.encode("cp437", errors="ignore") + b"\x0A"

    if bold:
        cmd += b"\x1B\x45\x00"  # Bold off

    # Feed paper (3 lines) then cut
    cmd += b"\x1B\x64\x03"
    cmd += b"\x1D\x56\x01"  # Partial cut

    return cmd


def print_to_usb_printer(
    text: str,
    port: str = "/dev/usb/lp0",
    bold: bool = False,
) -> str:
    """Send plain text to a USB thermal printer via ESC/POS.

    Args:
        text: Plain text receipt content.
        port: USB device path (default /dev/usb/lp0).
        bold: Use bold font for the receipt.

    Returns:
        "ok" on success, or error message string.
    """
    try:
        escpos_bytes = text_to_escpos(text, bold=bold)
        with open(port, "wb") as f:
            f.write(escpos_bytes)
        return "ok"
    except FileNotFoundError:
        return f"Printer device not found: {port}"
    except PermissionError:
        return f"Permission denied writing to {port}. Add user to dialout group or run with sudo."
    except OSError as e:
        return f"IO error writing to printer: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


# ── Test with mock ESC/POS payload ──────────────────────────────────────

if __name__ == "__main__":
    # Build a minimal ESC/POS payload manually
    # ESC @  = initialize printer
    # "STORE NAME\n"
    # GS W 08 02 = set barcode width
    # "ITEM 1        10.00\n"
    # ESC ! 01   = bold on
    # "TOTAL       10.00\n"
    # ESC d 03   = feed 3 lines
    # GS @       = cut paper (alternative init)

    payload = (
        b"\x1B\x40"                       # ESC @  — initialize
        b"STORE NAME\n"                   # store name
        b"\x1D\x57\x08\x02"              # GS W 08 02 — barcode width
        b"ITEM 1        10.00\n"         # item line
        b"\x1B\x21\x01"                  # ESC ! 01 — bold on
        b"TOTAL       10.00\n"           # total line
        b"\x1B\x64\x03"                  # ESC d 03 — feed 3 lines
        b"\x1D\x40"                      # GS @ — initialize/cut
    )

    text = esc_pos_to_text(payload)
    lines = esc_pos_to_lines(payload)

    print("=== Text output ===")
    print(repr(text))
    print()
    print("=== Lines output ===")
    for i, line in enumerate(lines):
        print(f"  [{i}] {repr(line)}")
    print()
    print("OK")
