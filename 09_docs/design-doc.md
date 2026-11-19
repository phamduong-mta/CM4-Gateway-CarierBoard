# CM4 Security Gateway — Tài liệu thiết kế Rev A

Ngày: 2026-11-11 · Cập nhật cho giai đoạn 2 (đã đi dây, bản final Rev A) · Đầu bài: `task.md`

Nguồn sự thật của mạch nguyên lý là `scripts/gen/design.py` (sinh ra các file `hardware/*.kicad_sch`).
Bố trí PCB sinh từ `scripts/gen/board.py`; đi dây sinh từ `scripts/gen/route.py` (bộ đi dây tự viết: `rt_core.py` +
`astar.c`). Các con số trong tài liệu này khớp với các file đó.

---

## 1. Mục đích và phạm vi

Bo mạch mang (carrier board) cho Raspberry Pi **CM4 bản eMMC, không WiFi**, dùng làm gateway bảo mật mạng
(IPsec/WireGuard). Mục đích chính là học tập, sản xuất vài bo ở JLCPCB (PCB + lắp ráp).

**Có trong Rev A**

| Hạng mục | Thực hiện |
|---|---|
| WAN | 1 cổng RJ45 từ PHY Gigabit có sẵn trên CM4 |
| LAN | 4 cổng RJ45, mỗi cổng 1 NIC RTL8111H riêng, qua 2 PCIe switch ghép tầng |
| USB | 1 cổng USB-A host (giới hạn dòng ~1.2 A) |
| Nạp eMMC | 1 cổng USB-C "FLASH" (chỉ dữ liệu) + công tắc BOOT bên trong vỏ |
| Debug | 1 cổng micro-USB "DEBUG" → CH340C → UART0 của CM4 |
| Bảo mật | TPM 2.0 SLB9670, RTC PCF85063A, pin CR2032, SRAM 23LCV1024 bị xóa khi mở vỏ (MX switch) |
| Nguồn | Jack DC 5.5×2.1 mm ở mặt sau, 12 V (chịu 9–24 V) |

**Không làm**: HDMI, audio, CSI/DSI, NVMe, WiFi/BT, PoE, 2.5GbE, header 40 chân, MCU phụ, vỏ hộp.

**Coi là thất bại**: gói sản xuất còn lỗi ERC/DRC hoặc lỗi bị giấu bằng luật theo từng linh kiện; NIC không có driver
sẵn trong kernel; linh kiện không lắp được ở JLC mà không ghi rõ; cấp ngược điện vào CM4 hoặc vào SRAM.

---

## 2. Thay đổi so với đầu bài (đã ghi trong `docs/notes/decisions.md`)

1. **PCIe switch: ASM1184e → 2× Diodes PI7C9X2G404SL ghép tầng.** ASM1184e hết hàng và bị JLC ghi "ngừng sản xuất".
   PI7C9X2G404SL có 1 cổng lên + 3 cổng xuống nên cần 2 chip cho 4 NIC (dư 1 cổng). Chi phí tăng ~15 USD/bo, thêm rail 1.0 V.
2. **RJ45**: 5 cổng đơn HR911130A (không có khối 1×4 Gigabit trong kho JLC).
3. **Adapter khuyến nghị 12 V/3 A** (tối thiểu 2 A) thay cho 12 V/2 A.
4. **Kích thước bo 150 × 105 mm** (mục tiêu ban đầu ~130 × 100): 5 RJ45 + 3 USB + 2 lỗ vít cần 150 mm chiều ngang.
5. **Thứ tự cổng mặt trước** (trái → phải, nhìn từ trên, mặt trước ở dưới): LAN4, LAN3, LAN2, LAN1, USB-A, DEBUG, FLASH, WAN.
   Lý do: PCIe và USB nằm trên đầu nối bên trái của CM4, Ethernet nằm trên đầu nối bên phải → các cặp vi sai ngắn và ít cắt nhau.
6. Tín hiệu báo mở vỏ tên `TAMPER_OPEN` (mức cao = mở).

Thay đổi ở giai đoạn 2 (sau khi chủ dự án duyệt giai đoạn 1; chi tiết ở `decisions.md`, các dòng "(GĐ2)"):

