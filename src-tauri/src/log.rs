use chrono::Local;
use log::{LevelFilter, info, error, warn, debug};
use once_cell::sync::OnceCell;
use std::fs;
use std::path::Path;

pub struct Logger;

static LOGGER_INSTANCE: OnceCell<Logger> = OnceCell::new();

impl Logger {
    pub fn get_instance() -> &'static Self {
        LOGGER_INSTANCE.get_or_init(|| {
            Self::init_logger();
            Logger
        })
    }

    fn init_logger() {
        let log_dir = Path::new("logs");
        if !log_dir.exists() {
            fs::create_dir_all(log_dir).unwrap();
        }
        let log_file = log_dir.join(format!(
            "serial_{}.log",
            Local::now().format("%Y%m%d")
        ));
        let logger_config = fern::Dispatch::new()
            .format(move |out, message, record| {
                out.finish(format_args!(
                    "[{}] [{}] {}",
                    Local::now().format("%Y-%m-%d %H:%M:%S"),
                    record.level(),
                    message
                ))
            })
            .level(LevelFilter::Debug)
            .chain(fern::log_file(log_file).unwrap())
            .chain(std::io::stdout());

        logger_config.apply().unwrap();
    }

    pub fn info(&self, msg: &str) {
        info!("{}", msg);
    }

    pub fn error(&self, msg: &str) {
        error!("{}", msg);
    }

    pub fn warn(&self, msg: &str) {
        warn!("{}", msg);
    }

    #[allow(dead_code)]
    pub fn debug(&self, msg: &str) {
        debug!("{}", msg);
    }

    #[allow(dead_code)]
    pub fn critical(&self, msg: &str) {
        error!("CRITICAL: {}", msg);
    }
}
