import serial
from serial.tools.list_ports import comports
import concurrent.futures
import queue
import time
from Log import Logger

class Serial:

    def __init__(self):
        #初始化参数
        self.Serial=None
        self.Serial_ports=[]
        self.Serial_port = None
        self.Serial_baudrate = 9600
        self.Serial_bytesize = 8
        self.Serial_parity = serial.PARITY_NONE
        self.Serial_stopbits = serial.STOPBITS_ONE
        self.Serial_timeout = 1

        #一些选项数据
        self.Decode_Mode='utf-8'
        self.Max_Data_Num=2000

        #接收数据
        self.Receive_Data=None
        self.Send_Data=None
        
        #多线程处理
        self.thread_running=False
        self.executor=None
        self.rx_queue=queue.Queue(maxsize=self.Max_Data_Num)
        self.tx_queue=queue.Queue(maxsize=self.Max_Data_Num)

        # 接收数据统计
        self.rx_bytes=0
        self.tx_bytes=0
        self.rx_count=0
        self.tx_count=0
        self.last_rx_time=None
        self.last_tx_time=None
        self.rx_rate=0
        self.tx_rate=0
        self.current_time = time.time()

        #状态管理
        self.status ={
            'serial':
            {
                'port':None,
                'is_open':False,
                'baudrate':None,
                'bytesize':None,
                'parity':None,
                'stopbits':None,
                'timeout':None,
            },
            'thread':
            {
                'is_running':False,
                'start_time':None,
                'update_time':None,
            },
            'queue':
            {
                'rx_size':None,
                'tx_size':None,
                'max_size':None,
            },
            'data':
            {
                'rx_bytes':None,
                'tx_bytes':None,
                'rx_count':None,
                'tx_count':None,
                'rx_rate':None,
                'tx_rate':None,
                'last_rx_time':None,
                'last_tx_time':None,
            },
            'system':
            {
                'timestamp':time.time(),
                'cpu_usage':None,
                'memory_usage':None,
            }
        }

        self.callbacks=[]
        self.last_update_time=time.time()        

        #启用日志
        self.Logger=Logger.get_instance()


##==============================open_close==============================##
    #打开串口
    def open_port(self):
        try:
            if self.Serial_port is None: 
                self.Logger.warning("未配置串口")
                return False
            if self.Serial is None:
                self.Logger.warning("未初始化串口")
                return False
            else:
                self.Serial.open()
            return True
        except serial.SerialException as e:
            self.Logger.error(f"打开串口失败: {e}")
            return False
            
    #关闭串口
    def close_port(self):
        try:
            if self.check_serial_state():
                self.Serial.close()
                self.Logger.info(f"串口已关闭: {self.Serial_port}")
            return True
        except serial.SerialException as e:
            self.Logger.error(f"关闭串口失败: {e}")
            return False
