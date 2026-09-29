# BOARDNOTES — Tuya WBR3 / RTL8720CF

## Module pinout (LibreTiny `wbr3.svg`, matches the Tuya WBR3 datasheet)

| Pin | Name | Note |
|---|---|---|
| 1 | NC | pulled up, for compatibility with other modules |
| 2 | PA07 | |
| 3 | CEN | reset (active low) |
| 4 | PA11 | TX0 |
| 5 | PA02 | RX1 |
| 6 | PA03 | TX1 |
| 7 | PA04 | |
| 8 | 3V3 | |
| 9 | GND | |
| 10 | PA12 | RX0 |
| 11 | **PA16** | **TX2**: log/flash TX, on an edge pad |
| 12 | PA17 | |
| 13 | PA18 | |
| 14 | PA19 | |
| 15 | PA13 | RXD / UART0 RX: user serial, the TuyaMCU link to IC1. Must NOT be pulled low at boot |
| 16 | PA14 | TXD / UART0 TX: user serial, the TuyaMCU link to IC1 |
| bottom (not in the Tuya table) | **PA15** | **RX2**: log/flash RX, **pad under the module** |
| bottom (not in the Tuya table) | **PA00** | **download strap: pull to 3.3 V at reset**; also **SWCLK** (JTAG_CLK), **pad under the module** |
| bottom | PA01 | TX1, **SWDIO** (JTAG_TMS) |

⇒ **You can't UART-flash this module in place.** RX2 and the download strap are both
under the module. LibreTiny: "usually not possible to flash this module (via UART)
without desoldering it." Flash UART = UART2 (PA16/PA15). 2 MB flash.

## Carrier: EasyComfort box, silkscreen `TP618RX`

| Ref | Part | Role |
|---|---|---|
| M1 | WBR3, P/N 2.01.99.00006 | Wi-Fi. Castellated edge pads soldered to the carrier |
| IC1 | HDSC **HC32F030J8TA** (LQFP48) | Thermostat MCU. Talks to the WBR3 over TuyaMCU |
| U1 | CMT2300A-class sub-GHz transceiver, 26 MHz xtal, spring antenna | RF link to the wireless TP618 room thermostat |
| JP1 | 5-pin header beside M1 | **IC1 SWD programming header** : 1 = 3V3, 2 = PA14/SWCLK (pin 37), 3 = under IC1 (expected: PA13/SWDIO, pin 34), 4 = R1 10k (expected: RESETB, pin 7), 5 = GND |
| JP2 | 3-pin header by IC1 | Unknown. Probably HC32 SWD |
| K1 | HF7520 16 A relay | Heating load |
| K2 | HK4101F 3 A relay | Second output (pump/valve?) |
| SW2 | push button | Pairing/reset |
| LEDs | red / green / yellow / blue | Blue is lit: Wi-Fi status |
| — | flyback transformer + LNK-type switcher | **Mains on the board.** Only work on it unplugged |

## Which WBR3 pins are soldered to the carrier

Only **6 of 16** module pins have solder. The rest sit on bare carrier pads:

| Pin | Name | Soldered | Likely goes to |
|---|---|---|---|
| 3 | CEN | yes | **R15** (trace + via under M1). Module boots fine with CEN floating |
| 2 | PA07 | yes | **nothing**: no trace, mechanical only |
| 8 | 3V3 | yes | C7/R1 at the bottom of JP1 |
| 9 | GND | yes | ground |
| 15 | PA13 RX0 | yes | **R14 → IC1 pin 30 PA09 = UART0 TX** (traced) |
| 16 | PA14 TX0 | yes | **R13 (100 Ω) → IC1 pin 31 PA10 = UART0 RX** (traced) |
| 1, 4–7, 10–14 | incl. **TX2 (pin 11)** | **no** | nothing |

⇒ Nothing on the carrier reaches the flash UART (TX2 isn't soldered; RX2/PA00 are under
the module). JP1 can't be the WBR3 flash port. Upside: removing the module means
desoldering only 6 joints.

