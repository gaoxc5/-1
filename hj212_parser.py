import struct

class HJ212Parser:
    def __init__(self):
        # 报文头
        self.header = "##"
        # CRC16 初始值 0xFFFF
        self.crc_init = 0xFFFF
        # CRC16 多项式 0xA001
        self.crc_poly = 0xA001

    def is_valid_message(self, message):
        """检查报文格式是否正确"""
        if not isinstance(message, str):
            return False
        # 检查是否以 ## 开头，以 \r\n 结尾
        if not message.startswith(self.header) or not message.endswith("\r\n"):
            return False
        # 检查长度是否符合 ## + 4位长度 + 数据段 + 4位CRC + \r\n
        if len(message) < 12: 
            return False
        try:
            # 提取长度字段（第3到6个字符）
            data_len = int(message[2:6])
            # 计算实际数据段长度：总长度 - 头部(2) - 长度字段(4) - CRC(4) - 结尾(2)
            actual_data_len = len(message) - 12
            if data_len != actual_data_len:
                return False
        except ValueError:
            return False
        return True

    def validate_crc(self, message):
        """实现 ANSI CRC16 算法，校验报文的 CRC 值"""
        if not self.is_valid_message(message):
            return False
        
        # 提取数据段（从第6个字符开始，截取 data_len 长度）
        data_len = int(message[2:6])
        data_segment = message[6:6+data_len]
        
        # 提取报文中的 CRC 字符串（数据段后面的4位）
        crc_str = message[6+data_len:10+data_len]
        
        # 计算 CRC
        crc = self.crc_init
        for char in data_segment.encode('ascii'):
            crc ^= char
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ self.crc_poly
                else:
                    crc >>= 1
        
        # 将计算出的 CRC 转为大写十六进制字符串，不足4位前补0
        calculated_crc = f"{crc:04X}"
        return calculated_crc == crc_str.upper()

    def parse_data_segment(self, message):
        """解析数据段，返回包含所有键值对的字典"""
        result = {}
        if not self.is_valid_message(message):
            return result
        
        data_len = int(message[2:6])
        data_segment = message[6:6+data_len]
        
        # 数据段通常以分号分隔
        items = data_segment.split(';')
        for item in items:
            if '=' in item:
                key, value = item.split('=', 1)
                result[key.strip()] = value.strip()
        return result

    def extract_monitoring_data(self, message):
        """从 CP 字段中提取所有监测因子及其数值"""
        monitoring_data = {}
        parsed_data = self.parse_data_segment(message)
        
        # 检查是否包含 CP 字段（通常代表监测数据）
        if 'CP' not in parsed_data:
            return monitoring_data
        
        cp_value = parsed_data['CP']
        # CP 字段内的数据通常以逗号分隔
        factors = cp_value.split(',')
        for factor in factors:
            if '-' in factor:
                # 例如 "a01001-Rtd=25.5" 或 "a01001-Avg=25.5"
                parts = factor.split('-')
                if len(parts) == 2 and '=' in parts[1]:
                    factor_code = parts[0].strip()
                    val_part = parts[1].split('=')
                    if len(val_part) == 2:
                        factor_type = val_part[0].strip() # Rtd, Avg 等
                        factor_value = val_part[1].strip()
                        
                        # 如果因子已存在，将其存为字典（包含不同类型），否则直接存值
                        if factor_code in monitoring_data:
                            if isinstance(monitoring_data[factor_code], dict):
                                monitoring_data[factor_code][factor_type] = factor_value
                            else:
                                monitoring_data[factor_code] = {
                                    'value': monitoring_data[factor_code],
                                    factor_type: factor_value
                                }
                        else:
                            monitoring_data[factor_code] = {factor_type: factor_value}
        return monitoring_data