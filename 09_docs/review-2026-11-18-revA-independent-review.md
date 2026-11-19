# Review độc lập Rev A (gói release) — CM4 Security Gateway

Ngày: 2026-11-18 · Phạm vi: `hardware/` (schematic + PCB đã đi dây), `out/release/rev-a/` (BOM/CPL/Gerber/báo cáo), tài liệu.
Không lặp lại các mục đã đóng của review giai đoạn 1. Đảo cực PCIe RX và hoán đổi cổng xuôi là chủ ý — không xét.

**Cách kiểm**: netlist `out/release/rev-a/07_bom_netlist/cm4-gateway.net.xml` (đối chiếu từng chân), đọc hình học PCB bằng
`pcbnew` 10.0.6 (pad, track, via, zone theo từng net), chạy lại `kicad-cli pcb drc` (kết quả trùng `05_reports/drc.json`:
0 lỗi, 78 cảnh báo, 0 chưa nối, 0 lệch parity; SHA256 của PCB trùng `08_source`), so khớp `bom_jlc.csv` ↔ `cpl_jlc.csv`
↔ PCB (397 = 397, không lệch tên), đọc `scripts/export_release.py` (ROT_FIX, toạ độ), header Gerber/Excellon/gbrjob,
datasheet trong `docs/datasheets/` (PI7C9X2G404SL, RTL8111H, SLB9670, 23LCV1024, CM4).

## Bảng phát hiện

