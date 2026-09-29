#!/bin/sh
# Build OBK 1.18.313 + the `bootswap` command for RTL87X0C. Output: bootswap/out/*_ota.img
# usage: build.sh <stock_dump_0-10000.bin> <obk_uart_unit_dump_0-10000.bin>
#   first 64 KB of a cloudcutter unit (stock ptable+boot) and of a UART-flashed OBK unit
set -eu
here=$(cd "$(dirname "$0")" && pwd)
repo=$here/..
obk=$here/obk
ver=1.18.313
full=$repo/openbeken/OpenRTL87X0C_$ver.bin      # new ptable + bootloader, the same bytes as a UART-flashed unit
stock=$(realpath "$1")                         # stock ptable + bootloader
u1=$(realpath "$2")                            # UART-flashed OBK unit, for the sanity check

[ -d "$obk" ] || git clone -q --depth 1 --branch "$ver" https://github.com/openshwprojects/OpenBK7231T_App.git "$obk"
cd "$obk"

# blobs: ptable 0x0..0x1000, bootloader 0x4000..0xB000 (OBK boot ends ~0xA6C0, stock ~0x81C0)
b=$here/blobs; mkdir -p "$b"
dd if="$full"  of="$b/pt_new"   bs=4096 skip=0 count=1 status=none
dd if="$full"  of="$b/bl_new"   bs=4096 skip=4 count=7 status=none
dd if="$stock" of="$b/pt_stock" bs=4096 skip=0 count=1 status=none
dd if="$stock" of="$b/bl_stock" bs=4096 skip=4 count=7 status=none
# sanity: a UART-flashed unit's live dump must equal the blobs we are about to ship
dd if="$u1" bs=4096 count=1 status=none | cmp - "$b/pt_new"
dd if="$u1" bs=4096 skip=4 count=7 status=none | cmp - "$b/bl_new"
(cd "$b" && for f in pt_new bl_new pt_stock bl_stock; do xxd -i $f | sed 's/^unsigned char/static const unsigned char/; s/^unsigned int/static const unsigned int/'; done) \
  > src/hal/realtek/bootswap_blobs.h
cp "$here/bootswap.c" src/hal/realtek/bootswap.c

grep -q bootswap.c platforms/RTL87X0C/OpenBeken.mk || \
  sed -i 's|^SRC_C  += $(OBK_DIR)/src/hal/realtek/hal_ota_realtek.c|&\nSRC_C  += $(OBK_DIR)/src/hal/realtek/bootswap.c|' platforms/RTL87X0C/OpenBeken.mk
grep -q BootSwap_Init src/cmnds/cmd_main.c || \
  sed -i 's|^\tCMD_RegisterCommand("reboot", CMD_Restart, NULL);|&\n#if PLATFORM_RTL87X0C\n\t{ extern void BootSwap_Init(void); BootSwap_Init(); }\n#endif|' src/cmnds/cmd_main.c
grep -q bootswap.c platforms/RTL87X0C/OpenBeken.mk && grep -q BootSwap_Init src/cmnds/cmd_main.c

make OpenRTL87X0C APP_VERSION=$ver-bootswap > "$here/build.log" 2>&1 || { tail -30 "$here/build.log"; exit 1; }
mkdir -p "$here/out"
cp output/$ver-bootswap/OpenRTL87X0C_$ver-bootswap_ota.img "$here/out/"
ls -l "$here/out"
