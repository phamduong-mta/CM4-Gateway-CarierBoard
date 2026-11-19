# Báo cáo đi dây — CM4 Security Gateway Rev A

Sinh tự động từ `hardware/cm4-gateway.kicad_pcb` bằng `scripts/routing_report.py`.

## Tổng quan

- Số đoạn đường: **4670**, số via: **962** (via nhỏ nhất Ø0.45/0.20 mm, không có via-in-pad trên pad linh kiện ngoài via tản nhiệt trong đế IC).
- Tổng chiều dài theo lớp: L1 4379 mm, L3 1450 mm, L6 2443 mm.
- Stackup JLC06161H-3313: L1 tín hiệu · L2 GND · L3 tín hiệu · L4 GND · L5 nguồn · L6 tín hiệu.

## Cặp vi sai

Độ dài tính theo tâm đường (không tính chiều cao via). Giới hạn lệch: PCIe 0.1 mm, USB 1.0 mm, MDI 3.0 mm.

| Cặp | Net class | Rộng (mm) | Dài P (mm) | Dài N (mm) | Lệch (mm) | Giới hạn | Via/dây | Lớp |
|---|---|---|---|---|---|---|---|---|
| /LAN1/HSO | PCIE_90R | 0.150 | 2.99 | 2.99 | 0.000 | 0.1 | 0 | L1 |
| /LAN1/MDI0 | MDI_100R | 0.125 | 13.04 | 10.96 | 2.074 | 3.0 | 0 | L1 |
| /LAN1/MDI1 | MDI_100R | 0.125 | 12.67 | 10.73 | 1.934 | 3.0 | 1 | L1+L3 |
| /LAN1/MDI2 | MDI_100R | 0.125 | 10.24 | 12.54 | 2.301 | 3.0 | 0 | L1 |
| /LAN1/MDI3 | MDI_100R | 0.125 | 14.02 | 13.49 | 0.533 | 3.0 | 0 | L1 |
| /LAN2/HSO | PCIE_90R | 0.150 | 2.99 | 2.99 | 0.000 | 0.1 | 0 | L1 |
| /LAN2/MDI0 | MDI_100R | 0.125 | 13.04 | 10.96 | 2.074 | 3.0 | 0 | L1 |
| /LAN2/MDI1 | MDI_100R | 0.125 | 12.67 | 10.73 | 1.934 | 3.0 | 1 | L1+L3 |
| /LAN2/MDI2 | MDI_100R | 0.125 | 10.24 | 12.54 | 2.301 | 3.0 | 0 | L1 |
| /LAN2/MDI3 | MDI_100R | 0.125 | 14.02 | 13.49 | 0.533 | 3.0 | 0 | L1 |
| /LAN3/HSO | PCIE_90R | 0.150 | 2.99 | 2.99 | 0.000 | 0.1 | 0 | L1 |
| /LAN3/MDI0 | MDI_100R | 0.125 | 13.04 | 10.98 | 2.053 | 3.0 | 0 | L1 |
| /LAN3/MDI1 | MDI_100R | 0.125 | 12.67 | 10.73 | 1.934 | 3.0 | 1 | L1+L3 |
| /LAN3/MDI2 | MDI_100R | 0.125 | 10.24 | 12.54 | 2.301 | 3.0 | 0 | L1 |
| /LAN3/MDI3 | MDI_100R | 0.125 | 14.02 | 13.49 | 0.533 | 3.0 | 0 | L1 |
| /LAN4/HSO | PCIE_90R | 0.150 | 2.99 | 2.99 | 0.000 | 0.1 | 0 | L1 |
| /LAN4/MDI0 | MDI_100R | 0.125 | 13.04 | 10.98 | 2.053 | 3.0 | 0 | L1 |
| /LAN4/MDI1 | MDI_100R | 0.125 | 12.67 | 10.73 | 1.934 | 3.0 | 1 | L1+L3 |
| /LAN4/MDI2 | MDI_100R | 0.125 | 10.24 | 12.54 | 2.301 | 3.0 | 0 | L1 |
| /LAN4/MDI3 | MDI_100R | 0.125 | 14.04 | 13.49 | 0.553 | 3.0 | 0 | L1 |
| /SW1/CLKO0 | PCIE_90R | 0.150 | 5.80 | 5.80 | 0.000 | 0.1 | 0 | L1 |
| /SW1/CLKO1 | PCIE_90R | 0.150 | 5.27 | 5.27 | 0.000 | 0.1 | 0 | L1 |
| /SW1/CLKO2 | PCIE_90R | 0.150 | 5.11 | 5.11 | 0.000 | 0.1 | 0 | L1 |
| /SW1/CLKO3 | PCIE_90R | 0.150 | 5.77 | 5.77 | 0.000 | 0.1 | 0 | L1 |
| /SW1/DN1_TXC | PCIE_90R | 0.150 | 3.72 | 3.72 | 0.000 | 0.1 | 0 | L1 |
| /SW1/DN2_TXC | PCIE_90R | 0.150 | 6.16 | 6.16 | 0.000 | 0.1 | 0 | L1 |
| /SW1/DN3_TXC | PCIE_90R | 0.150 | 5.87 | 5.87 | 0.000 | 0.1 | 0 | L1 |
| /SW1/SELFCLK | PCIE_90R | 0.150 | 3.47 | 3.47 | 0.000 | 0.1 | 0 | L1 |
| /SW1/SELFT | PCIE_90R | 0.150 | 32.38 | 32.38 | 0.000 | 0.1 | 2 | L1+L6 |
| /SW1/UP_TXC | PCIE_90R | 0.150 | 3.72 | 3.72 | 0.000 | 0.1 | 0 | L1 |
| /SW2/CLK3 | PCIE_90R | 0.150 | 3.20 | 3.20 | 0.000 | 0.1 | 1 | L1+L6 |
| /SW2/CLKO0 | PCIE_90R | 0.150 | 5.80 | 5.80 | 0.000 | 0.1 | 0 | L1 |
| /SW2/CLKO1 | PCIE_90R | 0.150 | 5.27 | 5.27 | 0.000 | 0.1 | 0 | L1 |
| /SW2/CLKO2 | PCIE_90R | 0.150 | 5.11 | 5.11 | 0.000 | 0.1 | 0 | L1 |
| /SW2/CLKO3 | PCIE_90R | 0.150 | 5.77 | 5.77 | 0.000 | 0.1 | 0 | L1 |
| /SW2/DN1_TXC | PCIE_90R | 0.150 | 3.72 | 3.72 | 0.000 | 0.1 | 0 | L1 |
| /SW2/DN2_TXC | PCIE_90R | 0.150 | 6.16 | 6.16 | 0.000 | 0.1 | 0 | L1 |
| /SW2/DN3_TXC | PCIE_90R | 0.150 | 5.87 | 5.87 | 0.000 | 0.1 | 0 | L1 |
| /SW2/SELFCLK | PCIE_90R | 0.150 | 3.47 | 3.47 | 0.000 | 0.1 | 0 | L1 |
| /SW2/SELFT | PCIE_90R | 0.150 | 32.38 | 32.38 | 0.000 | 0.1 | 2 | L1+L6 |
| /SW2/UP_TXC | PCIE_90R | 0.150 | 3.72 | 3.72 | 0.000 | 0.1 | 0 | L1 |
| /USB_Debug/DBG_CON_ | USB_FS | 0.150 | 5.25 | 3.10 | 2.149 | — | 0 | L1 |
| /USB_Debug/DBG_ | USB_FS | 0.150 | 2.60 | 8.02 | 5.422 | — | 0 | L1 |
| /USB_Debug/USBA_CON_ | USB_90R | 0.150 | 9.75 | 9.75 | 0.000 | 1.0 | 0 | L1 |
| /USB_Debug/USBA_ | USB_90R | 0.150 | 21.54 | 21.54 | 0.000 | 1.0 | 0 | L1 |
| /USB_Debug/USBC_CON_ | USB_90R | 0.150 | 11.58 | 12.20 | 0.619 | 1.0 | 0 | L1 |
| /USB_Debug/USBC_ | USB_90R | 0.150 | 38.88 | 38.88 | 0.000 | 1.0 | 2 | L1+L3 |
| P1_CLK | PCIE_90R | 0.150 | 26.57 | 26.57 | 0.000 | 0.1 | 2 | L1+L3+L6 |
| P1_NIC2SW | PCIE_90R | 0.150 | 23.52 | 23.52 | 0.000 | 0.1 | 0 | L1 |
| P1_SW2NIC | PCIE_90R | 0.150 | 27.46 | 27.46 | 0.000 | 0.1 | 0 | L1 |
| P2_CLK | PCIE_90R | 0.150 | 15.08 | 15.08 | 0.000 | 0.1 | 2 | L1+L3+L6 |
| P2_NIC2SW | PCIE_90R | 0.150 | 29.17 | 29.17 | 0.000 | 0.1 | 0 | L1 |
| P2_SW2NIC | PCIE_90R | 0.150 | 32.90 | 32.90 | 0.000 | 0.1 | 0 | L1 |
| P3_CLK | PCIE_90R | 0.150 | 26.57 | 26.57 | 0.000 | 0.1 | 2 | L1+L3+L6 |
| P3_NIC2SW | PCIE_90R | 0.150 | 23.52 | 23.52 | 0.000 | 0.1 | 0 | L1 |
| P3_SW2NIC | PCIE_90R | 0.150 | 27.46 | 27.46 | 0.000 | 0.1 | 0 | L1 |
| P4_CLK | PCIE_90R | 0.150 | 15.08 | 15.08 | 0.000 | 0.1 | 2 | L1+L3+L6 |
| P4_NIC2SW | PCIE_90R | 0.150 | 29.17 | 29.17 | 0.000 | 0.1 | 0 | L1 |
| P4_SW2NIC | PCIE_90R | 0.150 | 32.90 | 32.90 | 0.000 | 0.1 | 0 | L1 |
| PCIE_CLK | PCIE_90R | 0.150 | 40.88 | 40.88 | 0.000 | 0.1 | 2 | L1+L3+L6 |
| PCIE_RX | PCIE_90R | 0.150 | 13.99 | 13.99 | 0.000 | 0.1 | 0 | L1 |
| PCIE_TX | PCIE_90R | 0.150 | 15.84 | 15.84 | 0.000 | 0.1 | 0 | L1 |
| SW2_CLK | PCIE_90R | 0.150 | 48.79 | 48.79 | 0.000 | 0.1 | 2 | L1+L3+L6 |
| USB_ | USB_90R | 0.150 | 40.17 | 40.17 | 0.000 | 1.0 | 0 | L1 |
| WAN_MDI0 | MDI_100R | 0.125 | 62.00 | 62.00 | 0.000 | 3.0 | 1 | L1+L3 |
| WAN_MDI1 | MDI_100R | 0.120 | 61.97 | 59.05 | 2.920 | 3.0 | 1 | L1+L3+L6 |
| WAN_MDI2 | MDI_100R | 0.125 | 62.92 | 59.96 | 2.959 | 3.0 | 2 | L1+L3+L6 |
| WAN_MDI3 | MDI_100R | 0.125 | 62.24 | 62.24 | 0.000 | 3.0 | 1 | L1+L3 |
| X_SW1TO2 | PCIE_90R | 0.150 | 65.14 | 65.14 | 0.000 | 0.1 | 2 | L1+L3 |
| X_SW2TO1 | PCIE_90R | 0.150 | 64.82 | 64.82 | 0.000 | 0.1 | 2 | L1+L3 |