| ID | Mức | Vị trí | Vấn đề | Sửa cụ thể |
|---|---|---|---|---|
| R1 | **BLOCKER** | net `+12V`: U101.2 (VIN), C104/C105/C106, `cm4-gateway.kicad_pcb` | **Chân VIN của buck 5 V chỉ được nối bằng đường 0.12 mm.** Toàn bộ đồng chạm pad U101.2 là chuỗi F.Cu 0.12 mm dài ≈ 5 mm: (72.35,53.35)→(73.45,54.35)→(73.45,54.85)→(73.15,55.15)→(70.95,55.15)→(70.15,54.35) tới via (70.0,54.1). Tụ vào C104/C105 (10 µF) tới via đó qua In2; C106 100 nF qua 0.3 mm + via. Nguồn từ Q101/C101 tới cụm này là **một** đường B.Cu 0.3 mm dài ≈ 18 mm (66.2,37.7)→(66.2,50.3)→(70.0,54.1) qua 2 via Ø0.3. Hệ quả: (a) dòng vào ~1–2.1 A DC cộng dòng xung AC (RMS tới ~2.9 A ở 4.5 A tải) đi qua cổ 0.12 mm → nóng quá mức / có thể đứt; (b) không có tụ nào sát chân VIN — vòng nóng của buck không đóng, VIN/SW sẽ dao động mạnh. Net class `PWR_HV` khai 1.0 mm nhưng DRC không kiểm bề rộng theo class (`connection_width` = warning, `min_connection` = 0) nên không bị bắt. | Đi lại: đổ đồng F.Cu ≥ 1.5 mm (hoặc zone `+12V`) từ Q101 S/C101+ → C104/C105 → U101.2; đặt C106 ngay giữa pad 2 và GND (≤ 1 mm), C104 ≤ 2 mm; xoá các đoạn 0.12/0.3 mm. Thêm luật `.kicad_dru`: `(rule pwr_hv_w (condition "A.NetClass == 'PWR_HV'") (constraint track_width (min 0.8mm)))` và tương tự `PWR` ≥ 0.3 mm (loại trừ stub chân CM4 bằng điều kiện theo footprint, không theo Reference). Nếu bo đã làm: câu dây 0.5 mm² từ C104+ tới U101.2 và từ C101+ tới C104+. |
| R2 | **BLOCKER** | `cpl_jlc.csv` U102, U103 (TSOT-23-6) vs U1002–U1005 (SOT-23-6); `export_release.py` ROT_FIX | Hai footprint có **hình học pad giống hệt** (pad 1 tại (−1.137, −0.95), 3 chân mỗi bên — kiểm bằng pcbnew), và LCSC dùng cùng quy ước gói SOT-23-6 cho cả hai, nhưng ROT_FIX chỉ khớp `^SOT-23` → U1002–U1005 được +180°, **U102/U103 được 0°**. Một trong hai nhóm chắc chắn lệch 180°. Với TPS563201 xoay 180°: VIN rơi vào chân VBST, GND vào VFB → hỏng U102/U103 và chập +5V; với USBLC6 xoay 180°: GND↔VBUS. | Thêm `(r"^TSOT-23", 180)` vào ROT_FIX (đồng nhất với SOT-23-6), xuất lại CPL (U102/U103 → 180). Ở bước "Confirm Parts Placement" của JLC kiểm chấm chân 1 của **cả 6 IC SOT-23-6/TSOT-23-6** trước khi duyệt. |
| R3 | MAJOR | net `/Power/SW_5V`: U101.8, L101.1, D104.1 | (a) Dòng cuộn cảm (tới 4.5 A + gợn) từ pad U101.8 (mép phải x = 78.45) sang đường 1.0 mm (đầu tròn bắt đầu x = 78.65) chỉ nối bằng **đoạn 0.15 mm**. (b) Diode bắt D104 (cathode ở (80.4,59.4), cách chân SW ≈ 8 mm) nối về SW qua **In2 1.0 mm (đồng 0.5 oz) + 2 via Ø0.3 nối tiếp**; anode GND ở (80.4,66.2) cách GND tụ vào C104/C105 ≈ 15 mm. Vòng nóng của buck không đồng bộ (tụ vào → FET cao → D104) lớn và có điện cảm via → ringing âm trên SW, EMI; mỗi via mang ~2.6 A trung bình ở tải tối đa. | Đặt D104 sát U101 trên F.Cu, cathode nối pad 8 / L101.1 bằng đồng ≥ 1.5 mm cùng lớp, anode chung điểm GND với C104/C105; bỏ cổ 0.15 mm (cho đường 1.0 mm vào thẳng pad). Đây cũng chính là mục S3 của GĐ1 — bố trí đã sửa nhưng đi dây làm hỏng lại. |
| R4 | MAJOR | `/Power/SW_3V3`, `/Power/SW_1V0`, `/Power/BST_*`: U102/L102/C117, U103/L103/C123 | L102/L103 đặt với pad **ngõ ra** quay về phía IC, pad SW ở phía xa: nút SW đi 0.3 mm vòng qua thân cuộn cảm (~6–8 mm), và tụ boot C117/C123 nối về SW qua đường vòng thêm ~8–13 mm (ví dụ (43.35,51.0)→(42.45,53.7)→(43.75,55.0)→(47.95,55.0)→C117). Vòng boot dài làm dao động cổng FET cao, nút SW dài phát xạ gần cụm switch PCIe/clock. | Xoay L102/L103 180° (pad 1 về phía chân SW), C117/C123 đặt ngay giữa chân 6 (VBST) và chân 2 (SW), nút SW ≤ 3 mm, rộng ≥ 0.6 mm. |
| R5 | MINOR | SW1001, J201, JP201, J202, J1101 (F.Silkscreen); `docs/BRINGUP.md` bước 4.1 | BRINGUP ghi "trên lụa có nhãn BOOT / eMMC ở hai đầu công tắc" nhưng PCB **không có** text đó (chỉ có các text: 12V DC, DEBUG, FLASH, CR2032, SW1/SW2, USB, TAMPER, LAN1–4, WAN, CM4, tên bo). J201 (GLOBAL_EN), JP201 (EEPROM_WP), J202 (FAN), J1101 (TAMPER_EXT) chỉ có ref. Chỉ 53/≈400 ref hiển thị; text 0.8 mm / nét 0.12 mm (< nét tối thiểu 0.15 mm của JLC → dễ nhoè). | Thêm text "BOOT ◄ ► eMMC" cạnh SW1001 (chiều xác định theo pad 1 = GND, x = 142.25), "PWR", "WP", "FAN +", "TAMPER" cạnh header; nét text ≥ 0.15 mm, cao ≥ 1.0 mm. Sửa BRINGUP cho khớp. |
| R6 | MINOR | `06_fabrication/ORDERING.md` §2 | Liệt kê U101 và J1002 vào nhóm "xuyên lỗ, có thể bỏ chọn và tự hàn". U101 là HSOP có via tản nhiệt trong footprint (pad PTH 0.2 mm), J1002 là USB-C SMD bước 0.5 mm + 4 chân giữ — không hợp hàn tay. | Script chỉ coi linh kiện là THT khi **không** có pad SMD; ghi rõ U101/J1002 phải để JLC lắp SMT. |
| R7 | MINOR | U401/U501 (EP: 13/16 via Ø0.25), U601–U901 (4 via/EP); ORDERING §1 "Via Covering" | Có via trong pad tản nhiệt (mặt trên hở theo mặt nạ của EP, mặt dưới tented) trong khi ORDERING ghi "KHÔNG dùng via-in-pad" và cho chọn "Tented". Hàn lỗ hút thiếc / bọt khí dưới EP. | Chọn "Epoxy Filled & Capped" (JLC 6 lớp) hoặc chấp nhận và sửa câu trong ORDERING. |
| R8 | MINOR | `export_release.py` dòng 232–233; CPL U1001, Y601–Y901, SW1001, J1002 | (a) Nhánh lật góc cho mặt dưới là code chết (`if False`); hiện vô hại vì mặt dưới chỉ có R/C/FB không phân cực — sẽ sai nếu sau này đặt linh kiện phân cực ở mặt dưới. (b) U1001 (MSOP-10, 270°), Y601–Y901 (3225-4 chân, 0°), SW1001 (PCM12, 0°) dựa vào quy ước chung; một số bảng hiệu chỉnh cộng đồng dùng giá trị khác cho các họ này (không kiểm được ngoại tuyến). Thạch anh xoay 90° = 2 chân tinh thể rơi vào pad GND → NIC không chạy. | Sửa nhánh mặt dưới (`(180 − rot − fix)` rồi kiểm). Đưa U1001, Y601–Y901, SW1001, J1002 vào danh sách bắt buộc soát ở màn hình xem trước JLC (ORDERING §4 hiện thiếu Y và SW1001). |
| R9 | MINOR | `05_reports/drc.json` | 13 `track_dangling` + 6 `via_dangling`: đáng chú ý là stub 2.65 mm treo trên **cả XTAL1 và XTAL2** của 4 NIC (vd. `/LAN1/XTAL1` tại (109.65,105.8)), stub trên `/SW1/AVDD_1V0`, `/SW2/CVDD_3V3`, `USBC_CC2`; via treo trên P1..P4_RST_N, SW2_RST_N, `/LAN1/CLKREQ_N`. Không làm hỏng mạch nhưng stub ở nút thạch anh thêm điện dung/ăng-ten. | Xoá stub/via treo trong `route.py`/`patch_rev_a.py` rồi xuất lại; mục tiêu 0 cảnh báo track/via dangling. |
| R10 | MINOR | net `+12V_JACK` | Toàn bộ dòng vào (tới 2.8 A ở 9 V) đi qua **1 via Ø0.3** từ B.Cu lên F101. | Thêm ≥ 3 via 0.6/0.3 song song (làm cùng lúc với R1). |
| R11 | MINOR | PCB (toàn bo) / ORDERING | Không có fiducial; RJ45/USB-A/micro-USB/USB-C nhô khỏi mép trước → JLC phải thêm rail (tính phí) và căn LQFP-128/DF40 bước 0.4 mm theo pad. | Thêm 3 fiducial toàn cục mỗi mặt (Ø1 mm, mở mặt nạ Ø2 mm); ghi trong ORDERING là cần edge rail. |
| R12 | MINOR | BOM U201A/B (C3642394), U601–U901 (C2761340), U1101, U1103 | Tồn kho tại lúc xuất: DF40C 24 (cần 2/bo), RTL8111H 152, SLB9670 141, 23LCV1024 226. DF40 giới hạn đơn ≤ 12 bo và dễ hết. | Đặt trước/giữ hàng (JLC "Parts pre-order") cho DF40C trước khi đặt PCBA. |
| R13 | MINOR | `hardware/cm4-gateway.kicad_dru` rule `cap_vi_sai_cach_net_khac` | Chú thích ghi khe hở cặp vi sai tới net khác ≥ 0.15 mm, luật thật là 0.11 mm (design doc §10 cũng ghi 0.15). | Sửa luật thành 0.15 mm hoặc sửa tài liệu. |

