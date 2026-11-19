# Ghi chú phần mềm — CM4 Security Gateway Rev A

Hệ điều hành đích: Raspberry Pi OS Lite 64-bit (kernel ≥ 6.6). Bằng chứng driver: `driver-check.md`.

## 1. `config.txt`

```ini
[all]
arm_64bit=1
enable_uart=1                      # console trên GPIO14/15 → CH340C → cổng DEBUG
dtoverlay=disable-bt               # CM4 không WiFi/BT: giải phóng UART PL011 cho console
dtoverlay=dwc2,dr_mode=host        # bật USB 2.0 host (CM4 tắt USB mặc định)
dtparam=spi=on
dtoverlay=tpm-slb9670              # TPM trên SPI0 CE1 (GPIO7)
dtoverlay=i2c-rtc,pcf85063a,i2c_csi_dsi   # RTC trên SDA0/SCL0 (GPIO44/45)
dtoverlay=gpio-fan,gpiopin=18,temp=65000  # tùy chọn: quạt trên J202
gpio=17=op,dl                      # LED STATUS, mặc định tắt
gpio=23=ip,pn                      # TAMPER_OPEN: ngõ vào, KHÔNG kéo (mạch ngoài đã kéo lên 10 k)
```

Ghi chú: overlay `tpm-slb9670` chiếm CE1; CE0 (GPIO8) vẫn là `/dev/spidev0.0` cho SRAM. Nếu kernel báo trùng chip-select,
thêm `dtoverlay=spi0-2cs` trước overlay TPM.

## 2. PCIe: 2 switch + 4 NIC

```bash
lspci -tv          # 2 cầu Diodes/Pericom 12d8:2404, 4 NIC Realtek 10ec:8168
dmesg | grep -i -e pcie -e r8169
```

- Không cần driver cho switch (cầu PCI-PCI chuẩn). `r8169` có sẵn dạng module.
- **Đảo cực làn**: trên PCB mọi đầu thu PCIe được nối chéo P/N có chủ đích; PCIe tự nhận và sửa ở tầng vật lý
  (trong `lspci -vv` không cần cấu hình gì). Nếu một cổng không lên liên kết, đây **không** phải nguyên nhân đầu tiên
  cần nghi; kiểm tra clock, reset, tụ AC trước.
- Gán cổng: SW1 cổng xuôi 1 → **LAN2**, cổng 2 → **LAN1**, cổng 3 → SW2; SW2 cổng 1 → **LAN4**, cổng 2 → **LAN3**.

### Đặt tên giao diện và MAC cố định

RTL8111H mua lẻ có thể chưa nạp MAC riêng (xem `driver-check.md`). Gán theo đường dẫn PCI bằng systemd, ví dụ
`/etc/systemd/network/10-lan1.link`:

```ini
[Match]
Path=platform-fd500000.pcie-pci-0000:04:00.0     # xem đường dẫn thật bằng: udevadm info /sys/class/net/<if>
[Link]
Name=lan1
MACAddress=02:c4:67:00:00:01                     # địa chỉ quản trị cục bộ (bit 1 của byte đầu = 1), tự chọn, không trùng
```

Làm tương tự cho `lan2…lan4`; `eth0` (PHY của CM4) đổi tên thành `wan`. WAN và LAN là các giao diện độc lập:
cấu hình NAT/firewall bằng nftables, VPN bằng WireGuard hoặc strongSwan (IPsec).

## 3. TPM 2.0

```bash
sudo apt install tpm2-tools
tpm2_getcap properties-fixed | head
tpm2_getrandom 16 --hex
```

Dùng TPM để niêm phong khóa (ví dụ `systemd-cryptenroll --tpm2-device=auto` cho phân vùng dữ liệu LUKS, hoặc
`tpm2_create`/`tpm2_unseal` cho khóa VPN).

## 4. RTC

```bash
sudo hwclock -w      # ghi giờ hệ thống vào RTC
sudo hwclock -r
```

**Tắt CLKOUT để tiết kiệm pin** (vỏ SO-8 bật CLKOUT 32.768 kHz mặc định; tắt đi mới đạt 0.22 µA). Chạy một lần sau
mỗi lần thay pin (thanh ghi Control_2 = 0x01, đặt COF[2:0] = 111):

```bash
sudo rmmod rtc_pcf85063 2>/dev/null
sudo i2cset -y 10 0x51 0x01 0x07     # địa chỉ 0x51; với overlay i2c_csi_dsi bus thường là 10 (hoặc 0) — xem `i2cdetect -l`
sudo modprobe rtc_pcf85063
```

Driver kernel cũng tắt được CLKOUT nếu không có ai dùng clock này (`CONFIG_COMMON_CLK`); kiểm tra lại bằng cách đo
dòng pin khi tắt máy.

## 5. SRAM giữ khóa (23LCV1024, `/dev/spidev0.0`) và chống mở vỏ

Lệnh SPI: `0x02` WRITE, `0x03` READ, địa chỉ 24 bit; tốc độ ≤ 5 MHz (bus có điện trở nối tiếp 1 k/10 k chống cấp
ngược). Ví dụ Python (`python3-spidev`):

```python
import spidev, os, hashlib
MAGIC = b"GWK1"
s = spidev.SpiDev(); s.open(0, 0); s.max_speed_hz = 1_000_000; s.mode = 0

def write(addr, data):
    s.xfer2([0x02, addr >> 16 & 0xFF, addr >> 8 & 0xFF, addr & 0xFF] + list(data))

def read(addr, n):
    return bytes(s.xfer2([0x03, addr >> 16 & 0xFF, addr >> 8 & 0xFF, addr & 0xFF] + [0] * n)[4:])

def store_key(key: bytes):                     # key: 32 byte
    write(0, MAGIC + key + hashlib.sha256(MAGIC + key).digest())

def load_key():
    blob = read(0, 4 + 32 + 32)
    if blob[:4] != MAGIC or hashlib.sha256(blob[:36]).digest() != blob[36:]:
        return None                             # SRAM đã bị xóa → vỏ đã bị mở (kể cả lúc tắt máy)
    return blob[4:36]
```

Luồng đề xuất: lúc khởi động gọi `load_key()`; trả về `None` nghĩa là **đã có sự kiện mở vỏ** → không mở khóa dữ liệu,
ghi log, yêu cầu cấp lại khóa. Nên kết hợp: khóa trong SRAM chỉ là một nửa, nửa kia niêm phong trong TPM.

Ngắt khi đang chạy — `TAMPER_OPEN` = GPIO23, **mức cao = vỏ mở**:

```bash
gpiomon --rising-edge gpiochip0 23      # libgpiod; in ra sự kiện khi nhả switch / rút jumper J1101
```

Phần cứng không tự tắt CM4: khi nhận ngắt, phần mềm tự xóa khóa trong RAM, dừng VPN, ghi log.
Lưu ý: SRAM mất nguồn VCC khi vỏ mở nên mọi lệnh SPI lúc đó trả về rác; nhấn lại switch thì SRAM chạy lại nhưng trống.

## 6. Nạp lại eMMC

Xem `BRINGUP.md` bước 4 (công tắc BOOT + cổng FLASH + `rpiboot`). Khóa ghi EEPROM bootloader: đóng jumper `JP201`.
