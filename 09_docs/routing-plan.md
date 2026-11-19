# Kế hoạch đi dây cho giai đoạn 2

Toạ độ: gốc = góc sau-trái của bo, X sang phải, Y về mặt trước (mm). Vị trí lấy từ bố trí hiện tại
(`hardware/placement.json`).

## 1. Thứ tự thực hiện

1. Fanout đầu nối CM4 (DF40 bước 0.4 mm) và hai LQFP-128: via 0.45/0.20 đặt ngoài hàng pad, không via-in-pad.
2. Cặp vi sai theo thứ tự: PCIe CM4↔SW1 → SW1↔SW2 → 4 làn switch↔NIC → REFCLK → MDI (5 cổng) → USB.
3. Nguồn: vùng đồng L5 (+5V, +3V3_SW, +1V0, +3V3), vòng nóng của U101/U102/U103 trên L1, via nối tụ decoupling.
4. Tín hiệu chậm (SPI, I2C, UART, reset, LED, strap) trên L1/L6; có thể dùng Freerouting cho nhóm này.
5. Khâu via GND dọc mép bo (bước ≤ 5 mm), quanh các cặp vi sai khi đổi lớp, và quanh vùng CHASSIS.

## 2. Hành lang cho từng nhóm tín hiệu

| Nhóm | Từ → đến | Lớp | Dài ước tính | Ghi chú |
|---|---|---|---|---|
| PCIe TX/RX CM4↔SW1 | chân 116–124 của CM4 tại (81, 36–41) → cạnh phải SW1 tại (68, 42–45) | L1 | ~15 mm | Đi thẳng sang trái dưới mép module; tụ AC C401/C402 ở cột X≈70. Không đổi lớp. |
| REFCLK CM4→SW1 | chân 110/112 tại (81, 39) → chân 73/74 ở cạnh dưới SW1 (≈ 64, 58) | L1 | ~30 mm | Vòng qua góc dưới-phải của SW1; điện trở phân cực R209–R212 đã đặt ngay tại chân 73/74 (cách 3–4 mm), đi qua pad để không tạo nhánh cụt. |
| SW1 cổng 3 ↔ SW2 cổng lên | cạnh phải SW1 (68, 45–47) → cạnh phải SW2 (38, 42–45) | L3 | ~45 mm | Một lần đổi lớp ở mỗi đầu, chui dưới SW1; kèm via GND. |
| SW1 → NIC1, NIC2 | cạnh phải SW1 (68, 51–57) → NIC tại (71.6, 72) và (53.4, 72) | L1 | 20–30 mm | Đi xuống giữa cột tụ AC và module CM4. |
| SW2 → NIC3, NIC4 | cạnh phải SW2 (38, 51–57) → NIC tại (35.2, 72) và (17.0, 72) | L1 | 20–35 mm | |
| REFCLK switch → NIC | cạnh dưới mỗi switch (Y≈58) → cạnh phải NIC | L1 | 15–30 mm | Rs/Rp đặt ngay dưới switch (hàng Y 59.6–63.4). |
| MDI NIC → jack LAN | cạnh trước NIC (Y≈78) → chân jack (Y 87–90) | L1 | ~10 mm | Bốn cặp đi thẳng, không via. |
| MDI CM4 → jack WAN | chân 3–12 của CM4 tại (115, 38–41) → jack WAN (133, 87–90) | L3 | ~65 mm | Đổi lớp ngay tại đầu nối (dưới module) và tại jack; 4 cặp giữ song song, cách nhau ≥ 0.5 mm. |
| USB CM4 → mux | chân 103/105 tại (82.6, 40) → U1001 tại (≈ 92, 73) | L3 | ~40 mm | Chui dưới module ra phía trước. |
| USB mux → USB-A / USB-C | U1001 → J1001 (90, 94), J1002 (116, 101) | L1 | 20–35 mm | Qua USBLC6 đặt sát đầu nối. |

## 3. Nguồn

- **L5 chia vùng**: +5V phủ nửa sau-trái và dải tới chân +5V của CM4 (115, 22–26); +3V3_SW phủ vùng NIC và switch;
  +1V0 là đảo dưới hai switch (nối U103 tại góc trái); +3V3 (CM4) phủ vùng USB/debug và bảo mật.
- +12V_JACK, +12V, nút SW của U101 đi bằng vùng đồng trên L1, bề rộng ≥ 2 mm, vòng Cin–U101–D104 nhỏ nhất có thể.
- Đế tản nhiệt: U401/U501 (5.5 × 5.5 mm) lưới 4×4 via 0.3 mm; NIC lưới 2×2; U101 dùng via có sẵn trong footprint.

## 4. Điểm cần chú ý

- Không đi cặp vi sai qua khe hở mặt phẳng tham chiếu (đặc biệt quanh lỗ của jack RJ45 và lỗ vít CM4).
- Vùng dưới module CM4 mặt trên không có linh kiện: dùng làm hành lang L1 cho tín hiệu chậm.
- `V_SW` (trở kháng cao, 4.7 MΩ) đi ngắn, có vòng bảo vệ GND, tránh xa nút chuyển mạch.
- Sau khi đi dây: báo cáo độ dài/độ lệch từng cặp, kiểm tra DRC 0 lỗi và 0 chưa nối.