7. **Công tắc chống mở vỏ là switch bàn phím cơ Kailh Red** (CPG151101D05, C49234236; tương thích Cherry MX, lắp được
   loại 3 chân và 5 chân). Vỏ đè trục xuống ≥ 2 mm = thông mạch; nhả = ngắt → xóa SRAM.
8. **Đảo cực P/N tại mọi đầu thu PCIe** (switch, NIC, CM4) để cặp vi sai không bắt chéo; clock không đảo.
9. **Gán cổng xuôi**: SW1 cổng 1 → LAN2, cổng 2 → LAN1, cổng 3 → SW2; SW2 cổng 1 → LAN4, cổng 2 → LAN3.
10. **Dời linh kiện bên trong**: SW2 về (23.6, 50); tụ AC/Rs/Rp xếp theo cặp; khu USB xếp lại. Cổng, kích thước bo, lỗ vít giữ nguyên.

---

## 3. Kiến trúc

Hình: `out/stage1/01_overview/block-diagram.png`, `power-tree.png`.

```
12V jack → F101 → Q101 (chống ngược) → +12V → U101 TPS54560B → +5V
   +5V → CM4, USB-A (U1003), quạt, U102 → +3V3_SW (NIC, I/O switch), U103 → +1V0 (lõi switch)
   CM4 +3V3 (ra) → TPM, USB mux, CH340C, SRAM, kéo lên; và bật U102/U103 qua PERIPH_EN

CM4 PCIe ×1 → SW1 (U401) ─ cổng 1 → NIC1 (U601) → LAN1
                          ├ cổng 2 → NIC2 (U701) → LAN2
                          └ cổng 3 → SW2 (U501) ─ cổng 1 → NIC3 (U801) → LAN3
                                                  ├ cổng 2 → NIC4 (U901) → LAN4
                                                  └ cổng 3: dự phòng, để hở
CM4 MDI → J301 (WAN)        CM4 USB2 → U1001 mux → USB-A (bình thường) / USB-C (BOOT)
CM4 UART0 → CH340C → micro-USB     CM4 SPI0 → TPM (CE1), SRAM (CE0)     CM4 SDA0/SCL0 → RTC
```

### Cấu trúc schematic (8 file, 12 trang, 420 linh kiện, 525 net)

| Sheet | File | Số tham chiếu | Nội dung |
|---|---|---|---|
| Gốc | `cm4-gateway.kicad_sch` | — | sơ đồ khối + nối các sheet |
| Power | `power.kicad_sch` | 1xx | đầu vào, bảo vệ, 3 bộ hạ áp, PERIPH_EN, test point |
| CM4 | `cm4.kicad_sch` | 2xx | module, LED, reset, jumper, quạt, phân cực clock PCIe, lỗ vít |
| WAN | `wan.kicad_sch` | 3xx | RJ45 WAN, nối CHASSIS–GND |
| SW1, SW2 | `pcie_switch.kicad_sch` (dùng 2 lần) | 4xx, 5xx | PI7C9X2G404SL + clock + strap + decoupling |
| LAN1..4 | `lan_nic.kicad_sch` (dùng 4 lần) | 6xx..9xx | RTL8111H + RJ45 |
| USB_Debug | `usb_debug.kicad_sch` | 10xx | mux, USB-A, USB-C, CH340C |
| Security | `security.kicad_sch` | 11xx | TPM, RTC, pin, SRAM + mạch tamper |

---

## 4. Nguồn

### 4.1 Đầu vào và bảo vệ
- J101 DC-005-5A-2.0 (5 A, tâm dương). Chân vỏ và chân công tắc đều nối GND.
- F101 cầu chì 1206 4 A/32 V → Q101 AO4407A (P-MOSFET, D về phía jack, S về phía tải; cổng kéo GND qua 100 kΩ,
  kẹp Vgs bằng Zener 12 V D101) → `+12V`.
- D102 SMBJ24A (TVS một chiều) sau Q101; C101 100 µF/35 V + tụ gốm 10 µF/50 V.
- Dải làm việc 9–24 V. Giới hạn bởi F101 (32 V), Q101 (30 V) và TVS; U101 chịu 60 V.

