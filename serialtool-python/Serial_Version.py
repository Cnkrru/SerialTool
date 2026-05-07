
class Serial_Version:
    def __init__(self):
        self.Version='1.0.0'
        self.Author='Cnkrru'
        self.Date='2026-04-08'
        self.Description='串口工具'
        self.Copyright='Copyright (c) 2026 Cnkrru'
        self.License='MIT License'
        self.Website='https://github.com/Cnkrru'
        self.QQEmail='3253884026@qq.com'
        self.GoogleEmail='j19323850@gmail.com'

    def print_version(self):
        print(f"版本: {self.Version}")
        print(f"作者: {self.Author}")
        print(f"日期: {self.Date}")
        print(f"描述: {self.Description}")
        print(f"版权: {self.Copyright}")
        print(f"协议: {self.License}")
        print(f"网站: {self.Website}")
        print(f"QQ邮箱: {self.QQEmail}")
        print(f"Google邮箱: {self.GoogleEmail}")
