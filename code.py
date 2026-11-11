"""Type one fixed string, then print NFC tag IDs.

The string is typed once at startup, as a US keyboard. Tag IDs are printed
on the USB serial console.
"""
import time
import board
import busio
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_pn532.i2c import PN532_I2C

# Typed once after power-up. The computer must be using a US keyboard layout.
TYPE_THIS = "hello from the dongle"

SDA = board.GP4
SCL = board.GP5


def hex_id(uid):
    return ":".join("%02X" % b for b in uid)


def type_string():
    layout = KeyboardLayoutUS(Keyboard(usb_hid.devices))
    time.sleep(1)
    layout.write(TYPE_THIS)


def connect():
    """Return a reader that is answering. Keeps trying until it does."""
    i2c = busio.I2C(SCL, SDA)
    warned = False
    while True:
        try:
            nfc = PN532_I2C(i2c)
            _ic, ver, rev, _support = nfc.firmware_version
            nfc.SAM_configuration()
            print("Reader found. Firmware %d.%d" % (ver, rev))
            return nfc
        except (OSError, RuntimeError):
            if not warned:
                warned = True
                print("The reader does not answer. Check power, ground, SDA and SCL.")
            time.sleep(1)


def main():
    print("nfc dongle")
    type_string()
    print("Typed.")

    nfc = connect()
    print("Hold a tag on the reader.")
    last = None
    while True:
        uid = nfc.read_passive_target(timeout=0.5)
        if uid is None:
            last = None
            continue
        uid = bytes(uid)
        if uid == last:
            continue
        last = uid
        print("NFC " + hex_id(uid))


main()
