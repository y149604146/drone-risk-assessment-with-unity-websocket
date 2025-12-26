import math
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.animation as animation
import matplotlib as mpl
import threading
import time
import requests
from dataclasses import dataclass
from flask import Flask, jsonify
import random

# ====================== 全局配置：解决中文显示问题 ======================
plt.rcParams["font.family"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams['axes.unicode_minus'] = False
mpl.rcParams['font.sans-serif'] = ['SimHei']

# ====================== 全局常量 ======================
HTTP_SERVER_HOST = "127.0.0.1"  # 服务端IP
HTTP_SERVER_PORT = 5000  # 服务端端口
REQUEST_TIMEOUT = 3  # HTTP请求超时时间（秒）


# ====================== 数据结构定义 ======================
@dataclass
class DroneData:
    """无人机实时数据结构体"""
    timestamp: float  # 时间戳（秒）
    distance: float  # 距离（米）
    change_rate: float  # 距离变化率（米/秒）
    risk_value: float  # 风险值（0-100）
    is_valid: bool = True  # 数据是否有效


# ====================== 2. HTTP客户端：请求数据+滚动绘图 ======================
class DroneHTTPClient:
    """HTTP客户端：每秒请求数据，固定宽度滚动绘制图表"""

    def __init__(self, display_window=60):
        self.display_window = display_window  # 画布固定显示的时间窗口（秒）
        self.collected_data = []  # 已接收的数据缓存
        self.failed_count = 0  # 连续失败计数器
        self.max_failed = 3  # 最大连续失败次数
        self.is_running = False  # 客户端运行状态

        # 初始化图表
        self.fig, self.ax1, self.ax2 = self._init_figure()
        self.line1, self.point1 = self._init_distance_plot()
        self.line2, self.point2 = self._init_risk_plot()
        self.info_text = self._init_info_text()
        self.ani = None

    def _init_figure(self):
        """初始化固定宽度的图表"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        fig.suptitle(f'无人机距离与风险值实时变化（HTTP版 | 固定宽度{self.display_window}秒）', fontsize=16)

        # 固定X轴范围
        ax1.set_xlim(0, self.display_window)
        ax2.set_xlim(0, self.display_window)

        # Y轴范围
        ax1.set_ylim(0, 1600)
        ax2.set_ylim(-5, 105)

        # 标记区域边界
        ax1.axhline(y=1000, color='orange', linestyle='--', label='防范区边界（1000米）')
        ax1.axhline(y=200, color='red', linestyle='--', label='击毙区边界（200米）')
        ax2.axhline(y=70, color='orange', linestyle='--', label='防范区基础风险值')
        ax2.axhline(y=100, color='darkred', linestyle='--', label='击毙区风险值')

        # 轴标签
        ax1.set_ylabel('距离（米）')
        ax2.set_xlabel('时间（秒）')
        ax2.set_ylabel('风险值')

        # 网格和图例
        ax1.grid(True)
        ax1.legend(loc='upper right')
        ax2.grid(True)
        ax2.legend(loc='upper right')

        return fig, ax1, ax2

    def _init_distance_plot(self):
        """初始化距离曲线"""
        line1, = self.ax1.plot([], [], color='blue', linewidth=2, label='无人机距离（米）')
        point1, = self.ax1.plot([], [], 'bo', markersize=8, label='当前位置')
        return line1, point1

    def _init_risk_plot(self):
        """初始化风险值曲线"""
        line2, = self.ax2.plot([], [], color='red', linewidth=2, label='风险值（0-100）')
        point2, = self.ax2.plot([], [], 'ro', markersize=8, label='当前风险值')
        return line2, point2

    def _init_info_text(self):
        """初始化实时信息文本框"""
        return self.fig.text(
            0.02, 0.02, '', fontsize=12,
            bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8)
        )

    def _filter_visible_data(self, current_time):
        """过滤出当前可视窗口内的数据"""
        start_time = max(0, current_time - self.display_window)
        return [d for d in self.collected_data if start_time <= d.timestamp <= current_time]

    def _request_drone_data(self):
        """向HTTP服务端请求数据"""
        try:
            response = requests.get(
                url=f"http://{HTTP_SERVER_HOST}:{HTTP_SERVER_PORT}/get_drone_data",
                timeout=REQUEST_TIMEOUT
            )
            if response.status_code == 200:
                # 解析JSON数据
                data = response.json()
                return DroneData(
                    timestamp=data["timestamp"],
                    distance=data["distance"],
                    change_rate=data["change_rate"],
                    risk_value=data["risk_value"],
                    is_valid=data["is_valid"]
                )
            else:
                print(f"[HTTP客户端] 请求失败，状态码：{response.status_code}")
                return DroneData(timestamp=0, distance=0, change_rate=0, risk_value=0, is_valid=False)
        except requests.exceptions.RequestException as e:
            # 请求超时/连接失败等异常
            print(f"[HTTP客户端] 请求异常：{str(e)}")
            return DroneData(timestamp=0, distance=0, change_rate=0, risk_value=0, is_valid=False)

    def _update_plot(self, frame):
        """每秒请求数据并更新图表"""
        if not self.is_running:
            return self.line1, self.point1, self.line2, self.point2, self.info_text

        # 1. 向HTTP服务端请求数据
        drone_data = self._request_drone_data()

        # 2. 处理请求结果
        if drone_data.is_valid:
            # 数据有效
            self.failed_count = 0
            self.collected_data.append(drone_data)
            current_time = drone_data.timestamp
            print(
                f"[HTTP客户端] 成功获取数据 - 时间：{current_time:.1f}s | 距离：{drone_data.distance:.1f}m | 风险值：{drone_data.risk_value}")

            # 过滤可视数据
            visible_data = self._filter_visible_data(current_time)
            timestamps = [d.timestamp for d in visible_data]
            distances = [d.distance for d in visible_data]
            risks = [d.risk_value for d in visible_data]

            # 滚动更新X轴
            if current_time > self.display_window:
                self.ax1.set_xlim(current_time - self.display_window, current_time)
                self.ax2.set_xlim(current_time - self.display_window, current_time)

            # 更新图表
            self.line1.set_data(timestamps, distances)
            self.line2.set_data(timestamps, risks)
            self.point1.set_data([current_time], [drone_data.distance])
            self.point2.set_data([current_time], [drone_data.risk_value])

            # 更新信息文本
            trend = "靠近" if drone_data.change_rate < 0 else "远离"
            self.info_text.set_text(
                f'HTTP客户端（每秒请求）\n'
                f'当前时间：{current_time:.1f}秒\n'
                f'当前距离：{drone_data.distance:.1f}米\n'
                f'移动趋势：{trend}（速率：{drone_data.change_rate:.1f}米/秒）\n'
                f'当前风险值：{drone_data.risk_value}\n'
                f'连续失败次数：{self.failed_count}/{self.max_failed}'
            )
        else:
            # 数据无效
            self.failed_count += 1
            print(f"[HTTP客户端] 获取数据失败，连续失败次数：{self.failed_count}/{self.max_failed}")
            self.info_text.set_text(
                f'HTTP客户端（每秒请求）\n'
                f'获取数据失败！\n'
                f'连续失败次数：{self.failed_count}/{self.max_failed}\n'
                f'失败达到{self.max_failed}次将终止程序'
            )

        # 3. 检查终止条件
        if self.failed_count >= self.max_failed:
            self.is_running = False
            print(f"[HTTP客户端] 连续{self.max_failed}次请求失败，程序终止")
            self.info_text.set_text(
                f'程序终止！\n'
                f'原因：连续{self.max_failed}次HTTP请求失败\n'
                f'最后更新时间：{self.collected_data[-1].timestamp if self.collected_data else 0:.1f}秒'
            )

        # 4. 等待1秒
        time.sleep(1)

        return self.line1, self.point1, self.line2, self.point2, self.info_text

    def start_client(self):
        """启动客户端"""
        self.is_running = True
        print(f"[HTTP客户端] 已启动，开始每秒请求数据（画布固定显示{self.display_window}秒）...")

        # 创建动画
        self.ani = animation.FuncAnimation(
            self.fig,
            self._update_plot,
            interval=1,
            blit=False,
            repeat=False
        )

        plt.tight_layout()
        plt.subplots_adjust(bottom=0.15)
        plt.show()

    def stop_client(self):
        """停止客户端"""
        self.is_running = False
        print("[HTTP客户端] 已停止")