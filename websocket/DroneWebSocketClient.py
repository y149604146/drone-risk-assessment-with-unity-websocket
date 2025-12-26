import math
import json
import threading
import time
import websocket
import ssl
from datetime import datetime

from dynamic_calculate.unmanned_aerial_vehicle.websocket.DataBuffer import DataBuffer
from dynamic_calculate.unmanned_aerial_vehicle.websocket.Drondata import DroneData
from dynamic_calculate.unmanned_aerial_vehicle.websocket.globals import Constant


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
        if distance <= Constant.KILL_ZONE:
            r_base = max_risk
        elif Constant.KILL_ZONE < distance <= Constant.PROTECT_ZONE:
            r_base = 100 - (distance - Constant.KILL_ZONE) * 30 / (Constant.PROTECT_ZONE - Constant.KILL_ZONE)
            r_base = max(70, min(100, r_base))
        else:
            r_base = 70 - (distance - Constant.PROTECT_ZONE) * 70 / (Constant.PROTECT_ZONE * 2)
            r_base = max(0, min(70, r_base))
        return round(r_base, 2)

    def on_open(self, ws):
        """连接成功：立即发送触发消息 + 启动持续发送线程"""
        print(f"\n✅ [{datetime.now().strftime('%H:%M:%S')}] 成功连接到: {Constant.WS_URL}")

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
                    time.sleep(Constant.SEND_TRIGGER_INTERVAL)  # 每1秒发送一次（和Postman频率一致）
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
            print(f"🔄 {Constant.RECONNECT_INTERVAL}秒后重连...")
            time.sleep(Constant.RECONNECT_INTERVAL)
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
            Constant.WS_URL,
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
        print(f"[主程序] WebSocket客户端启动，连接：{Constant.WS_URL}")
        print(f"[提示] 客户端会像Postman一样持续发送触发消息，接收服务端响应...")

    def stop(self):
        self.is_running = False
        self.reconnect_flag = False
        self.heartbeat_running = False
        if self.ws:
            self.ws.close()
        print("[WebSocket] 客户端已停止")
