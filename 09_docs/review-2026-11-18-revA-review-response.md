# Phản hồi review độc lập rev A → thay đổi trong rev B (2026-11-18)

| ID | Kết luận | Xử lý trong rev B |
|----|----------|-------------------|
| R1 | Đồng ý | C104/C105/C106 quay pad +12V về cùng hàng chân VIN; dải đồng 1 mm (cổ 0.6 mm giữa hai chân kề) đi **trước** mọi net khác và **khóa** không cho gỡ (`route.py: pre_power`, `rt.fixed`). Net PWR_HV chỉ đi lớp ngoài 1 oz, rộng 1.0/0.8/0.6 mm, mọi bước cứu/sửa không được hẹp hơn 0.6 mm (`rt.minw`). Luật DRC mới `nguon_dong_lon_rong_toi_thieu` (≥ 0.6 mm) bắt lỗi nếu còn sót. |
| R2 | Đồng ý | `ROT_FIX` thêm `^TSOT-23` → 180° (cùng quy ước SOT-23-6). Vẫn phải xem trước vị trí ở bước đặt hàng (ORDERING §3). |
| R3 | Đồng ý | SW_5V: dải 1 mm chân 8 → L101.1, dải 1.5 mm L101.1 → catốt D104, cố định. +5V: dải 1.5 mm L101.2 → C110–C113. |
| R4 | Đồng ý | U102/U103 bố trí cố định: cuộn cảm xoay 180° (pad SW quay về IC, nút SW ≈ 2 mm, 0.6 mm), tụ boot ngay trên chân VBST, tụ vào sát chân VIN, tụ ra sát pad ra cuộn cảm. Luật DRC `nut_sw_buck_rong_toi_thieu` (≥ 0.5 mm). |
| R5 | Đồng ý | Thêm lụa BOOT / eMMC ở hai đầu SW1001, nhãn chức năng PWR BTN / EEPROM WP / TAMPER EXT / RESET / FAN 5V; nét lụa và nét chữ ≥ 0.15 mm, chữ ≥ 0.8 mm (`polish_rev_b.py`). BRINGUP có bước đo xác nhận chiều gạt. |
| R6 | Đồng ý | Phân loại THT theo thuộc tính footprint (pad PTH của via tản nhiệt / chân giữ vỏ không còn bị tính là xuyên lỗ). |
| R7 | Đồng ý | Via tản nhiệt trong pad đế là chủ ý; ORDERING chọn **Epoxy Filled & Capped** (mặc định, miễn phí với 6 lớp). |
| R8 | Đồng ý | Bỏ nhánh code chết; mặt dưới chỉ có R/C/ferrite không cực tính. U1001, thạch anh, SW1001, J1002 nằm trong danh sách xem trước ở bước đặt hàng. |
| R9 | Đồng ý | `polish_rev_b.py` xóa từng đoạn/via treo, chạy DRC sau mỗi lần, hoàn tác nếu làm hở mạch. |
| R10 | Một phần | +12V_JACK đi lớp ngoài, via 0.6/0.3; xem số via trong `routing-report.md`. |
| R11 | Đồng ý | ORDERING: chọn "Edge Rails/Fiducials: Added by JLCPCB" (rail có fiducial). |
| R12 | Ghi nhận | Tồn kho thay đổi theo ngày — kiểm tra lại ở bước BOM; DF40C có thể đặt trước (pre-order / global sourcing). |
| R13 | Đồng ý | Sửa chú thích luật cho khớp 0.11 mm. |
