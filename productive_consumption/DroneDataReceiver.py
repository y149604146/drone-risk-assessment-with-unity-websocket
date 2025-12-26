import math
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.animation as animation
import matplotlib as mpl
import threading
import time
import queue
from dataclasses import dataclass

from dynamic_calculate.unmanned_aerial_vehicle.productive_consumption.DroneSimService import DroneSimService

# ====================== 全局配置：解决中文显示问题 ======================
plt.rcParams["font.family"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams['axes.unicode_minus'] = False
mpl.rcParams['font.sans-serif'] = ['SimHei']


# ====================== 服务类2：数据接收与动态渲染服务（消费者） ======================
class DroneDataReceiver:
    """数据接收端，实时接收数据并更新图表"""

    def __init__(self, sim_service: DroneSimService):
        self.sim_service = sim_service  # 关联模拟服务
        self.collected_data = []  # 已接收的数据缓存

        # 初始化图表（修复核心错误：确保返回值匹配）
        self.fig, self.ax1, self.ax2 = self._init_figure()
        self.line1, self.point1 = self._init_distance_plot()
        self.line2, self.point2 = self._init_risk_plot()
        self.info_text = self._init_info_text()

        # 动画更新器
        self.ani = None

    def _init_figure(self):
        """初始化图表画布（修复：返回3个值，而非嵌套元组）"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        fig.suptitle('无人机距离与风险值实时动态变化（1秒/次）', fontsize=16)

        # 配置X轴范围
        ax1.set_xlim(0, self.sim_service.total_time)
        ax2.set_xlim(0, self.sim_service.total_time)

        # 配置Y轴范围
        ax1.set_ylim(0, 1600)  # 距离范围
        ax2.set_ylim(-5, 105)  # 风险值范围

        # 标记区域边界
        ax1.axhline(y=self.sim_service.D1, color='orange', linestyle='--', label=f'防范区边界（{self.sim_service.D1}米）')
        ax1.axhline(y=self.sim_service.D2, color='red', linestyle='--', label=f'击毙区边界（{self.sim_service.D2}米）')
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

        # 修复：返回3个独立值，而非嵌套元组
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

    def _update_plot(self, frame):
        """图表更新函数：从队列获取最新数据并更新"""
        try:
            # 非阻塞获取队列数据
            drone_data = self.sim_service.data_queue.get_nowait()

            if drone_data is None:
                # 收到结束标记，停止更新
                return self.line1, self.point1, self.line2, self.point2, self.info_text

            # 缓存数据
            self.collected_data.append(drone_data)

            # 提取缓存数据用于绘图
            timestamps = [d.timestamp for d in self.collected_data]
            distances = [d.distance for d in self.collected_data]
            risks = [d.risk_value for d in self.collected_data]

            # 更新曲线
            self.line1.set_data(timestamps, distances)
            self.line2.set_data(timestamps, risks)

            # 更新实时点
            self.point1.set_data([drone_data.timestamp], [drone_data.distance])
            self.point2.set_data([drone_data.timestamp], [drone_data.risk_value])

            # 更新信息文本
            trend = "靠近" if drone_data.change_rate < 0 else "远离"
            self.info_text.set_text(
                f'实时数据（1秒/次）\n'
                f'时间：{drone_data.timestamp:.1f}秒\n'
                f'当前距离：{drone_data.distance:.1f}米\n'
                f'移动趋势：{trend}（速率：{drone_data.change_rate:.1f}米/秒）\n'
                f'当前风险值：{drone_data.risk_value}'
            )

        except queue.Empty:
            # 队列为空，不更新
            pass

        return self.line1, self.point1, self.line2, self.point2, self.info_text

    def start_rendering(self):
        """启动实时渲染"""
        # 创建动画：每100ms检查一次队列（比1秒快，确保不遗漏）
        self.ani = animation.FuncAnimation(
            self.fig,
            self._update_plot,
            interval=100,  # 100ms检查一次队列
            blit=False,
            repeat=False
        )

        plt.tight_layout()
        plt.subplots_adjust(bottom=0.15)
        plt.show()
