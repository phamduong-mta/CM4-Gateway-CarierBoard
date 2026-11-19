"""Cơ sở dữ liệu linh kiện: giá trị -> footprint, mã LCSC, mã nhà sản xuất.
Mọi mã LCSC đã tra trên thư viện PCBA JLCPCB ngày 2026-11-11 (xem docs/notes/)."""

FP_R0402 = "Resistor_SMD:R_0402_1005Metric"
FP_C0402 = "Capacitor_SMD:C_0402_1005Metric"
FP_C0603 = "Capacitor_SMD:C_0603_1608Metric"
FP_C0805 = "Capacitor_SMD:C_0805_2012Metric"
FP_C1206 = "Capacitor_SMD:C_1206_3216Metric"

# Điện trở 0402 1% (UNI-ROYAL 0402WGFxxxxTCE)
R = {
    "0R": ("C17168", "0402WGF0000TCE"),
    "10R": ("C25077", "0402WGF100JTCE"),
    "22R": ("C25092", "0402WGF220JTCE"),
    "33R": ("C25105", "0402WGF330JTCE"),
    "49.9R": ("C25120", "0402WGF499JTCE"),
    "100R": ("C25076", "0402WGF1000TCE"),
    "220R": ("C25091", "0402WGF2200TCE"),
    "330R": ("C25104", "0402WGF3300TCE"),
    "470R": ("C25117", "0402WGF4700TCE"),
    "475R": ("C49065", "0402WGF4750TCE"),
    "1k": ("C11702", "0402WGF1001TCE"),
    "1.37k": ("C423239", "0402WGF1371TCE"),
    "1.43k": ("C11671", "0402WGF1431TCE"),
    "2.2k": ("C25879", "0402WGF2201TCE"),
    "2.49k": ("C25884", "0402WGF2491TCE"),
    "3.01k": ("C25889", "0402WGF3011TCE"),
    "3.4k": ("C4940", "0402WGF3401TCE"),
    "4.7k": ("C25900", "0402WGF4701TCE"),
    "5.1k": ("C25905", "0402WGF5101TCE"),
    "10k": ("C25744", "0402WGF1002TCE"),
    "10.2k": ("C11660", "0402WGF1022TCE"),
    "13k": ("C25754", "0402WGF1302TCE"),
    "15k": ("C25756", "0402WGF1502TCE"),
    "22k": ("C25768", "0402WGF2202TCE"),
    "33.2k": ("C122548", "0402WGF3322TCE"),
    "51k": ("C25794", "0402WGF5102TCE"),
    "53.6k": ("C53398", "0402WGF5362TCE"),
    "100k": ("C25741", "0402WGF1003TCE"),
    "243k": ("C43249", "0402WGF2433TCE"),
    "300k": ("C25774", "0402WGF3003TCE"),
    "1M": ("C26083", "0402WGF1004TCE"),
    "4.7M": ("C474132", "0402WGF4704TCE"),
    "10M": ("C26082", "0402WGF1005TCE"),
}

# Tụ: khoá = (giá trị, vỏ)
C = {
    ("18pF", "0402"): ("C307443", "CL05C180JB5NNNC", FP_C0402, "18pF 50V C0G"),
    ("47pF", "0402"): ("C84706", "CL05C470JB5NNNC", FP_C0402, "47pF 50V C0G"),
    ("1nF", "0402"): ("C14442", "CL05B102KB5NNNC", FP_C0402, "1nF 50V X7R"),
    ("4.7nF", "0402"): ("C84705", "CL05B472KB5NNNC", FP_C0402, "4.7nF 50V X7R"),
    ("10nF", "0402"): ("C15195", "CL05B103KB5NNNC", FP_C0402, "10nF 50V X7R"),
    ("100nF", "0402"): ("C1525", "CL05B104KO5NNNC", FP_C0402, "100nF 16V X7R"),
    ("100nF/50V", "0402"): ("C77020", "GRM155R71H104KE14D", FP_C0402, "100nF 50V X7R"),
    ("1uF", "0402"): ("C52923", "CL05A105KA5NQNC", FP_C0402, "1uF 25V X5R"),
    ("4.7uF", "0603"): ("C19666", "CL10A475KO8NNNC", FP_C0603, "4.7uF 16V X5R"),
    ("10uF", "0603"): ("C19702", "CL10A106KP8NNNC", FP_C0603, "10uF 10V X5R"),
    ("22uF", "0805"): ("C45783", "CL21A226MAQNNNE", FP_C0805, "22uF 25V X5R"),
    ("47uF", "1206"): ("C96123", "CL31A476MPHNNNE", FP_C1206, "47uF 10V X5R"),
    ("10uF/50V", "1206"): ("C13585", "CL31A106KBHNNNE", FP_C1206, "10uF 50V X5R"),
    ("4.7nF/2kV", "1206"): ("C41017", "1206B472K202NT", FP_C1206, "4.7nF 2kV X7R"),
}

