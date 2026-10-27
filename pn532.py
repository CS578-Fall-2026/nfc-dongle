"""Minimal PN532 driver for MicroPython, I2C only.

Covers just what the reader test needs: firmware version, reader setup,
detecting a tag, and reading one block of data from a tag.

Frame layout on the wire (host to chip and back):
    00 00 FF LEN LCS TFI CMD [data...] DCS 00
LEN counts TFI + CMD + data. LCS makes LEN + LCS add up to 0 (mod 256).
DCS does the same for everything from TFI up to DCS. TFI is D4 going to the
chip and D5 coming back.

Over I2C every read starts with one status byte (bit 0 set = reply ready),
followed by the frame. A command is answered twice: first a fixed ACK frame,
then the real reply once the chip has finished.
"""
import time

ADDR = 0x24

_ACK = b"\x00\x00\xff\x00\xff\x00"

_CMD_GET_FIRMWARE = 0x02
_CMD_SAM_CONFIGURATION = 0x14
_CMD_RF_CONFIGURATION = 0x32
_CMD_IN_DATA_EXCHANGE = 0x40
_CMD_IN_LIST_PASSIVE_TARGET = 0x4A

DEFAULT_KEY = b"\xff\xff\xff\xff\xff\xff"


class PN532Error(Exception):
    pass


def tag_type(sel_res):
    """Name the tag family from the SEL_RES byte given at activation."""
    if sel_res in (0x08, 0x88):
        return "Mifare Classic 1K"
    if sel_res == 0x09:
        return "Mifare Classic Mini"
    if sel_res == 0x18:
        return "Mifare Classic 4K"
    if sel_res == 0x00:
        return "NTAG or Ultralight"
    return "Unknown type"


class PN532:
    def __init__(self, i2c, addr=ADDR):
        self.i2c = i2c
        self.addr = addr

    def _ready(self):
        try:
            return (self.i2c.readfrom(self.addr, 1)[0] & 0x01) == 1
        except OSError:
            # The chip does not answer its address while it is busy.
            return False

    def _wait_ready(self, timeout_ms):
        deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
        while not self._ready():
            if time.ticks_diff(time.ticks_ms(), deadline) >= 0:
                raise PN532Error("timeout")
            time.sleep_ms(5)

    def call(self, cmd, params=b"", max_reply=16, timeout_ms=1000):
        """Send one command and return the reply data (after the reply code).

        max_reply is the most data bytes the reply can carry. The read is
        sized from it, and the chip pads any unused bytes.
        """
        body = bytes([0xD4, cmd]) + bytes(params)
        n = len(body)
        frame = (
            bytes([0x00, 0x00, 0xFF, n, (0x100 - n) & 0xFF])
            + body
            + bytes([(0x100 - sum(body)) & 0xFF, 0x00])
        )
        try:
            self.i2c.writeto(self.addr, frame)
        except OSError:
            # A sleeping chip drops the first write while it wakes up.
            time.sleep_ms(20)
            self.i2c.writeto(self.addr, frame)

        self._wait_ready(timeout_ms)
        ack = self.i2c.readfrom(self.addr, 7)
        if bytes(ack[1:7]) != _ACK:
            raise PN532Error("no acknowledge")

        self._wait_ready(timeout_ms)
        buf = bytes(self.i2c.readfrom(self.addr, max_reply + 10))

        start = buf.find(b"\x00\xff", 1)
        if start < 0 or start + 5 >= len(buf):
            raise PN532Error("bad frame")
        length = buf[start + 2]
        if (length + buf[start + 3]) & 0xFF != 0:
            raise PN532Error("bad length")
        end = start + 4 + length
        if end >= len(buf):
            raise PN532Error("reply too long")
        payload = buf[start + 4:end]
        if (sum(payload) + buf[end]) & 0xFF != 0:
            raise PN532Error("bad checksum")
        if payload[0] != 0xD5 or payload[1] != cmd + 1:
            raise PN532Error("unexpected reply")
        return payload[2:]

    def firmware_version(self):
        """Return (version, revision) of the chip firmware."""
        d = self.call(_CMD_GET_FIRMWARE, max_reply=4)
        return d[1], d[2]

    def setup(self):
        """Put the chip in normal reader mode and make detection quick."""
        # Normal mode, 1 s timeout (unused in normal mode), IRQ pin enabled.
        self.call(_CMD_SAM_CONFIGURATION, bytes([0x01, 0x14, 0x01]), max_reply=0)
        # Item 5 is the retry limits: ATR 0xFF, PSL 0x01, passive activation 2.
        # Two activation tries means a poll with no tag answers in a few ms
        # instead of waiting forever.
        self.call(_CMD_RF_CONFIGURATION, bytes([0x05, 0xFF, 0x01, 0x02]), max_reply=0)

    def rf_reset(self):
        """Switch the radio field off and on to return tags to their idle state.

        A tag that was read or authenticated ignores the next detection poll
        until its power is cycled, so this runs after each read.
        """
        self.call(_CMD_RF_CONFIGURATION, bytes([0x01, 0x00]), max_reply=0)
        time.sleep_ms(20)
        self.call(_CMD_RF_CONFIGURATION, bytes([0x01, 0x03]), max_reply=0)

    def read_passive_target(self):
        """Return (uid, sel_res) for a type A tag in range, or None."""
        d = self.call(_CMD_IN_LIST_PASSIVE_TARGET, bytes([0x01, 0x00]),
                      max_reply=24, timeout_ms=500)
        if d[0] == 0:
            return None
        # d: NbTg, Tg, SENS_RES (2 bytes), SEL_RES, NFCID length, NFCID
        sel_res = d[4]
        n = d[5]
        return bytes(d[6:6 + n]), sel_res

    def _exchange(self, payload):
        """Send a tag-level command. Return the tag's answer, or None if the
        tag refused or is out of range."""
        d = self.call(_CMD_IN_DATA_EXCHANGE, b"\x01" + bytes(payload), max_reply=20)
        if d[0] & 0x3F != 0:
            return None
        return bytes(d[1:])

    def classic_read_block(self, block, uid, key=DEFAULT_KEY):
        """Read 16 bytes from a Mifare Classic block using key A."""
        if self._exchange(bytes([0x60, block]) + key + uid[:4]) is None:
            return None
        return self._exchange(bytes([0x30, block]))

    def ultralight_read_page(self, page):
        """Read 16 bytes (4 pages) from an NTAG or Ultralight tag."""
        return self._exchange(bytes([0x30, page]))