##==============================thread==============================##
    #启动线程
    def start_thread(self):
        try:
            if not self.thread_running:
                self.thread_running=True
                self.executor=concurrent.futures.ThreadPoolExecutor(max_workers=2)
                self.future_receive=self.executor.submit(self.thread_receive)
                self.future_send=self.executor.submit(self.thread_send)
                self.Logger.info(f"线程已启动: {self.Serial_port}")
                return True
        except Exception as e:
            self.Logger.error(f"启动线程失败: {e}")
            return False


            
    #停止线程   
    def stop_thread(self):
        try:
            if self.thread_running:
                self.thread_running=False
            if self.executor:
                self.executor.shutdown(wait=True,cancel_futures=True)
                self.executor=None
                self.Logger.info(f"线程已停止: {self.Serial_port}")
        except Exception as e:
            self.Logger.error(f"停止线程失败: {e}")
            return False

    #获取线程状态
    def get_thread_state(self):
        status={
            'thread_running':self.thread_running,
            'receive_thread':{
                'alive':False,
                'status':'inactive'
            },
            'send_thread':{
                'alive':False,
                'status':'inactive'
            }
        }

        if hasattr(self,'future_receive'):
            status['receive_thread']['alive']=not self.future_receive.done()
            if self.future_receive.done():
                try:
                    self.future_receive.result()
                    status['receive_thread']['status']='success'
                    self.Logger.info(f"接收线程执行成功: {self.Receive_Data}")
                except Exception as e:
                    self.Logger.error(f"接收线程执行失败: {e}")
                status['receive_thread']['status']='error'
            else:    
                status['receive_thread']['status']='running'
                self.Logger.info(f"接收线程执行中: {self.Receive_Data}")

        if hasattr(self,'future_send'):
            status['send_thread']['alive']=not self.future_send.done()
            if self.future_send.done():
                try:
                    self.future_send.result()
                    status['send_thread']['status']='success'
                    self.Logger.info(f"发送线程执行成功: {self.Send_Data}")
                except Exception as e:
                    self.Logger.error(f"发送线程执行失败: {e}")
                status['send_thread']['status']='error'
            else:    
                status['send_thread']['status']='running'
                self.Logger.info(f"发送线程执行中: {self.Send_Data}")
                
        return status
