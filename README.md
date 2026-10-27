# PN532 reader test for the Pico 2 W

Checks that a PN532 NFC reader works by reading the tag that came with it. The build is two parts, a Raspberry Pi Pico 2 W and a PN532 module. Nothing else is needed.

You pass the test when the Pico shows the tag's ID and confirms the same ID is stored on the tag.

## Parts

- Raspberry Pi Pico 2 W
- PN532 module with the NFC tag that came with it
- Four jumper wires
- USB cable from the Pico to a computer

## Wiring

| Pico label | Pico pin number | PN532 pin |
| --- | --- | --- |
| 3V3(OUT) | 36 | VCC |
| GND | 38 | GND |
| GP4 | 6 | SDA |
| GP5 | 7 | SCL |

The labels are printed on the underside of the Pico, so the easiest way is to match the wires to those. The pin numbers are positions along the edge. Hold the Pico with the USB connector at the top and the chip side up. The left column counts 1 to 20 from top to bottom, so GP4 and GP5 are pins 6 and 7, just below the first GND at pin 3. The right column counts 21 to 40 from bottom to top, so 3V3(OUT) is pin 36 and GND is pin 38, both near the top.

Set the mode switches on the PN532 module for I2C. On most modules that means switch 1 ON and switch 2 OFF. If your module prints the settings on the board, follow what it says for I2C.

## Installing MicroPython

1. Download the MicroPython file for the Pico 2 W from https://micropython.org/download/RPI_PICO2_W/. It ends in `.uf2`.
2. Hold the BOOTSEL button on the Pico and plug it into the computer. Let go once a drive named RP2350 appears.
3. Drag the `.uf2` file onto that drive. The drive disappears and the Pico restarts. MicroPython is now installed.

## Copying the test onto the Pico

Both `main.py` and `pn532.py` go onto the Pico, in the top folder.

With Thonny:

1. Install Thonny from https://thonny.org and open it.
2. Choose the interpreter in the bottom right corner and pick MicroPython (Raspberry Pi Pico).
3. Open `pn532.py`, choose File, Save as, pick the MicroPython device and save it as `pn532.py`.
4. Do the same for `main.py`.

With mpremote:

```
pip install mpremote
mpremote connect auto cp pn532.py main.py :
```

## Running the test

The test starts by itself each time the Pico gets power. Right after copying, unplug the USB cable and plug it back in, or press the stop and restart button in Thonny.

To watch the results, use either of these:

- Thonny. The text appears in the Shell panel at the bottom.
- mpremote. Run `mpremote connect auto repl` and press Ctrl+D if the screen is blank.

The Pico also works without a computer, on any USB power. You then only see the LED and not the text.

## Reading the results

Starting up prints this:

```
PN532 reader test
-----------------
Reader found. Firmware 1.6
Ready. Hold the tag flat against the reader.
```

Hold the tag flat against the antenna of the PN532 module. A successful read looks like this:

```
Tag read (1)
  ID:   04:A1:B2:C3
  Type: Mifare Classic 1K
  Data check: passed. The ID stored on the tag matches.
  TEST PASSED. The reader reads your tag.
```

The ID and type on your screen will differ. That is expected.

| What you see | Meaning |
| --- | --- |
| TEST PASSED | The reader found the tag and read data from it. The chip works. |
| Data check: skipped | The ID was read but the tag keeps its data locked. Check the ID with a phone as described below. |
| Data check: failed | The ID found and the ID stored on the tag differ. Take the tag away and try again. |
| Same tag as last time | You presented the same tag again. The ID matches the earlier read. |
| Different tag from last time | You presented another tag. |
| Tag removed | The tag left the reader. Place it again for another read. |

The LED on the Pico gives a second signal:

| LED | Meaning |
| --- | --- |
| Two short blinks | The reader was found and the test is ready |
| Solid on | The tag is on the reader |
| Five fast blinks, repeating | The reader was not found |

Press Stop in Thonny, or Ctrl+C in mpremote, to end the test. It prints how many tags were read and whether the test passed.

## Checking the tag with a phone

This gives a second opinion on the ID, from a device other than the PN532.

1. Install a free NFC reader app on your phone, for example NFC Tools.
2. Scan the tag and note the ID the app shows.
3. Compare it with the ID printed by the Pico. Some apps show the same bytes in reverse order, which still counts as a match.

## Troubleshooting

- **Nothing answers on the wires.** Check the four wires, especially SDA and SCL, which are easy to swap. The test keeps trying and carries on once the reader answers.
- **Something is on the wires but the reader does not answer.** Check the mode switches on the PN532 module for I2C.
- **Reader found but the tag is not read.** Hold the tag flat on the antenna side of the module and keep it still for a second. Metal surfaces under the tag can block the read.
- **No text appears.** Unplug the Pico and plug it back in, then reopen the Shell or the mpremote screen.
