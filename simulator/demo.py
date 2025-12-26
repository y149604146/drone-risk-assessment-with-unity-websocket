# ====================== 主程序：整合调用 ======================
from dynamic_calculate.unmanned_aerial_vehicle.simulator.DroneAnimation import DroneAnimation
from dynamic_calculate.unmanned_aerial_vehicle.simulator.DroneRiskCalculator import DroneRiskCalculator
from dynamic_calculate.unmanned_aerial_vehicle.simulator.DroneSimulation import DroneSimulation

if __name__ == "__main__":
    # 1. 初始化无人机模拟类
    drone_sim = DroneSimulation(
        protect_zone=1300,  # 防范区1000米
        kill_zone=900,  # 击毙区200米
        total_time=60  # 模拟60秒
    )

    # 2. 初始化风险计算类（关联模拟类）
    risk_calc = DroneRiskCalculator(drone_sim)

    # 3. 初始化动画类（关联模拟和计算类）
    drone_ani = DroneAnimation(drone_sim, risk_calc)

    # 4. 运行动态模拟
    drone_ani.run_animation(
        frame_num=100,  # 100帧
        interval=50,  # 每50毫秒一帧
        repeat=False  # 播放一次停止
    )