| Fact | Verified |
|---|---|
| ltchiptool family `realtek-ambz2` | [x] |
| JP1 pinout | [x] traced; to confirm: JP1-2 ↔ WBR3 pin 15, JP1-3 ↔ pin 16, and where R1's other end goes |
| Which WBR3 UART goes to IC1, and at what baud | [x] UART0 (pins 15/16) ↔ IC1 PA09/PA10, 9600 baud, TuyaMCU v3 |

## IC1: HDSC HC32F030J8TA (datasheet Rev1.4, ZLG mirror)

Cortex-M0+, 48 MHz, 64 KB flash, LQFP48. Pin 1 is at the package's dot, and pins count counter-clockwise.

| Pin | Signal | Why it matters for JP1 |
|---|---|---|
| 1 | VCAP | core regulator cap, not a header pin |
| 7 | RESETB | reset (internal pull-up) |
| 8 / 9 | AVSS / AVCC | ground / 3V3 |
| 23 / 24 | DVSS / DVCC | ground / 3V3 |
| 47 / 48 | DVSS / DVCC | ground / 3V3 |
| 34 | PA13 / SWDIO | SWD data |
| 37 | PA14 / SWCLK (also UART0/1 TX) | SWD clock |
| 44 | PD03 / MODE | boot mode (ISP bootloader strap) |
| 29 / 30 / 31 | PA08 / PA09 / PA10 | UART0 TX / TX / RX alternates |
| 12 / 13 | PA02 / PA03 | UART1 TX / RX |
| 38 | PA15 | UART1 RX alternate |
| 42 / 43, 45 / 46 | PB06 / PB07, PB08 / PB09 | UART0 TX / RX alternates |

JP1 guess: **HC32 SWD** if its holes go to 34 / 37 / 7 / 3V3 / GND. **TuyaMCU breakout** if they go to the WBR3's pins 15 / 16 (and one of the UART pins above).

**TuyaMCU link = IC1 UART0 (PA09/PA10) ↔ WBR3 UART0 (pins 15/16), through the 100 Ω R13/R14.**
The 0603 pads of R13/R14 are the easiest points to listen on.

## SWD on the RTL8720CF (datasheet Rev 0.8, pin mux table)

**JTAG_CLK / SWCLK = GPIOA_0 (PA00)** and **JTAG_TMS / SWDIO = GPIOA_1 (PA01)**. On the WBR3,
both are bottom pads. So SWD, like UART download (PA00 strap + PA15 RX2), can't be reached
with the module soldered down. **Every path that writes flash on this module needs the bottom pads.**

## RTL8720CF die pins (QFN40, 5×5 mm, 0.4 mm pitch, under the WBR3 metal shield)

From the datasheet's Figure 1 (RTL8720CF-VA1 QFN40): **15 = GPIOA_0 (PA00: strap/SWCLK)**, 14 = CHIP_EN (next to it!),
16 = GPIOA_1 (SWDIO), **36 = GPIOA_15 (RX2)**, 37 = GPIOA_16 (TX2), 41 = exposed pad = GND.
A QFN has no legs, only the small side flanks of each pad. The shield has to come off to reach them.

## WBR3 bottom test pads (Tuya datasheet "Bottom View")

Exposed round pads on the module underside, a little inboard from the edge castellations:
- **A_0 (PA00)**: pin 1–8 side, between pins 5 and 6 (A_2/A_3). Download strap / SWCLK
- **A_1 (PA01)**: pin 1–8 side, between pins 6 and 7 (A_3/A_4). SWDIO
- **A_15 (PA15)**: pin 9–16 side, between pins 14 and 15 (A_19/RXD). RX2
- The centre square is exposed GND. The round pad at pin 1 is NC

The bottom view is mirrored: seen from the top (antenna up), A_0/A_1 sit under the LEFT column, A_15 under the RIGHT.
