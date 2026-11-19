# Review độc lập Rev B (gói release) — CM4 Security Gateway

Ngày: 2026-11-19 · Phạm vi: `hardware/cm4-gateway.kicad_pcb` (SHA256 `2af0486b…` = `08_source`), `out/release/rev-b/`.
Cách kiểm: chạy lại `kicad-cli pcb drc --refill-zones --severity-all --schematic-parity` và `kicad-cli sch erc --severity-all`
trên bản sao; đọc hình học bằng `pcbnew` 10.0.6 (track/via/zone/pad theo net, đảo vùng đổ đồng); render F.Cu/F.Silk để soát;
đối chiếu `bom_jlc.csv` ↔ `cpl_jlc.csv` ↔ PCB và bảng `ROT_FIX`; `gbrjob`, file khoan, `SHA256SUMS` (tất cả OK).
Không sửa file dự án nào.

## Kết luận

**Chưa đặt PCBA được ngay.** Thiết kế không còn lỗi chặn kiểu chắc chắn hỏng như rev A (R1, R2 đã sửa đúng). Lý do chặn
là **tồn kho**: RTL8111H-CG chỉ còn 1 con trong khi cần 20 (B1). Thêm vào đó có hai mục MAJOR cùng loại với R1/R3 mà phản hồi
rev A ghi là đã sửa nhưng thực tế mới sửa một phần (M1, M2). Cả hai sửa bằng script trong khoảng 1 giờ, nên sửa trong lúc chờ
giải quyết B1. Riêng phần PCB trần thì đặt được.

## BLOCKER

| ID | Vấn đề | Bằng chứng | Sửa |
|---|---|---|---|
| B1 | Thiếu hàng RTL8111H-CG cho PCBA | `07_bom_netlist/bom.csv`: U601–U901 C2761340, tồn kho **1**, cần 4/bo × 5 bo = 20 (lúc review rev A còn 152). DF40C C3642394 còn 36 (cần 10, ổn nhưng ít dư). | Kiểm tra lại kho khi đặt. Nếu vẫn thiếu: đặt trước hoặc nhờ JLC tìm hàng (pre-order / global sourcing) trước khi đặt PCBA, hoặc tìm mã LCSC khác cho cùng MPN. Không đặt PCBA khi BOM còn báo thiếu. |

## WARNING