##==============================init==============================##
    #检查串口状态
    def check_serial_state(self):
        if self.Serial is not None and self.Serial.is_open:
            self.Logger.info(f"串口已打开: {self.Serial_port}")
            return True
        else:    
            self.Logger.info(f"串口未打开: {self.Serial_port}")
            return False

    #初始化串口函数    
    def port_init(self):
        #检查是否配置了端口
        if self.Serial_port is None:
            return None
        #如果串口开启了，先关闭它，再尝试初始化新的串口
        if self.check_serial_state():
            self.Serial.close()
        try:
            self.Serial=serial.Serial(
            port=self.Serial_port,
            baudrate=self.Serial_baudrate,
            bytesize=self.Serial_bytesize,
            parity=self.Serial_parity,
            stopbits=self.Serial_stopbits,
            timeout=self.Serial_timeout,)
            self.Logger.info(f"初始化串口成功: {self.Serial_port}")
            return self.Serial
        except serial.SerialException as e:
            self.Logger.error(f"初始化串口失败: {e}")
            return None    

    #获取串口列表
    def get_port_list(self):
        self.Serial_ports=[]
        try:
            Temp_Ports = list(comports())
            for port in Temp_Ports:
                port_info = {
                    'device': port.device,               # 设备名，例如 'COM3' 或 '/dev/ttyUSB0'
                    'name': port.name,                   # 端口名称
                    'description': port.description,     # 描述
                    'hwid': port.hwid,                   # 硬件ID
                    'vid': port.vid,                     # Vendor ID
                    'pid': port.pid,                     # Product ID
                    'serial_number': port.serial_number, # 序列号
                    'location': port.location,           # 位置
                    'manufacturer': port.manufacturer,   # 制造商
                    'product': port.product,             # 产品名称
                    'interface': port.interface          # 接口类型
                }
                self.Serial_ports.append(port_info)
            self.Logger.info(f"获取串口列表成功: {self.Serial_ports}")
            return self.Serial_ports
        except serial.SerialException as e:
            self.Logger.error(f"获取串口列表失败: {e}")
            return self.Serial_ports 

    #设置串口
    def set_port(self,Temp_port):
        Ports=self.get_port_list()
        try:
            for i,port_info in enumerate(Ports):
                if Ports[i]['device']==Temp_port:
                    self.Serial_port = Ports[i]['device']
                    self.port_init()
                    self.Logger.info(f"设置串口成功: {Temp_port}")
                    break
            return True
        except serial.SerialException as e:
            self.Logger.error(f"设置串口失败: {e}")
            return False

    #设置波特率
    def set_baud_rate(self,Temp_baudrate):
        if self.check_serial_state():
            self.port_init()        
        try:
            if Temp_baudrate == 9600:
                self.Serial_baudrate = 9600
            elif Temp_baudrate == 19200:
                self.Serial_baudrate = 19200
            elif Temp_baudrate == 38400:
                self.Serial_baudrate = 38400
            elif Temp_baudrate == 57600:
                self.Serial_baudrate = 57600
            elif Temp_baudrate == 115200:
                self.Serial_baudrate = 115200
            self.port_init()
            self.Logger.info(f"设置波特率成功: {Temp_baudrate}")
            return True
        except serial.SerialException as e:
            self.Logger.error(f"设置波特率失败: {e}")
            return False



    #设置数据大小
    def set_bytesize(self,Temp_bytesize):
        if self.check_serial_state():        
            self.port_init()
        try:
            if Temp_bytesize==5:
                self.Serial_bytesize=serial.FIVEBITS
            elif Temp_bytesize==6:
                self.Serial_bytesize=serial.SIXBITS
            elif Temp_bytesize==7:
                self.Serial_bytesize=serial.SEVENBITS
            elif Temp_bytesize==8:
                self.Serial_bytesize=serial.EIGHTBITS
            self.port_init()
            self.Logger.info(f"设置数据大小成功: {Temp_bytesize}")
            return True
        except serial.SerialException as e:
            self.Logger.error(f"设置数据大小失败: {e}")
            return False

    
    #设置校验位
    def set_parity(self,Temp_parity):
        if self.check_serial_state():        
            self.port_init()
        try:
            if Temp_parity=='无':
                self.Serial_parity=serial.PARITY_NONE
            elif Temp_parity=='奇':
                self.Serial_parity=serial.PARITY_ODD
            elif Temp_parity=='偶':
                self.Serial_parity=serial.PARITY_EVEN
            self.port_init()
            self.Logger.info(f"设置校验位成功: {Temp_parity}")
            return True
        except serial.SerialException as e:
            self.Logger.error(f"设置校验位失败: {e}")  
            return False

    #设置停止位
    def set_stopbits(self,Temp_stopbits):
        if self.check_serial_state():        
            self.port_init()    
        try:
            if Temp_stopbits=='1':
                self.Serial_stopbits=serial.STOPBITS_ONE
            elif Temp_stopbits=='1.5':
                self.Serial_stopbits=serial.STOPBITS_ONE_POINT_FIVE
            elif Temp_stopbits=='2':
                self.Serial_stopbits=serial.STOPBITS_TWO
            self.port_init()
            self.Logger.info(f"设置停止位成功: {Temp_stopbits}")
            return True
        except serial.SerialException as e:
            self.Logger.error(f"设置停止位失败: {e}")
            return False

    #设置超时时间
    def set_timeout(self,Temp_timeout):
        if self.check_serial_state():        
            self.port_init()
        try:
            self.Serial_timeout = float(Temp_timeout)
            self.port_init()
            self.Logger.info(f"设置超时时间成功: {Temp_timeout}")
            return True
        except serial.SerialException as e:
            self.Logger.error(f"设置超时时间失败: {e}")
            return False
##==============================recover==============================##
    #错误恢复机制
    def recover_from_error(self):
        try:
            self.Logger.info("尝试从错误中恢复...")
            # 检查串口状态
            if not self.check_serial_state():
                self.Logger.info("尝试重新打开串口...")
                if self.Serial_port:
                    self.port_init()
                    self.open_port()
            
            # 检查线程状态
            if not self.thread_running and self.executor:
                self.Logger.info("尝试重启线程...")
                self.start_thread()  
            self.Logger.info("错误恢复完成")
        except serial.SerialException as e:
            self.Logger.error(f"错误恢复失败: {e}")

##==============================config==============================##
    #获取当前配置
    def get_port_config(self):
        return {
            'port': self.Serial_port,
            'baudrate': self.Serial_baudrate,
            'bytesize': self.Serial_bytesize,
            'parity': self.Serial_parity,
            'stopbits': self.Serial_stopbits,
            'timeout': self.Serial_timeout
        }

