# Kiểm tra linh kiện chính (P0) — tồn kho thư viện PCBA JLCPCB ngày 2026-11-11

Tra bằng `scripts/jlc_search.py` (API trang đặt hàng JLCPCB). "Kho" = số lượng JLC có thể lắp ngay.

| Vai trò | Ứng viên trong task | Kết quả | Chốt | Mã LCSC | Kho | Giá lẻ |
|---|---|---|---|---|---|---|
| PCIe switch | ASM1184e | **Không đạt** — kho 0, JLC ghi "no longer manufactured" (C2943483). ASM1182e/ASM2806/ASM1806 cũng kho 0 | **2× Diodes PI7C9X2G404SLBFDEX** ghép tầng (mỗi con 1 lên + 3 xuống) | C500767 | 2529 | $10.72 |
| NIC | RTL8111H | Đạt | RTL8111H-CG (QFN-32, LDO nội, không cần cuộn cảm) | C2761340 | 4046 | $1.95 |
| TPM | SLB9670 | Đạt | SLB9670VQ20FW785XTMA1 (VQFN-32 5×5) | C1012863 | 399 | $4.20 |
| SRAM tamper | 23LCV1024 | Đạt | 23LCV1024-I/SN (SOIC-8) | C615097 | 231 | $4.20 |
| RTC | PCF85063A | Đạt | PCF85063AT/AY (SO-8) | C5151540 | 6646 | $0.81 |
| Đầu nối CM4 | DF40C-100DS-0.4V | Đạt | DF40C-100DS-0.4V(58) ×2 (hậu tố (58)/(51) chỉ khác đóng gói) | C3642394 | 462 | $1.85 |
| RJ45 | magjack 1×4 | Không có 1×4 Gigabit trong kho | **5× HanRun HR911130A** (cổng đơn, 1000Base-T, có biến áp + LED) | C54408 | 19598 | $2.54 |
| USB mux | TS3USB221 | Có; chọn loại CM4 IO Board dùng | FSUSB42MUX (MSOP-10) | C11355 | 31312 | $0.30 |
| USB-UART | CH340C / CP2102N | Cả hai có | CH340C (SOP-16, dao động nội) | C84681 | 97232 | $0.54 |
| Buck 12V→5V | (chưa chốt) | AP64501SP của IO Board: kho 1 → loại | TPS54560BDDAR (60 V, 5 A) | C1850354 | 36025 | $0.93 |
| Buck 5V→3V3, 5V→1V0 | (chưa chốt) | Đạt | TPS563201DDCR ×2 (3 A, SOT-23-6) | C116592 | 101647 | $0.07 |
| Công tắc tamper | switch MX | Đạt | Kailh CPG151101D05 Red (tuyến tính 45 gf, hành trình tác động 2 mm, tương thích Cherry MX, THT; lỗ footprint nhận cả loại 3 chân và 5 chân) | C49234236 | 2422 | $0.11 |
| Giá pin | CR2032 | Đạt | Keystone 3034 (SMD) | C5199422 | 874 | $0.35 |
| USB-A | — | Đạt | Molex 67643-2910 (THT, nằm ngang) | C564920 | 2051 | $0.92 |
| USB-C | — | Đạt | GCT USB4105-GF-A (16 chân; có footprint + mô hình 3D chuẩn trong KiCad) | C3020560 | 18422 | — |
| micro-USB | — | Đạt | Molex 47346-0001 (có mô hình 3D chuẩn trong KiCad) | C132560 | 17065 | — |
| Jack DC | DC-005 | DC-005-20A chỉ ghi 0.5 A → loại | XKB DC-005-5A-2.0 (5 A, 57 V) | C381116 | 8145 | — |
| Nút reset | — | Đạt | Alps SKQGABE010 | C115351 | 42547 | — |
| Công tắc BOOT | — | Đạt | C&K PCM12SMTR | C221841 | 8929 | $1.27 |
| Hạt ferrite | GZ1608D601TF (450 mΩ, 0.2 A) → loại theo review C2 | Đạt | Murata BLM18PG121SN1D (50 mΩ, 2 A) | C14709 | 1804499 | $0.014 |

