# Review độc lập giai đoạn 1 — CM4 Security Gateway Rev A

Ngày: 2026-11-11 · Phạm vi: schematic hoàn chỉnh + bố trí linh kiện (chưa đi dây) · Người review: reviewer độc lập (EE cấp bo mạch)

Phương pháp: xuất netlist thật bằng `kicad-cli sch export netlist --format kicadxml` (408 linh kiện, 521 net), đọc vị trí/pad
thật từ `hardware/cm4-gateway.kicad_pcb` bằng `pcbnew`, chạy lại ERC/DRC, đối chiếu từng chân với datasheet trong
`docs/datasheets/` (pdftotext; bản vẽ HR911130A, DC-005 và vỏ LQFP-128 đọc bằng ảnh). Không sửa file nào của dự án ngoài báo cáo này.

## 1. Kết luận ngắn

**Chưa nên vào giai đoạn đi dây.** Có **2 lỗi CHẶN**, cả hai đều sửa được ở mức schematic với vài linh kiện:

1. Mạch tamper **không cắt được VCC của SRAM khi CM4 đang chạy** ở cấu hình GPIO mặc định, vì nút `VCC_GATE` bị
   điện trở kéo xuống nội của GPIO23 kéo qua R1106 1 kΩ.
2. Hạt ferrite 600 Ω (450 mΩ, 200 mA) trên rail **AVDD 1.0 V** của hai PCIe switch làm sụt áp xuống dưới mức tối thiểu 0.95 V.

Phần còn lại của schematic nhìn chung đúng: toàn bộ pin map symbol tự tạo khớp datasheet, topo PCIe/clock/reset đúng
hướng và đúng cực, tụ AC đúng một lần mỗi chiều, footprint RJ45 tự dựng khớp bản vẽ và không bị lật gương, khối nguồn
tính đúng. Các mục NÊN SỬA chủ yếu là bố trí linh kiện (vòng nóng buck, điện trở tham chiếu, decoupling) và tài liệu lệch netlist.

ERC: 0 vi phạm. DRC: 0 lỗi đặt linh kiện (chỉ 28 cảnh báo silkscreen), 499 chưa nối (đúng kỳ vọng vì chưa đi dây), 0 lỗi parity.

## 2. Bảng phát hiện

### CHẶN — phải sửa trước khi đi dây

