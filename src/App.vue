<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from "vue";
import { invoke } from "@tauri-apps/api/core";

interface PortInfo {
  device: string;
  name: string;
  description: string;
}

interface SerialStatus {
  port: string | null;
  is_open: boolean;
  baudrate: number;
  bytesize: number;
  parity: string;
  stopbits: string;
  timeout: number;
  thread_running: boolean;
  rx_bytes: number;
  tx_bytes: number;
  rx_count: number;
  tx_count: number;
  rx_rate: number;
  tx_rate: number;
}

interface Version {
  version: string;
  author: string;
  description: string;
}

const ports = ref<PortInfo[]>([]);
const selectedPort = ref("");
const baudrate = ref(9600);
const bytesize = ref(8);
const parity = ref("无");
const stopbits = ref("1");
const timeout = ref(1.0);

const baudrateOptions = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600];
const bytesizeOptions = [5, 6, 7, 8];
const parityOptions = ["无", "奇", "偶"];
const stopbitsOptions = ["1", "1.5", "2"];

const isOpen = ref(false);
const status = ref<SerialStatus>({
  port: null,
  is_open: false,
  baudrate: 9600,
  bytesize: 8,
  parity: "无",
  stopbits: "1",
  timeout: 1.0,
  thread_running: false,
  rx_bytes: 0,
  tx_bytes: 0,
  rx_count: 0,
  tx_count: 0,
  rx_rate: 0,
  tx_rate: 0,
});

const sendText = ref("");
const isHexSend = ref(false);
const appendNewline = ref(true);

const receiveText = ref("");
const receiveHex = ref("");
const isHexDisplay = ref(false);

const appVersion = ref<Version | null>(null);
const errorMsg = ref("");
const successMsg = ref("");

let pollTimer: ReturnType<typeof setInterval> | null = null;
const receiveArea = ref<HTMLTextAreaElement | null>(null);

async function loadPorts() {
  try {
    ports.value = await invoke<PortInfo[]>("get_port_list");
  } catch (e) {
    errorMsg.value = "获取串口列表失败: " + e;
  }
}

async function openPort() {
  if (!selectedPort.value) {
    errorMsg.value = "请先选择串口";
    return;
  }
  try {
    errorMsg.value = "";
    successMsg.value = "";
    await invoke("open_port", {
      port: selectedPort.value,
      baudrate: baudrate.value,
      bytesize: bytesize.value,
      parity: parity.value,
      stopbits: stopbits.value,
      timeout: timeout.value,
    });
    isOpen.value = true;
    successMsg.value = `串口 ${selectedPort.value} 已打开`;
    startPolling();
  } catch (e) {
    errorMsg.value = "打开串口失败: " + e;
    isOpen.value = false;
  }
}

async function closePort() {
  try {
    await invoke("close_port");
    isOpen.value = false;
    successMsg.value = "串口已关闭";
    stopPolling();
  } catch (e) {
    errorMsg.value = "关闭串口失败: " + e;
  }
}

async function sendData() {
  if (!sendText.value.trim() && !isHexSend.value) return;
  try {
    errorMsg.value = "";
    await invoke("send_data", {
      data: sendText.value,
      isHex: isHexSend.value,
      appendNewline: appendNewline.value,
    });
    if (!isHexSend.value || !appendNewline.value) {
      sendText.value = "";
    }
  } catch (e) {
    errorMsg.value = "发送失败: " + e;
  }
}

async function pollReceive() {
  try {
    const data = await invoke<number[]>("get_received_data");
    if (data && data.length > 0) {
      const bytes = new Uint8Array(data);
      const hexStr = Array.from(bytes)
        .map((b) => b.toString(16).padStart(2, "0").toUpperCase())
        .join(" ");
      receiveHex.value += (receiveHex.value ? " " : "") + hexStr;

      const decoder = new TextDecoder("gbk");
      let text: string;
      try {
        text = decoder.decode(bytes);
      } catch {
        text = new TextDecoder("utf-8").decode(bytes);
      }
      receiveText.value += text;

      await nextTick();
      if (receiveArea.value) {
        receiveArea.value.scrollTop = receiveArea.value.scrollHeight;
      }
    }

    const s = await invoke<SerialStatus>("get_status");
    status.value = s;
  } catch {
    // 静默处理轮询错误
  }
}

