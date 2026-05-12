#!/usr/bin/env python3
"""
USB Serial Receipt Receiver for PrepRight.

Reads raw receipt text from USB serial port, parses it using configured templates,
and posts results to the PrepRight API.

Usage (on Raspberry Pi):
    python3 serial_receiver.py --port /dev/ttyUSB0 --baud 9600 --host localhost --port-api 8000

Configuration (via environment variables):
    SERIAL_PORT=/dev/ttyUSB0
    SERIAL_BAUD=9600
    API_HOST=localhost
    API_PORT=8000
"""

import argparse
import logging
import sys
import time
import requests

import serial
import serial.tools.list_ports

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("serial_receiver")

# ── Receipt delimiters ──────────────────────────────────
# Patterns that indicate a complete receipt has been received
RECEIPT_END_PATTERNS = [
    r"Totaal\s+\d+\s+stuk",  # Dutch: "Totaal 5 stuk(s) 19.86"
    r"Total\s+\d+\s+items?",  # English
    r"Subtotal",
    r"Charge\s+amount",
    r"<CR>",  # Raw control character
    r"\n\n\n",  # Multiple blank lines
    r"Thank\s+you",
    r"Bedankt",  # Dutch: "Thank you"
    r"Ga\s+voor\s+onze",  # HEMA: "Ga voor onze actuele openingstijden"
    r"We\s+kijken\s+ernaar",  # HEMA: "We kijken ernaar uit"
    r"Ruilen\s+of\s+terugbrengen",  # HEMA return policy
]


class SerialReceiver:
    """Listens on a USB serial port and processes complete receipts."""

    def __init__(self, port: str, baud: int = 9600, api_host: str = "localhost", api_port: int = 8000):
        self.port = port
        self.baud = baud
        self.api_url = f"http://{api_host}:{api_port}"
        self.buffer = ""
        self.running = False

    def _is_receipt_end(self, text: str) -> bool:
        """Check if the text ends with a receipt delimiter."""
        for pattern in RECEIPT_END_PATTERNS:
            if text.strip().endswith(pattern) or pattern in text:
                return True
        return False

    def _process_receipt(self, text: str):
        """Send a complete receipt to the API for processing."""
        # Clean up the text
        text = text.strip()
        if not text or len(text) < 10:
            return

        log.info(f"Processing receipt ({len(text)} chars):")
        for line in text.split("\n")[:20]:  # Show first 20 lines
            log.info(f"  {line}")

        try:
            resp = requests.post(
                f"{self.api_url}/api/receipts/process",
                json={"text": text},
                timeout=10,
            )
            if resp.status_code == 200:
                result = resp.json()
                log.info(f"Parsed {result.get('parsed_line_count', 0)} lines, "
                         f"matched {result.get('matched_count', 0)} products")
                if result.get("unmatched"):
                    log.warning(f"Unmatched lines: {result['unmatched'][:5]}")
            else:
                log.error(f"API error {resp.status_code}: {resp.text}")
        except requests.exceptions.ConnectionError:
            log.error("Cannot connect to API. Is it running?")
        except Exception as e:
            log.error(f"Error processing receipt: {e}")

    def _detect_port(self):
        """Auto-detect USB serial port if /dev/ttyUSB* is available."""
        ports = serial.tools.list_ports.comports()
        for p in ports:
            if "ttyUSB" in p.device or "ttyACM" in p.device:
                return p.device
        return None

    def run(self):
        """Main loop: read serial data and process complete receipts."""
        port = self.port
        if not port:
            port = self._detect_port()
            if not port:
                log.error("No serial port found. Specify with --port")
                sys.exit(1)
            log.info(f"Auto-detected port: {port}")

        log.info(f"Opening serial port {port} at {self.baud} baud")
        ser = serial.Serial(port, self.baud, timeout=1)
        self.running = True
        log.info("Listening for receipts...")

        try:
            while self.running:
                if ser.in_waiting:
                    data = ser.read(ser.in_waiting).decode("utf-8", errors="ignore")
                    self.buffer += data

                    # Check if we have a complete receipt
                    if self._is_receipt_end(self.buffer):
                        self._process_receipt(self.buffer)
                        self.buffer = ""
                    elif len(self.buffer) > 10000:
                        # Buffer overflow — reset
                        log.warning("Buffer overflow, resetting")
                        self.buffer = ""

                time.sleep(0.01)
        except KeyboardInterrupt:
            log.info("Shutting down...")
        finally:
            ser.close()
            self.running = False


def main():
    parser = argparse.ArgumentParser(description="USB Serial Receipt Receiver")
    parser.add_argument("--port", default=None, help="Serial port (e.g., /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=9600, help="Baud rate (default: 9600)")
    parser.add_argument("--host", default="localhost", help="API host (default: localhost)")
    parser.add_argument("--port-api", type=int, default=8000, help="API port (default: 8000)")
    args = parser.parse_args()

    receiver = SerialReceiver(
        port=args.port,
        baud=args.baud,
        api_host=args.host,
        api_port=args.port_api,
    )
    receiver.run()


if __name__ == "__main__":
    main()
