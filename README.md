# wbr3-flash — OpenBeken on Tuya WBR3 floor-heating thermostats

Notes and tools for replacing the stock Tuya firmware on **Tuya WBR3** (RTL8720CF / AmebaZ2)
Wi-Fi modules in EasyComfort 484/494 (TP618) floor-heating controllers with
[OpenBeken](https://github.com/openshwprojects/OpenBK7231T_App), so they run locally in
Home Assistant over MQTT with no Tuya cloud.

> WBR3 is RTL8720CF, not BK7231 (that's WB3S/CB3S).

## Flash routes

### Route 1: tuya-cloudcutter OTA (no soldering)
The WBR3 here runs Tuya's generic RTL8720CF TuyaMCU firmware
`rtl8720cf_common_user_config_ty`. Cloudcutter has profiles for 2.1.6 / 2.5.0 / 2.5.2
(2.5.2 worked with `tuya-generic-m3h-thermostat-v2.5.2`).
1. Tuya app → device → Device update → note the Wi-Fi module version.
2. Supported version: run `tuya-cloudcutter.sh -f` → "by firmware version" → flash `OpenRTL87X0C_*_ota.img`.
3. In the OBK setup AP, enter the SSID in the first field with "Open access point" unticked, or it stays in AP mode.

Cloudcutter only writes the inactive app slot, so the stock Tuya partition table and
bootloader stay. See [bootswap](#bootswap-obk-bootloader-over-the-air) to replace them.

### Route 2: desolder and UART-flash
RX2 (PA15) and the download strap (PA00) are pads **under** the module (see BOARDNOTES.md),
so in-place UART flashing isn't possible.
1. Unplug from mains. Hot-air the WBR3 (M1) off the carrier.
2. On the loose module: 3V3 from a separate regulator, GND, TX2 pin 11 → adapter RX,
   RX2 bottom pad → adapter TX, PA00 bottom pad → 3V3, PA13 (pin 15) floating.
3. Pulse CEN (pin 3) low, or power-cycle.

```sh
uvx ltchiptool flash read  -d /dev/ttyUSB0 realtek-ambz2 backup/stock.bin   # twice, then cmp
uvx ltchiptool flash write -d /dev/ttyUSB0 OpenRTL87X0C_<ver>.bin
```
4. Release PA00, boot, check the `OpenRTL87X0C_XXXXXXXX` setup AP, solder the module back.

A CH341A in serial mode works (1k/2k divider on its 5 V TXD). ltchiptool's post-write SHA
mismatch is a false alarm (XMODEM pads the last 1K block with 0x1A); verify by readback.
A UART bridge that mangles bytes ≥0x80 is fine for logs but useless for XMODEM writes.

> ⚠️ Never share a flash dump: it holds Wi-Fi credentials and Tuya keys.

## TuyaMCU mapping

The WBR3 is only the Wi-Fi bridge; the thermostat MCU talks TuyaMCU v3 at 9600 baud on
UART0 (pins 15/16). `config/autoexec.bat` maps it to OBK channels:

| Ch | dpID | Meaning |
|---|---|---|
| 1 | 1 | heating on/off |
| 2 | 2 | mode (0 manual, 1 eco?, 2 program) — needs `setChannelType 2 ReadOnly` or OBK never publishes it |
| 3 | 16 | target ×10 |
| 4 | 24 | room temp ×10 |
| 5 | 106 | floor temp ×10 |
| 6 | 101 | heating active (relay) |

Other dpIDs (from the TP618RFW manual, matched by default values): 10 frost protection,
19 max setpoint, 26 min setpoint, 27 temp calibration, 32 ECO setpoint, 39 child lock,
40 ECO function, 45 fault bitmap, 48 week program (raw), 105 floor over-temp limit.

Program mode = 5+1+1 days, 6 periods. A setpoint change from the app in program mode is a
temporary override; a change on the room unit switches to manual.

`config/ha-mqtt.yaml` is a Home Assistant MQTT template for one unit (climate + floor
temperature + raw mode); repeat it per unit with that unit's OBK shortName as the topic.
Upload the autoexec with `curl -X POST --data-binary @config/autoexec.bat http://<ip>/api/lfs/autoexec.bat`.

## Boot layout (AmebaZ2, 2 MB)

| Addr | Content |
|---|---|
| 0x0 | partition table |
| 0x1000 | system data (`system_data_t`) |
| 0x2000 | calibration |
| 0x4000 | bootloader |
| 0x10000 | fw1 |
| 0xF0000 | fw2 |

- OBK exposes a read-only flash dump over HTTP: `curl http://<ip>/api/flash/<hex addr>-<hex len>`.
- Tuya's bootloader picks the slot with a bit counter at sysdata 0x1004 (cleared bits: odd → fw2,
  even → fw1). Realtek's `system_data_t` marks 0x04 as `reserved1`; the OBK bootloader ignores it
  and picks by image validity and serial number.
- A full OBK `.bin` flashed over UART brings its own partition table + bootloader. A cloudcutter
  unit keeps Tuya's. Both boot OBK and accept OBK OTA updates.

## bootswap: OBK bootloader over the air

`bootswap/` adds a `bootswap` command to OBK that replaces a stock Tuya partition table and
bootloader with the OBK ones in place, without desoldering. `build.sh` clones OBK, embeds the
OBK ptable (0x0) and bootloader (0x4000..0xB000) from the release `.bin` plus the known stock
ones from a dump of a cloudcutter unit, and builds an `_ota.img`.

- `bootswap check` — read-only: logs ptable/boot state, running slot, serial numbers.
- `bootswap go I_ACCEPT_BRICK` — refuses unless ptable and bootloader are byte-exact stock and
  the slot info is consistent. Then: zero the other slot's first word (so the running OBK is the
  only valid image), write the bootloader, then the ptable, sector by sector with read-back
  verify (retries, never reboots mid-way), re-check everything, reboot.

Per unit: OTA the bootswap image → `bootswap check` → `bootswap go I_ACCEPT_BRICK` → OTA the
stock OBK `_ota.img` to drop the command → dump 0x0–0x10000 and compare with a UART-flashed unit.

Done on two cloudcutter units without a bench module; the only remaining difference from a
UART-flashed unit is the ignored sysdata byte at 0x1004. A power loss during the ~1 s write
window means desoldering + UART.