### 4.2 Buck +5V (U101 TPS54560B, 400 kHz)
| Thông số | Giá trị | Tính toán |
|---|---|---|
| UVLO | bật 7.9 V / tắt 6.9 V | R105 300 k, R106 51 k (ngưỡng EN 1.2 V, dòng trễ 3.4 µA) |
| Tần số | 400 kHz | R107 243 k |
| Vout | 5.00 V | 0.8 V × (1 + 53.6 k/10.2 k) |
| Cuộn cảm | L101 10 µH, Isat 8.5 A | gợn dòng 0.73 A ở 12 V, 0.99 A ở 24 V |
| Tụ ra | 4× 47 µF/10 V 1206 (≈ 90 µF hiệu dụng) | gợn áp < 10 mV |
| Bù | R108 13 k + C107 4.7 nF, C108 47 pF | tần số cắt ≈ 19 kHz |
| Diode | D104 B560C 60 V/5 A | tổn hao ≈ 1.6 W ở 4.5 A/12 V |

### 4.3 Rail ngoại vi (U102, U103 — TPS563201, vào từ +5V)
- `+3V3_SW` = 0.768 × (1 + 33.2 k/10 k) = 3.32 V, L 2.2 µH, 2× 22 µF.
- `+1V0` = 0.768 × (1 + 3.4 k/10 k) = **1.03 V**, L 2.2 µH, 2× 22 µF. Đặt cao hơn 1.00 V một chút để sau hạt ferrite
  AVDD vẫn > 0.95 V (giới hạn dưới của switch); 1.03 V nằm trong dải 0.95–1.1 V của VDDC.
- EN của cả hai = `PERIPH_EN` = +3V3 của CM4 qua R103 10 k (kéo xuống R104 100 k, C103 100 nF).

### 4.4 Ngân sách công suất
| Tải trên +5V | Điển hình | Tối đa |
|---|---|---|
| CM4 | 1.4 A | 1.8 A |
| USB-A (giới hạn bởi U1003) | 0 | 1.2 A |
| U102 → +3V3_SW (1.3 A max ở 3.3 V) | 0.5 A | 0.95 A |
| U103 → +1V0 (1.35 A max ở 1.0 V) | 0.13 A | 0.32 A |
| Quạt | 0 | 0.2 A |
| **Tổng +5V** | **≈ 2.0 A** | **≈ 4.5 A** (U101 giới hạn dòng ≥ 6.3 A) |
| **Phía 12 V** (η 90 %) | ≈ 1.0 A | ≈ 2.1 A → adapter 12 V/3 A |

### 4.5 Trình tự và chống cấp ngược
CM4 yêu cầu không chân nào có điện trước +5V. Giải pháp:
- IC nhỏ nối với GPIO/USB của CM4 (TPM, FSUSB42, CH340C, SRAM, điện trở kéo) lấy nguồn từ **+3V3 do CM4 cấp ra**
  (tải ước tính < 80 mA so với giới hạn 600 mA).
- NIC và switch dùng `+3V3_SW`/`+1V0`, chỉ bật khi +3V3 của CM4 đã có. 3.3 V và 1.0 V lên đồng thời (datasheet switch cho phép).
- Reset PCIe: CM4 `PCIe_nRST` (kéo xuống 100 k) → SW1; SW1 `DWNRST#` → NIC1, NIC2, SW2; SW2 `DWNRST#` → NIC3, NIC4.
- VBUS của USB-C và micro-USB không nối vào rail nào của bo.

---

## 5. CM4 và bảng gán chân

Footprint gộp của Raspberry Pi (2× DF40C-100DS-0.4V + 4 lỗ M2.5). Bảng đầy đủ 200 chân: `out/stage1/01_overview/cm4-pinout.csv`.