## Đã kiểm và thấy đúng (không cần sửa)

- **Fab set**: đủ 6 lớp đồng, 2 mask, 2 paste, 2 silk, Edge.Cuts, PTH + NPTH Excellon, gbrjob (6 lớp, 1.6 mm, ENIG,
  impedance = true). Gerber và khoan cùng gốc (không đặt aux origin; `--drill-origin plot`), toạ độ CPL = toạ độ Gerber
  (X tuyệt đối, Y đảo dấu) — kiểm bằng header và vị trí lỗ.
- **Stackup** trong PCB (3313 0.0994 / lõi 0.55 / 2116 0.1088 / lõi 0.55 / 3313, đồng 1 oz ngoài, 0.5 oz trong) khớp mô tả
  JLC06161H-3313 trong ORDERING. Tính lại: L1 0.15/0.15 → Zdiff ≈ 88 Ω (≈ 85 Ω có mặt nạ), 0.125/0.18 → ≈ 100 Ω; trong ±10 %.
- **BOM ↔ CPL ↔ schematic**: 397/397, tên khớp hoàn toàn; 24 linh kiện không lắp (TP, H) đúng là không có mã LCSC.
  Mã LCSC/MPN khớp gói footprint (đối chiếu cột MPN trong `bom.csv`). Chỉ linh kiện thụ động không phân cực ở mặt dưới.