| # | Phát hiện | Bằng chứng | Đề xuất sửa |
|---|---|---|---|
| C1 | **Tamper bị vô hiệu khi CM4 có điện và GPIO23 còn kéo xuống mặc định.** Khi mở vỏ, Q1101 ngắt và `VCC_GATE` phải lên 3.3 V để ngắt Q1102 và mở Q1103. Nhưng `VCC_GATE` chỉ được kéo lên bằng R1105 100 kΩ, trong khi nối với GPIO23 qua R1106 chỉ 1 kΩ. Với điện trở kéo xuống nội 47 kΩ (33–73 kΩ) của GPIO: `VCC_GATE` = 3.3 × 48/148 ≈ **1.07 V** (0.84–1.40 V). Khi đó Vgs của Q1102 (AO3401A) ≈ −2.2 V → **vẫn dẫn hoàn toàn**, SRAM_VCC giữ 3.3 V (> VTRIP 1.8 V) nên dữ liệu **không mất**; Q1103 (2N7002, Vth 1–2.5 V) không kẹp; GPIO23 đọc ~1 V là mức không xác định (VIL 0.8 / VIH 2.0) nên cũng **không báo được**. Ngoài ra nếu phần mềm đặt GPIO23 là ngõ ra mức thấp thì phần cứng không bao giờ xóa được. Vi phạm task §5.9 mục 1 và 2. | Netlist: `/Security/VCC_GATE` = Q1101.3(D), Q1102.1(G), Q1103.1(G), R1105.2, R1106.1; `TAMPER_OPEN` = R1106.2, TP1103, U201.47 (GPIO23). `design.py` dòng `c.R("100k", "+3V3", ".VCC_GATE")` và `c.R("1k", ".VCC_GATE", "TAMPER_OPEN")`. CM4 datasheet bảng DC: RPD(gpio) 33/47/73 kΩ. 23LCV1024 DS25156A bảng 1-1 D012 VTRIP và mục 5.0. *Lưu ý: việc GPIO23 mặc định kéo xuống sau reset là kiến thức chung về BCM2711 (GPIO9–27 kéo xuống), không có trong tài liệu của dự án — nên đo xác nhận; nhưng kể cả khi không kéo xuống, phần cứng tamper vẫn không được phép phụ thuộc trạng thái GPIO.* | Tách tín hiệu báo khỏi nút điều khiển: thêm 1 FET (BSS138/2N7002) riêng có cổng nối `V_SW`, cực máng kéo lên +3V3 bằng 10 kΩ → `TAMPER_OPEN` (cùng cực tính: cao = mở; 10 kΩ so với 47 kΩ kéo xuống vẫn cho ≥ 2.5 V). `VCC_GATE` không nối ra CM4 nữa. Đồng thời giảm R1105 xuống 10–22 kΩ (dòng này lấy từ +3V3 của CM4, không tốn pin). Cập nhật bảng phân tích ở design doc §8.3. |
| C2 | **AVDD 1.0 V của PCIe switch sụt dưới mức tối thiểu do hạt ferrite.** FB401/FB501 là GZ1608D601TF: DCR 450 mΩ, dòng định mức 200 mA. AVDD tiêu thụ 144 mW điển hình (≈ 144 mA) và tối đa 346 mW ở 1.1 V (≈ 315 mA). Sụt áp 65 mV (điển hình) đến 142 mV (tối đa) → AVDD ≈ **0.935 V / 0.86 V**, dưới mức tối thiểu **0.95 V**; dòng tối đa còn vượt định mức 200 mA của hạt. Đây là nguồn analog của PHY PCIe → rủi ro link không lên/không ổn định trên cả hai switch. | Netlist: `/SW1/AVDD_1V0` = FB401.2, U401.99/105/108/119/125, C411–C416 (tương tự SW2). `parts.py`: `FB600` = C1002 GZ1608D601TF. `docs/notes/raw/passives_search.txt` dòng 52: "200mA 450mΩ 600Ω@100MHz". PI7C9X2G404SL DS40068 bảng 12-2 (AVDD 0.95–1.1 V) và bảng 12-8 (1.0AVDD 144.10 / 346.06 mW). | Đổi FB401/FB501 sang hạt DCR thấp, ví dụ BLM18PG121SN1D (C14709, 2 A, 50 mΩ, đã có trong kết quả tra kho) hoặc 0 Ω. Nên nâng `+1V0` lên khoảng 1.03 V (R113 3.01 k → 3.4 k cho 1.029 V) để có biên so với 0.95 V sau sụt áp trên mặt phẳng. FB402/FB403 (3.3 V, dòng ≤ ~100 mA) giữ được. |

### NÊN SỬA

