import math
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.animation as animation
import matplotlib as mpl

# ====================== 解决中文显示问题 ======================
plt.rcParams["font.family"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams['axes.unicode_minus'] = False
mpl.rcParams['font.sans-serif'] = ['SimHei']

# ====================== 类3：动态可视化类（可选，封装显示逻辑） ======================
class DroneAnimation:
    """无人机数据动态可视化类"""
    def __init__(self, drone_simulator, risk_calculator):
        """
        初始化动画类
        :param drone_simulator: DroneSimulation实例
        :param risk_calculator: DroneRiskCalculator实例
        """
        self.sim = drone_simulator
        self.calc = risk_calculator
        self.fig, self.ax1, self.ax2 = self._init_figure()
        self.line1, self.point1, self.line2, self.point2 = self._init_plots()
        self.info_text = self._init_info_text()
        self.ani = None

    def _init_figure(self):
        """初始化画布和子图"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        fig.suptitle('无人机距离与风险值动态变化', fontsize=16)
        return fig, ax1, ax2

    def _init_plots(self):
        """初始化绘图对象"""
        # 距离曲线和实时点
        line1, = self.ax1.plot([], [], color='blue', linewidth=2, label='无人机距离（米）')
        point1, = self.ax1.plot([], [], 'bo', markersize=8, label='当前位置')

        # 风险值曲线和实时点
        line2, = self.ax2.plot([], [], color='red', linewidth=2, label='风险值（0-100）')
        point2, = self.ax2.plot([], [], 'ro', markersize=8, label='当前风险值')

        # 配置子图1（距离）
        self.ax1.set_xlim(0, self.sim.total_time)
        self.ax1.set_ylim(0, 1600)
        self.ax1.axhline(y=self.sim.D1, color='orange', linestyle='--', label=f'防范区边界（{self.sim.D1}米）')
        self.ax1.axhline(y=self.sim.D2, color='red', linestyle='--', label=f'击毙区边界（{self.sim.D2}米）')
        self.ax1.set_ylabel('距离（米）')
        self.ax1.grid(True)
        self.ax1.legend(loc='upper right')

        # 配置子图2（风险值）
        self.ax2.set_xlim(0, self.sim.total_time)
        self.ax2.set_ylim(-5, 105)
        self.ax2.axhline(y=70, color='orange', linestyle='--', label='防范区基础风险值')
        self.ax2.axhline(y=100, color='darkred', linestyle='--', label='击毙区风险值')
        self.ax2.set_xlabel('时间（秒）')
        self.ax2.set_ylabel('风险值')
        self.ax2.grid(True)
        self.ax2.legend(loc='upper right')

        return line1, point1, line2, point2

    def _init_info_text(self):
        """初始化实时信息文本框"""
        return self.fig.text(
            0.02, 0.02, '', fontsize=12,
            bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8)
        )

    def _update_frame(self, frame):
        """动画帧更新函数"""
        t = self.sim.time_points[frame]
        d = self.sim.all_distances[frame]
        risk = self.calc.all_risk_values[frame]
        dr = self.sim.all_change_rates[frame]
        trend = "靠近" if dr < 0 else "远离"

        # 更新曲线数据
        self.line1.set_data(self.sim.time_points[:frame+1], self.sim.all_distances[:frame+1])
        self.line2.set_data(self.sim.time_points[:frame+1], self.calc.all_risk_values[:frame+1])

        # 更新实时点（修复序列问题）
        self.point1.set_data([t], [d])
        self.point2.set_data([t], [risk])

        # 更新信息文本
        self.info_text.set_text(
            f'时间：{t:.1f}秒\n'
            f'当前距离：{d:.1f}米\n'
            f'移动趋势：{trend}（速率：{dr:.1f}米/秒）\n'
            f'当前风险值：{risk}'
        )

        return self.line1, self.point1, self.line2, self.point2, self.info_text

    def run_animation(self, frame_num=100, interval=50, repeat=False):
        """
        运行动态动画
        :param frame_num: 总帧数
        :param interval: 帧间隔（毫秒）
        :param repeat: 是否循环播放
        """
        # 确保数据已生成
        if self.sim.time_points is None:
            self.sim.generate_all_data(frame_num)
        if self.calc.all_risk_values is None:
            self.calc.generate_risk_data()

        # 创建动画
        self.ani = animation.FuncAnimation(
            self.fig,
            self._update_frame,
            frames=frame_num,
            interval=interval,
            blit=False,
            repeat=repeat
        )

        plt.tight_layout()
        plt.subplots_adjust(bottom=0.15)
        plt.show()