function startPolling() {
  stopPolling();
  pollTimer = setInterval(pollReceive, 50);
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

function clearReceive() {
  receiveText.value = "";
  receiveHex.value = "";
}

function refreshPorts() {
  loadPorts();
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(2) + " MB";
}

function formatRate(rate: number): string {
  if (rate < 1024) return rate.toFixed(1) + " B/s";
  return (rate / 1024).toFixed(1) + " KB/s";
}

onMounted(async () => {
  await loadPorts();
  try {
    appVersion.value = await invoke<Version>("get_version");
  } catch {
    // 忽略版本获取错误
  }
});

onUnmounted(() => {
  stopPolling();
});
</script>

<template>
  <div class="app">
    <header class="header">
      <div class="header-left">
        <span class="header-icon">⚡</span>
        <h1>串口助手</h1>
        <span v-if="appVersion" class="version">v{{ appVersion.version }}</span>
      </div>
      <div class="header-right">
        <span :class="['status-dot', isOpen ? 'connected' : 'disconnected']"></span>
        <span class="status-text">{{ isOpen ? '已连接' : '未连接' }}</span>
      </div>
    </header>

    <div v-if="errorMsg" class="toast toast-error" @click="errorMsg = ''">
      {{ errorMsg }}
    </div>
    <div v-if="successMsg" class="toast toast-success" @click="successMsg = ''">
      {{ successMsg }}
    </div>

    <div class="config-panel">
      <div class="config-row">
        <div class="config-item">
          <label>端口</label>
          <select v-model="selectedPort" :disabled="isOpen">
            <option value="" disabled>选择串口...</option>
            <option v-for="p in ports" :key="p.device" :value="p.device">
              {{ p.device }} - {{ p.description }}
            </option>
          </select>
        </div>
        <div class="config-item">
          <label>波特率</label>
          <select v-model="baudrate" :disabled="isOpen">
            <option v-for="b in baudrateOptions" :key="b" :value="b">{{ b }}</option>
          </select>
        </div>
        <div class="config-item">
          <label>数据位</label>
          <select v-model="bytesize" :disabled="isOpen">
            <option v-for="b in bytesizeOptions" :key="b" :value="b">{{ b }}</option>
          </select>
        </div>
        <div class="config-item">
          <label>校验位</label>
          <select v-model="parity" :disabled="isOpen">
            <option v-for="p in parityOptions" :key="p" :value="p">{{ p }}</option>
          </select>
        </div>
        <div class="config-item">
          <label>停止位</label>
          <select v-model="stopbits" :disabled="isOpen">
            <option v-for="s in stopbitsOptions" :key="s" :value="s">{{ s }}</option>
          </select>
        </div>
        <div class="config-item config-timeout">
          <label>超时(s)</label>
          <input
            type="number"
            v-model.number="timeout"
            :disabled="isOpen"
            min="0.1"
            max="10"
            step="0.1"
          />
        </div>
      </div>
      <div class="config-actions">
        <button
          v-if="!isOpen"
          class="btn btn-open"
          @click="openPort"
          :disabled="!selectedPort"
        >
          打开串口
        </button>
        <button v-else class="btn btn-close" @click="closePort">关闭串口</button>
        <button class="btn btn-refresh" @click="refreshPorts">刷新</button>
      </div>
    </div>

    <div class="main-area">
      <div class="panel panel-send">
        <div class="panel-header">
          <h2>发送区</h2>
          <div class="panel-controls">
            <label class="checkbox-label">
              <input type="checkbox" v-model="isHexSend" />
              HEX发送
            </label>
            <label class="checkbox-label" v-if="!isHexSend">
              <input type="checkbox" v-model="appendNewline" />
              追加换行
            </label>
          </div>
        </div>
        <textarea
          v-model="sendText"
          class="send-input"
          :placeholder="isHexSend ? '输入HEX数据，如: AA BB 0D 1A' : '输入要发送的文本...'"
          @keydown.enter.exact.prevent="sendData"
        ></textarea>
        <button class="btn btn-send" @click="sendData" :disabled="!isOpen">
          发送 (Enter)
        </button>
      </div>

      <div class="panel panel-receive">
        <div class="panel-header">
          <h2>接收区</h2>
          <div class="panel-controls">
            <label class="checkbox-label">
              <input type="checkbox" v-model="isHexDisplay" />
              HEX显示
            </label>
            <button class="btn btn-clear" @click="clearReceive">清空</button>
          </div>
        </div>
        <textarea
          ref="receiveArea"
          class="receive-area"
          readonly
          :value="isHexDisplay ? receiveHex : receiveText"
          placeholder="等待接收数据..."
        ></textarea>
      </div>
    </div>

    <footer class="status-bar">
      <div class="status-item">
        <span class="status-label">端口</span>
        <span class="status-value">{{ isOpen ? selectedPort : '-' }}</span>
      </div>
      <div class="status-item">
        <span class="status-label">配置</span>
        <span class="status-value">
          {{ isOpen ? `${baudrate},${bytesize}${parity === '无' ? 'N' : parity === '奇' ? 'O' : 'E'}${stopbits}` : '-' }}
        </span>
      </div>
      <div class="status-item">
        <span class="status-label">接收</span>
        <span class="status-value">{{ formatBytes(status.rx_bytes) }} ({{ status.rx_count }}帧)</span>
      </div>
      <div class="status-item">
        <span class="status-label">发送</span>
        <span class="status-value">{{ formatBytes(status.tx_bytes) }} ({{ status.tx_count }}帧)</span>
      </div>
      <div class="status-item">
        <span class="status-label">速率</span>
        <span class="status-value">
          RX:{{ formatRate(status.rx_rate) }} TX:{{ formatRate(status.tx_rate) }}
        </span>
      </div>
    </footer>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

:root {
  --bg: #f0f2f5;
  --card-bg: #ffffff;
  --border: #e4e7ed;
  --text: #303133;
  --text-secondary: #909399;
  --primary: #409eff;
  --success: #67c23a;
  --danger: #f56c6c;
  --warning: #e6a23c;
  --radius: 6px;
  --shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  font-size: 13px;
  overflow: hidden;
  user-select: none;
}
</style>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  color: #fff;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-icon {
  font-size: 18px;
}

