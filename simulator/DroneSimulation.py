import numpy as np

# ====================== 类1：无人机飞行数据模拟类 ======================
class DroneSimulation:
    """无人机飞行轨迹与距离模拟类"""

    def __init__(self, protect_zone=1000, kill_zone=200, total_time=60):
        """
        初始化无人机模拟参数
        :param protect_zone: 防范区边界距离（米）
        :param kill_zone: 击毙区边界距离（米）
        :param total_time: 模拟总时长（秒）
        """
        self.D1 = protect_zone  # 防范区边界
        self.D2 = kill_zone  # 击毙区边界
        self.total_time = total_time  # 总模拟时长

        # 模拟结果存储
        self.time_points = None
        self.all_distances = None
        self.all_change_rates = None

    def simulate_distance(self, time):
        """
        计算指定时间点无人机的距离和变化率
        :param time: 当前时间（秒）
        :return: 距离（米）、距离变化率（米/秒）
        """
        if time <= self.total_time / 2:
            # 0-half_time：靠近（1500→800米）
            distance = 1500 - (1500 - 800) * (time / (self.total_time / 2))
            change_rate = -(1500 - 800) / (self.total_time / 2)
        else:
            # half_time-total_time：远离（800→1500米）
            distance = 800 + (1500 - 800) * ((time - self.total_time / 2) / (self.total_time / 2))
            change_rate = (1500 - 800) / (self.total_time / 2)
        return distance, change_rate

    def generate_all_data(self, frame_num=100):
        """
        生成所有时间点的模拟数据
        :param frame_num: 总帧数（数据点数量）
        :return: 时间点数组、距离数组、变化率数组
        """
        self.time_points = np.linspace(0, self.total_time, frame_num)
        self.all_distances = []
        self.all_change_rates = []

        for t in self.time_points:
            d, dr = self.simulate_distance(t)
            self.all_distances.append(d)
            self.all_change_rates.append(dr)

        return self.time_points, self.all_distances, self.all_change_rates