| # | Phát hiện | Bằng chứng | Đề xuất sửa |
|---|---|---|---|
| S1 | **Nút `V_SW` trở kháng cao dùng chung cho chân VBAT của SRAM và cổng Q1101; VBAT không được kẹp chủ động.** (a) Datasheet 23LCV1024 không đặc tả dòng rò ngược từ VCC ra chân VBAT. Khi CM4 đang chạy, chỉ cần > ~0.25 µA rò ra `V_SW` (1.2 V / 4.7 MΩ) là Q1101 không bao giờ ngắt → vòng tự giữ, tamper không kích. **Chưa chắc chắn — cần đo trên chip thật.** (b) Khi chỉ còn pin, +3V3 = 0 nên Q1103 không hoạt động; VBAT chỉ xả thụ động qua R1104 4.7 MΩ // C1105 4.7 nF (τ ≈ 22 ms, về 0.1 V mất ~75 ms). Task §5.9 mục 1 yêu cầu "chủ động kẹp về GND"; hiện đạt con số < 100 ms nhưng sát biên với dung sai R/C và không có kẹp chủ động. (c) Dây công tắc ngoài qua J1101 nối thẳng vào nút 4.7 MΩ này, dễ nhiễm nhiễu/ESD. | Netlist: `/Security/V_SW` = C1105.1, J1101.2, Q1101.1(G), R1104.1, U1103.7(VBAT). DS25156A bảng 1-1 (không có thông số rò VBAT), mục 5.0. | Đặt diode rò thấp nối tiếp từ `V_SW` vào chân VBAT để SRAM không cấp ngược nút cảm biến; thêm điện trở xả riêng tại chân VBAT và giảm C1105 xuống ~1 nF (τ ≈ 5 ms). Thêm điện trở nối tiếp + tụ nhỏ/TVS cho J1101. Đo dòng rò VCC→VBAT khi bring-up. |
| S2 | **Phân tích cấp nguồn ký sinh trong design doc lạc quan.** Doc ghi "SRAM_VCC ≤ 0.1 V" khi bị kẹp. Trường hợp xấu SCK và MOSI cùng ở 3.3 V (bus SPI0 dùng chung với TPM nên vẫn hoạt động): 2 × (3.3 − 0.6)/1 kΩ + 0.3 mA ≈ 5.7 mA qua R1107 100 Ω + Rds Q1103 → SRAM_VCC ≈ **0.6 V**. Vẫn dưới VTRIP nên không giữ được dữ liệu (nguồn mảng nhớ lúc này là VBAT = 0), nhưng biên nhỏ hơn tài liệu nói. | Netlist: R1110/R1111/R1112 1 k, R1109 10 k, R1107 100 Ω → `/Security/CLAMP` → Q1103.3. Design doc §8.3 bảng, dòng "Chặn cấp nguồn ký sinh". | Giảm R1107 xuống 10 Ω (hoặc bỏ), giữ điện trở nối tiếp; sửa con số trong doc. |
| S3 | **Vòng nóng của buck 5 V (U101) đặt quá xa.** Tụ cao tần C106 100 nF cách chân VIN **17.4 mm**; C104 10 µF cách 8.9 mm, C105 cách 13.7 mm; diode D104 cách chân SW 11.7 mm; tụ boot C109 cách chân BOOT 13.6 mm. Với 400 kHz / 5 A sẽ gây ringing và nhiễu lớn. Task P4 yêu cầu tụ decoupling sát chân IC; doc tự ghi rủi ro R6. | `cm4-gateway.kicad_pcb`: U101 (50.6, 20.8); C106 (33.1, 29.2); C104 (56.8, 19.2); C105 (61.6, 19.2); D104 (41.8, 21.4); C109 (39.1, 29.2). | Xếp lại trước khi đi dây: C106 + 1 tụ 10 µF sát chân 2–7, D104 sát chân 8 và chung điểm GND với tụ vào, C109 sát chân 1/8. |
| S4 | **Điện trở tham chiếu và decoupling của hai PCIe switch đặt xa.** R401 (REXT 1.43 k) cách chân 116 **21.5 mm**; R402 (IREF 475 Ω) cách chân 86 **20.3 mm**; tụ vòng clock C409/C410 cách chân 110/111 ~19 mm; R404 (Rs của REFCLKO0) cách chân 85 9.7 mm. Tụ 100 nF gần nhất của nhiều chân nguồn cách 9–14 mm (chân 113 AVDDH 13.9 mm, chân 91/65 VDDC ~13.8 mm, chân 99 AVDD 11.6 mm). | PCB: R401 (47.2, 42.0), R402 (49.3, 42.0), C409 (52.5, 62.4); U401 chân 116 ở cạnh X = 67.7, chân 86 ở cạnh Y = 57.7. Khoảng cách pad–pad cùng net tính từ file PCB. SW2 bố trí giống hệt. | Đưa R401/R402 vào trong 2–3 mm cạnh chân tương ứng; C409/C410 sát chân 110/111; phân bố lại tụ 100 nF mặt dưới theo từng chân nguồn (≤ 2–3 mm). |
| S5 | **Điện trở phân cực clock R208–R211 không nằm gần SW1 như routing-plan nói.** Chúng ở (74–76, 25.7–26.8), cách chân REFCLKI 73/74 của U401 ~35 mm và cách chân 110/112 của CM4 ~13 mm → tạo nhánh cụt trên cặp clock 100 MHz. | PCB: R208 (76.1, 25.7), R209 (74.0, 26.8), R210 (76.1, 26.8); U401.74 tại (57.45, 57.7). `routing-plan.md` §2 dòng REFCLK: "điện trở phân cực R208–R211 đặt gần SW1". | Dời 4 điện trở sát chân 73/74 của U401, đi kiểu nối xuyên pad. |
| S6 | **Thạch anh RTC Y1101 cách chân OSCI/OSCO của U1102 ~12.4 mm.** Nút dao động 32 kHz trở kháng rất cao, dễ bắt nhiễu và lệch tần. | PCB: Y1101 (135.5, 65.2); U1102 (125.6, 66.8), chân 1/2 ở cạnh trái. | Đặt Y1101 sát chân 1/2 (≤ 3 mm), có vòng GND bảo vệ. |
| S7 | **Q201 (2N7002) lái quạt 0.2 A bằng cổng 3.3 V.** Rds(on) của 2N7002 chỉ được đặc tả ở Vgs ≥ 4.5 V, Vth tối đa 2.5 V; ở 3.3 V sụt áp và phát nhiệt không bảo đảm. | Netlist: Q201.1 = `/CM4/FAN_G` (GPIO18 qua R206 100 Ω), Q201.3 = `/CM4/FAN_N`; design doc §4.4 ghi quạt tối đa 0.2 A. | Đổi sang MOSFET mức logic (ví dụ AO3400A, cùng footprint SOT-23 G/S/D). |
| S8 | **Ngân sách dòng pin 2.1 µA là giá trị điển hình ở 25 °C, thiếu hai khoản.** (a) PCF85063A bật CLKOUT 32.768 kHz mặc định sau khi cấp nguồn; bản SO-8 không có chân CLKOE nên phải tắt bằng phần mềm (COF = 111), nếu không dòng RTC cao hơn 0.22 µA. (b) Dòng rò ngược của BAT54C (từ `V_KEEP` về rail +3V3 khi CM4 tắt) tăng mạnh theo nhiệt độ, trong vỏ kín ấm có thể vượt 1 µA. Yêu cầu ≤ 3 µA có thể không đạt khi nóng. *Con số rò cụ thể chưa kiểm được vì không có datasheet BAT54C/PCF85063A trong dự án.* | Netlist: D1101.1 = +3V3, D1101.3 = `V_KEEP`; U1102.7 (CLKOUT) để hở. Design doc §8.3 dòng "Dòng pin ≤ 3 µA". `docs/datasheets/PCF85063A.pdf` thực chất là file HTML, không phải datasheet. | Ghi yêu cầu tắt CLKOUT vào SOFTWARE.md; cân nhắc diode rò thấp cho nhánh +3V3; tải lại datasheet PCF85063A; đo dòng pin khi bring-up. |
| S9 | **Thứ tự cổng mặt trước lệch task §6 và chưa có trong decisions.md.** Task yêu cầu "nhóm 5 RJ45 liền nhau"; thiết kế đặt LAN4–LAN1, USB-A, DEBUG, FLASH rồi mới tới WAN (WAN tách khỏi khối LAN bởi 3 cổng USB). Design doc §2 ghi mục 4 (kích thước 150 × 105) và mục 5 (thứ tự cổng) "đã ghi trong decisions.md" nhưng file đó không có hai mục này. Theo task §0.3, thay đổi thứ nhìn thấy ở mặt trước phải hỏi chủ dự án. | `placement.json` front_x: LAN4 17.0, LAN3 35.2, LAN2 53.4, LAN1 71.6, USB-A 90.0, DEBUG 104.5, FLASH 116.0, WAN 133.0. `docs/notes/decisions.md` (9 dòng, không có thứ tự cổng/kích thước bo). | Nêu rõ điểm này trong README gói giai đoạn 1 để chủ dự án duyệt; bổ sung 2 dòng vào decisions.md. |
| S10 | **parts-check.md lệch với schematic/BOM ở 3 đầu nối.** USB-C: parts-check ghi HRO TYPE-C-31-M-12 (C165948), schematic/BOM dùng GCT USB4105-GF-A (C3020560). micro-USB: Amphenol 10118194-0001LF (C132563) so với Molex 47346-0001 (C132560). Jack DC: DC-005-20A (C136744) so với DC-005-5A-2.0 (C381116). Footprint trên bo khớp với linh kiện trong schematic, nhưng kết quả "tồn kho đã kiểm" lại là của linh kiện khác. | `docs/notes/parts-check.md` dòng 21–23; `out/stage1/06_bom/bom.csv` dòng 27, 32, 33; `design.py` sheet_power / sheet_usb. | Cập nhật parts-check theo mã thật và kiểm lại tồn kho của 3 mã đang dùng. |
| S11 | **Nút RESET nối thẳng RUN_PG xuống GND.** CM4 datasheet ghi RUN_PG là chân hai chiều, kéo xuống "qua điện trở 220 Ω". | Netlist: `RUN_PG` = SW201.1, TP201, U201.92; SW201.2 = GND. CM4 datasheet bảng chân, chân 92. | Thêm 220 Ω nối tiếp với SW201. |

