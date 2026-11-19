# CM4 Security Gateway Rev B — GÓI FINAL (giai đoạn 2)

Xuất lúc 2026-11-19 14:27 · commit `5cdd320` (file chưa commit: 29) · KiCad 10.0.6

Bo mạch mang cho Raspberry Pi CM4 (eMMC, không WiFi): 1 WAN + 4 LAN Gigabit, USB-A, USB-C nạp eMMC, console micro-USB,
TPM 2.0, RTC, SRAM giữ khóa bị xóa khi mở vỏ (switch bàn phím cơ). 150 × 105 mm, 6 lớp, ENIG, nguồn 12 V DC.

## Trạng thái

| Hạng mục | Kết quả |
|---|---|
| ERC schematic | **0 lỗi**, 0 cảnh báo |
| DRC PCB (đã đi dây) | **0 lỗi**, 0 cảnh báo |
| Chưa nối | **0** |
| Lệch schematic ↔ PCB | **0** |
| Luật DRC theo Reference | không có |
| Linh kiện | 420 footprint; BOM JLC 397 = CPL 397 → đạt |
| Chân CM4 có nối | 100 / 200 |
| Tiền linh kiện | ≈ 56.7 USD/bo (5 bo, chưa gồm CM4, PCB, công lắp) |

## Đặt mạch: làm theo `06_fabrication/ORDERING.md`

Ba file cần tải lên JLCPCB: `06_fabrication/gerber.zip`, `bom_jlc.csv`, `cpl_jlc.csv`.
Trước khi thanh toán phải xem lại chiều xoay linh kiện ở màn hình xem trước của JLC (mục 4 của ORDERING.md).

## Nên xem

1. `03_images/3d_iso.png`, `3d_top.png`, `3d_bottom.png`, `3d_front.png`, `3d_back.png` — hình dạng bo.
2. `03_images/copper_L1…L6.png` — từng lớp đồng; `02_pcb_drawings/` — PDF từng lớp, bản vẽ lắp ráp, kích thước.
3. `01_schematic/cm4-gateway-schematic.pdf` — nguyên lý.
4. `05_reports/SUMMARY.md`, `routing-report.md` — DRC/ERC, độ dài và độ lệch từng cặp vi sai.
5. `09_docs/BRINGUP.md` — cấp nguồn lần đầu, nạp eMMC, thử từng khối, thử chống mở vỏ.
6. `09_docs/SOFTWARE.md` — `config.txt`, PCIe/NIC, TPM, RTC, SRAM + GPIO tamper.
7. `09_docs/design-doc.md`, `decisions.md` — thiết kế và mọi quyết định (kể cả thay đổi ở giai đoạn 2).

## Thay đổi so với gói giai đoạn 1 đã duyệt

- **Công tắc chống mở vỏ**: theo phản hồi của chủ dự án — Kailh Red (C49234236), model 3D switch bàn phím cơ thật.
  Nhấn (vỏ đậy) = thông mạch; nhả (mở vỏ) = ngắt → SRAM mất cả VCC lẫn VBAT.
- **Đảo cực P/N tại mọi đầu thu PCIe** (chuẩn PCIe cho phép, không cần cấu hình phần mềm) để cặp vi sai không bắt chéo.
- **Đổi gán cổng xuôi của switch** (SW1: cổng 1 → LAN2, cổng 2 → LAN1; SW2: cổng 1 → LAN4, cổng 2 → LAN3).
- **Dời linh kiện bên trong bo**: SW2 sang trái 6.4 mm; tụ AC và điện trở clock xếp thành cặp cạnh chân; khu USB xếp lại.
  Vị trí mọi cổng mặt trước/sau, kích thước bo và lỗ bắt vít **không đổi**.
- Chi tiết và lý do: `09_docs/decisions.md` (các dòng "(GĐ2)").

## Rủi ro còn mở (chi tiết ở design-doc §11)

- **R1** — chưa có bằng chứng công khai PI7C9X2G404SL ghép tầng chạy với CM4 (về nguyên tắc là cầu PCIe chuẩn).
- **R2** — mạch phân cực lại clock PCIe của CM4 chưa đo thực tế (đo ở BRINGUP bước 6).
- **R7** — bề rộng đường theo trở kháng tính bằng công thức gần đúng; cần chọn đúng stackup JLC06161H-3313 khi đặt.
- **Góc xoay CPL** chưa kiểm chứng được ngoại tuyến → xem lại trên trang JLC.
- Bản đi dây do script sinh, đã qua DRC của KiCad và review độc lập bằng máy; **chưa có người rà layout** — nên đặt
  số lượng nhỏ (5 bo) cho lần đầu.

## Cấu trúc gói

```
01_schematic/      PDF toàn bộ sheet + SVG
02_pcb_drawings/   PDF từng lớp đồng, bản vẽ lắp ráp top/bottom, kích thước, floorplan
03_images/         render 3D 5 góc, ảnh từng lớp đồng, sơ đồ khối, cây nguồn
04_3d/             STEP đầy đủ
05_reports/        ERC + DRC (rpt + json), tóm tắt, báo cáo đi dây
06_fabrication/    gerber.zip (+ thư mục gerber, bản đồ khoan), bom_jlc.csv, cpl_jlc.csv, lcsc_map.csv, ORDERING.md
07_bom_netlist/    BOM đầy đủ kèm tồn kho/giá, netlist, toạ độ mọi linh kiện
08_source/         nguồn KiCad + thư viện + model 3D + toàn bộ script sinh thiết kế
09_docs/           design doc, bảng chân CM4, driver-check, BRINGUP.md, SOFTWARE.md, quyết định, review
```

Sinh lại toàn bộ từ nguồn: `python3 scripts/gen/design.py && python3 scripts/gen/board.py &&
git show 5cdd320:hardware/cm4-gateway.kicad_pcb > /tmp/revA.kicad_pcb && .venv/bin/python scripts/gen/reuse_route.py /tmp/revA.kicad_pcb && .venv/bin/python scripts/gen/finish.py 8 && .venv/bin/python scripts/gen/patch_rev_b.py && python3 scripts/gen/polish_rev_b.py hardware/cm4-gateway.kicad_pcb && python3 scripts/export_release.py` (Rev B giữ nguyên dây của Rev A ngoài khu nguồn, chỉ đi lại khu nguồn; Rev A sinh bằng `route.py` + `patch_rev_a.py`).
