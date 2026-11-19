# Xử lý kết quả review độc lập giai đoạn 1

Báo cáo gốc: `2026-11-11-stage1-independent-review.md` (agent độc lập, đối chiếu netlist và datasheet).
Kết luận của review: **2 lỗi chặn, 11 điểm nên sửa, 9 ghi chú**. Bảng dưới là cách xử lý; mọi thay đổi đã được sinh lại
vào schematic/PCB và kiểm bằng ERC/DRC.

| Mã | Nội dung | Xử lý | Kiểm chứng |
|---|---|---|---|
| **C1** | Tamper không cắt VCC của SRAM khi CM4 đang chạy (GPIO23 kéo VCC_GATE xuống) | **Đã sửa.** VCC_GATE không còn nối CM4; kéo lên 10 k; Q1104 tạo `TAMPER_OPEN` riêng. | Netlist: `/Security/VCC_GATE` chỉ gồm Q1101.3, Q1102.1, Q1103.1, R1107; `TAMPER_OPEN` = R1111, TP1103, U201.47. |
| **C2** | Ferrite 450 mΩ/0.2 A làm AVDD 1.0 V của switch tụt dưới 0.95 V | **Đã sửa.** FB → BLM18PG121SN1D (50 mΩ, 2 A, C14709); +1V0 = 1.03 V (R113 3.4 k). | AVDD ≥ 1.03 − 0.05 × 0.32 = 1.01 V. |
| S1 | Nút V_SW dùng chung cho VBAT và cổng FET; rò ngược có thể giữ FET dẫn; J1101 không bảo vệ | **Đã sửa.** D1102 + R1106 10 MΩ tách nhánh VBAT; C1105 1 nF; R1104 1 k nối tiếp J1101. | Netlist `/Security/V_SW`, `/Security/VBAT_SRAM`. Vẫn cần đo khi bring-up. |
| S2 | Ước lượng điện áp ký sinh trên SRAM_VCC quá lạc quan | **Đã sửa.** Điện trở kẹp 100 Ω → 10 Ω; sửa số liệu trong design doc. | 5.7 mA × ~15 Ω ≈ 0.1 V. |
| S3 | Vòng nóng U101 trải rộng | **Đã sửa bố trí.** C106 cách VIN 2.7 mm, L101 cách SW 4.2 mm, C109 2.9 mm, D104 7.8 mm. | Đo trên `placement.json`. |
| S4 | REXT/IREF/tụ clock và decoupling của switch xa chân | **Đã sửa bố trí.** Mỗi tụ 100 nF nằm dưới đúng một chân nguồn (xa nhất 2.8 mm, trung bình 1.9 mm); REXT 2.5 mm, IREF 1.6 mm, tụ clock tự vòng 3.6–4.3 mm. NIC tương tự (≤ 3.2 mm). | Đo trên `placement.json`. |
| S5 | Điện trở phân cực clock cách REFCLKI 35 mm | **Đã sửa bố trí.** Cách chân 73/74 của U401 2.7–4.2 mm. | — |
| S6 | Thạch anh RTC cách IC 12 mm | **Đã sửa bố trí.** 2.8–3.0 mm. | — |
| S7 | FET quạt 2N7002 không đủ ở Vgs 3.3 V | **Đã sửa.** Q201 → AO3400A (C20917). | BOM. |
| S8 | Ngân sách pin là giá trị điển hình; CLKOUT của RTC bật mặc định; file datasheet RTC hỏng | **Đã sửa tài liệu**: nêu rõ điều kiện, yêu cầu phần mềm tắt CLKOUT; xóa file hỏng và ghi chú trong `SOURCES.md`. Datasheet NXP **chưa tải được** — còn nợ. | design doc §8.2–8.3. |
| S9 | Thứ tự cổng và kích thước bo chưa ghi trong decisions.md; cần chủ dự án duyệt | **Đã ghi** vào `decisions.md`; nêu thành mục cần xác nhận trong README của gói. | — |
| S10 | parts-check.md ghi sai mã 3 đầu nối | **Đã sửa**; BOM được tra kho tự động mỗi lần xuất gói. | `06_bom/bom_summary.md`. |
| S11 | Nút reset nối thẳng RUN_PG xuống GND | **Đã sửa.** Thêm R206 220 Ω. | Netlist `RUN_PG`, `/CM4/RST_BTN`. |
| N1 | Màu LED WAN ngược gợi ý của datasheet | Đã đổi: chân 15 (activity) → xanh, chân 17 (speed) → vàng. | Netlist `WAN_LED_G` = U201.15. |
| N3 | Cổng 3 SW2 vẫn lắp linh kiện | Giữ nguyên làm dự phòng; ghi rủi ro R9. | — |
| N4 | Yêu cầu thời gian lên/tắt 3.3 V của RTL8111H | Ghi rủi ro R10, đo khi bring-up. | — |
| N5 | Các đầu nối mặt trước không đồng phẳng | Đã ghi trong bản vẽ kích thước; thuộc thiết kế vỏ. | — |
| N6 | Khe khoan jack DC 3.0 mm so với 3.5 mm của bản vẽ | **Đã sửa.** Footprint riêng `BarrelJack_XKB_DC-005-5A` (khe 1.0 × 3.5, khoảng chân 5.9 mm). | `footprints.py`. |
| N7 | IC ESD USB cách đầu nối 6–9 mm | Đã đưa lại gần: 5.3–6.0 mm; tinh chỉnh thêm khi đi dây. | — |
| N8 | Thiếu điểm đo rail lọc của switch và 1.0 V của NIC | **Đã thêm** TP401, TP501 (AVDD_1V0) và TP601–TP901 (V1P0). | Netlist. |
| N2, N9 | Xác nhận đúng | Không cần xử lý. | — |

## Còn nợ sau review

- Datasheet PCF85063A của NXP chưa tải được bằng script; cần đọc trực tiếp trước giai đoạn 2 để xác nhận dòng tiêu thụ và thanh ghi tắt CLKOUT.
- Hai điểm review đánh dấu "không chắc" (kéo xuống mặc định của GPIO23; rò VCC→VBAT của SRAM) chỉ xác nhận được bằng đo trên bo thật. Mạch đã được sửa để không phụ thuộc vào chúng.
- Sau khi sửa **chưa chạy lại một vòng review độc lập thứ hai**; các sửa đổi được kiểm bằng netlist, ERC/DRC và phép đo khoảng cách ở trên.