## Hệ quả thiết kế của việc đổi PCIe switch

- PI7C9X2G404SL chỉ có **3 cổng xuống** → cần **2 chip ghép tầng** để có 4 NIC (còn dư 1 cổng):
  `CM4 → SW1 → {NIC1, NIC2, SW2}`, `SW2 → {NIC3, NIC4}`.
- Ưu điểm: datasheet công khai đầy đủ (87 trang, có bảng chân + trình tự nguồn), **bộ đệm clock 100 MHz tích hợp** (4 ngõ ra
  HCSL/chip) nên không cần IC clock riêng; kho JLC lớn.
- Chi phí: +~$15/bo so với ASM1184e; thêm rail 1.0 V (~1.35 A cực đại cho 2 chip).
- Công suất 2 switch: điển hình 2×0.62 W, cực đại 2×1.07 W (datasheet bảng 12-8).

## Thông số đã đọc từ datasheet (dùng cho thiết kế)

- **PI7C9X2G404SL**: VDDC/AVDD/VDDCAUX 1.0 V (0.95–1.1), VDDR/CVDDR/AVDDH/VAUX 3.3 V; cấp 3.3 V trước hoặc đồng thời với 1.0 V;
  PERST# nhả sau khi nguồn + clock ổn định ≥100 ms; REXT 1.43 kΩ 1%; IREF 475 Ω 1%; ngõ ra clock thử với Rs 33.2 Ω + Rp 49.9 Ω;
  REFCLKP/N phải ghép AC 0.1 µF; REFCLKI nhận HCSL ghép DC, nếu nguồn clock ghép AC thì phải dựng lại phân cực ~0.4 V;
  EEPROM (24C04) là tùy chọn; các chân strap có điện trở kéo nội.
- **RTL8111H**: QFN-32, AVDD33/VDDREG 3.3 V, LDO nội ra REGOUT 1.0 V cấp AVDD10/DVDD10; RSET 2.49 kΩ; thạch anh 25 MHz ±50 ppm,
  ESR ≤ 30 Ω; LED mặc định tích cực thấp: LED0=10M, LED1=100M, LED2=1000M (kèm nháy khi có dữ liệu); PERSTB nhả ≥100 ms sau nguồn.
- **23LCV1024**: VCC 2.5–5.5 V; VTRIP 1.8 V (dưới mức này chuyển sang VBAT); VBAT 1.4–3.6 V; IBAT 1 µA điển hình; giữ dữ liệu tới 1.0 V.
- **SLB9670**: VDD 3.3 V (chân 8, 22), SPI: CS# 20, SCLK 19, MOSI 21, MISO 24, PIRQ# 18, RST# 17.
- **CM4**: +5 V đơn; +3.3 V out tối đa 600 mA; **không chân nào được có điện trước +5 V**; PCIe 90 Ω, lệch trong cặp < 0.1 mm;
  Ethernet 100 Ω, < 0.15 mm; USB 90 Ω; CM4 đã có tụ AC trên PCIe_TX và PCIe_CLK, phía RX cần tụ ngoài đặt gần nguồn phát;
  `PCIe_CLK_nREQ` phải được kéo để CM4 phát clock; USB_OTG_ID nối GND khi vai trò cố định.
- **HR911130A**: chân 1 = điểm giữa biến áp (chung), 2/3, 4/7, 5/6, 8/9 = bốn cặp MDI, 10 = đất vỏ (đã có 4×75 Ω + 1 nF/2 kV bên trong),
  11–12 LED xanh, 13–14 LED vàng; kích thước lỗ lấy từ bản vẽ trang 2.

## Ghi chú cập nhật (sau review độc lập)

Bảng trên phản ánh linh kiện **đang dùng trong schematic**. Tồn kho và giá của toàn bộ 100+ dòng BOM được tra lại tự động
mỗi lần xuất gói bằng `scripts/bom_check.py` (kết quả ở `out/stage1/06_bom/`): đó là nguồn đúng nhất về kho.
