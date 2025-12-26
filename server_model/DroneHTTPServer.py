import threading
from dataclasses import dataclass
from flask import Flask, jsonify

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


# ====================== 1. HTTP服务端：提供无人机数据接口 ======================
class DroneHTTPServer:
    """基于Flask的无人机数据HTTP服务端"""

    def __init__(self, protect_zone=1000, kill_zone=200):
        self.D1 = protect_zone  # 防范区边界
        self.D2 = kill_zone  # 击毙区边界
        self.current_time = 0.0  # 当前模拟时间
        self.is_running = False  # 服务运行状态
        self.app = Flask(__name__)
        self.server_thread = None  # HTTP服务线程

        # 注册HTTP接口
        self._register_routes()

    def _register_routes(self):
        """注册HTTP接口路由"""

        @self.app.route('/get_drone_data', methods=['GET'])
        def get_drone_data():
            """获取最新无人机数据的HTTP接口"""
            if not self.is_running:
                return jsonify({
                    "timestamp": 0,
                    "distance": 0,
                    "change_rate": 0,
                    "risk_value": 0,
                    "is_valid": False
                }), 503  # 服务不可用

            # 计算当前时间点数据
            data = self._calculate_drone_data(self.current_time)
            # 时间递增（每次请求+1秒）
            self.current_time += 1.0

            # 返回JSON格式数据
            return jsonify({
                "timestamp": data.timestamp,
                "distance": data.distance,
                "change_rate": data.change_rate,
                "risk_value": data.risk_value,
                "is_valid": data.is_valid
            })

    def _calculate_drone_data(self, current_time):
        """计算指定时间点的无人机数据（无限循环飞行）"""
        cycle_time = 60  # 一个飞行周期（30秒靠近+30秒远离）
        cycle_pos = current_time % cycle_time

        # 计算距离和变化率
        if cycle_pos <= cycle_time / 2:
            distance = 1500 - (1500 - 800) * (cycle_pos / (cycle_time / 2))
            change_rate = -(1500 - 800) / (cycle_time / 2)
        else:
            distance = 800 + (1500 - 800) * ((cycle_pos - cycle_time / 2) / (cycle_time / 2))
            change_rate = (1500 - 800) / (cycle_time / 2)

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
            risk_value=r_final,
            is_valid=True
        )

    def start_server(self):
        """启动HTTP服务（后台线程）"""
        self.is_running = True
        # 启动Flask服务（禁用调试模式，避免多线程冲突）
        self.server_thread = threading.Thread(
            target=self.app.run,
            kwargs={"host": HTTP_SERVER_HOST, "port": HTTP_SERVER_PORT, "debug": False, "use_reloader": False},
            daemon=True
        )
        self.server_thread.start()
        print(f"[HTTP服务端] 已启动，地址：http://{HTTP_SERVER_HOST}:{HTTP_SERVER_PORT}")
        print(f"[HTTP服务端] 数据接口：http://{HTTP_SERVER_HOST}:{HTTP_SERVER_PORT}/get_drone_data")

    def stop_server(self):
        """停止HTTP服务"""
        self.is_running = False
        print(f"[HTTP服务端] 已停止")