### GHI CHÚ

| # | Nội dung | Bằng chứng |
|---|---|---|
| N1 | Màu LED WAN ngược với gợi ý của CM4 datasheet: chân 15 (nLED3, activity, "thường là LED xanh") đang nối LED vàng; chân 17 (nLED2, speed, "thường là LED vàng") nối LED xanh. Chỉ là thẩm mỹ; nên thống nhất ý nghĩa màu với 4 cổng LAN. | Netlist `WAN_LED_G` = J301.12 + U201.17; `WAN_LED_Y` = J301.13 + U201.15. |
| N2 | Datasheet switch mục 8 viết "three reference clock outputs" nhưng chip có 4 cặp REFCLKO[3:0]; thanh ghi 98h bit[19:16] reset = Fh xác nhận cả 4 ngõ ra bật mặc định → cách dùng REFCLKO0 tự vòng + REFCLKO1..3 ra ngoài là đúng. | DS40068 mục 8 và mục 7.2.57 (offset 98h). |
| N3 | Cổng 3 của SW2 không dùng nhưng vẫn lắp C507/C508, R516–R519; ngõ ra clock này vẫn chạy (phát xạ, tốn điện). Có thể để DNP. | Net `/SW2/CLK3_*`, `/SW2/DN3_*`. |
| N4 | RTL8111H yêu cầu thời gian lên của 3.3 V ≥ 0.5 ms và thời gian tắt ≥ 50 ms trước khi cấp lại. Cần kiểm soft-start của TPS563201 khi đo, và tránh bật/tắt nhanh bằng GLOBAL_EN. | RTL8111H rev 1.2 bảng 17 (Rt1, Rt2). |
| N5 | Mặt trước các đầu nối không đồng phẳng: RJ45 nhô 2.0 mm, USB-A ~2.5 mm (theo courtyard), micro-USB ~1.3 mm, USB-C ~0.6 mm. Cần tính khi làm panel. | Courtyard trong PCB: J601 Y tới 107.3; J1001 107.6; J1003 106.3; J1002 105.6 (mép bo 105.0). |
| N6 | Footprint jack DC của KiCad dùng khe khoan 1.0 × 3.0 mm, bản vẽ DC-005-5A-2.0 khuyến nghị 1.0 × 3.5 mm; khoảng cách chân 1–2 là 6.0 so với 5.9 mm. Chân rộng 2.5 mm nên vẫn lắp được, nhưng nên nới khe theo bản vẽ. | Bản vẽ X-DC-005-5A-2.0 "PCB layout top view"; `BarrelJack_Horizontal.kicad_mod`. |
| N7 | IC ESD USB đặt cách đầu nối 6–9 mm (U1002 9.2 mm, U1004 7.6 mm, U1005 6.4 mm). Nên đưa sát đầu nối khi đi dây. | Vị trí trong PCB. |
| N8 | Task §5.1 yêu cầu test point cho các rail của switch/NIC: hiện có +1V0 và +3V3_SW, chưa có cho rail 1.0 V nội của từng NIC (`V1P0`) và AVDD/CVDD sau ferrite. | Danh sách TP101–TP108 trong netlist. |
| N9 | 3D/cơ khí: MX switch (SW1101) và giá pin nằm ở cột phải, không chồng module CM4; không có linh kiện mặt trên dưới module (chỉ C201–C204 ở mặt dưới). Tụ +5V của CM4 (C201/C202) cách chân +5V 6–10 mm. | Quét courtyard trong vùng X 78–118, Y 6–61. |

