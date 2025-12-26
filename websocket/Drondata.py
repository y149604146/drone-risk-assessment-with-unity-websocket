from dataclasses import dataclass
from datetime import datetime

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