.header h1 {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.version {
  color: #a0aec0;
  font-size: 11px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.status-dot.connected {
  background: #4ade80;
  box-shadow: 0 0 6px rgba(74, 222, 128, 0.5);
  animation: pulse 2s infinite;
}

.status-dot.disconnected {
  background: #94a3b8;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-text {
  font-size: 12px;
  color: #cbd5e1;
}

.toast {
  position: fixed;
  top: 48px;
  left: 50%;
  transform: translateX(-50%);
  padding: 8px 20px;
  border-radius: var(--radius);
  font-size: 13px;
  z-index: 1000;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.toast-error {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
}

.toast-success {
  background: #f0fdf4;
  color: #16a34a;
  border: 1px solid #bbf7d0;
}

.config-panel {
  background: var(--card-bg);
  border-bottom: 1px solid var(--border);
  padding: 10px 16px;
  flex-shrink: 0;
  box-shadow: var(--shadow);
}

.config-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: flex-end;
}

.config-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.config-item label {
  font-size: 11px;
  color: var(--text-secondary);
  font-weight: 500;
}

.config-item select,
.config-item input {
  height: 30px;
  padding: 0 8px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 12px;
  font-family: inherit;
  color: var(--text);
  background: #fff;
  outline: none;
  transition: border-color 0.2s;
  min-width: 100px;
}

.config-item select:focus,
.config-item input:focus {
  border-color: var(--primary);
}

.config-item select:disabled,
.config-item input:disabled {
  background: #f5f7fa;
  color: #c0c4cc;
  cursor: not-allowed;
}

.config-timeout input {
  width: 80px;
}

.config-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.btn {
  padding: 6px 16px;
  border: 1px solid transparent;
  border-radius: var(--radius);
  font-size: 12px;
  font-family: inherit;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  outline: none;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-open {
  background: var(--success);
  color: #fff;
}

.btn-open:hover:not(:disabled) {
  background: #5daf34;
}

.btn-close {
  background: var(--danger);
  color: #fff;
}

.btn-close:hover {
  background: #e04a4a;
}

.btn-refresh {
  background: #fff;
  color: var(--text);
  border-color: var(--border);
}

.btn-refresh:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.main-area {
  display: flex;
  flex: 1;
  gap: 1px;
  background: var(--border);
  overflow: hidden;
}

.panel {
  flex: 1;
  background: var(--card-bg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-send {
  flex: 0 0 40%;
  min-width: 280px;
}

.panel-receive {
  flex: 1;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.panel-header h2 {
  font-size: 13px;
  font-weight: 600;
}

.panel-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  cursor: pointer;
}

.send-input {
  flex: 1;
  border: none;
  resize: none;
  padding: 10px 12px;
  font-size: 13px;
  font-family: "Consolas", "Courier New", monospace;
  color: var(--text);
  background: #fafbfc;
  outline: none;
  line-height: 1.5;
}

.send-input::placeholder {
  color: #c0c4cc;
}

.btn-send {
  margin: 8px 12px;
  background: var(--primary);
  color: #fff;
  align-self: flex-start;
}

.btn-send:hover:not(:disabled) {
  background: #66b1ff;
}

.receive-area {
  flex: 1;
  border: none;
  resize: none;
  padding: 10px 12px;
  font-size: 13px;
  font-family: "Consolas", "Courier New", monospace;
  color: var(--text);
  background: #fafbfc;
  outline: none;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

.receive-area::placeholder {
  color: #c0c4cc;
}

.btn-clear {
  background: #fff;
  color: var(--text-secondary);
  border-color: var(--border);
  padding: 3px 10px;
  font-size: 11px;
}

.btn-clear:hover {
  color: var(--danger);
  border-color: var(--danger);
}

.status-bar {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 5px 16px;
  background: var(--card-bg);
  border-top: 1px solid var(--border);
  flex-shrink: 0;
  font-size: 11px;
  color: var(--text-secondary);
}

.status-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.status-label {
  font-weight: 500;
}

.status-value {
  color: var(--text);
  font-family: "Consolas", "Courier New", monospace;
}
</style>
