# Hướng dẫn đặt hàng JLCPCB — CM4 Security Gateway Rev B

File dùng để đặt: `gerber.zip`, `bom_jlc.csv`, `cpl_jlc.csv` (cùng thư mục này).

## 1. Đặt PCB (tải `gerber.zip` lên jlcpcb.com)

| Mục | Chọn | Ghi chú |
|---|---|---|
| Base Material | FR-4 | |
| Layers | **6** | |
| Dimensions | 150 × 105 mm | tự nhận từ gerber |
| PCB Thickness | **1.6 mm** | |
| Impedance Control | **Yes — stackup JLC06161H-3313** | bề rộng đường đã tính theo bộ này; nếu trang đặt hàng không còn mã này, chọn bộ 6 lớp 1.6 mm có prepreg 3313 giữa L1–L2 và L5–L6 và báo lại để tính lại bề rộng (rủi ro R7) |
| Material Type | FR4 TG155 (mặc định của 6 lớp) | |
| Surface Finish | **ENIG** (1U") | bắt buộc: đầu nối DF40 và LQFP bước 0.4 mm |
| Outer / Inner Copper Weight | 1 oz / 0.5 oz | |
| Via Covering | **Epoxy Filled & Capped** (mặc định, miễn phí với bo 6 lớp) | các IC có đế tản nhiệt (U101, PCIe switch, NIC…) có via tản nhiệt trong pad đế — lấp+phủ để thiếc không chảy xuống via; via nhỏ nhất Ø0.40 mm / khoan 0.20 mm |
| Min via hole / diameter | 0.2 mm / 0.40 mm | nằm trong năng lực 6 lớp |
| Solder mask / Silkscreen | tùy chọn (xanh / trắng) | |
| Edge Rails / Fiducials (bước SMT) | **Added by JLCPCB** | đầu nối RJ45/USB nhô khỏi mép trước nên máy SMT cần rail kẹp; rail do JLC thêm có sẵn fiducial (bo không đặt fiducial riêng) |
| Remove Order Number | Specify a location hoặc Yes | |
| Gold Fingers / Castellated | No | |

Bảng trở kháng yêu cầu (ghi vào ô ghi chú nếu được hỏi):

| Loại | Lớp | Tham chiếu | Rộng / khe (mm) | Mục tiêu |
|---|---|---|---|---|
| Vi sai PCIe + USB | L1 | L2 | 0.15 / 0.15 | 90 Ω |
| Vi sai Ethernet MDI | L1 | L2 | 0.125 / 0.18 | 100 Ω |
| Vi sai trên L3 (clock, liên kết switch, MDI WAN) | L3 | L2 + L4 | như L1 | 85–100 Ω (đoạn ngắn / tần số thấp, xem design-doc §10) |

## 2. Đặt PCBA

| Mục | Chọn |
|---|---|
| PCBA Type | **Standard** (bo 6 lớp, lắp 2 mặt, có linh kiện bước 0.4 mm) |
| Assembly Side | **Both** (mặt trên 255 vị trí, mặt dưới 142 vị trí) |
| Tooling holes | Added by JLCPCB |
| Confirm Parts Placement | **Yes** (bắt buộc — xem mục 4) |
| BOM | `bom_jlc.csv` (88 dòng, 397 linh kiện) |
| CPL | `cpl_jlc.csv` (397 vị trí) |

Linh kiện xuyên lỗ (12 vị trí: J101, J201, J202, J301, J601, J701, J801, J901, J1001, J1101, JP201, SW1101) đều có mã LCSC. JLC lắp bằng dịch vụ hàn tay/sóng (tính thêm phí);
nếu muốn giảm phí thì bỏ chọn các dòng này ở bước chọn linh kiện và tự hàn.

`U201A`, `U201B` trong BOM/CPL là **hai đầu nối Hirose DF40C-100DS-0.4V** của CM4 (trên schematic là một ký hiệu U201).

## 3. Linh kiện JLC KHÔNG lắp (tự chuẩn bị)

| Tham chiếu | Giá trị | Lý do |
|---|---|---|
| H201 | M3 | không có mã LCSC (điểm đo / lỗ vít / pin) |
| H202 | M3 | không có mã LCSC (điểm đo / lỗ vít / pin) |
| H203 | M3 | không có mã LCSC (điểm đo / lỗ vít / pin) |
| H204 | M3 | không có mã LCSC (điểm đo / lỗ vít / pin) |
| TP101 | +12V | không có mã LCSC (điểm đo / lỗ vít / pin) |
| TP102 | +5V | không có mã LCSC (điểm đo / lỗ vít / pin) |
| TP103 | +3V3 | không có mã LCSC (điểm đo / lỗ vít / pin) |
| TP104 | +3V3_SW | không có mã LCSC (điểm đo / lỗ vít / pin) |
| TP105 | +1V0 | không có mã LCSC (điểm đo / lỗ vít / pin) |
| TP106 | GND | không có mã LCSC (điểm đo / lỗ vít / pin) |
| TP107 | GND | không có mã LCSC (điểm đo / lỗ vít / pin) |
| TP108 | PERIPH_EN | không có mã LCSC (điểm đo / lỗ vít / pin) |
| TP201 | RUN_PG | không có mã LCSC (điểm đo / lỗ vít / pin) |
| TP202 | PCIE_RST_N | không có mã LCSC (điểm đo / lỗ vít / pin) |
| TP401 | AVDD_1V0 | không có mã LCSC (điểm đo / lỗ vít / pin) |
| TP501 | AVDD_1V0 | không có mã LCSC (điểm đo / lỗ vít / pin) |
| TP601 | V1P0 | không có mã LCSC (điểm đo / lỗ vít / pin) |
| TP701 | V1P0 | không có mã LCSC (điểm đo / lỗ vít / pin) |
| TP801 | V1P0 | không có mã LCSC (điểm đo / lỗ vít / pin) |
| TP901 | V1P0 | không có mã LCSC (điểm đo / lỗ vít / pin) |
| TP1001 | USBC_VBUS | không có mã LCSC (điểm đo / lỗ vít / pin) |
| TP1101 | V_KEEP | không có mã LCSC (điểm đo / lỗ vít / pin) |
| TP1102 | SRAM_VCC | không có mã LCSC (điểm đo / lỗ vít / pin) |
| TP1103 | TAMPER_OPEN | không có mã LCSC (điểm đo / lỗ vít / pin) |
| — | Raspberry Pi CM4 (eMMC, không WiFi) | tự gắn lên 2 đầu nối DF40 + 4 trụ M2.5 cao 1.5 mm |
| BT1101 | pin CR2032 | tự lắp vào đế pin |
| J1101 | jumper 2.54 mm | đặt lên header TAMPER_EXT khi chưa có công tắc ngoài |

## 4. Việc phải kiểm tra trên trang JLC trước khi thanh toán

1. **Chiều xoay linh kiện**: file CPL đã cộng hiệu chỉnh góc theo bảng quen dùng cho thư viện JLC, nhưng không thể
   kiểm chứng ngoại tuyến. Ở màn hình xem trước vị trí, kiểm tra chấm chân 1 của: U401, U501 (LQFP-128), U601–U901
   (QFN-32), U101, U102, U103, U1001–U1006, U1101–U1103, các diode (D101–D104, D201–D203, D1101, D1102), LED, tụ hóa C101,
   các transistor SOT-23 (Q101, Q201, Q1101–Q1104), thạch anh Y601–Y901, Y1101, công tắc SW1001 (BOOT/eMMC), SW201, SW1101,
   đế pin BT1101 (cực + theo chữ trên lụa), đầu nối J1002, và **U201A/U201B (DF40, 270°)** — hai đầu nối phải song song, khít
   đúng 2 nhóm pad. Nếu lệch, xoay ngay trên trang (JLC cũng soát lại và hỏi qua email khi bật Confirm Parts Placement).
2. **Tồn kho**: giá và kho lấy tại thời điểm xuất gói (`../07_bom_netlist/bom.csv`). Mã hết hàng → chọn mã thay thế
   cùng thông số hoặc đặt trước (pre-order). **Chú ý RTL8111H-CG (C2761340, U601–U901, 4 con/bo)**: kho có lúc chỉ còn vài
   con — nếu thiếu, dùng *Pre-order / Global Sourcing* của JLC cho mã này, hoặc đặt ít bo hơn (2 bo = 8 con). DF40C
   (C3642394, 2 con/bo) cũng kiểm tra đủ số lượng.
3. Hai đầu nối DF40 phải nằm đúng mặt trên, song song, cách nhau 33 mm.

## 5. Kiểm tra chéo số lượng (sinh tự động)

- Linh kiện trên schematic: 420; BOM JLC: 397; CPL: 397 (U201 tính là 2 đầu nối) → **ĐẠT**
  (chi tiết ở `crosscheck.json`).

## 6. Ước tính chi phí (5 bo)

| Khoản | Ước tính |
|---|---|
| Linh kiện | ≈ 56.7 USD/bo |
| Phí nạp linh kiện extended | 53 mã × ~3 USD (một lần cho cả đơn) |
| PCB 6 lớp ENIG 150 × 105 mm, 5 bo | ~60–90 USD |
| Công lắp Standard 2 mặt + linh kiện xuyên lỗ | ~60–100 USD |
| CM4 (tự mua) | theo cấu hình RAM/eMMC |