##==============================update_rates==============================##
    #更新速率
    def update_rates(self):
        try:
            if self.last_rx_time is not None and self.current_time - self.last_rx_time > 0:
                self.rx_rate = self.rx_bytes / (self.current_time - self.last_rx_time)
            else:
                self.rx_rate = 0
            if self.last_tx_time is not None and self.current_time - self.last_tx_time > 0:
                self.tx_rate = self.tx_bytes / (self.current_time - self.last_tx_time)
            else:
                self.tx_rate = 0
        except Exception as e:
            self.Logger.error(f"更新速率失败: {e}")
            self.rx_rate = 0
            self.tx_rate = 0

##==============================get==============================##
    #获取接收数据
    def get_receive_data(self):
        try:
            if self.check_serial_state():
                in_waiting=self.Serial.in_waiting
                if in_waiting>0:
                    data=self.Serial.readline().strip()
                    if data:
                        self.rx_queue.put(data)
                        self.rx_bytes += len(data)
                        self.rx_count += 1
                        self.current_time = time.time()
                        self.last_rx_time = self.current_time
                        self.update_rates()
                        self.Receive_Data=data
                        self.Logger.info(f"读取成功: {data}")
                        return True
        except queue.Empty:
            pass
        except serial.SerialException as e:
            self.Logger.error(f"读取失败: {e}")
            return False

    #线程读取接收数据
    def thread_receive(self):
        min_time=0.001
        max_time=0.1
        while self.thread_running:
            try:
                self.get_receive_data()
                queue_size=self.rx_queue.qsize()
                if queue_size>100:
                    sleep_time=min_time
                elif queue_size>10:
                    sleep_time=0.01
                else:
                    sleep_time=max_time
                    time.sleep(sleep_time)
            except serial.SerialException as e:
                self.Logger.error(f"线程读取失败: {e}")
                time.sleep(min_time)
                return False



##==============================convert==============================##
    #转化为二进制（处理传进来的Data，可以是接收值，也可以是发送值）
    def convert_to_bin(self,Data):
        try:
            Bin_Data=[format(i,'08b') for i in Data]
            self.Logger.info(f"转化为为二进制成功: {Bin_Data}")
            return Bin_Data
        except Exception as e:
            self.Logger.error(f"转化为为二进制失败: {e}")
            return None

    #转化为十六进制（处理传进来的Data，可以是接收值，也可以是发送值）
    def convert_to_hex(self,Data):
        try:
            Hex_Data=[format(i,'02x') for i in Data]
            self.Logger.info(f"转化为为十六进制成功: {Hex_Data}")
            return Hex_Data
        except Exception as e:
            self.Logger.error(f"转化为为十六进制失败: {e}")
            return None

    #转化为十进制（处理传进来的Data，可以是接收值，也可以是发送值）
    def convert_to_dec_ascii(self,Data):
        try:
            Dec_ASCII_Data=[i for i in Data]
            self.Logger.info(f"转化为为十进制ASCII成功: {Dec_ASCII_Data}")
            return Dec_ASCII_Data
        except Exception as e:
            self.Logger.error(f"转化为为十进制ASCII失败: {e}")
            return None

    #常见编码格式的解码函数
    #解码utf-8（处理传进来的Data，可以是接收值，也可以是发送值）
    def decode_utf8(self,Data):
        try:
            Data=Data.decode('utf-8')
            self.Logger.info(f"解码utf-8成功: {Data}")
            return Data
        except Exception as e:
            self.Logger.error(f"解码utf-8失败: {e}")
            return None

    def decode_utf16(self,Data):
        try:
            Data=Data.decode('utf-16')
            self.Logger.info(f"解码utf-16成功: {Data}")
            return Data
        except Exception as e:
            self.Logger.error(f"解码utf-16失败: {e}")
            return None

    #解码gbk（处理传进来的Data，可以是接收值，也可以是发送值）
    def decode_gbk(self,Data):
        try:
            Data=Data.decode('gbk')
            self.Logger.info(f"解码gbk成功: {Data}")
            return Data
        except Exception as e:
            self.Logger.error(f"解码gbk失败: {e}")
            return None

    #解码gb3212（处理传进来的Data，可以是接收值，也可以是发送值）
    def decode_gb3212(self,Data):
        try:
            Data=Data.decode('gb3212')
            self.Logger.info(f"解码gb3212成功: {Data}")
            return Data
        except Exception as e:
            self.Logger.error(f"解码gb3212失败: {e}")
            return None

    #解码gb18030（处理传进来的Data，可以是接收值，也可以是发送值）
    def decode_gb18030(self,Data):
        try:
            Data=Data.decode('gb18030')
            self.Logger.info(f"解码gb18030成功: {Data}")
            return Data
        except Exception as e:
            self.Logger.error(f"解码gb18030失败: {e}")
            return None

    #选择解码模式函数(处理传进来的Data，可以是接收值，也可以是发送值,编码格式用全局变量来决定)
    def choose_decode_mode(self,Data):
        try:
            if not isinstance(Data,bytes):
                self.Logger.error("待解码数据不是字节类型")
                return None
            default_decode_mode=['utf-8','utf-16','gbk','gb3212','gb18030']
            if self.Decode_Mode not in default_decode_mode:
                self.Logger.error(f"不支持的编码格式:{self.Decode_Mode}")
                self.Decode_Mode='utf-8'
            if self.Decode_Mode=='utf-8':
                return self.decode_utf8(Data)
            elif self.Decode_Mode=='utf-16':
                return self.decode_utf16(Data)
            elif self.Decode_Mode=='gbk':
                return self.decode_gbk(Data)
            elif self.Decode_Mode=='gb3212':
                return self.decode_gb3212(Data)
            elif self.Decode_Mode=='gb18030':
                return self.decode_gb18030(Data)
        except Exception as e:
            self.Logger.error(f"解码数据失败:{e}")
            return None

