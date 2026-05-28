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


def esc_pos_to_text(data: bytes) -> str:
    """Convert raw ESC/POS bytes to plain text.

    Strips all ESC/POS control commands and returns only printable text.
    Handles line feeds, column positioning, and character set changes.

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

        # Printable ASCII (0x20-0x7E)
        if 0x20 <= byte <= 0x7E:
            result.append(chr(byte))
            i += 1

        # Carriage return → newline
        elif byte == 0x0D:
            result.append("\n")
            i += 1

        # Line feed
        elif byte == 0x0A:
            result.append("\n")
            i += 1

        # Null byte → space (common padding/separator)
        elif byte == 0x00:
            result.append(" ")
            i += 1

        # ESC (0x1B) sequence: skip ESC + all following command bytes
        elif byte == 0x1B:
            # Skip the ESC byte itself and all subsequent command bytes
            # until we hit printable text or end of data
            i += 1
            while i < length:
                next_byte = data[i]
                # Stop skipping when we encounter another control prefix
                # or printable text
                if next_byte == 0x1B:
                    # Nested ESC — treat as start of new sequence
                    break
                elif next_byte == 0x1D:
                    # GS inside ESC sequence — skip it too
                    i += 1
                    continue
                elif next_byte == 0x1C:
                    # FS inside ESC sequence — skip it too
                    i += 1
                    continue
                elif 0x20 <= next_byte <= 0x7E:
                    # Printable text resumes — stop skipping
                    break
                elif next_byte == 0x0A:
                    # Line feed inside ESC sequence — treat as newline
                    result.append("\n")
                    i += 1
                    break
                elif next_byte == 0x0D:
                    # CR inside ESC sequence — treat as newline
                    result.append("\n")
                    i += 1
                    break
                else:
                    # Other control byte inside ESC sequence — skip
                    i += 1
                    continue
            i += 1

        # GS (0x1D) sequence: skip GS + all following command bytes
        elif byte == 0x1D:
            i += 1
            while i < length:
                next_byte = data[i]
                if next_byte == 0x1D:
                    break
                elif next_byte == 0x1B:
                    break
                elif next_byte == 0x1C:
                    i += 1
                    continue
                elif 0x20 <= next_byte <= 0x7E:
                    break
                elif next_byte == 0x0A:
                    result.append("\n")
                    i += 1
                    break
                elif next_byte == 0x0D:
                    result.append("\n")
                    i += 1
                    break
                else:
                    i += 1
                    continue
            i += 1

        # FS (0x1C) sequence: skip FS + all following command bytes
        elif byte == 0x1C:
            i += 1
            while i < length:
                next_byte = data[i]
                if next_byte == 0x1C:
                    break
                elif next_byte == 0x1B:
                    break
                elif next_byte == 0x1D:
                    break
                elif 0x20 <= next_byte <= 0x7E:
                    break
                elif next_byte == 0x0A:
                    result.append("\n")
                    i += 1
                    break
                elif next_byte == 0x0D:
                    result.append("\n")
                    i += 1
                    break
                else:
                    i += 1
                    continue
            i += 1

        # High bytes (0x80-0xFF): try cp437, fall back to latin-1
        elif byte >= 0x80:
            try:
                result.append(byte.to_bytes(1, "big").decode("cp437"))
            except (UnicodeDecodeError, ValueError):
                try:
                    result.append(byte.to_bytes(1, "big").decode("latin-1"))
                except (UnicodeDecodeError, ValueError):
                    pass
            i += 1

        # Other control bytes (0x01-0x1F except 0x0D, 0x0A): skip
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
