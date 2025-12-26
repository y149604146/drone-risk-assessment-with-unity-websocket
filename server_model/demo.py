import time

from dynamic_calculate.unmanned_aerial_vehicle.server_model.DronHTTPClient import DroneHTTPClient
from dynamic_calculate.unmanned_aerial_vehicle.server_model.DroneHTTPServer import DroneHTTPServer

# ====================== 主程序：启动HTTP服务端+客户端 ======================
if __name__ == "__main__":
    # 1. 启动HTTP服务端
    http_server = DroneHTTPServer(
        protect_zone=1000,
        kill_zone=200
    )
    http_server.start_server()

    # 等待服务端启动完成
    time.sleep(1)

    # 2. 启动HTTP客户端
    http_client = DroneHTTPClient(
        display_window=60  # 固定60秒宽度
    )
    try:
        http_client.start_client()
    finally:
        # 清理资源
        http_client.stop_client()
        http_server.stop_server()
        print("[主程序] 所有服务已停止，程序退出")