# Stackup và trở kháng (sơ bộ — chốt lại bằng máy tính trở kháng JLC ở giai đoạn 2)

## Stackup 6 lớp, 1.6 mm — theo JLC06161H-3313

Đã khai báo trong `hardware/cm4-gateway.kicad_pcb` (mục `stackup`). Giá trị điện môi lấy theo bảng công bố của JLCPCB
cho bộ 3313; **phải đối chiếu lại bộ stackup JLC đang áp dụng khi đặt hàng** (rủi ro R7).

| Lớp | Tên KiCad | Vật liệu | Dày (mm) | εr | Vai trò |
|---|---|---|---|---|---|
| L1 | F.Cu | đồng 1 oz | 0.035 | — | linh kiện + tín hiệu, cặp vi sai ưu tiên |
| | | prepreg 3313 | 0.0994 | 4.1 | |
| L2 | In1.Cu | đồng 0.5 oz | 0.0152 | — | **GND liền** (tham chiếu cho L1) |
| | | lõi | 0.55 | 4.6 | |
| L3 | In2.Cu | đồng 0.5 oz | 0.0152 | — | tín hiệu tốc độ cao (khi phải chui dưới linh kiện) |
| | | prepreg 2116 | 0.1088 | 4.16 | |
| L4 | In3.Cu | đồng 0.5 oz | 0.0152 | — | **GND liền** (tham chiếu cho L3) |
| | | lõi | 0.55 | 4.6 | |
| L5 | In4.Cu | đồng 0.5 oz | 0.0152 | — | nguồn: +5V, +3V3_SW, +1V0, +3V3 (chia vùng) |
| | | prepreg 3313 | 0.0994 | 4.1 | |
| L6 | B.Cu | đồng 1 oz | 0.035 | — | tụ decoupling + tín hiệu chậm |

Tổng ≈ 1.57 mm (chưa kể mặt nạ hàn). Hoàn thiện bề mặt: **ENIG** (đầu nối DF40 bước 0.4 mm, LQFP bước 0.4 mm).

Lý do chọn cách phân lớp: mọi cặp vi sai (L1 và L3) đều tham chiếu GND cách ~0.1 mm; lớp nguồn L5 nằm sát mặt dưới,
nơi đặt tụ decoupling của switch/NIC.

## Bề rộng đường cho trở kháng (tính gần đúng theo IPC-2141, đồng 35 µm, h = 0.0994 mm, εr = 4.1)

| Loại | Lớp | Rộng / khe (mm) | Z tính được | Net class |
|---|---|---|---|---|
| PCIe, REFCLK 90 Ω vi sai | L1 | 0.15 / 0.15 | Z0 ≈ 49.8 Ω, Zdiff ≈ 88 Ω | `PCIE_90R` |
| USB 2.0 90 Ω vi sai | L1 | 0.15 / 0.15 | ≈ 88 Ω | `USB_90R` |
| Ethernet MDI 100 Ω vi sai | L1 | 0.125 / 0.18 | Z0 ≈ 54.9 Ω, Zdiff ≈ 100.6 Ω | `MDI_100R` |
| Vi sai trên L3 (stripline lệch, tham chiếu L4) | L3 | chưa chốt | tính bằng máy tính JLC | — |
| Tín hiệu thường | L1/L6 | 0.15 (tối thiểu 0.10) | — | `Default` |
| Nguồn | — | ≥ 0.5; +12V ≥ 1.0; ưu tiên đổ vùng | — | `PWR`, `PWR_HV` |

Công thức: Z0 = 87/√(εr+1.41) · ln(5.98h/(0.8w+t)); Zdiff = 2·Z0·(1 − 0.48·e^(−0.96·s/h)).

## Yêu cầu khớp độ dài (theo CM4 datasheet)

| Giao tiếp | Lệch trong cặp | Giữa các cặp |
|---|---|---|
| PCIe (dữ liệu, clock) | < 0.1 mm | không yêu cầu |
| USB 2.0 | < 0.15 mm | — |
| Ethernet MDI | < 0.15 mm | < 50 mm (không cần bù) |

## Luật DRC đang dùng (`cm4-gateway.kicad_pro` + `.kicad_dru`)

Đường/khe tối thiểu 0.09/0.10 mm; via tối thiểu Ø0.40/khoan 0.20; via mặc định 0.50/0.25; khoảng cách đồng–mép bo 0.3 mm;
lỗ–lỗ 0.25 mm; lỗ–đồng 0.19 mm (do footprint USB-C GCT, rủi ro R5). Không có luật theo Reference.
Các giá trị này phải được đối chiếu với bảng năng lực 6 lớp của JLCPCB trước khi đi dây.
