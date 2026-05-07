use serde::Serialize;

#[derive(Clone, Debug, Serialize)]
pub struct Version {
    pub version: String,
    pub author: String,
    pub date: String,
    pub description: String,
    pub copyright: String,
    pub license: String,
    pub website: String,
    pub qq_email: String,
    pub google_email: String,
}

impl Version {
    pub fn new() -> Self {
        Self {
            version: "1.0.0".to_string(),
            author: "Cnkrru".to_string(),
            date: "2026-04-08".to_string(),
            description: "串口工具".to_string(),
            copyright: "Copyright (c) 2026 Cnkrru".to_string(),
            license: "MIT License".to_string(),
            website: "https://github.com/Cnkrru".to_string(),
            qq_email: "3253884026@qq.com".to_string(),
            google_email: "j19323850@gmail.com".to_string(),
        }
    }
}
