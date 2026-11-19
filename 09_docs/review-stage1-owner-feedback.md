# Phản hồi của chủ dự án về gói giai đoạn 1

Ngày 2026-11-11 — gói `out/stage1/` (commit `0a09bc9`).

## Kết luận

**Duyệt giai đoạn 1.** Cho phép thực hiện giai đoạn 2 (P5–P7) theo `task.md`.
Các điểm khác đầu bài nêu trong README của gói (2× PI7C9X2G404SL, bo 150 × 105 mm, thứ tự cổng mặt trước,
adapter 12 V/3 A, 5 jack RJ45 đơn, tên `TAMPER_OPEN`) không bị phản đối ⇒ coi như chấp nhận.

## Điểm cần sửa

| # | Phản hồi | Xử lý |
|---|---|---|
| 1 | Trong ảnh 3D, công tắc chống mở vỏ trông như nút nhấn thường, "chưa chuẩn". Muốn dùng switch bàn phím cơ, ví dụ Red switch 3 chân: vỏ đè xuống thì thông mạch, nâng nắp lên thì ngắt ⇒ SRAM bị xóa. | Mạch và footprint từ đầu đã là switch kiểu Cherry MX (thường hở, nhấn = đóng) đúng nguyên lý chủ dự án mô tả; chỉ **hình 3D** dùng tạm model nút nhấn 12 mm vì bản cài KiCad không có model MX. Đã sửa: (a) thay model 3D bằng model Cherry MX thật (`hardware/lib/3dmodels/SW_Cherry_MX_PCB.stp`, nguồn kiswitch); (b) đổi mã linh kiện từ Kailh Blue (C49234235, có khấc "click") sang **Kailh Red CPG151101D05 (C49234236)** — tuyến tính 45 gf, điểm tác động 2 mm, hợp làm công tắc nắp hơn; (c) footprint `SW_Cherry_MX_1.00u_PCB` có 2 lỗ chân điện + lỗ trục 4 mm + 2 lỗ định vị 1.7 mm nên **lắp được cả switch 3 chân lẫn 5 chân** của Cherry/Kailh/Gateron/Outemu. |

## Ghi chú cho thiết kế vỏ (không đổi mạch)

- Switch MX đóng mạch khi trục bị nhấn ≥ 2 mm (hành trình tối đa 4 mm). Nắp vỏ cần một gờ/trụ đè trục xuống
  khoảng 3 mm khi đậy; đỉnh trục khi chưa nhấn cao ≈ 15 mm so với mặt bo (thân 11.6 mm + trục 3.6 mm).
- Nếu vỏ không đè trực tiếp được, dùng header `J1101` để nối công tắc ngoài nối tiếp (rút jumper = mở mạch).
