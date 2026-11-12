# Hardware inputs (pinned copies)

| File | What | Source | sha256 |
|---|---|---|---|
| NDI_1W_RevA0.net | KiCad netlist, NDI 1 W LoRa radio board Rev A0 (613 parts, 375 nets) | Drive folder "Dart pcb", NDI_1W_RevA0_files (2).zip, out/schematic.net, netlist stamp 2026-11-11 12:24:47 | e86142cb8ccedde0424e884f4840f8926cb669946edda010dfd70e88d7d3ddeb |

- Cross-check: the newest board page (artifact published 2026-11-11 21:47 UTC) has identical connectivity (1,697 connected pins, 0 differences).
- NOT yet here: docs/firmware_interface.md (only in NDI_1W_RevA0_files (3).zip, 13.8 MB, over the Drive connector's 10 MB limit). When it arrives, any difference from pin_table.csv is reported and the netlist wins.
- Design source of truth is scripts/ndi_design.py in the hardware package, not this repo.