## 3. Những gì đã kiểm và thấy đúng

**Pin map symbol (so với datasheet)**
- PI7C9X2G404SL: đủ 128 chân + EP (129), khớp từng chân với bảng 4.1 và mục 3.1–3.5 của DS40068 Rev 5-2.
- RTL8111H-CG: đủ 32 chân + EP, khớp bảng 1–7 của datasheet rev 1.2.
- SLB9670: CS# 20, SCLK 19, MOSI 21, MISO 24, PIRQ# 18, RST# 17, GPIO 6, PP 7, VDD 8/22, GND 2/9/23/32 + EP, NC 29/30 để hở — khớp bảng 3–5.
- 23LCV1024 SOIC-8 (CS 1, SO 2, NC 3, VSS 4, SI 5, SCK 6, VBAT 7, VCC 8) — khớp bảng 3-1.
- HR911130A: MDI0 2/3, MDI1 4/7, MDI2 5/6, MDI3 8/9, CT 1, chân 10 = đất vỏ, LED xanh anode 11/cathode 12, LED vàng anode 14/cathode 13 — khớp sơ đồ trang 1.
- CM4: tên cả 200 chân trong `cm4_pins.json` khớp bảng chân của CM4 datasheet; mọi chân GND nối GND; chân Reserved 104/106/76 để hở.
- FSUSB42 MSOP-10 và CH340C SOP-16: khớp datasheet. Netlist cho thấy thứ tự chân đúng với TPS54560B (HSOP-8), TPS563201, TPS2553DBV, USBLC6-2SC6, AO4407A, BAT54C và các FET SOT-23 (G1/S2/D3) — các linh kiện này không có datasheet trong dự án, đối chiếu theo pinout chuẩn của nhà sản xuất.
- PCF85063AT SO-8: đối chiếu theo pinout chuẩn (datasheet trong dự án là file hỏng — xem S8).