# Linh kiện khác: tên -> dict
P = {
    # --- bán dẫn rời
    "2N7002": dict(sym="Transistor_FET:Q_NMOS_GSD", fp="Package_TO_SOT_SMD:SOT-23", lcsc="C8545", mpn="2N7002"),
    "AO3400A": dict(sym="Transistor_FET:Q_NMOS_GSD", fp="Package_TO_SOT_SMD:SOT-23", lcsc="C20917", mpn="AO3400A"),
    "BSS138": dict(sym="Transistor_FET:Q_NMOS_GSD", fp="Package_TO_SOT_SMD:SOT-23", lcsc="C8490", mpn="LBSS138LT1G"),
    "AO3401A": dict(sym="Transistor_FET:Q_PMOS_GSD", fp="Package_TO_SOT_SMD:SOT-23", lcsc="C15127", mpn="AO3401A"),
    "BAT54C": dict(sym="Device:D_Schottky_Dual_CommonCathode_AAK", fp="Package_TO_SOT_SMD:SOT-23", lcsc="C2135", mpn="BAT54C"),
    "B560C": dict(sym="Device:D_Schottky", fp="Diode_SMD:D_SMC", lcsc="C85100", mpn="B560C-13-F"),
    "SMBJ24A": dict(sym="Device:D_Zener", fp="Diode_SMD:D_SMB", lcsc="C123819", mpn="SMBJ24A"),
    "BZT52C12": dict(sym="Device:D_Zener", fp="Diode_SMD:D_SOD-123", lcsc="C43491", mpn="BZT52C12"),
    "1N4148WS": dict(sym="Device:D", fp="Diode_SMD:D_SOD-323", lcsc="C2128", mpn="1N4148WS"),
    "LED_G": dict(sym="Device:LED", fp="LED_SMD:LED_0603_1608Metric", lcsc="C12624", mpn="KT-0603G"),
    "LED_R": dict(sym="Device:LED", fp="LED_SMD:LED_0603_1608Metric", lcsc="C2286", mpn="KT-0603R"),
    # --- cuộn cảm, hạt ferrite, cầu chì, thạch anh
    "10uH": dict(sym="Device:L", fp="Inductor_SMD:L_Changjiang_FXL1040", lcsc="C475915", mpn="FXL1040-100-M"),
    "2.2uH": dict(sym="Device:L", fp="Inductor_SMD:L_Changjiang_FXL0420", lcsc="C167206", mpn="FXL0420-2R2-M"),
    # 120 Ω@100 MHz, 50 mΩ, 2 A: sụt áp < 20 mV ở dòng AVDD tối đa 0.32 A (review C2)
    "FB120": dict(sym="Device:FerriteBead_Small", fp="Inductor_SMD:L_0603_1608Metric", lcsc="C14709", mpn="BLM18PG121SN1D"),
    "FUSE4A": dict(sym="Device:Fuse", fp="Fuse:Fuse_1206_3216Metric", lcsc="C187596", mpn="0466004.NRHF"),
    "XTAL25M": dict(sym="Device:Crystal_GND24", fp="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", lcsc="C9006", mpn="X322525MOB4SI"),
    "XTAL32K": dict(sym="Device:Crystal", fp="Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm", lcsc="C97604", mpn="SC-32S 32.768kHz 7pF"),
    "CE100u": dict(sym="Device:C_Polarized", fp="Capacitor_SMD:CP_Elec_6.3x7.7", lcsc="C176683", mpn="VZH101M1VTR-0607"),
    # --- cơ điện
    "TP": dict(sym="Connector:TestPoint", fp="TestPoint:TestPoint_Pad_D1.0mm", lcsc="", mpn=""),
    "HDR2": dict(sym="Connector_Generic:Conn_01x02", fp="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", lcsc="C124375", mpn="B-2100S02P-A110"),
    "TACT": dict(sym="Switch:SW_Push", fp="Button_Switch_SMD:SW_SPST_SKQG_WithStem", lcsc="C115351", mpn="SKQGABE010"),
    "SLIDE": dict(sym="Switch:SW_SPDT", fp="Button_Switch_SMD:SW_SPDT_PCM12", lcsc="C221841", mpn="PCM12SMTR"),
    "MX": dict(sym="Switch:SW_Push", fp="Button_Switch_Keyboard:SW_Cherry_MX_1.00u_PCB", lcsc="C49234236", mpn="CPG151101D05"),
    "BATT": dict(sym="Device:Battery_Cell", fp="Battery:BatteryHolder_Keystone_3034_1x20mm", lcsc="C5199422", mpn="3034"),
    "HOLE": dict(sym="Mechanical:MountingHole_Pad", fp="MountingHole:MountingHole_3.2mm_M3_Pad_Via", lcsc="", mpn=""),
}