| ID | Mức | Vấn đề | Bằng chứng | Đề xuất |
|---|---|---|---|---|
| M1 | MAJOR | Tụ vào của U102/U103 (TPS563201) chỉ nối với chân VIN bằng đường 0.12 mm. Đây là lỗi cùng loại với R1, ở công suất thấp hơn. | U102: C115+ (50.20,52.65) → (50.20,51.15) → chân 3 (50.36,50.95), F.Cu **0.12 mm**. DC vào qua via 0.6/0.3 đặt trong pad chân 3 rồi B.Cu 0.8 mm. U103: C121+ (50.20,74.15) ← (50.35,73.95)…(50.35,72.45), **0.12 mm**. DC vào U103 cũng chỉ qua đường 0.12 mm: F.Cu (50.35,72.45)→(49.35,72.15), via 0.4/0.2, B.Cu 0.12 mm tới (48.05,69.85), rồi B.Cu 0.4 mm. C116/C122 (100 nF) nằm phía chân 4–6, không ở trong vòng VIN–GND. Net class `PWR` khai 0.3 mm nhưng `.kicad_dru` không có luật cho class này, nên DRC không bắt. Tổng đoạn 0.11–0.12 mm: +5V 17.9 mm, +3V3_SW 31.8 mm, +1V0 4.9 mm. | Nối C115/C121 tới chân 3 bằng đồng ≥ 0.6 mm (đủ chỗ, hai pad cách nhau 0.9 mm). Đưa 100 nF về sát chân 3/chân 1. Cấp DC cho U103 bằng đường ≥ 0.4 mm. Thêm luật `A.NetClass == 'PWR'` → `track_width min 0.3mm`, chừa pad bước nhỏ theo điều kiện footprint. |
| M2 | MAJOR | R3 mới sửa một phần: các cổ hẹp đã hết, nhưng **vị trí D104 không đổi** so với rev A, nên vòng nóng của buck 5 V vẫn lớn. | D104 catốt (80.40,59.40), anốt (80.40,66.20), trùng toạ độ rev A. Chân SW (77.65,52.09) → catốt 7.8 mm. Anốt → GND của C104 (67.60,55.48) 16.7 mm, nối qua vùng đổ F.Cu. Diện tích vòng Cin → VIN → SW → D104 → GND → Cin ≈ **110 mm²**. Pad GND (chân 7 + EP) của U101 là đảo F.Cu riêng (bbox 73.1–79.6 × 50.6–56.4), chỉ nối GND qua via. Phần đã đạt: SW 1.0 mm vào thẳng pad 8, 1.5 mm L101.1 → D104, không via. | Dời D104 sát U101, ví dụ ngay dưới chân 8 hoặc giữa U101 và L101. Anốt D104 chung cụm GND với C104/C105, cách ≤ 3 mm, nối đồng F.Cu. Nối đảo GND của U101 với vùng đổ F.Cu quanh Cin. |
| W3 | MINOR | R10 mới sửa một phần: +12V_JACK không còn via, nhưng toàn bộ dòng vào vẫn đi qua **một via 0.6/0.3** ở mỗi lần đổi lớp. | VIN_FUSED: via (99.00,34.15), (79.40,34.45). +12V tới U101: via (65.00,37.80), (65.00,49.90), B.Cu 0.6 mm dài 12 mm. Đồng 0.6 mm lớp ngoài 1 oz chịu ≈ 2.2 A ở mức tăng 20 °C (IPC-2221). Dòng vào khoảng 1.5–2.2 A ở 9–12 V: đủ nhưng ít dư. | Mỗi điểm đổi lớp dùng ≥ 3 via song song. Nếu còn chỗ thì nới +12V/VIN_FUSED lên ≥ 1.0 mm. |
| W4 | MINOR | R4 đã sửa nút SW nhưng vòng boot vẫn vòng qua cuộn cảm. | SW_3V3: chân 2 → L102.1 dài 2.3 mm × 0.6 mm (đạt). Nhánh tới C117 đi tiếp 0.5 mm qua (48.05,48.0) → (48.45,47.6) → (51.82,47.6), dài ≈ 6 mm. U103/C123 giống hệt. | Chấp nhận được. Nếu đi lại M1 thì nối C117/C123 thẳng về chân 2. |
| W5 | MINOR | ORDERING §4 thiếu một số linh kiện mà phản hồi R8 hứa đưa vào danh sách xem trước. | §4 không có Y601–Y901, Y1101, SW1001, J1002, U201A/U201B (DF40, CPL 270°) và BT1101. Chiều xoay của các footprint không có trong `ROT_FIX` (thạch anh 3225 = 0°, PCM12, USB4105, MSOP) không kiểm được ngoại tuyến. | Bổ sung các ref này vào ORDERING §4. |
| W6 | MINOR | Chữ lụa đạt ngưỡng 0.8 mm / 0.15 mm nhưng thấp hơn mức JLC khuyến nghị (cao ≥ 1.0 mm). Luật DRC `min_text_thickness` = 0.08 nên không bắt được nét < 0.15 mm. | 61/72 chữ cao 0.8 mm, nét 0.15 mm; không có chữ nào < 0.8 mm hoặc nét < 0.15 mm. Mọi nét đường lụa đều 0.15 mm. | Nhãn chức năng (BOOT/eMMC, PWR BTN, EEPROM WP, TAMPER EXT, FAN 5V) nên tăng lên 1.0 mm. Đặt `min_text_thickness` = 0.15 mm. |
| W7 | INFO | Không có fiducial trên bo, chỉ dựa vào fiducial trên rail của JLC (R11). | ORDERING §1 chọn "Added by JLCPCB". Có LQFP-128 và DF40 bước 0.4 mm. | Chấp nhận được. Nếu đi lại bo, thêm 3 fiducial mặt trên. |

## Đối chiếu R1–R13 của rev A

| ID | Trạng thái rev B | Bằng chứng |
|---|---|---|
| R1 | **Đã sửa** | U101.2 → dải F.Cu 0.6 mm (70.90,53.37) → 1.0 mm (70.90,52.90)→(65.00,52.90) qua C106 (cách chân 2.1 mm), C104 (4.75 mm), C105. Không còn đoạn < 0.6 mm trên +12V/+12V_JACK/VIN_FUSED. Có luật `nguon_dong_lon_rong_toi_thieu`. |
| R2 | **Đã sửa** | `ROT_FIX` có `^TSOT-23` → 180°. CPL: U102/U103 = 180, U1002–U1005 = 180. 395/395 dòng CPL khớp công thức. |
| R3 | **Một phần** | Xem M2. |
| R4 | **Phần lớn đã sửa** | L102/L103 xoay 180°, nút SW 2.3 mm × 0.6 mm. Vòng boot và tụ vào: xem W4, M1. |
| R5 | **Đã sửa** | Có lụa BOOT (141.0,106.6) phía pad 1 = GND (142.25) và eMMC (147.3,106.6). Có thêm PWR BTN, EEPROM WP, FAN 5V, TAMPER EXT, RESET, CR2032 (+) trên. |
| R6 | **Đã sửa** | ORDERING liệt kê 12 THT: J101, J201, J202, J301, J601–J901, J1001, J1101, JP201, SW1101 (khớp pad, không còn U101/J1002). |
| R7 | **Đã sửa** | ORDERING chọn Epoxy Filled & Capped. Lựa chọn này cũng cần cho via 0.6/0.3 trong pad chân 3 của U102. |
| R8 | **Một phần** | Mặt dưới chỉ có 142 linh kiện thụ động không cực tính (C/R/L 0402/0603/1206). Danh sách xem trước còn thiếu: xem W5. |
| R9 | **Đã sửa** | DRC `--severity-all`: 0 track_dangling, 0 via_dangling. |
| R10 | **Một phần** | Xem W3. |
| R11 | Chấp nhận | Xem W7. |
| R12 | **Xấu hơn** | Xem B1. |
| R13 | **Đã sửa** | Chú thích luật khớp giá trị 0.11 mm. |

