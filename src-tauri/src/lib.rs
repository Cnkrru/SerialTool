mod serial;
mod version;

use serial::SerialPortManager;
use std::sync::Mutex;

#[tauri::command]
fn get_port_list(state: tauri::State<'_, Mutex<SerialPortManager>>) -> Vec<serial::PortInfo> {
    let manager = state.lock().unwrap();
    manager.get_port_list()
}

#[tauri::command]
fn open_port(
    state: tauri::State<'_, Mutex<SerialPortManager>>,
    port: String,
    baudrate: u32,
    bytesize: u8,
    parity: String,
    stopbits: String,
    timeout: f64,
) -> Result<bool, String> {
    let manager = state.lock().unwrap();

    if !manager.set_port(&port) {
        return Err(format!("串口 {} 不存在", port));
    }

    manager.set_baud_rate_inner(baudrate);
    manager.set_bytesize_inner(bytesize);
    manager.set_parity_inner(&parity);
    manager.set_stopbits_inner(&stopbits);
    manager.set_timeout_inner(timeout);

    if !manager.port_init() {
        return Err("串口初始化失败".to_string());
    }

    if !manager.open_port() {
        return Err("串口打开失败".to_string());
    }

    manager.start_thread();

    Ok(true)
}

#[tauri::command]
fn close_port(state: tauri::State<'_, Mutex<SerialPortManager>>) -> bool {
    let manager = state.lock().unwrap();
    manager.stop_thread();
    std::thread::sleep(std::time::Duration::from_millis(100));
    manager.close_port()
}

#[tauri::command]
fn send_data(
    state: tauri::State<'_, Mutex<SerialPortManager>>,
    data: String,
    is_hex: bool,
    append_newline: bool,
) -> Result<bool, String> {
    let manager = state.lock().unwrap();

    if !manager.check_serial_state() {
        return Err("串口未打开".to_string());
    }

    let mut bytes = if is_hex {
        let hex_str = data.replace(" ", "").replace("\n", "").replace("\r", "");
        if hex_str.len() % 2 != 0 {
            return Err("HEX数据长度必须为偶数".to_string());
        }
        let mut result = Vec::new();
        for i in (0..hex_str.len()).step_by(2) {
            match u8::from_str_radix(&hex_str[i..i + 2], 16) {
                Ok(b) => result.push(b),
                Err(_) => return Err(format!("无效的HEX字符: {}", &hex_str[i..i + 2])),
            }
        }
        result
    } else {
        let mut text = data;
        if append_newline {
            text.push_str("\r\n");
        }
        text.as_bytes().to_vec()
    };

    if append_newline && is_hex {
        bytes.extend_from_slice(b"\r\n");
    }

    if bytes.is_empty() {
        return Ok(false);
    }

    Ok(manager.send_data(bytes))
}

#[tauri::command]
fn get_received_data(state: tauri::State<'_, Mutex<SerialPortManager>>) -> Vec<u8> {
    let manager = state.lock().unwrap();
    manager.drain_rx_queue()
}

#[tauri::command]
fn get_status(state: tauri::State<'_, Mutex<SerialPortManager>>) -> serial::SerialStatus {
    let manager = state.lock().unwrap();
    manager.get_status()
}

#[tauri::command]
fn refresh_ports(state: tauri::State<'_, Mutex<SerialPortManager>>) -> Vec<serial::PortInfo> {
    let manager = state.lock().unwrap();
    manager.get_port_list()
}

#[tauri::command]
fn get_version() -> version::Version {
    version::Version::new()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let serial_manager = Mutex::new(SerialPortManager::new());

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .manage(serial_manager)
        .invoke_handler(tauri::generate_handler![
            get_port_list,
            open_port,
            close_port,
            send_data,
            get_received_data,
            get_status,
            refresh_ports,
            get_version,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
