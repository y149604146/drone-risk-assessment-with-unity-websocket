# ====================== 类2：风险计算与数据调用类 ======================
class DroneRiskCalculator:
    """无人机风险值计算与数据管理类"""

    def __init__(self, drone_simulator):
        """
        初始化风险计算器
        :param drone_simulator: DroneSimulation实例（依赖注入）
        """
        self.drone_sim = drone_simulator  # 关联的模拟实例
        self.max_risk = 100
        self.min_risk = 0

        # 风险计算结果存储
        self.all_risk_values = None

    def calculate_risk(self, distance, change_rate):
        """
        计算单个时间点的风险值
        :param distance: 无人机距离（米）
        :param change_rate: 距离变化率（米/秒）
        :return: 风险值（0-100）
        """
        # 1. 基础风险值
        if distance > self.drone_sim.D1:
            r_base = self.max_risk * (self.drone_sim.D1 - distance) / (self.drone_sim.D1 - self.drone_sim.D2)
            r_base = max(self.min_risk, min(self.max_risk, r_base))
        elif self.drone_sim.D2 < distance <= self.drone_sim.D1:
            r_base = 70
        else:
            r_base = self.max_risk

        # 2. 趋势修正
        if change_rate < 0:
            r_final = r_base * 1.2
        elif change_rate > 0:
            r_final = r_base * 0.8
        else:
            r_final = r_base

        # 限制范围
        r_final = max(self.min_risk, min(self.max_risk, r_final))
        return round(r_final, 2)

    def generate_risk_data(self):
        """
        基于模拟数据生成所有时间点的风险值
        :return: 风险值数组
        """
        if self.drone_sim.all_distances is None:
            raise ValueError("请先调用DroneSimulation的generate_all_data()生成模拟数据！")

        self.all_risk_values = []
        for d, dr in zip(self.drone_sim.all_distances, self.drone_sim.all_change_rates):
            risk = self.calculate_risk(d, dr)
            self.all_risk_values.append(risk)

        return self.all_risk_values
