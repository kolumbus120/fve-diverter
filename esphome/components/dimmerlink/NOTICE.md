# DimmerLink — ESPHome component (modified copy)

Original: <https://github.com/robotdyn-dimmer/DimmerLink> (`components/dimmerlink`, commit
`2d4e425`, 2026-08-16), © 2024 RBDimmer, **MIT License** (see [`LICENSE`](LICENSE), the original
license text from `esphome/LICENSE` of that repository). This folder stays under the MIT
license; the rest of this repository is GPL-3.0.

## Change against the original

`DimmerLinkHub::read_register()` in `dimmerlink.cpp`: DimmerLink firmware 1 returns the value of
the register from the **previous** request (verified with a register dump; repeated start, STOP
or a pause make no difference). Fix: every byte is read twice — the first read sets the register
pointer, the second one returns the correct value. Writes are unchanged.

Without the fix, reading back the level / frequency / period / version returns nonsense
(e.g. level 49–50 %, period 4096 µs). With it: 50 Hz, 10 000 µs, FW 1, level 36 % → 35 %.
