use serde::{Deserialize, Serialize};
use serialport::{DataBits, Parity, StopBits, SerialPort};
use std::io::{Read, Write};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PortInfo {
    pub device: String,
    pub name: String,
    pub description: String,
    pub hwid: String,
    pub vid: Option<u16>,
    pub pid: Option<u16>,
    pub serial_number: Option<String>,
    pub location: Option<String>,
    pub manufacturer: Option<String>,
    pub product: Option<String>,
    pub interface: Option<String>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct SerialStatus {
    pub port: Option<String>,
    pub is_open: bool,
    pub baudrate: u32,
    pub bytesize: u8,
    pub parity: String,
    pub stopbits: String,
    pub timeout: f64,
    pub thread_running: bool,
    pub rx_bytes: usize,
    pub tx_bytes: usize,
    pub rx_count: usize,
    pub tx_count: usize,
    pub rx_rate: f64,
    pub tx_rate: f64,
}

pub struct SerialPortManager {
    serial: Arc<Mutex<Option<Box<dyn SerialPort>>>>,
    serial_port: Arc<Mutex<Option<String>>>,
    serial_baudrate: Arc<Mutex<u32>>,
    serial_bytesize: Arc<Mutex<DataBits>>,
    serial_parity: Arc<Mutex<Parity>>,
    serial_stopbits: Arc<Mutex<StopBits>>,
    serial_timeout: Arc<Mutex<Duration>>,

    #[allow(dead_code)]
    decode_mode: Arc<Mutex<String>>,
    #[allow(dead_code)]
    max_data_num: Arc<Mutex<usize>>,

    rx_queue: Arc<Mutex<Vec<Vec<u8>>>>,
    tx_queue: Arc<Mutex<Vec<Vec<u8>>>>,

    thread_running: Arc<Mutex<bool>>,
    rx_bytes: Arc<Mutex<usize>>,
    tx_bytes: Arc<Mutex<usize>>,
    rx_count: Arc<Mutex<usize>>,
    tx_count: Arc<Mutex<usize>>,
    last_rx_time: Arc<Mutex<Option<Instant>>>,
    last_tx_time: Arc<Mutex<Option<Instant>>>,
    rx_rate: Arc<Mutex<f64>>,
    tx_rate: Arc<Mutex<f64>>,

    #[allow(dead_code)]
    callbacks: Arc<Mutex<Vec<Box<dyn Fn(SerialStatus) + Send>>>>,
}

impl SerialPortManager {
    pub fn new() -> Self {
        Self {
            serial: Arc::new(Mutex::new(None)),
            serial_port: Arc::new(Mutex::new(None)),
            serial_baudrate: Arc::new(Mutex::new(9600)),
            serial_bytesize: Arc::new(Mutex::new(DataBits::Eight)),
            serial_parity: Arc::new(Mutex::new(Parity::None)),
            serial_stopbits: Arc::new(Mutex::new(StopBits::One)),
            serial_timeout: Arc::new(Mutex::new(Duration::from_secs(1))),

            decode_mode: Arc::new(Mutex::new("utf-8".to_string())),
            max_data_num: Arc::new(Mutex::new(2000)),

            rx_queue: Arc::new(Mutex::new(Vec::new())),
            tx_queue: Arc::new(Mutex::new(Vec::new())),

            thread_running: Arc::new(Mutex::new(false)),
            rx_bytes: Arc::new(Mutex::new(0)),
            tx_bytes: Arc::new(Mutex::new(0)),
            rx_count: Arc::new(Mutex::new(0)),
            tx_count: Arc::new(Mutex::new(0)),
            last_rx_time: Arc::new(Mutex::new(None)),
            last_tx_time: Arc::new(Mutex::new(None)),
            rx_rate: Arc::new(Mutex::new(0.0)),
            tx_rate: Arc::new(Mutex::new(0.0)),

            callbacks: Arc::new(Mutex::new(Vec::new())),
        }
    }

    pub fn open_port(&self) -> bool {
        let port_name = self.serial_port.lock().unwrap().clone();
        if port_name.is_none() {
            return false;
        }

        let serial = self.serial.lock().unwrap();
        if serial.is_none() {
            return false;
        }
        true
    }

    pub fn close_port(&self) -> bool {
        let mut serial = self.serial.lock().unwrap();
        if serial.is_some() {
            *serial = None;
        }
        true
    }

    pub fn check_serial_state(&self) -> bool {
        let serial = self.serial.lock().unwrap();
        serial.is_some()
    }

    pub fn port_init(&self) -> bool {
        let port_name = self.serial_port.lock().unwrap().clone();
        if port_name.is_none() {
            return false;
        }

        let baudrate = *self.serial_baudrate.lock().unwrap();
        let bytesize = *self.serial_bytesize.lock().unwrap();
        let parity = *self.serial_parity.lock().unwrap();
        let stopbits = *self.serial_stopbits.lock().unwrap();
        let timeout = *self.serial_timeout.lock().unwrap();

        match serialport::new(port_name.clone().unwrap(), baudrate)
            .data_bits(bytesize)
            .parity(parity)
            .stop_bits(stopbits)
            .timeout(timeout)
            .open()
        {
            Ok(port) => {
                let mut serial = self.serial.lock().unwrap();
                *serial = Some(port);
                true
            }
            Err(_) => false,
        }
    }

    pub fn get_port_list(&self) -> Vec<PortInfo> {
        let mut ports = Vec::new();
        match serialport::available_ports() {
            Ok(available_ports) => {
                for port in available_ports {
                    let info = PortInfo {
                        device: port.port_name.clone(),
                        name: port.port_name.clone(),
                        description: format!("{:?}", port.port_type),
                        hwid: String::new(),
                        vid: None,
                        pid: None,
                        serial_number: None,
                        location: None,
                        manufacturer: None,
                        product: None,
                        interface: None,
                    };
                    ports.push(info);
                }
            }
            Err(_) => {}
        }
        ports
    }

    pub fn set_port(&self, temp_port: &str) -> bool {
        let ports = self.get_port_list();
        for port in &ports {
            if port.device == temp_port {
                let mut serial_port = self.serial_port.lock().unwrap();
                *serial_port = Some(temp_port.to_string());
                return true;
            }
        }
        false
    }

    pub fn set_baud_rate_inner(&self, temp_baudrate: u32) -> bool {
        let mut baudrate = self.serial_baudrate.lock().unwrap();
        *baudrate = temp_baudrate;
        true
    }

    pub fn set_bytesize_inner(&self, temp_bytesize: u8) -> bool {
        let bytesize = match temp_bytesize {
            5 => DataBits::Five,
            6 => DataBits::Six,
            7 => DataBits::Seven,
            8 => DataBits::Eight,
            _ => return false,
        };

        let mut serial_bytesize = self.serial_bytesize.lock().unwrap();
        *serial_bytesize = bytesize;
        true
    }

    pub fn set_parity_inner(&self, temp_parity: &str) -> bool {
        let parity = match temp_parity {
            "无" => Parity::None,
            "奇" => Parity::Odd,
            "偶" => Parity::Even,
            _ => return false,
        };

        let mut serial_parity = self.serial_parity.lock().unwrap();
        *serial_parity = parity;
        true
    }

    pub fn set_stopbits_inner(&self, temp_stopbits: &str) -> bool {
        let stopbits = match temp_stopbits {
            "1" => StopBits::One,
            "1.5" => StopBits::Two,
            "2" => StopBits::Two,
            _ => return false,
        };

        let mut serial_stopbits = self.serial_stopbits.lock().unwrap();
        *serial_stopbits = stopbits;
        true
    }

    pub fn set_timeout_inner(&self, temp_timeout: f64) -> bool {
        let mut timeout = self.serial_timeout.lock().unwrap();
        *timeout = Duration::from_secs_f64(temp_timeout);
        true
    }

    pub fn start_thread(&self) -> bool {
        let mut running = self.thread_running.lock().unwrap();
        if *running {
            return false;
        }
        *running = true;
        drop(running);

        let serial = Arc::clone(&self.serial);
        let thread_running = Arc::clone(&self.thread_running);
        let rx_queue = Arc::clone(&self.rx_queue);
        let tx_queue = Arc::clone(&self.tx_queue);
        let rx_bytes = Arc::clone(&self.rx_bytes);
        let tx_bytes = Arc::clone(&self.tx_bytes);
        let rx_count = Arc::clone(&self.rx_count);
        let tx_count = Arc::clone(&self.tx_count);
        let last_rx_time = Arc::clone(&self.last_rx_time);
        let last_tx_time = Arc::clone(&self.last_tx_time);
        let rx_rate = Arc::clone(&self.rx_rate);
        let tx_rate = Arc::clone(&self.tx_rate);

        thread::spawn(move || {
            let mut buffer = vec![0u8; 1024];
            loop {
                let running = *thread_running.lock().unwrap();
                if !running {
                    break;
                }

                let mut serial_guard = serial.lock().unwrap();
                if let Some(ref mut port) = *serial_guard {
                    match port.bytes_to_read() {
                        Ok(available) if available > 0 => {
                            let read_size = std::cmp::min(available as usize, buffer.len());
                            match port.read(&mut buffer[..read_size]) {
                                Ok(n) if n > 0 => {
                                    let data = buffer[..n].to_vec();
                                    let mut queue = rx_queue.lock().unwrap();
                                    if queue.len() < 2000 {
                                        queue.push(data);
                                    }
                                    drop(queue);

                                    let mut rx_b = rx_bytes.lock().unwrap();
                                    *rx_b += n;
                                    drop(rx_b);

                                    let mut rx_c = rx_count.lock().unwrap();
                                    *rx_c += 1;
                                    drop(rx_c);

                                    let now = Instant::now();
                                    let mut last_rx = last_rx_time.lock().unwrap();
                                    if let Some(last) = *last_rx {
                                        let duration = now.duration_since(last).as_secs_f64();
                                        if duration > 0.0 {
                                            let mut rate = rx_rate.lock().unwrap();
                                            *rate = (*rate * 0.7) + ((n as f64 / duration) * 0.3);
                                        }
                                    }
                                    *last_rx = Some(now);
                                }
                                _ => {}
                            }
                        }
                        _ => {}
                    }

                    let mut tx_queue_guard = tx_queue.lock().unwrap();
                    if !tx_queue_guard.is_empty() {
                        let data = tx_queue_guard.remove(0);
                        drop(tx_queue_guard);

                        match port.write_all(&data) {
                            Ok(_) => {
                                let mut tx_b = tx_bytes.lock().unwrap();
                                *tx_b += data.len();
                                drop(tx_b);

                                let mut tx_c = tx_count.lock().unwrap();
                                *tx_c += 1;
                                drop(tx_c);

                                let now = Instant::now();
                                let mut last_tx = last_tx_time.lock().unwrap();
                                if let Some(last) = *last_tx {
                                    let duration = now.duration_since(last).as_secs_f64();
                                    if duration > 0.0 {
                                        let mut rate = tx_rate.lock().unwrap();
                                        *rate = (*rate * 0.7) + ((data.len() as f64 / duration) * 0.3);
                                    }
                                }
                                *last_tx = Some(now);
                            }
                            Err(_) => {}
                        }
                    }
                }
                drop(serial_guard);

                thread::sleep(Duration::from_millis(10));
            }
        });

        true
    }

    pub fn stop_thread(&self) -> bool {
        let mut running = self.thread_running.lock().unwrap();
        *running = false;
        true
    }

    pub fn send_data(&self, data: Vec<u8>) -> bool {
        if data.is_empty() {
            return false;
        }
        let mut queue = self.tx_queue.lock().unwrap();
        if queue.len() < 2000 {
            queue.push(data);
            true
        } else {
            false
        }
    }

    pub fn drain_rx_queue(&self) -> Vec<u8> {
        let mut queue = self.rx_queue.lock().unwrap();
        let mut result = Vec::new();
        while !queue.is_empty() {
            result.extend(queue.remove(0));
        }
        result
    }

    pub fn get_status(&self) -> SerialStatus {
        let port = self.serial_port.lock().unwrap().clone();
        let is_open = self.check_serial_state();
        let baudrate = *self.serial_baudrate.lock().unwrap();
        let bytesize = match *self.serial_bytesize.lock().unwrap() {
            DataBits::Five => 5,
            DataBits::Six => 6,
            DataBits::Seven => 7,
            DataBits::Eight => 8,
        };
        let parity = match *self.serial_parity.lock().unwrap() {
            Parity::None => "无".to_string(),
            Parity::Odd => "奇".to_string(),
            Parity::Even => "偶".to_string(),
        };
        let stopbits = match *self.serial_stopbits.lock().unwrap() {
            StopBits::One => "1".to_string(),
            StopBits::Two => "2".to_string(),
        };
        let timeout = self.serial_timeout.lock().unwrap().as_secs_f64();
        let thread_running = *self.thread_running.lock().unwrap();
        let rx_bytes = *self.rx_bytes.lock().unwrap();
        let tx_bytes = *self.tx_bytes.lock().unwrap();
        let rx_count = *self.rx_count.lock().unwrap();
        let tx_count = *self.tx_count.lock().unwrap();
        let rx_rate = *self.rx_rate.lock().unwrap();
        let tx_rate = *self.tx_rate.lock().unwrap();

        SerialStatus {
            port,
            is_open,
            baudrate,
            bytesize,
            parity,
            stopbits,
            timeout,
            thread_running,
            rx_bytes,
            tx_bytes,
            rx_count,
            tx_count,
            rx_rate,
            tx_rate,
        }
    }
}
