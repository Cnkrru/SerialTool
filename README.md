# 串口助手 / Serial Assistant

[中文](#中文) | [English](#english)

---

## 中文

一款基于 **Tauri 2 + Vue 3 + Rust** 开发的跨平台串口调试助手，界面简洁，功能实用。

### 功能特性

- 自动检测系统可用串口
- 支持常用波特率：9600 ~ 921600
- 可配置数据位(5/6/7/8)、校验位(无/奇/偶)、停止位(1/1.5/2)
- 文本/HEX 双模式发送，Enter 快捷发送
- 文本/HEX 双模式接收显示，自动滚动
- 可选追加换行符
- 实时统计：RX/TX 字节数、帧数、速率

### 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + Vite |
| 后端 | Rust + serialport |
| 框架 | Tauri 2 |

### 开发

```bash
# 安装依赖
npm install

# 启动开发环境
npm run tauri dev

# 打包发布
npm run tauri build
```

### 截图

> TODO: 添加截图

### 协议

MIT License

---

## English

A cross-platform serial port debug assistant built with **Tauri 2 + Vue 3 + Rust**. Clean interface, practical features.

### Features

- Auto-detect available serial ports
- Common baud rates: 9600 ~ 921600
- Configurable data bits (5/6/7/8), parity (None/Odd/Even), stop bits (1/1.5/2)
- Text / HEX dual-mode sending with Enter shortcut
- Text / HEX dual-mode display with auto-scroll
- Optional newline append
- Real-time statistics: RX/TX bytes, frames, transfer rate

### Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Vue 3 + TypeScript + Vite |
| Backend | Rust + serialport |
| Framework | Tauri 2 |

### Development

```bash
# Install dependencies
npm install

# Start dev environment
npm run tauri dev

# Build for release
npm run tauri build
```

### Screenshot

> TODO: add screenshot

### License

MIT License
