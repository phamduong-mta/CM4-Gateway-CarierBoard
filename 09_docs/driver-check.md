# Kiểm tra driver / overlay (P0)

Nguồn: `raspberrypi/linux`, nhánh `rpi-6.12.y` (tải ngày 2026-11-11, bản lưu ở `docs/notes/raw/`).

| Ngoại vi | Driver / cấu hình | Bằng chứng | Kết luận |
|---|---|---|---|
| NIC RTL8111H | `r8169` | `bcm2711_defconfig`: `CONFIG_R8169=m` | **Đạt** — module có sẵn trong kernel Raspberry Pi OS 64-bit |
| NIC dự phòng Intel I210 | `igb` | `CONFIG_IGB=m` | Đạt (không dùng ở Rev A) |
| PCIe switch (PI7C9X2G404SL) | cầu PCI-PCI chuẩn, không cần driver riêng | `CONFIG_PCI=y`, `CONFIG_PCIEPORTBUS=y` | **Đạt** — switch trong suốt với OS; CM4 datasheet §2.3 xác nhận MSI/MSI-X từ kernel 5.10 |
| TPM SLB9670 | `tpm_tis_spi` | `CONFIG_TCG_TIS_SPI=m`; overlay `tpm-slb9670` | **Đạt** — overlay dùng **SPI0, CE1 (GPIO7)**, 32 MHz, không dùng GPIO reset/IRQ |
| RTC PCF85063A | `rtc-pcf85063` | `CONFIG_RTC_DRV_PCF85063=m`; overlay `i2c-rtc,pcf85063a` | **Đạt** — đặt trên SDA0/SCL0 (GPIO44/45) như CM4 IO Board: `dtoverlay=i2c-rtc,pcf85063a,i2c_csi_dsi` |
| USB host | `dwc2` | `CONFIG_USB_DWC2=y`; overlay `dwc2,dr_mode=host` | **Đạt** — CM4 datasheet §2.4: USB tắt mặc định, bật bằng `otg_mode=1` hoặc overlay dwc2 |
| SRAM 23LCV1024 | `spidev` (truy cập từ user space) | `CONFIG_SPI_SPIDEV=m` | **Đạt** — `/dev/spidev0.0` (SPI0 CE0 = GPIO8) |
| UART console | `ttyAMA0`/`ttyS0` trên GPIO14/15 | chuẩn Raspberry Pi (`enable_uart=1`) | Đạt |
| USB-UART CH340C | driver phía máy tính (`ch341`) | có sẵn trong Linux/Windows/macOS | Đạt |

## Ghi chú quan trọng

- **MAC của RTL8111H**: datasheet RTL8111H rev 1.2 chỉ nói cấu hình nằm trong eFUSE/OTP nội, không hỗ trợ EEPROM ngoài.
  Chip mua lẻ có thể chưa nạp MAC riêng → `r8169` sẽ dùng MAC trong eFUSE (có thể trùng nhau giữa các chip) hoặc
  sinh MAC ngẫu nhiên. **Giải pháp Rev A: gán MAC cố định bằng phần mềm** (systemd `.link` theo đường dẫn PCI),
  ghi trong `SOFTWARE.md` ở giai đoạn 2. Không thêm EEPROM vì chip không hỗ trợ.
- **RTL8111H là PCIe Gen1 (2.5 GT/s)**: đủ cho 1 GbE; switch Gen2 tự hạ tốc từng cổng.
- **Bus number**: cây PCIe của bo = root (bus 0) → switch 1 (bus 1–2..) → switch 2 → 4 NIC, cần ~9 bus number. Kernel
  Raspberry Pi hiện hành khai báo `bus-range` đủ rộng cho switch (các bo CM4 nhiều NIC qua switch đã chạy phổ biến).
  Cần xác nhận lại bằng `lspci -t` khi bring-up.
- **Bằng chứng PI7C9X2G404SL chạy với CM4**: chưa tìm được bài công khai cho đúng mã này; đây là switch PCIe chuẩn
  (không cần driver), nên rủi ro nằm ở phần cứng (clock, reset, nguồn) chứ không phải driver. Ghi nhận là **rủi ro mở R1**.
