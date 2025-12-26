import threading
import time
from typing import Optional
from datetime import datetime, timedelta

from dynamic_calculate.unmanned_aerial_vehicle.websocket.Drondata import DroneData
from dynamic_calculate.unmanned_aerial_vehicle.websocket.globals import Constant

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
            cutoff_time = datetime.now() - timedelta(seconds=Constant.DISPLAY_WINDOW)
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

