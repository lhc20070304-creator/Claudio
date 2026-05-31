# Claudio 启动文档

## 一键启动

```bash
cd c:/Users/Lenovo/Desktop/Claudio
bash start.sh
```

## 手动启动

### 1. 网易云音乐 API（端口 3000）

```bash
node node_modules/NeteaseCloudMusicApi/app.js &
```

验证：`curl http://localhost:3000/` 返回 200

### 2. Flask 主服务器（端口 8080）

```bash
python app.py &
```

验证：`curl http://localhost:8080/` 返回 200

## 访问

浏览器打开 **http://localhost:8080**

## 关闭

```bash
# 查找并终止
lsof -ti:3000 | xargs kill
lsof -ti:8080 | xargs kill
```

## 端口说明

| 端口 | 服务 | 作用 |
|------|------|------|
| 3000 | NeteaseCloudMusicApi | 搜索、播放、歌单 |
| 8080 | Flask (app.py) | 前端 + AI 聊天 + WebSocket |
