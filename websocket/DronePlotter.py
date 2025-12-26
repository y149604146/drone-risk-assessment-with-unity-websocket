import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import matplotlib as mpl

from dynamic_calculate.unmanned_aerial_vehicle.websocket.DataBuffer import DataBuffer
from dynamic_calculate.unmanned_aerial_vehicle.websocket.globals import Constant

# ====================== 全局配置 ======================
plt.rcParams["font.family"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams['axes.unicode_minus'] = False
mpl.rcParams['font.sans-serif'] = ['SimHei']

# ====================== 绘图逻辑（保持不变） ======================
class DronePlotter:
    def __init__(self, data_buffer: DataBuffer):
        self.data_buffer = data_buffer
        self.is_running = False
        self.fig, self.ax1, self.ax2 = self._init_figure()
        self.line1, self.point1 = self._init_distance_plot()
        self.line2, self.point2 = self._init_risk_plot()
        self.info_text = self._init_info_text()
        self.ani = None

    def _init_figure(self):
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        fig.suptitle(f'无人机实时数据监控（防控区{Constant.PROTECT_ZONE}m | 击毙区{Constant.KILL_ZONE}m | 窗口{Constant.DISPLAY_WINDOW}s）',
                     fontsize=16)
        ax1.set_ylim(0, Constant.PROTECT_ZONE + 2000)
        ax2.set_ylim(-5, 105)
        ax1.axhline(y=Constant.PROTECT_ZONE, color='orange', linestyle='--', label=f'防控区（{Constant.PROTECT_ZONE}m）')
        ax1.axhline(y=Constant.KILL_ZONE, color='red', linestyle='--', label=f'击毙区（{Constant.KILL_ZONE}m）')
        ax2.axhline(y=70, color='orange', linestyle='--', label='防控区最低风险')
        ax2.axhline(y=100, color='red', linestyle='--', label='击毙区最高风险')
        ax1.set_ylabel('无人机距离（米）')
        ax2.set_xlabel('系统时间（时:分:秒）')
        ax2.set_ylabel('风险值（0-100）')
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        ax2.xaxis.set_major_locator(mdates.SecondLocator(interval=5))
        ax1.grid(True, alpha=0.5)
        ax1.legend(loc='upper right')
        ax2.grid(True, alpha=0.5)
        ax2.legend(loc='upper right')
        now = datetime.now()
        ax1.set_xlim([now - timedelta(seconds=Constant.DISPLAY_WINDOW), now])
        ax2.set_xlim([now - timedelta(seconds=Constant.DISPLAY_WINDOW), now])
        return fig, ax1, ax2

    def _init_distance_plot(self):
        line1, = self.ax1.plot([], [], color='blue', linewidth=2, label='无人机距离')
        point1, = self.ax1.plot([], [], 'bo', markersize=8, label='当前位置')
        return line1, point1

    def _init_risk_plot(self):
        line2, = self.ax2.plot([], [], color='red', linewidth=2, label='风险值')
        point2, = self.ax2.plot([], [], 'ro', markersize=8, label='当前风险')
        return line2, point2

    def _init_info_text(self):
        return self.fig.text(0.02, 0.02, '', fontsize=10, bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))

    def _filter_visible_data(self, window_start, window_end):
        collected_data = self.data_buffer.get_collected_data()
        return [d for d in collected_data if window_start <= d.sys_time <= window_end]

    def _update_plot(self, frame):
        if not self.is_running:
            return
        current_sys_time = datetime.now()
        window_start = current_sys_time - timedelta(seconds=Constant.DISPLAY_WINDOW)
        window_end = current_sys_time
        self.ax1.set_xlim([window_start, window_end])
        self.ax2.set_xlim([window_start, window_end])

        latest_data = self.data_buffer.get_latest_data()
        last_receive_time_str, elapsed_time = self.data_buffer.get_last_receive_info()
        visible_data = self._filter_visible_data(window_start, window_end)

        if latest_data and latest_data.is_valid:
            speed = 0
            if len(visible_data) >= 2:
                d1, d2 = visible_data[-2], visible_data[-1]
                time_diff = (d2.sys_time - d1.sys_time).total_seconds()
                if time_diff > 0:
                    speed = abs(d2.distance - d1.distance) / time_diff
            if visible_data:
                sys_times = [d.sys_time for d in visible_data]
                distances = [d.distance for d in visible_data]
                risks = [d.risk_value for d in visible_data]
                self.line1.set_data(sys_times, distances)
                self.line2.set_data(sys_times, risks)
                self.point1.set_data([latest_data.sys_time], [latest_data.distance])
                self.point2.set_data([latest_data.sys_time], [latest_data.risk_value])
            speed_label = "民用级" if speed <= Constant.DRONE_SPEED_CIVIL * 1.2 else "军用级" if speed >= Constant.DRONE_SPEED_MILITARY * 0.8 else "未知"
            self.info_text.set_text(
                f'防控区：{Constant.PROTECT_ZONE}m | 击毙区：{Constant.KILL_ZONE}m | 窗口：{Constant.DISPLAY_WINDOW}s\n'
                f'当前时间：{current_sys_time.strftime("%H:%M:%S")}\n'
                f'无人机距离：{latest_data.distance:.1f}m | 风险值：{latest_data.risk_value}\n'
                f'无人机速度：{speed:.1f}m/s（{speed_label}）\n'
                f'最后接收：{last_receive_time_str}（{elapsed_time:.1f}s前）\n'
                f'WS地址：{Constant.WS_URL} | ✅ 数据正常（Postman模式）'
            )
        else:
            self.line1.set_data([], [])
            self.line2.set_data([], [])
            self.point1.set_data([], [])
            self.point2.set_data([], [])
            self.info_text.set_text(
                f'防控区：{Constant.PROTECT_ZONE}m | 击毙区：{Constant.KILL_ZONE}m | 窗口：{Constant.DISPLAY_WINDOW}s\n'
                f'当前时间：{current_sys_time.strftime("%H:%M:%S")}\n'
                f'连接地址：{Constant.WS_URL} | ❌ 未接收响应数据\n'
                f'排查：1.确认触发消息格式 2.服务端是否推送响应 3.网络连通性\n'
                f'最后接收：{last_receive_time_str}\n'
                f'发送频率：{Constant.SEND_TRIGGER_INTERVAL}秒/次（和Postman一致）'
            )
        self.fig.canvas.draw()

    def start_plotting(self):
        self.is_running = True
        print(f"[绘图] 已启动 | 窗口{Constant.DISPLAY_WINDOW}s | 更新间隔{Constant.UPDATE_INTERVAL}ms")
        self.ani = animation.FuncAnimation(
            self.fig, self._update_plot, interval=Constant.UPDATE_INTERVAL, blit=False, repeat=True, cache_frame_data=False)
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.22, left=0.1, right=0.95)
        plt.show()

    def stop_plotting(self):
        self.is_running = False
        print("[绘图] 已停止")
