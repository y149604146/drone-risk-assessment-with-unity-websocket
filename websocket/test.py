import math
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.animation as animation
import matplotlib as mpl
import matplotlib.dates as mdates
import json
import threading
import time
import websocket
import ssl
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timedelta

# ====================== 全局配置 ======================
plt.rcParams["font.family"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams['axes.unicode_minus'] = False
mpl.rcParams['font.sans-serif'] = ['SimHei']

# WebSocket配置（和Postman完全一致）
WS_URL = "ws://192.168.50.163:8083/drone"  # Postman连接的地址
RECONNECT_INTERVAL = 3
DISPLAY_WINDOW = 40
UPDATE_INTERVAL = 200
SEND_TRIGGER_INTERVAL = 1  # 每1秒发送一次触发消息（和Postman频率一致）

# 无人机区域配置
PROTECT_ZONE = 10000
KILL_ZONE = 1000
DRONE_SPEED_CIVIL = 20
DRONE_SPEED_MILITARY = 290


# ====================== 数据结构 ======================
@dataclass
class DroneData:
    sys_time: datetime
    x: float
    y: float
    z: float
    distance: float
    risk_value: float
    is_valid: bool = True


# ====================== 线程安全缓存 ======================
class DataBuffer:
    def __init__(self):
        self.lock = threading.Lock()
        self.latest_data: Optional[DroneData] = None
        self.collected_data = []
        self.last_receive_time = None

    def update_data(self, drone_data: DroneData):
        with self.lock:
            self.latest_data = drone_data
            cutoff_time = datetime.now() - timedelta(seconds=DISPLAY_WINDOW)
            self.collected_data = [d for d in self.collected_data if d.sys_time >= cutoff_time]
            self.collected_data.append(drone_data)
            self.last_receive_time = time.time()

    def get_latest_data(self) -> Optional[DroneData]:
        with self.lock:
            return self.latest_data

    def get_collected_data(self):
        with self.lock:
            return self.collected_data.copy()

    def get_last_receive_info(self):
        with self.lock:
            if self.last_receive_time is None:
                return "从未接收数据", 0.0
            else:
                elapsed = time.time() - self.last_receive_time
                return f"最近接收", elapsed


# ====================== WebSocket客户端（核心修改：主动发送触发消息） ======================
class DroneWebSocketClient:
    def __init__(self, data_buffer: DataBuffer):
        self.data_buffer = data_buffer
        self.is_running = False
        self.reconnect_flag = True
        self.ws = None
        self.client_thread = None
        self.send_thread = None  # 发送触发消息的线程
        self.heartbeat_running = False

    def _calculate_risk(self, distance: float) -> float:
        max_risk = 100
        min_risk = 0
        if distance <= KILL_ZONE:
            r_base = max_risk
        elif KILL_ZONE < distance <= PROTECT_ZONE:
            r_base = 100 - (distance - KILL_ZONE) * 30 / (PROTECT_ZONE - KILL_ZONE)
            r_base = max(70, min(100, r_base))
        else:
            r_base = 70 - (distance - PROTECT_ZONE) * 70 / (PROTECT_ZONE * 2)
            r_base = max(0, min(70, r_base))
        return round(r_base, 2)

    def on_open(self, ws):
        """连接成功：立即发送触发消息 + 启动持续发送线程"""
        print(f"\n✅ [{datetime.now().strftime('%H:%M:%S')}] 成功连接到: {WS_URL}")

        # 1. 发送初始触发消息（和Postman发送的格式完全一致）
        self._send_trigger_message(ws)

        # 2. 启动持续发送触发消息的线程（模拟Postman连续发送）
        self.start_send_thread(ws)

        # 3. 启动心跳保活
        self.start_heartbeat(ws)

    def _send_trigger_message(self, ws):
        """发送和Postman完全一致的触发消息（核心）"""
        # 这里替换为Postman中实际发送的消息格式！！！
        # 示例格式（根据你的Postman实际数据修改）
        trigger_msg = {
            "type": "position",
            "data": {
                "x": 100.0,  # 和Postman发送的初始值一致
                "y": 200.0,
                "z": 50.0,
                "timestamp": int(time.time() * 1000)
            }
        }
        try:
            ws.send(json.dumps(trigger_msg))
            print(f"📤 发送触发消息（和Postman一致）：{json.dumps(trigger_msg)}")
        except Exception as e:
            print(f"❌ 发送触发消息失败：{e}")

    def start_send_thread(self, ws):
        """持续发送触发消息，模拟Postman连续发送"""

        def send_loop():
            x, y = 100.0, 200.0
            step = 10.0  # 模拟坐标递增（和Postman一致）
            while self.is_running and self.reconnect_flag:
                try:
                    # 构造和Postman完全一致的持续触发消息
                    send_data = {
                    }
                    ws.send(json.dumps(send_data))
                    print(f"📤 持续发送触发消息：{json.dumps(send_data)}")

                    # 坐标递增（模拟无人机移动）
                    x += step
                    y += step
                    time.sleep(SEND_TRIGGER_INTERVAL)  # 每1秒发送一次（和Postman频率一致）
                except Exception as e:
                    print(f"❌ 持续发送失败：{e}")
                    break

        self.send_thread = threading.Thread(target=send_loop, daemon=True)
        self.send_thread.start()

    def on_message(self, ws, message):
        """接收服务端响应数据（持续接收response）"""
        print(f"\n📥 收到服务端响应：{message}")  # 打印原始响应，对齐Postman
        try:
            msg_data = json.loads(message)
            # 兼容服务端响应的所有格式
            if "data" in msg_data:
                pos_data = msg_data["data"]
            else:
                pos_data = msg_data

            # 提取响应中的无人机数据
            x = float(pos_data.get("x", 0.0))
            y = float(pos_data.get("y", 0.0))
            z = float(pos_data.get("z", 0.0))
            sys_time = datetime.now()

            distance = math.hypot(x, y)
            risk_value = self._calculate_risk(distance)

            # 存入缓存供绘图使用
            drone_data = DroneData(sys_time, x, y, z, distance, risk_value, True)
            self.data_buffer.update_data(drone_data)
            print(f"✅ 响应数据解析完成 - 距离：{distance:.1f}m | 风险：{risk_value}")

        except json.JSONDecodeError:
            print(f"❌ 非JSON格式响应：{message}")
        except Exception as e:
            print(f"❌ 解析响应失败：{str(e)} | 原始响应：{message}")

    def on_error(self, ws, error):
        print(f"\n❌ [{datetime.now().strftime('%H:%M:%S')}] WebSocket错误：{str(error)}")
        self.heartbeat_running = False

    def on_close(self, ws, close_status_code, close_msg):
        close_msg = close_msg.decode('utf-8') if isinstance(close_msg, bytes) else close_msg
        print(f"\n🔌 连接关闭 | 状态码：{close_status_code} | 消息：{close_msg}")
        self.heartbeat_running = False
        if self.reconnect_flag:
            print(f"🔄 {RECONNECT_INTERVAL}秒后重连...")
            time.sleep(RECONNECT_INTERVAL)
            self.start_client()

    def start_heartbeat(self, ws):
        """心跳保活，避免连接断开"""
        self.heartbeat_running = True

        def heartbeat_loop():
            while self.heartbeat_running:
                try:
                    heartbeat = {"type": "ping", "timestamp": int(time.time() * 1000)}
                    ws.send(json.dumps(heartbeat))
                    time.sleep(3)
                except Exception as e:
                    print(f"❌ 心跳发送失败：{e}")
                    break

        threading.Thread(target=heartbeat_loop, daemon=True).start()

    def start_client(self):
        """启动客户端（兼容所有版本）"""
        websocket.enableTrace(True)  # 打印详细日志，对齐Postman的调试信息
        self.ws = websocket.WebSocketApp(
            WS_URL,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            header=["Sec-WebSocket-Version: 13"]  # 对齐Postman的协议版本
        )
        try:
            self.ws.run_forever(
                ping_interval=5,
                ping_timeout=3,
                sslopt={"cert_reqs": ssl.CERT_NONE}
            )
        except Exception as e:
            print(f"❌ 客户端启动失败：{str(e)}")

    def start(self):
        self.is_running = True
        self.reconnect_flag = True
        self.client_thread = threading.Thread(target=self.start_client, daemon=True)
        self.client_thread.start()
        print(f"[主程序] WebSocket客户端启动，连接：{WS_URL}")
        print(f"[提示] 客户端会像Postman一样持续发送触发消息，接收服务端响应...")

    def stop(self):
        self.is_running = False
        self.reconnect_flag = False
        self.heartbeat_running = False
        if self.ws:
            self.ws.close()
        print("[WebSocket] 客户端已停止")


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
        fig.suptitle(f'无人机实时数据监控（防控区{PROTECT_ZONE}m | 击毙区{KILL_ZONE}m | 窗口{DISPLAY_WINDOW}s）',
                     fontsize=16)
        ax1.set_ylim(0, PROTECT_ZONE + 2000)
        ax2.set_ylim(-5, 105)
        ax1.axhline(y=PROTECT_ZONE, color='orange', linestyle='--', label=f'防控区（{PROTECT_ZONE}m）')
        ax1.axhline(y=KILL_ZONE, color='red', linestyle='--', label=f'击毙区（{KILL_ZONE}m）')
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
        ax1.set_xlim([now - timedelta(seconds=DISPLAY_WINDOW), now])
        ax2.set_xlim([now - timedelta(seconds=DISPLAY_WINDOW), now])
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
        window_start = current_sys_time - timedelta(seconds=DISPLAY_WINDOW)
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
            speed_label = "民用级" if speed <= DRONE_SPEED_CIVIL * 1.2 else "军用级" if speed >= DRONE_SPEED_MILITARY * 0.8 else "未知"
            self.info_text.set_text(
                f'防控区：{PROTECT_ZONE}m | 击毙区：{KILL_ZONE}m | 窗口：{DISPLAY_WINDOW}s\n'
                f'当前时间：{current_sys_time.strftime("%H:%M:%S")}\n'
                f'无人机距离：{latest_data.distance:.1f}m | 风险值：{latest_data.risk_value}\n'
                f'无人机速度：{speed:.1f}m/s（{speed_label}）\n'
                f'最后接收：{last_receive_time_str}（{elapsed_time:.1f}s前）\n'
                f'WS地址：{WS_URL} | ✅ 数据正常（Postman模式）'
            )
        else:
            self.line1.set_data([], [])
            self.line2.set_data([], [])
            self.point1.set_data([], [])
            self.point2.set_data([], [])
            self.info_text.set_text(
                f'防控区：{PROTECT_ZONE}m | 击毙区：{KILL_ZONE}m | 窗口：{DISPLAY_WINDOW}s\n'
                f'当前时间：{current_sys_time.strftime("%H:%M:%S")}\n'
                f'连接地址：{WS_URL} | ❌ 未接收响应数据\n'
                f'排查：1.确认触发消息格式 2.服务端是否推送响应 3.网络连通性\n'
                f'最后接收：{last_receive_time_str}\n'
                f'发送频率：{SEND_TRIGGER_INTERVAL}秒/次（和Postman一致）'
            )
        self.fig.canvas.draw()

    def start_plotting(self):
        self.is_running = True
        print(f"[绘图] 已启动 | 窗口{DISPLAY_WINDOW}s | 更新间隔{UPDATE_INTERVAL}ms")
        self.ani = animation.FuncAnimation(
            self.fig, self._update_plot, interval=UPDATE_INTERVAL, blit=False, repeat=True, cache_frame_data=False)
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.22, left=0.1, right=0.95)
        plt.show()

    def stop_plotting(self):
        self.is_running = False
        print("[绘图] 已停止")


# ====================== 主程序 ======================
if __name__ == "__main__":
    # 初始化数据缓存
    data_buffer = DataBuffer()

    # 启动WebSocket客户端（Postman模式：主动发消息，收响应）
    ws_client = DroneWebSocketClient(data_buffer)
    ws_client.start()

    # 启动绘图
    plotter = DronePlotter(data_buffer)
    try:
        plotter.start_plotting()
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断程序")
    finally:
        ws_client.stop()
        plotter.stop_plotting()
        print("[主程序] 所有服务已停止")