##==============================send==============================##
    #获取发送数据并发送（处理传进来的Data）
    def thread_send(self):
        min_time=0.001
        max_time=0.1
        while self.thread_running:
            try:
                if self.check_serial_state() and not self.tx_queue.empty():
                    queue_size=self.tx_queue.qsize()
                    if queue_size>100:
                        sleep_time=min_time
                    elif queue_size>10:
                        sleep_time=0.01
                    else:
                        sleep_time=max_time
                    Data=self.tx_queue.get()
                    self.Serial.write(Data)
                    self.Logger.info(f"发送成功: {Data}")
                    time.sleep(sleep_time)
            except serial.SerialException as e:
                self.Logger.error(f"发送失败: {e}")
            time.sleep(min_time)    

    #设置发送数据
    def send_datas(self):
        try:
            if self.check_serial_state():
                if isinstance(self.Send_Data,str):
                    self.Send_Data=self.Send_Data.encode(self.Decode_Mode)
                self.tx_queue.put(self.Send_Data)
                self.tx_bytes += len(self.Send_Data)
                self.tx_count += 1
                self.current_time = time.time()
                self.last_tx_time = self.current_time
                self.update_rates()
                self.Logger.info(f"设置发送数据成功: {self.Send_Data}")               
                self.Send_Data=None
            return True
        except serial.SerialException as e:
            self.Logger.error(f"设置发送数据失败: {e}")
            return False

    #设置整行数据
    def send_lines(self):
        try:
            if self.check_serial_state():
                if isinstance(self.Send_Data,str):
                    if not self.Send_Data.endswith('\r\n') and self.Send_Data.endswith('\n'):
                        self.Send_Data+= '\r\n'
                        self.Send_Data=self.Send_Data.encode(self.Decode_Mode)
                else :
                    if not self.Send_Data.endswith(b'\r\n') and self.Send_Data.endswith(b'\n'):
                        self.Send_Data+= b'\r\n'
                self.tx_queue.put(self.Send_Data)
                self.tx_bytes += len(self.Send_Data)
                self.tx_count += 1
                self.current_time = time.time()
                self.last_tx_time = self.current_time
                self.update_rates()
                self.Logger.info(f"设置发送数据成功: {self.Send_Data}")               
                self.Send_Data=None
                return True
        except serial.SerialException as e:
            self.Logger.error(f"设置发送数据失败: {e}")
            return False