| Chức năng | Chân CM4 | GPIO | Net |
|---|---|---|---|
| Ethernet cặp 0..3 | 12/10, 4/6, 11/9, 3/5 | — | `WAN_MDI0..3_P/N` |
| LED Ethernet | 15 (nLED3, activity → xanh), 17 (nLED2, speed → vàng) | — | `WAN_LED_G`, `WAN_LED_Y` |
| PCIe TX / RX / CLK | 122/124, 116/118, 110/112 | — | `PCIE_TX_*`, `PCIE_RX_*`, `PCIE_CLK_*` |
| PCIe reset / CLKREQ | 109, 102 | — | `PCIE_RST_N`; CLKREQ kéo GND qua R204 0 Ω |
| USB 2.0 | 105 (D+), 103 (D−), 101 (OTG_ID → GND) | — | `USB_DP`, `USB_DN` |
| UART console | 55 (TX), 51 (RX) | 14, 15 | `UART_TXD`, `UART_RXD` |
| SPI0 | 38 SCLK, 44 MOSI, 40 MISO | 11, 10, 9 | `SPI_*` |
| Chip select | 39 (CE0 → SRAM), 37 (CE1 → TPM) | 8, 7 | `SRAM_CS_N`, `TPM_CS_N` |
| Ngắt TPM | 45 | 24 | `TPM_PIRQ_N` |
| Báo mở vỏ | 47 | 23 | `TAMPER_OPEN` (cao = mở) |
| LED trạng thái | 50 | 17 | `LED_STATUS` |
| Quạt PWM | 49 | 18 | `FAN_PWM` → Q201 AO3400A (Rds(on) thấp ở Vgs 3.3 V) |
| I2C cho RTC | 80 (SCL0), 82 (SDA0) | 45, 44 | `RTC_SCL`, `RTC_SDA` |
| Điều khiển | 92 RUN_PG (nút reset kéo GND qua R206 220 Ω), 93 nRPIBOOT, 99 GLOBAL_EN, 100 nEXTRST, 20 EEPROM_nWP, 21 LED_nACT | — | cùng tên |
| Nguồn | 77–87 lẻ (+5V), 84/86 (+3V3 ra), 78 GPIO_VREF → +3V3 | — | |

Chân không dùng (HDMI, CSI, DSI, SD, GPIO dư, WL/BT_nDisable, +1V8) để hở.

---

## 6. PCIe: switch và NIC

### 6.1 PI7C9X2G404SL (U401 = SW1, U501 = SW2)
- **Làn**: tụ AC 100 nF đặt ở phía phát. CM4 đã có tụ trên TX và CLK của nó; switch có tụ trên mọi cổng phát;
  NIC có tụ trên HSO.
- **Clock**: bộ đệm tích hợp (CLKBUF_PD kéo xuống 330 Ω = bật). `REFCLKI` nhận clock vào; `REFCLKO0` quay về
  `REFCLKP/N` của chính chip qua tụ 100 nF; `REFCLKO1..3` cấp cho thiết bị phía dưới. Mỗi ngõ ra HCSL có
  Rs 33 Ω nối tiếp + Rp 49.9 Ω xuống GND (cấu hình đo của datasheet bảng 8-1); IREF 475 Ω 1 %.
- **Clock từ CM4 đã ghép AC trên module** nên SW1 cần dựng lại phân cực: mỗi dây 10 k lên +3V3_SW và 1.37 k xuống
  GND → Vcm = 0.40 V (datasheet bảng 8-1 ghi chú 4). SW2 nhận HCSL ghép DC từ SW1 nên không cần.
- **Tham chiếu**: REXT 1.43 k 1 % giữa chân 116 và 115.
- **Strap**: TEST1/TEST2 kéo lên 5.1 k; TEST3..6, PWR_SAV, TMS, TRST# kéo xuống 330 Ω; SMBCLK/SMBDATA/EEPD kéo lên 5.1 k;
  SLOTCLK kéo lên (dùng chung clock nền). Các strap có kéo xuống nội (VC1_EN, PL_512B, PRSNTx, SLOT_IMPx…) để hở.
  Không dùng EEPROM, SMBus, JTAG.
- **Nguồn**: VDDC/VDDCAUX ← +1V0; AVDD ← +1V0 qua hạt ferrite; VDDR/VAUX ← +3V3_SW; CVDDR và AVDDH ← +3V3_SW qua hạt
  ferrite riêng. Hạt ferrite là BLM18PG121SN1D (120 Ω@100 MHz, **50 mΩ, 2 A**): AVDD hút tối đa ~0.32 A nên sụt áp
  ≤ 16 mV → AVDD ≥ 1.01 V. Mỗi chân nguồn có 1 tụ 100 nF đặt ở mặt dưới ngay dưới chân đó (cách ≤ 3 mm) + tụ khối.
