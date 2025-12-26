# drone-risk-assessment-with-unity-websocket
接入unity实时数据的无人机风险评估demo，已与unity方完成联调

unity实时推送下列数据格式的无人机模拟数据，程序即可实时显示风险值。
{
  "type": "position",
  "data": {
    "x": 5000,
    "y": 5000,
    "z": 100,
    "timestamp": 1703318400000
  }
}