- **Nguồn**: Q101 AO4407A đúng chiều (S phía tải, cổng kéo GND, Zener 12 V kẹp Vgs), TVS sau Q101, chân TPS54560B /
  TPS563201 đúng, PERIPH_EN từ +3V3 của CM4 (không cấp ngược).
- **PI7C9X2G404SL**: RXPOLINV_DIS (chân 24) để hở = kéo xuống nội → **bật** tự sửa đảo cực (DS40068 §3.2) — điều kiện cần cho
  phương án đảo cực có chủ đích. Strap TEST1/2, TEST3–6, PWR_SAV, TMS, TRST_L, SMB, CLKBUF_PD đúng §3.2–3.4. Reset/clock
  từng cổng khớp với gán cổng đã đổi (DWNRST_L1 → NIC của cổng 1, v.v.).
- **RTL8111H, USB (FSUSB42 SEL = nRPIBOOT, CC 5.1 k, TPS2553 EN cao, USBLC6), CH340C (V3 = VCC = 3.3 V), TPM (GPIO/PP để hở
  được phép, NC 29/30 để hở), SRAM/tamper (Q1101–Q1104, D1102, V_KEEP)**: đúng chân, đúng logic.
- **CM4**: mọi chân dùng đúng; OTG_ID nối GND, CLK_nREQ nối GND, GPIO_VREF = +3V3. Cấp +5V cho CM4: 6 chân, mỗi chân
  1 via 0.45/0.2 xuống mặt phẳng L5 — đủ cho ~2 A. Không có linh kiện mặt trên dưới module; không có đồng/linh kiện trong bán
  kính 3.5 mm quanh 4 lỗ CM4 và 4 lỗ M3.

## Kết luận

**Chưa nên đặt hàng gói `rev-a` hiện tại.** Schematic đạt (không thấy lỗi nguyên lý mới), file sản xuất đủ và nhất quán, DRC
sạch lỗi — nhưng có hai lỗi chặn mà DRC không bắt được: (R1) chân VIN của buck 5 V chỉ nối bằng đường 0.12 mm và tụ vào nằm sau
cổ đó, gần như chắc chắn quá nhiệt/không ổn định khi tải CM4 + NIC; (R2) CPL xoay U102/U103 (TSOT-23-6) lệch 180° so với
U1002–U1005 (SOT-23-6) có cùng hình học pad — một trong hai nhóm sẽ bị lắp ngược và phá rail nguồn. Cả hai sửa được bằng script
trong vài giờ (đi lại khu nguồn + thêm luật bề rộng theo net class, thêm `^TSOT-23` vào ROT_FIX). Nên sửa luôn R3–R4 (vòng nóng
và nút SW của ba buck) trong cùng lần đi lại khu nguồn, xuất lại gói, rồi mới đặt; các mục MINOR có thể làm cùng lúc hoặc ghi cho Rev B.