- Điểm đo: `AVDD_1V0` của mỗi switch (TP401, TP501), `V1P0` của mỗi NIC (TP601…TP901).
- **Cổng 3 của SW2** để hở (đã có tụ và điện trở clock, không nối ra ngoài).
- **Đảo cực làn (giai đoạn 2)**: do thứ tự chân, mọi làn TX→RX giữa CM4, switch và NIC đều bị bắt chéo P/N nếu nối
  thẳng trên một lớp. Mọi đầu thu (PERPx/PERNx của switch, HSIP/HSIN của NIC, PCIe_RX của CM4) vì thế được nối chéo
  có chủ đích; đầu thu PCIe bắt buộc tự phát hiện và sửa đảo cực khi huấn luyện liên kết (Lane Polarity Inversion).
- **Clock vào REFCLKI** (chân 73/74) đi lớp L3 dưới thân chip và lên bằng cặp via nằm trong vùng giữa đế tản nhiệt và
  hàng chân, vào pad từ phía trong → không phải đảo cực clock và không cắt các ngõ ra clock. Điện trở phân cực
  R209–R212 nằm mặt dưới ngay tại cặp via đó.
- **Rs/Rp**: Rs 33 Ω thành cặp ngay dưới chân REFCLKO; cặp clock đổi lớp ngay sau Rs; Rp 49.9 Ω ở mặt dưới tại cặp via.

### 6.2 RTL8111H-CG (U601..U901)
- LDO nội 1.0 V: REGOUT → DVDD10/AVDD10, tụ 4.7 µF + 4× 100 nF; không cấp cho linh kiện khác.
- Thạch anh 25 MHz CL 12 pF, 2 tụ 18 pF; RSET 2.49 k.
- ISOLATEB kéo lên (1 k/15 k); CLKREQB, LANWAKEB kéo lên 10 k (không dùng); PERSTB từ switch.
- LED mặc định tích cực thấp: LED2 (1000M) → LED xanh, LED1 (100M) → LED vàng của jack; anode qua 470 Ω lên +3V3_SW.
- Điểm giữa biến áp của jack (chân 1) nối GND qua 100 nF.

### 6.3 Driver
`r8169` (CONFIG_R8169=m) có sẵn; switch là cầu PCI-PCI chuẩn. Chi tiết: `docs/notes/driver-check.md`.
MAC của RTL8111H gán bằng phần mềm (chip không hỗ trợ EEPROM ngoài).

---

## 7. USB, nạp eMMC, console

- U1001 FSUSB42: `SEL` = `nRPIBOOT`. Cao → HSD2 = USB-A; thấp → HSD1 = USB-C. /OE nối GND.
- SW1001 (công tắc gạt, trong vỏ): vị trí BOOT kéo `nRPIBOOT` xuống GND (R203 10 k kéo lên +3V3).
- USB-A: U1003 TPS2553 (ILIM 22 k ≈ 1.2 A, EN từ +3V3), 2× 47 µF, ESD USBLC6-2.
- USB-C: CC1/CC2 kéo xuống 5.1 k, ESD USBLC6-2, VBUS chỉ nối điện trở xả 100 k + test point.
- Console: CH340C (VCC = V3 = +3V3 của CM4), TXD/RXD qua 470 Ω tới GPIO15/GPIO14.
- `USB_OTG_ID` nối GND (vai trò cố định). Cấu hình phần mềm: `dtoverlay=dwc2,dr_mode=host`.

Ghi chú bảo mật: console ở mặt trước là điểm yếu, chấp nhận cho mục đích học.

---

## 8. Bảo mật

### 8.1 TPM SLB9670
SPI0 CE1 (đúng overlay `tpm-slb9670`), RST# ← `nEXTRST`, PIRQ# → GPIO24 (kéo lên 10 k).

### 8.2 RTC và rail V_KEEP
`V_KEEP` = OR bằng BAT54C của (+3V3, pin CR2032 qua 1 k). Nuôi PCF85063A (thạch anh 7 pF, không cần tụ ngoài)
và nhánh tamper. Khi CM4 có điện, pin không bị tiêu hao. Vỏ SO-8 của PCF85063A không có chân CLKOE nên CLKOUT bật
mặc định sau khi cấp nguồn lần đầu: phần mềm phải tắt CLKOUT (thanh ghi Control_2, COF = 111) để đạt dòng 0.22 µA.

### 8.3 Mạch chống mở vỏ (đã sửa theo review độc lập, mục C1/S1/S2)

