"""
智能噪音数据模拟器
根据区域类型、时间、位置等因素生成符合真实规律的噪音数据
"""

import random
import math
from datetime import datetime, timedelta


class SmartNoiseSimulator:
    """智能噪音数据模拟器"""
    
    def __init__(self):
        """初始化模拟器"""
        # 不同区域类型的基础噪音值（分贝）
        self.base_noise_levels = {
            '居住区': 45.0,
            '商业区': 55.0,
            '工业区': 65.0,
            '交通干线': 70.0,
            '文教区': 40.0,
            '混合区': 50.0
        }
        
        # 不同区域类型的噪音波动范围（分贝）
        self.noise_ranges = {
            '居住区': (35.0, 60.0),
            '商业区': (45.0, 70.0),
            '工业区': (55.0, 80.0),
            '交通干线': (60.0, 85.0),
            '文教区': (30.0, 55.0),
            '混合区': (40.0, 65.0)
        }
        
        # 时段系数（0-1之间，影响噪音水平）
        self.time_coefficients = {
            'morning': (6, 8, 1.2),      # 早高峰 (6-8点)
            'day': (8, 18, 1.0),         # 白天 (8-18点)
            'evening': (18, 22, 1.1),    # 晚高峰 (18-22点)
            'night': (22, 6, 0.7)        # 夜间 (22-6点)
        }
    
    def _get_time_period(self, time_obj):
        """根据时间获取时段"""
        hour = time_obj.hour
        
        if 6 <= hour < 8:
            return 'morning'
        elif 8 <= hour < 18:
            return 'day'
        elif 18 <= hour < 22:
            return 'evening'
        else:
            return 'night'
    
    def _calculate_base_noise(self, region_type, time_obj):
        """计算基础噪音值"""
        base = self.base_noise_levels.get(region_type, 50.0)
        period = self._get_time_period(time_obj)
        coefficient = self.time_coefficients[period][2]
        
        # 基础值 * 时段系数
        adjusted_base = base * coefficient
        
        # 添加随机波动（±5分贝）
        noise = adjusted_base + random.uniform(-5, 5)
        
        # 确保在合理范围内
        min_noise, max_noise = self.noise_ranges.get(region_type, (40.0, 70.0))
        noise = max(min_noise, min(max_noise, noise))
        
        return noise
    
    def _smooth_transition(self, previous_value, target_value, time_since_last):
        """平滑过渡，避免数据突变"""
        if previous_value is None:
            return target_value
        
        # 如果距离上次时间很短，使用平滑过渡
        if time_since_last and time_since_last < 60:  # 1分钟内
            # 计算变化幅度（最大变化5分贝/分钟）
            max_change = (time_since_last / 60.0) * 5.0
            diff = target_value - previous_value
            
            if abs(diff) > max_change:
                if diff > 0:
                    return previous_value + max_change
        else:
                    return previous_value - max_change
        
        # 如果距离上次时间较长，允许较大变化，但仍有平滑
        if time_since_last and time_since_last < 300:  # 5分钟内
            max_change = 10.0
            diff = target_value - previous_value
            
            if abs(diff) > max_change:
                if diff > 0:
                    return previous_value + max_change
                else:
                    return previous_value - max_change
        
        return target_value
    
    def _generate_frequency_analysis(self, noise_value):
        """生成频率分析数据"""
        # 模拟不同频率段的能量分布
        frequencies = {
            'low': random.uniform(0.2, 0.4),      # 低频 (20-200Hz)
            'mid': random.uniform(0.3, 0.5),      # 中频 (200-2000Hz)
            'high': random.uniform(0.2, 0.4)      # 高频 (2000-20000Hz)
        }
        
        # 归一化
        total = sum(frequencies.values())
        for key in frequencies:
            frequencies[key] = frequencies[key] / total
        
        return frequencies
    
    def _determine_data_quality(self, device_status, noise_value, region_type):
        """确定数据质量"""
        if device_status != '在线':
            return '无效'
        
        # 根据噪音值是否在合理范围内判断
        min_noise, max_noise = self.noise_ranges.get(region_type, (40.0, 70.0))
        
        if noise_value < min_noise - 10 or noise_value > max_noise + 10:
            return '较差'
        
        # 添加一些随机性，模拟真实情况
        quality_rand = random.random()
        if quality_rand < 0.7:
            return '优秀'
        elif quality_rand < 0.9:
            return '良好'
        else:
            return '一般'
    
    def _generate_weather_data(self):
        """生成天气相关数据"""
        weather_conditions = ['normal', 'sunny', 'cloudy', 'rainy', 'windy']
        weather = random.choice(weather_conditions)
        
        # 根据天气生成温度和湿度
        if weather == 'sunny':
            temperature = random.uniform(20, 30)
            humidity = random.uniform(40, 60)
        elif weather == 'rainy':
            temperature = random.uniform(15, 25)
            humidity = random.uniform(70, 90)
        elif weather == 'windy':
            temperature = random.uniform(18, 28)
            humidity = random.uniform(50, 70)
            wind_speed = random.uniform(5, 15)
        else:
            temperature = random.uniform(18, 26)
            humidity = random.uniform(50, 70)
            wind_speed = random.uniform(0, 5)
        
        return {
            'weather': weather,
            'temperature': round(temperature, 1),
            'humidity': round(humidity, 1),
            'wind_speed': round(wind_speed, 1) if weather == 'windy' else round(random.uniform(0, 5), 1)
        }
    
    def generate_realistic_noise_data(self, region_type, time, location=None, 
                                     device_status='在线', previous_value=None, 
                                     time_since_last=None):
        """
        生成真实的噪音数据
        
        参数:
            region_type: 区域类型（居住区、商业区、工业区等）
            time: 时间对象（datetime）
            location: 位置信息，包含 lng 和 lat（可选）
            device_status: 设备状态（默认：在线）
            previous_value: 上次的噪音值（用于平滑过渡，可选）
            time_since_last: 距离上次的时间（秒，可选）
        
        返回:
            dict: 包含噪音数据及其相关信息的字典
        """
        # 计算基础噪音值
        base_noise = self._calculate_base_noise(region_type, time)
        
        # 如果有上次值，进行平滑过渡
        if previous_value is not None:
            noise_value = self._smooth_transition(previous_value, base_noise, time_since_last)
        else:
            noise_value = base_noise
        
        # 添加一些随机波动（±2分贝）
        noise_value += random.uniform(-2, 2)
        
        # 确保在合理范围内
        min_noise, max_noise = self.noise_ranges.get(region_type, (40.0, 70.0))
        noise_value = max(min_noise - 5, min(max_noise + 5, noise_value))
        
        # 如果设备不在线，数据质量降低
        if device_status != '在线':
            noise_value = random.uniform(0, 30)  # 异常低值
        
        # 生成频率分析
        frequency_analysis = self._generate_frequency_analysis(noise_value)
        
        # 确定数据质量
        data_quality = self._determine_data_quality(device_status, noise_value, region_type)
        
        # 生成天气数据
        weather_data = self._generate_weather_data()
        
        # 构建返回数据
        result = {
            'noise_value': round(noise_value, 2),
            'timestamp': time if isinstance(time, datetime) else datetime.now(),
            'frequency_analysis': frequency_analysis,
            'data_quality': data_quality,
            'temperature': weather_data['temperature'],
            'humidity': weather_data['humidity'],
            'wind_speed': weather_data['wind_speed'],
            'weather': weather_data['weather']
        }
        
        return result

