import math
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.animation as animation
import matplotlib as mpl
import threading
import time
import queue
from dataclasses import dataclass

# ====================== 全局配置：解决中文显示问题 ======================
plt.rcParams["font.family"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams['axes.unicode_minus'] = False
mpl.rcParams['font.sans-serif'] = ['SimHei']


# ====================== 数据结构定义：统一数据格式 ======================
@dataclass
class DroneData:
    """无人机实时数据结构体"""
    timestamp: float  # 时间戳（秒）
    distance: float  # 距离（米）
    change_rate: float  # 距离变化率（米/秒）
    risk_value: float  # 风险值（0-100）


# ====================== 服务类1：无人机模拟服务（生产者） ======================
class DroneSimService:
    """无人机数据模拟服务，以1秒间隔推送实时数据"""

    def __init__(self, protect_zone=1000, kill_zone=200, total_time=60):
        self.D1 = protect_zone  # 防范区边界
        self.D2 = kill_zone  # 击毙区边界
        self.total_time = total_time  # 总模拟时长
        self.data_queue = queue.Queue()  # 数据推送队列
        self.is_running = False  # 服务运行状态
        self.sim_thread = None  # 模拟线程
        self.current_time = 0.0  # 当前模拟时间

    def _simulate_single_data(self, current_time):
        """模拟单个时间点的无人机数据"""
        # 计算距离和变化率
        if current_time <= self.total_time / 2:
            distance = 1500 - (1500 - 800) * (current_time / (self.total_time / 2))
            change_rate = -(1500 - 800) / (self.total_time / 2)
        else:
            distance = 800 + (1500 - 800) * ((current_time - self.total_time / 2) / (self.total_time / 2))
            change_rate = (1500 - 800) / (self.total_time / 2)

        # 计算风险值
        max_risk = 100
        min_risk = 0
        if distance > self.D1:
            r_base = max_risk * (self.D1 - distance) / (self.D1 - self.D2)
            r_base = max(min_risk, min(max_risk, r_base))
        elif self.D2 < distance <= self.D1:
            r_base = 70
        else:
            r_base = max_risk

        # 趋势修正
        if change_rate < 0:
            r_final = r_base * 1.2
        elif change_rate > 0:
            r_final = r_base * 0.8
        else:
            r_final = r_base
        r_final = max(min_risk, min(max_risk, round(r_final, 2)))

        return DroneData(
            timestamp=current_time,
            distance=distance,
            change_rate=change_rate,
            risk_value=r_final
        )

    def _run_sim_loop(self):
        """模拟循环：每1秒生成并推送一次数据"""
        self.current_time = 0.0
        self.is_running = True

        while self.is_running and self.current_time <= self.total_time:
            # 生成当前时间点数据
            drone_data = self._simulate_single_data(self.current_time)
            # 推送数据到队列
            self.data_queue.put(drone_data)
            # 打印日志（可选）
            print(
                f"[模拟服务] 推送数据 - 时间：{drone_data.timestamp:.1f}s | 距离：{drone_data.distance:.1f}m | 风险值：{drone_data.risk_value}")
            # 等待1秒
            time.sleep(1)
            # 时间递增
            self.current_time += 1.0

        # 模拟结束，推送结束标记
        self.data_queue.put(None)
        self.is_running = False
        print("[模拟服务] 模拟结束")

    def start_service(self):
        """启动模拟服务"""
        if not self.is_running:
            self.sim_thread = threading.Thread(target=self._run_sim_loop, daemon=True)
            self.sim_thread.start()
            print("[模拟服务] 已启动")

    def stop_service(self):
        """停止模拟服务"""
        self.is_running = False
        if self.sim_thread and self.sim_thread.is_alive():
            self.sim_thread.join()
        print("[模拟服务] 已停止")