```
V_KEEP ── SW1101 (MX, vỏ đậy = đóng) ── J1101 (jumper / công tắc ngoài) ── R1104 1 k ── V_SW
V_SW ── R1105 4.7 MΩ ── GND ;  V_SW ── C1105 1 nF ── GND          (τ ≈ 5 ms)
V_SW ── D1102 (1N4148WS) ──► VBAT_SRAM ── chân VBAT của SRAM ;  VBAT_SRAM ── R1106 10 MΩ ── GND
Q1101 (BSS138): cổng = V_SW;  V_SW cao → kéo VCC_GATE xuống thấp   (R1107 10 k kéo VCC_GATE lên +3V3)
Q1102 (AO3401A): VCC_GATE thấp → cấp +3V3 cho SRAM_VCC
Q1103 (2N7002):  VCC_GATE cao → kẹp SRAM_VCC về GND qua R1108 10 Ω
Q1104 (BSS138): cổng = V_SW;  máng kéo lên +3V3 qua R1110 10 k → R1111 1 k → TAMPER_OPEN (GPIO23)
```

Điểm mấu chốt: **`VCC_GATE` không nối tới CM4.** Tín hiệu báo về GPIO23 do Q1104 tạo riêng, nên trạng thái của GPIO
(kéo xuống nội ~47 k, hay phần mềm lái mức thấp) không thể giữ nguồn cho SRAM. Với kéo xuống nội 47 k, mức cao của
`TAMPER_OPEN` là 3.3 × 47/(47+11) ≈ 2.7 V (> VIH 2.0 V).

| Yêu cầu (task §5.9) | Đáp ứng |
|---|---|
| Mở vỏ hoặc đứt dây → ngắt VCC lẫn VBAT và kẹp về GND | Công tắc mắc nối tiếp nên đứt dây = mở. V_SW xả qua 4.7 MΩ (τ ≈ 5 ms) → Q1101 tắt → VCC_GATE lên 3.3 V → Q1102 ngắt, Q1103 kẹp SRAM_VCC. Nhánh VBAT mất nguồn cấp: D1102 chặn dòng rò từ chân VBAT quay về V_SW (không thể giữ Q1101 dẫn), VBAT_SRAM xả bằng dòng VBAT của SRAM (~1 µA) + 10 MΩ trên điện dung chỉ vài pF → dưới mức giữ dữ liệu 1.0 V trong vài ms. |
| Hoạt động khi chỉ còn pin | Khi đó SRAM_VCC = 0, dữ liệu chỉ sống nhờ VBAT_SRAM ≈ V_KEEP − 0.35 V ≈ 2.3 V (≥ 1.4 V); mở công tắc là mất. |
| Dòng pin ≤ 3 µA | Ở 25 °C: RTC 0.22 (CLKOUT đã tắt) + SRAM VBAT 1.0 + 4.7 MΩ 0.6 + 10 MΩ 0.25 + rò BAT54C ~0.3 ≈ **2.4 µA** → CR2032 (220 mAh) ≈ 10 năm. Con số này là giá trị điển hình; rò của BAT54C tăng theo nhiệt độ nên ở 50–60 °C có thể vượt 3 µA (tuổi pin vẫn nhiều năm). |
| Chặn cấp nguồn ký sinh qua SPI | Điện trở nối tiếp: CS 10 k, SCK/SI/SO 1 k. Trường hợp xấu nhất (SCK và MOSI cùng mức cao) ≈ 5.7 mA chảy qua diode bảo vệ vào Q1103 + 10 Ω → SRAM_VCC ≈ 0.1 V, thấp hơn nhiều so với VTRIP 1.8 V và mức giữ dữ liệu 1.0 V. Tốc độ SPI cho SRAM nên ≤ 5 MHz. |
| Báo về CM4, không cấp ngược | TAMPER_OPEN thuộc miền +3V3 của CM4 (kéo lên +3V3). |
| Không tự tắt CM4 | Đúng, chỉ xóa SRAM và báo GPIO. |

Chống xóa nhầm: τ 5 ms lọc được nảy tiếp điểm ngắn; rung mạnh làm hở tiếp điểm > ~5 ms sẽ xóa khóa (an toàn hơn là bỏ sót).
J1101 có R1104 1 k nối tiếp hạn dòng phóng tĩnh điện khi nối công tắc ngoài.
Phần mềm nhận biết "đã mở vỏ lúc tắt máy" bằng cách kiểm tra magic/checksum trong SRAM. Thử nghiệm: rút jumper J1101.

