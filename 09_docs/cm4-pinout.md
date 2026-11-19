# Bảng gán chân CM4 (200 chân) — sinh từ netlist

Đầu nối 1 = chân 1–100, đầu nối 2 = chân 101–200. "(để hở)" = không nối.

| Chân | Tên | Net | | Chân | Tên | Net |
|---|---|---|---|---|---|---|
| 1 | GND | GND | | 2 | GND | GND |
| 3 | Ethernet_Pair3_P | WAN_MDI3_P | | 4 | Ethernet_Pair1_P | WAN_MDI1_P |
| 5 | Ethernet_Pair3_N | WAN_MDI3_N | | 6 | Ethernet_Pair1_N | WAN_MDI1_N |
| 7 | GND | GND | | 8 | GND | GND |
| 9 | Ethernet_Pair2_N | WAN_MDI2_N | | 10 | Ethernet_Pair0_N | WAN_MDI0_N |
| 11 | Ethernet_Pair2_P | WAN_MDI2_P | | 12 | Ethernet_Pair0_P | WAN_MDI0_P |
| 13 | GND | GND | | 14 | GND | GND |
| 15 | Ethernet_nLED3(3.3v) | WAN_LED_G | | 16 | Ethernet_SYNC_IN(1.8v) | (để hở) |
| 17 | Ethernet_nLED2(3.3v) | WAN_LED_Y | | 18 | Ethernet_SYNC_OUT(1.8v) | (để hở) |
| 19 | Ethernet_nLED1(3.3v) | (để hở) | | 20 | EEPROM_nWP | EEPROM_nWP |
| 21 | PI_nLED_Activity | LED_nACT | | 22 | GND | GND |
| 23 | GND | GND | | 24 | GPIO26 | (để hở) |
| 25 | GPIO21 | (để hở) | | 26 | GPIO19 | (để hở) |
| 27 | GPIO20 | (để hở) | | 28 | GPIO13 | (để hở) |
| 29 | GPIO16 | (để hở) | | 30 | GPIO6 | (để hở) |
| 31 | GPIO12 | (để hở) | | 32 | GND | GND |
| 33 | GND | GND | | 34 | GPIO5 | (để hở) |
| 35 | ID_SC | (để hở) | | 36 | ID_SD | (để hở) |
| 37 | GPIO7 | TPM_CS_N | | 38 | GPIO11 | SPI_SCLK |
| 39 | GPIO8 | SRAM_CS_N | | 40 | GPIO9 | SPI_MISO |
| 41 | GPIO25 | (để hở) | | 42 | GND | GND |
| 43 | GND | GND | | 44 | GPIO10 | SPI_MOSI |
| 45 | GPIO24 | TPM_PIRQ_N | | 46 | GPIO22 | (để hở) |
| 47 | GPIO23 | TAMPER_OPEN | | 48 | GPIO27 | (để hở) |
| 49 | GPIO18 | FAN_PWM | | 50 | GPIO17 | LED_STATUS |
| 51 | GPIO15 | UART_RXD | | 52 | GND | GND |
| 53 | GND | GND | | 54 | GPIO4 | (để hở) |
| 55 | GPIO14 | UART_TXD | | 56 | GPIO3 | (để hở) |
| 57 | SD_CLK | (để hở) | | 58 | GPIO2 | (để hở) |
| 59 | GND | GND | | 60 | GND | GND |
| 61 | SD_DAT3 | (để hở) | | 62 | SD_CMD | (để hở) |
| 63 | SD_DAT0 | (để hở) | | 64 | SD_DAT5 | (để hở) |
| 65 | GND | GND | | 66 | GND | GND |
| 67 | SD_DAT1 | (để hở) | | 68 | SD_DAT4 | (để hở) |
| 69 | SD_DAT2 | (để hở) | | 70 | SD_DAT7 | (để hở) |
| 71 | GND | GND | | 72 | SD_DAT6 | (để hở) |
| 73 | SD_VDD_Override | (để hở) | | 74 | GND | GND |
| 75 | SD_PWR_ON | (để hở) | | 76 | Reserved | (để hở) |
| 77 | +5v_(Input) | +5V | | 78 | GPIO_VREF(1.8v/3.3v_Input) | +3V3 |
| 79 | +5v_(Input) | +5V | | 80 | SCL0 | RTC_SCL |
| 81 | +5v_(Input) | +5V | | 82 | SDA0 | RTC_SDA |
| 83 | +5v_(Input) | +5V | | 84 | +3.3v_(Output) | +3V3 |
| 85 | +5v_(Input) | +5V | | 86 | +3.3v_(Output) | +3V3 |
| 87 | +5v_(Input) | +5V | | 88 | +1.8v_(Output) | (để hở) |
| 89 | WiFi_nDisable | (để hở) | | 90 | +1.8v_(Output) | (để hở) |
| 91 | BT_nDisable | (để hở) | | 92 | RUN_PG | RUN_PG |
| 93 | nRPIBOOT | nRPIBOOT | | 94 | AnalogIP1 | (để hở) |
| 95 | nPI_LED_PWR | (để hở) | | 96 | AnalogIP0 | (để hở) |
| 97 | Camera_GPIO | (để hở) | | 98 | GND | GND |
| 99 | Global_EN | GLOBAL_EN | | 100 | nEXTRST | nEXTRST |
| 101 | USB_OTG_ID | GND | | 102 | PCIe_CLK_nREQ | /CM4/PCIE_CLKREQ_N |
| 103 | USB2_N | USB_DN | | 104 | Reserved | (để hở) |
| 105 | USB2_P | USB_DP | | 106 | Reserved | (để hở) |
| 107 | GND | GND | | 108 | GND | GND |
| 109 | PCIe_nRST | PCIE_RST_N | | 110 | PCIe_CLK_P | PCIE_CLK_P |
| 111 | VDAC_COMP | (để hở) | | 112 | PCIe_CLK_N | PCIE_CLK_N |
| 113 | GND | GND | | 114 | GND | GND |
| 115 | CAM1_D0_N | (để hở) | | 116 | PCIe_RX_P | PCIE_RX_N |
| 117 | CAM1_D0_P | (để hở) | | 118 | PCIe_RX_N | PCIE_RX_P |
| 119 | GND | GND | | 120 | GND | GND |
| 121 | CAM1_D1_N | (để hở) | | 122 | PCIe_TX_P | PCIE_TX_P |
| 123 | CAM1_D1_P | (để hở) | | 124 | PCIe_TX_N | PCIE_TX_N |
| 125 | GND | GND | | 126 | GND | GND |
| 127 | CAM1_C_N | (để hở) | | 128 | CAM0_D0_N | (để hở) |
| 129 | CAM1_C_P | (để hở) | | 130 | CAM0_D0_P | (để hở) |
| 131 | GND | GND | | 132 | GND | GND |
| 133 | CAM1_D2_N | (để hở) | | 134 | CAM0_D1_N | (để hở) |
| 135 | CAM1_D2_P | (để hở) | | 136 | CAM0_D1_P | (để hở) |
| 137 | GND | GND | | 138 | GND | GND |
| 139 | CAM1_D3_N | (để hở) | | 140 | CAM0_C_N | (để hở) |
| 141 | CAM1_D3_P | (để hở) | | 142 | CAM0_C_P | (để hở) |
| 143 | HDMI1_HOTPLUG | (để hở) | | 144 | GND | GND |
| 145 | HDMI1_SDA | (để hở) | | 146 | HDMI1_TX2_P | (để hở) |
| 147 | HDMI1_SCL | (để hở) | | 148 | HDMI1_TX2_N | (để hở) |
| 149 | HDMI1_CEC | (để hở) | | 150 | GND | GND |
| 151 | HDMI0_CEC | (để hở) | | 152 | HDMI1_TX1_P | (để hở) |
| 153 | HDMI0_HOTPLUG | (để hở) | | 154 | HDMI1_TX1_N | (để hở) |
| 155 | GND | GND | | 156 | GND | GND |
| 157 | DSI0_D0_N | (để hở) | | 158 | HDMI1_TX0_P | (để hở) |
| 159 | DSI0_D0_P | (để hở) | | 160 | HDMI1_TX0_N | (để hở) |
| 161 | GND | GND | | 162 | GND | GND |
| 163 | DSI0_D1_N | (để hở) | | 164 | HDMI1_CLK_P | (để hở) |
| 165 | DSI0_D1_P | (để hở) | | 166 | HDMI1_CLK_N | (để hở) |
| 167 | GND | GND | | 168 | GND | GND |
| 169 | DSI0_C_N | (để hở) | | 170 | HDMI0_TX2_P | (để hở) |
| 171 | DSI0_C_P | (để hở) | | 172 | HDMI0_TX2_N | (để hở) |
| 173 | GND | GND | | 174 | GND | GND |
| 175 | DSI1_D0_N | (để hở) | | 176 | HDMI0_TX1_P | (để hở) |
| 177 | DSI1_D0_P | (để hở) | | 178 | HDMI0_TX1_N | (để hở) |
| 179 | GND | GND | | 180 | GND | GND |
| 181 | DSI1_D1_N | (để hở) | | 182 | HDMI0_TX0_P | (để hở) |
| 183 | DSI1_D1_P | (để hở) | | 184 | HDMI0_TX0_N | (để hở) |
| 185 | GND | GND | | 186 | GND | GND |
| 187 | DSI1_C_N | (để hở) | | 188 | HDMI0_CLK_P | (để hở) |
| 189 | DSI1_C_P | (để hở) | | 190 | HDMI0_CLK_N | (để hở) |
| 191 | GND | GND | | 192 | GND | GND |
| 193 | DSI1_D2_N | (để hở) | | 194 | DSI1_D3_N | (để hở) |
| 195 | DSI1_D2_P | (để hở) | | 196 | DSI1_D3_P | (để hở) |
| 197 | GND | GND | | 198 | GND | GND |
| 199 | HDMI0_SDA | (để hở) | | 200 | HDMI0_SCL | (để hở) |
