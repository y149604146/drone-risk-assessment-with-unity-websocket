# ====================== 主程序：启动服务并运行 ======================
from dynamic_calculate.unmanned_aerial_vehicle.productive_consumption.DroneDataReceiver import DroneDataReceiver
from dynamic_calculate.unmanned_aerial_vehicle.productive_consumption.DroneSimService import DroneSimService

if __name__ == "__main__":
    # 1. 初始化模拟服务
    sim_service = DroneSimService(
        protect_zone=1000,
        kill_zone=200,
        total_time=60  # 模拟60秒，每秒推送一次数据
    )

    # 2. 初始化数据接收与渲染服务
    data_receiver = DroneDataReceiver(sim_service)

    # 3. 启动模拟服务（后台线程）
    sim_service.start_service()

    # 4. 启动实时渲染（阻塞，直到图表关闭）
    try:
        data_receiver.start_rendering()
    finally:
        # 确保模拟服务正常停止
        sim_service.stop_service()