**Cần đo khi bring-up** (review S1): điện áp `V_SW` và `VCC_GATE` khi đóng/mở với CM4 đang chạy; thời gian `VBAT_SRAM` về 0.

---

## 9. Cơ khí và bố trí

Hình: `out/release/rev-a/02_pcb_drawings/`, `03_images/` và `04_3d/`.

- Bo **150 × 105 mm**, góc bo R3, 4 lỗ M3 cách mép 4.5 mm (nối net CHASSIS).
- Mặt trước: tâm các cổng theo X (mm từ mép trái): LAN4 17.0, LAN3 35.2, LAN2 53.4, LAN1 71.6, USB-A 90.0,
  micro-USB 104.5, USB-C 116.0, WAN 133.0. RJ45 và USB-A nhô khỏi mép bo 2.0 mm; USB-C và micro-USB theo vạch mép
  của footprint (≈ 0.1 mm và 0.7 mm).
- Mặt sau: jack DC tại X = 16 mm, nhô 0.5 mm.
- CM4 ở giữa-phải (X 78–118, Y 6–61), xoay để đầu chân 1/101 hướng về mặt trước; không đặt linh kiện mặt trên
  dưới module (khe hở 0 mm với DF40C cao 1.5 mm).
- Nguồn ở góc sau-trái; hai switch ở giữa-trái; bốn NIC ngay sau jack LAN; USB/debug dưới CM4; bảo mật ở cột phải
  (pin, MX switch, TPM, RTC, SRAM).
- Mặt dưới chứa tụ decoupling, điện trở tham chiếu, Rp clock và điện trở phân cực clock (ngay dưới chân của switch, NIC;
  tụ của CM4); mọi linh kiện còn lại ở mặt trên.
- Vòng nóng của U101 (C106/C104/C105 – U101 – L101 – D104) và tụ boot đặt sát IC; thạch anh RTC cách U1102 < 3 mm;
  IC ESD cách chân đầu nối USB 5–6 mm; điện trở phân cực clock PCIe cách chân REFCLKI của SW1 3–4 mm.
- CHASSIS (vỏ RJ45/USB, lỗ vít) nối GND qua 1 MΩ // 4.7 nF/2 kV.

---

## 10. PCB

Chi tiết: `docs/specs/stackup.md`, `docs/reviews/routing-report.md` (độ dài/lệch từng cặp), `docs/notes/decisions.md`.

- 6 lớp 1.6 mm, stackup JLC06161H-3313, ENIG. Không dùng via-in-pad trên pad linh kiện (chỉ có via tản nhiệt trong
  đế của switch/NIC và via sẵn có trong footprint U101). Via: Ø0.45/0.20 mm cho tín hiệu, Ø0.6/0.3 mm cho nguồn.
- Phân lớp: L1 tín hiệu (mọi làn dữ liệu PCIe, MDI LAN, USB) · L2 GND liền · L3 tín hiệu chui (clock, liên kết
  SW1↔SW2, MDI WAN, MDI1 của LAN) · L4 GND liền · L5 nguồn · L6 tụ decoupling + tín hiệu chậm + clock tự vòng.
- Lớp nguồn L5: +3V3_SW nửa tây; +1V0 là đảo dưới hai switch nối về U103; +5V dải phía sau và nửa đông (CM4, USB-A,
  quạt). +3V3 do CM4 cấp (dòng nhỏ) và các rail cục bộ sau hạt ferrite đi bằng đường 0.3 mm.
- GND: L2 và L4 liền toàn bo; đổ thêm GND trên L1/L3/L6 và khâu via. Mỗi pad GND/nguồn SMD có via riêng xuống mặt phẳng.
- Net class: `PCIE_90R` 0.15/0.15, `USB_90R` 0.15/0.15, `MDI_100R` 0.125/0.18, `USB_FS`, `PWR`, `PWR_HV`, `Default`
  (trong `cm4-gateway.kicad_pro`). Khe hở cặp vi sai tới net khác ≥ 0.15 mm.
- Lệch độ dài trong cặp: PCIe/clock ≤ 0.1 mm (bù bằng gờ nhỏ trên dây ngắn hơn); USB ≤ 1.0 mm; MDI ≤ 3.0 mm
  (hai hàng chân so le của jack lệch nhau 2.54 mm).