##==============================status==============================##            

    #更新状态函数
    def update_status(self):
        current_time=time.time()
        time_diff=current_time-self.last_update_time
        # 更新串口状态
        self.status['serial']['port']=self.Serial_port
        self.status['serial']['is_open']=self.check_serial_state()
        self.status['serial']['baudrate']=self.Serial_baudrate
        self.status['serial']['bytesize']=self.Serial_bytesize
        self.status['serial']['parity']=self.Serial_parity
        self.status['serial']['stopbits']=self.Serial_stopbits
        self.status['serial']['timeout']=self.Serial_timeout
        
        # 更新线程状态
        self.status['thread']['is_running']=self.thread_running
        if self.thread_running:
            if self.status['thread']['start_time'] is None:
                self.status['thread']['start_time']=current_time
            self.status['thread']['update_time']=current_time-self.status['thread']['start_time']
        
        # 更新队列状态  
        self.status['queue']['rx_size']=self.rx_queue.qsize()
        self.status['queue']['tx_size']=self.tx_queue.qsize()
        self.status['queue']['max_size']=self.Max_Data_Num

        # 更新数据状态
        self.status['data']['rx_bytes']=self.rx_bytes
        self.status['data']['tx_bytes']=self.tx_bytes
        self.status['data']['rx_count']=self.rx_count
        self.status['data']['tx_count']=self.tx_count
        self.status['data']['last_rx_time']=self.last_rx_time
        self.status['data']['last_tx_time']=self.last_tx_time
        if time_diff > 0:
            self.status['data']['rx_rate']=self.rx_rate
            self.status['data']['tx_rate']=self.tx_rate
        else:
            self.status['data']['rx_rate']=0
            self.status['data']['tx_rate']=0
        
        self.status['system']['timestamp']=current_time

        try:
            import psutil
            self.status['system']['cpu_usage']=psutil.cpu_percent()
            memory=psutil.virtual_memory()
            self.status['system']['memory_usage']=memory.percent
        except Exception as e:
            self.Logger.error(f"获取系统信息失败: {e}")
            self.status['system']['cpu_usage']=None
            self.status['system']['memory_usage']=None

        self.notify_callbacks()
        self.last_update_time=current_time

    #获取状态
    def get_status(self):
        self.update_status()
        return self.status

    #注册回调函数
    def register_callback(self,callback):
        if callback not in self.callbacks:
            self.callbacks.append(callback)
    
    #注销回调函数
    def unregister_callback(self,callback):
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    #通知回调函数
    def notify_callbacks(self):
        for callback in self.callbacks:
            try:
                callback(self.status)
            except Exception as e:
                self.Logger.error(f"回调函数执行失败: {e}")
    
    #日志记录状态
    def log_status(self):
        self.update_status()
        self.Logger.info("状态报告:")
        self.Logger.info(f"串口状态: 端口={self.status['serial']['port']}, 打开={self.status['serial']['is_open']}, 波特率={self.status['serial']['baudrate']}")
        self.Logger.info(f"线程状态: 运行中={self.status['thread']['is_running']}, 运行时间={self.status['thread']['update_time']:.2f}秒")                  
        self.Logger.info(f"队列状态: 接收队列={self.status['queue']['rx_size']}/{self.status['queue']['max_size']}, 发送队列={self.status['queue']['tx_size']}/{self.status['queue']['max_size']}")
        self.Logger.info(f"系统状态: CPU={self.status['system']['cpu_usage']}%, 内存={self.status['system']['memory_usage']}%")        
