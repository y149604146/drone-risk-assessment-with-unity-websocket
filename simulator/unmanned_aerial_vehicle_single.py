import math
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.animation as animation
import matplotlib as mpl

# ====================== 解决中文显示问题 ======================
plt.rcParams["font.family"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams['axes.unicode_minus'] = False
mpl.rcParams['font.sans-serif'] = ['SimHei']

# ====================== 核心参数配置 ======================
D1 = 1000  # 防范区边界（米）
D2 = 200  # 击毙区边界（米）
max_risk = 100  # 最高风险值
min_risk = 0  # 最低风险值

# 模拟参数
total_time = 60  # 总模拟时长（秒）
frame_num = 100  # 动画总帧数（对应总时间）
time_interval = 50  # 每帧间隔毫秒（越小动画越快）


# ====================== 核心风险计算函数 ======================
def calculate_drone_risk(distance, distance_change_rate):
    """计算无人机实时风险值"""
    if distance > D1:
        r_base = max_risk * (D1 - distance) / (D1 - D2)
        r_base = max(min_risk, min(max_risk, r_base))
    elif D2 < distance <= D1:
        r_base = 70
    else:
        r_base = max_risk

    # 趋势修正
    if distance_change_rate < 0:
        r_final = r_base * 1.2
    elif distance_change_rate > 0:
        r_final = r_base * 0.8
    else:
        r_final = r_base

    r_final = max(min_risk, min(max_risk, r_final))
    return round(r_final, 2)


# ====================== 模拟无人机飞行轨迹 ======================
def simulate_drone_distance(time):
    """模拟无人机距离和变化率"""
    if time <= total_time / 2:
        # 0-30秒：靠近（1500→800米）
        distance = 1500 - (1500 - 800) * (time / (total_time / 2))
        change_rate = -(1500 - 800) / (total_time / 2)
    else:
        # 30-60秒：远离（800→1500米）
        distance = 800 + (1500 - 800) * ((time - total_time / 2) / (total_time / 2))
        change_rate = (1500 - 800) / (total_time / 2)
    return distance, change_rate


# ====================== 初始化动画数据 ======================
# 生成所有时间点和对应数据
time_points = np.linspace(0, total_time, frame_num)
all_distances = []
all_risk_values = []
all_change_rates = []

for t in time_points:
    d, dr = simulate_drone_distance(t)
    risk = calculate_drone_risk(d, dr)
    all_distances.append(d)
    all_risk_values.append(risk)
    all_change_rates.append(dr)

# ====================== 创建动画画布 ======================
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
fig.suptitle('无人机距离与风险值动态变化', fontsize=16)

# 初始化绘图对象
line1, = ax1.plot([], [], color='blue', linewidth=2, label='无人机距离（米）')
point1, = ax1.plot([], [], 'bo', markersize=8, label='当前位置')  # 实时位置点
line2, = ax2.plot([], [], color='red', linewidth=2, label='风险值（0-100）')
point2, = ax2.plot([], [], 'ro', markersize=8, label='当前风险值')  # 实时风险值点

# 配置子图1（距离）
ax1.set_xlim(0, total_time)
ax1.set_ylim(0, 1600)  # 距离范围0-1600米
ax1.axhline(y=D1, color='orange', linestyle='--', label=f'防范区边界（{D1}米）')
ax1.axhline(y=D2, color='red', linestyle='--', label=f'击毙区边界（{D2}米）')
ax1.set_ylabel('距离（米）')
ax1.grid(True)
ax1.legend(loc='upper right')

# 配置子图2（风险值）
ax2.set_xlim(0, total_time)
ax2.set_ylim(-5, 105)  # 风险值范围-5到105（留出余量）
ax2.axhline(y=70, color='orange', linestyle='--', label='防范区基础风险值')
ax2.axhline(y=100, color='darkred', linestyle='--', label='击毙区风险值')
ax2.set_xlabel('时间（秒）')
ax2.set_ylabel('风险值')
ax2.grid(True)
ax2.legend(loc='upper right')

# 添加实时信息文本框
info_text = fig.text(0.02, 0.02, '', fontsize=12,
                     bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))


# ====================== 动画更新函数 ======================
def update(frame):
    """每帧更新数据"""
    # 获取当前帧的时间和数据
    t = time_points[frame]
    d = all_distances[frame]
    risk = all_risk_values[frame]
    dr = all_change_rates[frame]
    trend = "靠近" if dr < 0 else "远离"

    # 更新线条数据（绘制到当前帧的历史数据）
    line1.set_data(time_points[:frame + 1], all_distances[:frame + 1])
    line2.set_data(time_points[:frame + 1], all_risk_values[:frame + 1])

    # 修复：将单个数值转为列表（序列）
    point1.set_data([t], [d])  # 关键修复：用列表包裹单个值
    point2.set_data([t], [risk])  # 关键修复：用列表包裹单个值

    # 更新信息文本
    info_text.set_text(
        f'时间：{t:.1f}秒\n'
        f'当前距离：{d:.1f}米\n'
        f'移动趋势：{trend}（速率：{dr:.1f}米/秒）\n'
        f'当前风险值：{risk}'
    )

    return line1, point1, line2, point2, info_text


# ====================== 创建并运行动画 ======================
ani = animation.FuncAnimation(
    fig,  # 画布对象
    update,  # 帧更新函数
    frames=frame_num,  # 总帧数
    interval=time_interval,  # 帧间隔（毫秒）
    blit=False,  # 关键修复：关闭blit避免兼容问题
    repeat=False  # 播放一次后停止（设为True则循环播放）
)

plt.tight_layout()
plt.subplots_adjust(bottom=0.15)  # 留出文本框空间
plt.show()