- Luật riêng trong `cm4-gateway.kicad_dru`; **không có luật theo Reference**.
- Đi dây bằng script (`scripts/gen/route.py`): cặp vi sai đi theo "tim cặp" qua các điểm mốc khai báo trong script,
  mặt phẳng/via nguồn và tín hiệu chậm đi tự động bằng A*. Chạy lại script cho đúng một kết quả.

---

## 11. Rủi ro còn mở

| # | Rủi ro | Mức | Xử lý |
|---|---|---|---|
| R1 | Chưa có bằng chứng công khai PI7C9X2G404SL chạy với CM4 (đặc biệt 2 switch ghép tầng) | Trung bình | Switch chuẩn, không cần driver; kiểm tra `lspci -t` khi bring-up. Dự phòng: `pci=nomsi`, giới hạn tốc độ Gen1. |
| R2 | Phân cực lại clock CM4 cho REFCLKI (10 k/1.37 k) dựa trên ghi chú datasheet, chưa đo | Trung bình | Điện trở 0402 dễ đổi/bỏ; có thể đo biên độ tại chân 73/74. |
| R3 | Cực tính LED của HR911130A đọc từ bản vẽ (anode = chân 11, 14) | Thấp | Sai chỉ làm LED không sáng; kiểm tra bằng đồng hồ khi nhận hàng. |
| R4 | MAC của RTL8111H mua lẻ có thể trùng nhau | Thấp | Gán MAC bằng phần mềm. |
| R5 | USB-C: khoảng hở lỗ NPTH–pad trong footprint GCT là 0.194 mm | Thấp | Xác nhận với năng lực JLC ở giai đoạn 2. |
| R6 | Dòng rò VCC→VBAT của 23LCV1024 và mức kéo xuống mặc định của GPIO23 không có trong datasheet | Thấp | Mạch đã được làm cho không phụ thuộc hai yếu tố này (D1102, Q1104); đo xác nhận khi bring-up. |
| R9 | Cổng 3 của SW2 không dùng nhưng tụ/điện trở clock vẫn lắp, ngõ ra clock vẫn chạy | Thấp | Có thể tắt bằng thanh ghi hoặc không lắp R516–R519, C507/C508. |
| R10 | RTL8111H yêu cầu 3.3 V lên ≥ 0.5 ms và tắt ≥ 50 ms trước khi cấp lại | Thấp | Đo soft-start của U102; tránh bật/tắt nhanh bằng GLOBAL_EN. |
| R7 | Stackup và bề rộng trở kháng lấy theo công thức gần đúng (không truy cập được máy tính trở kháng của JLC khi thiết kế) | Trung bình | Khi đặt hàng chọn Impedance Control + JLC06161H-3313 và đối chiếu bề rộng 0.15/0.15 (90 Ω), 0.125/0.18 (100 Ω) trên L1 với bảng của JLC; lệch vài % không ảnh hưởng ở các độ dài này. |
| R8 | Chiều cao MX switch (≈ 15 mm kể cả trục) so với RJ45 13.5 mm | Thấp | Thuộc thiết kế vỏ; có header J1101 cho công tắc ngoài. |

---

| R11 | Góc xoay linh kiện trong CPL chưa kiểm chứng được với thư viện JLC | Trung bình | Bật "Confirm Parts Placement", xem lại chân 1 ở màn hình xem trước (ORDERING.md mục 4). |
| R12 | Bản đi dây do script sinh, kiểm bằng DRC và review độc lập bằng máy; chưa có người rà layout | Trung bình | Đặt 5 bo cho lần đầu; làm đủ các bước trong BRINGUP.md. |
| R13 | Đảo cực làn PCIe dựa vào tính năng bắt buộc của chuẩn (đầu thu tự sửa) | Thấp | Nếu một cổng không lên liên kết, kiểm tra clock/reset/tụ AC trước. |

---

## 12. Giai đoạn 2 đã làm

Đi dây toàn bộ (DRC 0 lỗi, 0 chưa nối); via tản nhiệt cho đế switch/NIC; mặt phẳng nguồn L5; file sản xuất JLC
(Gerber, khoan, BOM/CPL, tách footprint CM4 thành 2 dòng DF40); `BRINGUP.md`, `SOFTWARE.md`; gói `out/release/rev-a/`.
