from dynamic_calculate.unmanned_aerial_vehicle.websocket.DataBuffer import DataBuffer
from dynamic_calculate.unmanned_aerial_vehicle.websocket.DronePlotter import DronePlotter
from dynamic_calculate.unmanned_aerial_vehicle.websocket.DroneWebSocketClient import DroneWebSocketClient

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