**PCIe**
- CM4 TX (122/124) → SW1 PERP0/PERN0 trực tiếp (tụ đã có trên CM4); SW1 PETP0/PETN0 → C401/C402 → CM4 RX (116/118).
- Mỗi cổng xuống: switch PET → tụ → NIC HSIP/HSIN; NIC HSOP/HSON → tụ → switch PER. SW1 cổng 3 ↔ SW2 cổng 0 đúng chéo. Tụ AC đúng một lần mỗi chiều, cực P/N nhất quán.
- Clock: CM4 CLK → REFCLKI (74/73) của SW1 kèm phân cực 10 k/1.37 k (Vcm 0.40 V, nguồn từ +3V3_SW nên không cấp ngược CM4); REFCLKO0 → 33 Ω/49.9 Ω → 100 nF → REFCLKP/N; REFCLKO1..3 → NIC1, NIC2, REFCLKI của SW2 (ghép DC). CLKBUF_PD kéo xuống 330 Ω, IREF 475 Ω, REXT 1.43 k giữa chân 116–115.
- Reset: PCIe_nRST (kéo xuống 100 k) → SW1 PERST_L; DWNRST_L1/2/3 → NIC1, NIC2, SW2; SW2 DWNRST_L1/2 → NIC3, NIC4. PCIe_CLK_nREQ nối GND qua 0 Ω.
- Strap theo mục 3.2–3.4: TEST1/TEST2 kéo lên 5.1 k; TEST3–6, PWR_SAV, TMS, TRST_L kéo xuống 330 Ω; SMBCLK/SMBDATA kéo lên 5.1 k; TCK/TDI/TDO để hở. Phân rail: VDDC/VDDCAUX/AVDD 1.0 V, VDDR/VAUX/CVDDR/AVDDH 3.3 V; số tụ 100 nF bằng số chân nguồn.

**Nguồn**
- Q101: cực máng phía jack, cực nguồn phía tải, cổng về GND qua 100 k, Zener 12 V cathode ở cực nguồn — đúng. TVS và diode bắt D104 đúng chiều.
- TPS54560B: Vout 5.00 V, RT 243 k → ~400 kHz, UVLO 7.9/6.9 V, bù 13 k + 4.7 nF // 47 pF, tụ boot 100 nF — tính lại khớp.
- TPS563201: 3.32 V và 1.00 V đúng; PERIPH_EN ≈ 2.8–3.0 V sau khi tính điện trở kéo xuống nội của hai chân EN, đủ ngưỡng.
- Chống cấp ngược: không tìm thấy IC nào được cấp nguồn khi +3V3 của CM4 tắt mà có chân lái vào CM4 (RTC dùng I2C cực máng hở; SRAM ở chế độ VBAT có ngõ ra trở kháng cao; clock PCIe đã ghép AC). VBUS của USB-C và micro-USB không nối rail nào.
- Ngân sách: tải +3V3 của CM4 ước < 80 mA so với 600 mA; +1V0 tối đa ~1.23 A cho 2 switch; tổng +5V ~4.5 A trong khả năng của U101.

