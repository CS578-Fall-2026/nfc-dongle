"""PN532 reader test for the Raspberry Pi Pico 2 W.

Runs by itself when the Pico powers up. Prints progress to the USB serial
console and uses the onboard LED as a second signal:
    two short blinks   reader found, ready for a tag
    solid on           tag is on the reader
    five fast blinks   reader not found, still trying
"""
from machine import I2C, Pin
import time
from pn532 import PN532, PN532Error, tag_type

SDA_PIN = 4
SCL_PIN = 5
POLL_MS = 100
# A held tag can miss one or two polls. Only call it removed after this many.
MISSES_BEFORE_REMOVED = 3

led = Pin("LED", Pin.OUT)


def blink(times, ms):
    for _ in range(times):
        led.on()
        time.sleep_ms(ms)
        led.off()
        time.sleep_ms(ms)


def hex_id(uid):
    return ":".join("%02X" % b for b in uid)


def connect():
    """Return a ready reader. Keeps trying until the reader answers."""
    i2c = I2C(0, sda=Pin(SDA_PIN), scl=Pin(SCL_PIN), freq=100000)
    warned = False
    while True:
        try:
            nfc = PN532(i2c)
            version, revision = nfc.firmware_version()
            nfc.setup()
            print("Reader found. Firmware %d.%d" % (version, revision))
            return nfc
        except (OSError, PN532Error):
            if not warned:
                warned = True
                if i2c.scan():
                    print("Something is on the wires but the reader does not answer.")
                    print("Check that the switches on the reader are set for I2C.")
                else:
                    print("Nothing answers on the wires.")
                    print("Check power, ground, SDA and SCL.")
                print("Still trying. The test carries on once the reader answers.")
            blink(5, 80)
            time.sleep(2)


def check_tag_data(nfc, uid, sel_res):
    """Read the ID a second way, from the tag's own memory.

    Returns True if the stored ID matches the one found at detection, False
    if it differs, None if the tag could not be read (locked or unknown type).
    A match proves data came back from the tag, not just that something
    was detected.
    """
    try:
        if sel_res in (0x08, 0x88, 0x09, 0x18):
            # Block 0 starts with the ID (4 or 7 bytes). Factory keys only.
            block = nfc.classic_read_block(0, uid)
            stored = block[:len(uid)] if block else None
        elif sel_res == 0x00:
            # Page 0 holds ID bytes 0-2, a check byte, then ID bytes 3-6.
            page = nfc.ultralight_read_page(0)
            stored = page[0:3] + page[4:8] if page else None
        else:
            return None
    except PN532Error:
        return None
    if stored is None:
        return None
    return stored == uid


def main():
    print("PN532 reader test")
    print("-----------------")
    nfc = connect()
    blink(2, 150)
    print("Ready. Hold the tag flat against the reader.")

    reads = 0
    seen = set()
    last_uid = None
    passed = False
    present = False
    misses = 0

    try:
        while True:
            try:
                tag = nfc.read_passive_target()
            except (OSError, PN532Error):
                led.off()
                print("Lost contact with the reader. Check the wires.")
                nfc = connect()
                print("Reader is back. Hold the tag flat against the reader.")
                present = False
                misses = 0
                continue

            if tag:
                misses = 0
                if not present:
                    present = True
                    led.on()
                    reads += 1
                    uid, sel_res = tag
                    seen.add(uid)
                    print()
                    print("Tag read (%d)" % reads)
                    print("  ID:   %s" % hex_id(uid))
                    print("  Type: %s" % tag_type(sel_res))
                    if last_uid is not None:
                        if uid == last_uid:
                            print("  Same tag as last time.")
                        else:
                            print("  Different tag from last time.")
                    last_uid = uid

                    result = check_tag_data(nfc, uid, sel_res)
                    if result is True:
                        print("  Data check: passed. The ID stored on the tag matches.")
                        if not passed:
                            passed = True
                            print("  TEST PASSED. The reader reads your tag.")
                    elif result is False:
                        print("  Data check: failed. The ID stored on the tag differs.")
                        print("  Take the tag away and try again.")
                    else:
                        print("  Data check: skipped. This tag keeps its data locked.")
                        print("  The ID was still read. Compare it with a phone to be sure.")
                    try:
                        nfc.rf_reset()
                    except (OSError, PN532Error):
                        pass  # a dead reader shows up on the next poll
            elif present:
                misses += 1
                if misses >= MISSES_BEFORE_REMOVED:
                    present = False
                    led.off()
                    print("Tag removed. Place it again to read it again.")

            time.sleep_ms(POLL_MS)
    except KeyboardInterrupt:
        led.off()
        print()
        print("Stopped.")
        print("Tags read: %d. Different tags: %d." % (reads, len(seen)))
        print("Result: %s" % ("passed" if passed else "not passed yet"))


main()