Lệch lớn nhất theo nhóm: MDI_100R 2.959 mm, PCIE_90R 0.000 mm, USB_90R 0.619 mm, USB_FS 5.422 mm. Số cặp vượt giới hạn: **0**.

## Trở kháng theo stackup (tính gần đúng, xem `stackup.md`)

| Loại | Lớp | Rộng / khe | Z vi sai ước tính |
|---|---|---|---|
| PCIe, clock, USB | L1 (tham chiếu L2, h = 0.0994 mm) | 0.15 / 0.15 | ≈ 88 Ω |
| Ethernet MDI | L1 | 0.125 / 0.18 | ≈ 100 Ω |
| Đoạn trên L3 (stripline lệch, cách L4 0.109 mm, cách L2 0.55 mm) | L3 | 0.15 / 0.15 | ≈ 80–85 Ω |
| MDI trên L3 | L3 | 0.125 / 0.18 | ≈ 92–96 Ω |
| Clock tự vòng trên L6 (tham chiếu L5) | L6 | 0.15 / 0.15 | ≈ 88 Ω |

Các đoạn L3 chỉ mang clock 100 MHz, liên kết giữa hai switch (5 GT/s, ~50 mm) và MDI (125 MBd); sai lệch trở kháng 5–10 % ở các đoạn này nằm trong dung sai ±15 % của PCIe/Ethernet. Mọi làn dữ liệu PCIe tới NIC và tới CM4 nằm trọn trên L1.