**USB / debug**
- FSUSB42: SEL = nRPIBOOT; thấp → HSD1 = USB-C, cao → HSD2 = USB-A; /OE nối GND — khớp bảng chân trị. CC1/CC2 mỗi chân 5.1 k xuống GND; D+/D− hai mặt USB-C nối chung.
- TPS2553 (EN tích cực cao, kéo lên +3V3), RILIM 22 k ≈ 1.2 A. USBLC6 đấu kiểu xuyên qua đúng cặp chân 1–6, 3–4.
- CH340C: V3 nối VCC = 3.3 V; TXD → 470 Ω → GPIO15 (RXD), GPIO14 (TXD) → 470 Ω → RXD.

**Bảo mật**
- TPM trên SPI0 CE1 (GPIO7), khớp `docs/notes/raw/tpm-slb9670-overlay.dts` (`reg = <1>`); SRAM trên CE0; RTC trên SDA0/SCL0 (chân 82/80, đã có kéo lên 1.8 k trên CM4).
- `V_KEEP` = OR của +3V3 và pin (qua 1 k) bằng BAT54C, cathode chung đúng chân 3. Công tắc MX và J1101 mắc nối tiếp nên đứt dây = mở.
- Khi chỉ còn pin: mở công tắc làm VBAT mất → dữ liệu mất (đúng nguyên lý, xem thêm S1). Nhiễu nảy phím < 5 ms không gây xóa nhầm (τ 22 ms).

**Ethernet**
- CM4 Pair0..3 → MDI0..3 của jack WAN; NIC MDIP/N0..3 → MDI0..3 của jack LAN, đúng cực. Điểm giữa biến áp qua 100 nF xuống GND; LED anode qua 470 Ω lên rail, cathode về chân LED tích cực thấp.
- Thạch anh 25 MHz CL 12 pF với 2 × 18 pF; RSET 2.49 k; ISOLATEB kéo lên (1 k/15 k); CLKREQB, LANWAKEB kéo lên 10 k.

**Footprint / cơ khí**
- RJ45 tự dựng: hàng lẻ/chẵn, bước 2.54/1.27 mm, LED 13.25 mm, trụ 11.43 mm, tai vỏ 15.49 mm, các khoảng 10.92 / 4.90 / 3.05 / 8.89 mm đều khớp bản vẽ trang 2. Nhìn từ trên, chân 1 và LED xanh ở đúng phía; xoay 180° trên bo là phép quay thuần, **không bị lật gương**.
- LQFP-128 + EP 5.5 mm: khớp vỏ FD128 (D/E 16 mm, e 0.4 mm, D2/E2 5.10–5.99 mm). U401/U501 xoay để các chân PCIe (97–128) quay về phía CM4.
- CM4: footprint gốc của Raspberry Pi, xoay 180° (không lật); chân PCIe ở X = 79.55, USB ở X = 82.63, MDI và +5V ở X ≈ 113.5–116.6 — khớp mô tả trong routing-plan.
- Jack DC: chân 1 = tâm (+), 2 = vỏ, 3 = công tắc, khớp sơ đồ và vị trí lỗ của bản vẽ; miệng jack quay ra mép sau, nhô ~0.4 mm. Các đầu nối mặt trước đều quay ra mép trước.

## 4. Giới hạn của review này

- Không có datasheet trong dự án cho: PCF85063A (file hỏng), BAT54C, BSS138, AO3401A, 2N7002, AO4407A, TPS54560B, TPS563201, TPS2553, USBLC6. Các mục liên quan đối chiếu theo pinout/thông số chuẩn đã biết, không phải từ file.
- Mặc định kéo xuống của GPIO23 (C1) và dòng rò VCC→VBAT của SRAM (S1) cần đo xác nhận trên phần cứng.
- Chưa kiểm: tồn kho LCSC hiện tại, stackup/trở kháng (đã ghi là sơ bộ, rủi ro R7), 3D model, cực tính LED mặc định của RTL8111H ngoài mô tả chung trong datasheet, và hành vi PCIe với hai switch ghép tầng (rủi ro R1 của doc).
