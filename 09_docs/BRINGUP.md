# Hướng dẫn bring-up — CM4 Security Gateway Rev A

Làm lần lượt từng bước; **không gắn CM4 cho tới bước 3**. Dụng cụ: nguồn phòng thí nghiệm có giới hạn dòng (hoặc adapter
12 V kèm ampe kế), đồng hồ vạn năng, máy hiện sóng (nên có), cáp USB-C, cáp micro-USB, máy tính Linux.

Điểm đo (hàng test point ở mép sau bo, từ trái sang phải): `TP101 +12V`, `TP102 +5V`, `TP103 +3V3`, `TP104 +3V3_SW`,
`TP105 +1V0`, `TP106 GND`; hàng dưới: `TP107 GND`, `TP108 PERIPH_EN`. Các điểm khác: `TP201 RUN_PG`, `TP202 PCIE_RST_N`
(cạnh hàng jumper), `TP401/TP501 AVDD_1V0` (phía trên SW1/SW2), `TP601…TP901 V1P0` (bên phải từng NIC),
`TP1001 USBC_VBUS`, `TP1101 V_KEEP`, `TP1102 SRAM_VCC`, `TP1103 TAMPER_OPEN`.

## Bước 0 — Kiểm tra nguội (chưa cấp điện)

1. Soi mối hàn: hai đầu nối DF40 của CM4, hai LQFP-128 (U401, U501), 4 QFN RTL8111H, cổng USB-C.
2. Đo điện trở so với GND (TP106), **không được chập**:

   | Điểm | Mong đợi |
   |---|---|
   | TP101 +12V | > 1 kΩ (tăng dần do tụ nạp) |
   | TP102 +5V | > 100 Ω |
   | TP104 +3V3_SW | > 50 Ω |
   | TP105 +1V0 | > 5 Ω (lõi switch có trở kháng thấp; < 1 Ω là chập) |
   | TP103 +3V3 | > 1 kΩ (chưa gắn CM4) |

3. Kiểm tra cực tính jack DC: tâm dương.

## Bước 1 — Cấp 12 V, chưa gắn CM4

Giới hạn dòng **0.3 A**. Cấp 12 V vào J101.

| Đo | Mong đợi | Nếu sai |
|---|---|---|
| Dòng tiêu thụ | < 30 mA | > 100 mA: tắt ngay, tìm chập ở khối 5 V |
| LED PWR (D103, đỏ) | sáng | — |
| TP101 +12V | 11.7–12.0 V (sụt qua Q101 rất nhỏ) | 0 V: cầu chì F101 hoặc Q101 hàn ngược |
| TP102 +5V | **4.9–5.1 V** | sai: xem R109/R110 (53.6 k/10.2 k), D104, L101 |
| TP108 PERIPH_EN | ≈ 0 V | — |
| TP104, TP105 | ≈ 0 V (hai buck ngoại vi **chưa** bật vì chưa có +3V3 của CM4) | có áp: kiểm tra R103/R104 |

Hạ nguồn xuống 9 V rồi tăng lên 24 V: +5V phải giữ nguyên. Dưới ≈ 6.9 V buck tắt (UVLO).
Đảo cực nguồn (tâm âm): không có dòng, không hỏng (Q101 chặn).

## Bước 2 — Thử hai buck ngoại vi không cần CM4

Nối tạm TP108 `PERIPH_EN` lên TP102 (+5V) qua **điện trở 10 kΩ** (mức > 1.6 V là bật). Giới hạn dòng 1 A.

| Đo | Mong đợi |
|---|---|
| TP104 +3V3_SW | 3.25–3.40 V |
| TP105 +1V0 | **1.00–1.06 V** (đặt 1.03 V) |
| TP401, TP501 AVDD_1V0 | ≥ 0.97 V (sau hạt ferrite) |
| TP601…TP901 V1P0 | 0.95–1.05 V (LDO nội của RTL8111H) |
| Dòng 12 V | 0.15–0.35 A (2 switch + 4 NIC ở trạng thái reset) |

Sờ thử U401, U501, U601–U901: chỉ ấm. Tháo điện trở tạm.

## Bước 3 — Gắn CM4, khởi động

1. Tắt nguồn. Gắn CM4 (eMMC), bắt 4 trụ M2.5. Lắp pin CR2032 (cực + lên trên). Đặt jumper lên `J1101`.
2. Giới hạn dòng 2 A, cấp 12 V. Mong đợi: TP103 +3V3 = 3.3 V, TP108 lên ≈ 3 V, TP104/TP105 lên theo;
   `TP201 RUN_PG` = 3.3 V; LED ACT (D201) nháy.
3. Dòng 12 V khi chạy không tải: 0.4–0.8 A.

## Bước 4 — Nạp eMMC (rpiboot)