## OK (đã kiểm, không cần sửa)

- **DRC** (tự chạy, có làm lại vùng đổ, đủ mọi mức): **0 vi phạm, 0 chưa nối, 0 lệch schematic**. Bỏ qua 7 kiểu kiểm tra
  liên quan footprint/thư viện (missing_courtyard, lib_footprint_mismatch…), chấp nhận được. **ERC**: 0 vi phạm (bỏ qua 4 kiểu,
  hợp lý). Kết quả trùng `05_reports/`.
- **Gói fab**: 6 lớp đồng (L1 Top, L2–L5 Inr, L6 Bot), 2 mask, 2 paste, 2 silk, Edge.Cuts, PTH.drl (có 7 rãnh G85) +
  NPTH.drl. `gbrjob`: 150.1 × 105.1 mm (kể cả nét viền 0.1 mm, tức bo 150 × 105 mm), 6 lớp, 1.6 mm, ENIG, có kiểm soát
  trở kháng. `gerber.zip` trùng thư mục `gerber/`. `SHA256SUMS`: toàn bộ OK.
- **BOM ↔ CPL ↔ PCB**: 397 = 397, không lệch ref, mọi dòng có mã LCSC dạng `C\d+`. 25 footprint ngoài BOM (H201–H204,
  TP×20, U201 tách thành U201A/B) đều đúng loại DNP. Mặt Top 255 / Bottom 142 khớp ORDERING. Toạ độ CPL = gốc footprint,
  riêng 14 đầu nối THT dùng tâm cụm pad (chủ ý). U201A/B tại (154.96, 61.0) và (121.04, 61.0), đúng tâm hai hàng pad.
- **Cực tính**: C101 pad 1 = +12V; D104 K = SW_5V, A = GND; D102 (TVS) K = +12V; D101 K = +12V, A = gate (kẹp Vgs đúng);
  D203 K = +5V; D1101 BAT54C chung catốt = V_KEEP; D103/D201/D202 đúng chiều; BT1101 (Keystone 3034) hai tab = VBAT,
  pad giữa = GND. Q101 S = +12V, D = VIN_FUSED.
- **Công tắc/header**: SW201 RESET (123.28,95.17) và SW1001 (144.50,103.73) nằm trong bo, ngoài vùng CM4 (courtyard CM4
  117.9–158.1 × 35.9–91.1). SW1101 MX (177.04,71.42) không đè BT1101 (courtyard tới y = 63.0). J201/JP201/J202/J1101 có
  pad 1 vuông và có nhãn chức năng. Jumper cho J1101 được ghi trong ORDERING §3 và BRINGUP.
- **Đầu nối ở mép bo**: J101 nhô ra mép sau 0.75 mm. RJ45 ×5 nhô ra mép trước 2.25 mm, USB-A 2.45 mm, micro-USB 1.15 mm,
  USB-C 0.45 mm. Tất cả cùng mép y = 135.05.
- **Buck 5 V**: U101 có 6 via trong EP và 8 via GND quanh EP xuống các lớp GND trong, đủ tản nhiệt. +5V ra 1.5 mm từ L101.2
  tới C110–C113, có 16 via 0.6/0.3 xuống vùng đổ In4.
- **Lụa**: 72 chữ, tất cả cao ≥ 0.8 mm và nét ≥ 0.15 mm. 448 nét lụa đều 0.15 mm. DRC không báo silk_over_copper.
  Lưu ý: chữ "nhân đôi" khi render SVG bằng ImageMagick là lớp text ẩn của SVG, không phải lụa thật.
- **ORDERING.md**: hợp lý. Stackup JLC06161H-3313, ENIG, Epoxy Filled & Capped, PCBA Standard hai mặt, có danh sách THT,
  danh sách linh kiện không lắp (CM4, pin, jumper J1101). Phần còn thiếu: xem W5.