1. Tắt nguồn. Gạt công tắc **BOOT** (SW1001, trong bo) sang vị trí BOOT (kéo `nRPIBOOT` xuống GND; đồng thời mux USB
   chuyển sang cổng **FLASH** USB-C). Trên lụa có nhãn **BOOT** / **eMMC** ở hai đầu công tắc. Lần đầu: tắt nguồn,
   gạt về phía nhãn BOOT rồi đo thông mạch giữa chân giữa (nRPIBOOT) và chân phía BOOT (GND) — phải ≈0 Ω; nếu ngược,
   coi nhãn là đảo (chỉ ghi chú, không ảnh hưởng mạch).
2. Nối cổng FLASH (USB-C) với máy tính. **Bo vẫn phải cấp 12 V** — VBUS của USB-C không cấp nguồn cho bo.
3. Trên máy tính: `sudo rpiboot` (gói `rpiboot` / repo `raspberrypi/usbboot`). eMMC hiện ra như ổ USB.
4. Ghi Raspberry Pi OS Lite 64-bit bằng Raspberry Pi Imager; trước khi rút, sửa `config.txt` theo `SOFTWARE.md`.
5. Tắt nguồn, rút USB-C, gạt BOOT về vị trí thường.

## Bước 5 — Console

Nối cổng DEBUG (micro-USB) với máy tính: xuất hiện `/dev/ttyUSB0` (CH340, 115200 8N1) ngay cả khi CM4 chưa chạy
(CH340 lấy nguồn từ +3V3 của CM4 nên chỉ lên khi bo có điện). Bật nguồn: thấy log khởi động.

## Bước 6 — Kiểm tra từng khối (trên CM4)

| Khối | Lệnh | Mong đợi |
|---|---|---|
| PCIe | `lspci -tv` | 2 cầu Pericom/Diodes `12d8:2404` (mỗi switch hiện 1 cổng lên + các cổng xuống) và **4** thiết bị Realtek `10ec:8168` |
| Tốc độ liên kết | `sudo lspci -vv \| grep LnkSta` | switch: 5 GT/s x1; NIC: 2.5 GT/s x1 |
| NIC | `ip -br link` | 4 giao diện `r8169` + `eth0` (WAN của CM4) |
| Ethernet | cắm cáp từng cổng, `ethtool <if>` | 1000 Mb/s Full; LED xanh/vàng trên jack sáng |
| USB-A | cắm USB, `lsusb` | thấy thiết bị; VBUS 5 V |
| TPM | `ls /dev/tpm0`, `tpm2_getrandom 8 --hex` | có thiết bị, trả về 8 byte |
| RTC | `sudo hwclock -r`; tắt máy, rút điện 1 phút, bật lại | giờ vẫn đúng |
| SRAM | xem `SOFTWARE.md` (đọc/ghi qua `/dev/spidev0.0`) | ghi rồi đọc lại đúng |
| Quạt (tùy chọn) | PWM GPIO18 | quạt 5 V trên J202 đổi tốc độ |

Nếu `lspci` không thấy switch: đo `TP202 PCIE_RST_N` (phải lên 3.3 V sau khi khởi động), đo clock 100 MHz tại chân
73/74 của U401 bằng đầu dò vi sai (biên độ ≈ 0.7 V, mức chung ≈ 0.4 V — rủi ro R2), kiểm tra +1V0.
Nếu chỉ thấy SW1 mà không thấy SW2/NIC: kiểm tra clock tại Rs của REFCLKO và các tụ AC 100 nF.

## Bước 7 — Thử mạch chống mở vỏ

Chuẩn bị: ghi một mẫu vào SRAM (xem `SOFTWARE.md`). Vỏ chưa có nên dùng tay nhấn giữ switch MX (SW1101) hoặc
thay bằng jumper: **switch nhấn = mạch kín = bình thường**.

| Thử | Cách làm | Mong đợi |
|---|---|---|
| A. Mở vỏ khi đang chạy | nhả switch (hoặc rút jumper J1101) | `TP1103 TAMPER_OPEN` lên ≈ 2.7 V (GPIO23 = 1); `TP1102 SRAM_VCC` về < 0.2 V trong vài ms; nhấn lại → đọc SRAM ra dữ liệu **đã mất** |
| B. Mở vỏ khi tắt máy | tắt nguồn 12 V (giữ switch), nhả switch 1 giây, nhấn lại, bật nguồn | dữ liệu **đã mất** |
| C. Giữ dữ liệu khi mất điện | giữ switch nhấn, tắt nguồn 10 phút, bật lại | dữ liệu **còn nguyên** |
| D. Rung/nảy | gõ nhẹ lên switch đang nhấn | dữ liệu còn (lọc τ ≈ 5 ms) |

Đo thêm (rủi ro còn mở): `V_SW` tại R1105 khi đóng ≈ V_KEEP; dòng pin khi tắt máy (ampe kế µA nối tiếp pin,
vỏ đóng) **≤ 3 µA** sau khi phần mềm đã tắt CLKOUT của RTC.

## Bước 8 — Chạy tải

`iperf3` đồng thời trên 4 LAN + WAN trong 30 phút; nhiệt độ U101, L101, U401, U501 < 80 °C; +5V không tụt dưới 4.85 V
khi cắm tải USB 1 A.
