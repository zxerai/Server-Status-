import os
import json
import time
import psutil
import platform
import plugins
from plugins import *
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from plugins.event import Event, EventContext, EventAction


@plugins.register(
    name="ServerStatus",
    desire_priority=0,
    hidden=False,
    desc="查看服务器运行状态和日志",
    version="0.2",
    author="Claude",
)
class ServerStatus(Plugin):
    def __init__(self):
        super().__init__()
        try:
            self.config = super().load_config()
            if not self.config:
                self.config = {}
            
            self.enabled = self.config.get("enabled", True)
            self.custom_commands = self.config.get("custom_commands", ["#status", "#服务器状态"])
            self.log_commands = self.config.get("log_commands", ["#log", "#日志"])
            self.system_log_commands = self.config.get("system_log_commands", ["#syslog", "#系统日志"])
            self.show_system_info = self.config.get("show_system_info", True)
            self.show_hardware_info = self.config.get("show_hardware_info", True)
            self.show_process_info = self.config.get("show_process_info", True)
            self.show_top_processes = self.config.get("show_top_processes", True)
            self.log_file_path = self.config.get("log_file_path", "logs/chatgpt.log")
            self.system_log_paths = self.config.get("system_log_paths", [
                "/var/log/syslog",
                "/var/log/messages",
                "/var/log/system.log",
                "/www/wwwlogs/error.log"
            ])
            self.log_lines = self.config.get("log_lines", 10)
            
            # 记录所有命令用于调试
            logger.info(f"[ServerStatus] 状态命令: {self.custom_commands}")
            logger.info(f"[ServerStatus] 日志命令: {self.log_commands}")
            logger.info(f"[ServerStatus] 系统日志命令: {self.system_log_commands}")
            
            self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
            logger.info("[ServerStatus] 插件已初始化")
        except Exception as e:
            logger.error(f"[ServerStatus] 初始化异常：{e}")

    def on_handle_context(self, e_context: EventContext):
        if e_context["context"].type != ContextType.TEXT:
            return
        
        content = e_context["context"].content.strip()
        logger.info(f"[ServerStatus] 收到消息: '{content}'")
        
        # 处理状态命令
        if content in self.custom_commands:
            logger.info(f"[ServerStatus] 匹配到状态命令: {content}")
            reply = Reply()
            reply.type = ReplyType.TEXT
            reply.content = self.get_server_status()
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS
            return
        
        # 简化日志命令处理 - 直接提取数字
        for cmd in self.log_commands:
            # 精确匹配原命令
            if content == cmd:
                logger.info(f"[ServerStatus] 精确匹配日志命令: {content}")
                reply = Reply()
                reply.type = ReplyType.TEXT
                reply.content = self.get_recent_logs(self.log_lines)
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
                
            # 提取数字的匹配
            elif content.startswith(cmd):
                # 提取命令后的部分
                remain = content[len(cmd):].strip()
                logger.info(f"[ServerStatus] 日志命令后缀: '{remain}'")
                
                # 提取数字
                import re
                num_match = re.search(r'\d+', remain)
                
                if num_match:
                    try:
                        log_num = int(num_match.group())
                        logger.info(f"[ServerStatus] 成功提取日志行数: {log_num}")
                        reply = Reply()
                        reply.type = ReplyType.TEXT
                        reply.content = self.get_recent_logs(log_num)
                        e_context["reply"] = reply
                        e_context.action = EventAction.BREAK_PASS
                        return
                    except Exception as e:
                        logger.error(f"[ServerStatus] 提取日志行数失败: {e}")
        
        # 简化系统日志命令处理
        for cmd in self.system_log_commands:
            # 精确匹配原命令
            if content == cmd:
                logger.info(f"[ServerStatus] 精确匹配系统日志命令: {content}")
                reply = Reply()
                reply.type = ReplyType.TEXT
                reply.content = self.get_system_logs(self.log_lines)
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
                
            # 提取数字的匹配
            elif content.startswith(cmd):
                # 提取命令后的部分
                remain = content[len(cmd):].strip()
                logger.info(f"[ServerStatus] 系统日志命令后缀: '{remain}'")
                
                # 提取数字
                import re
                num_match = re.search(r'\d+', remain)
                
                if num_match:
                    try:
                        log_num = int(num_match.group())
                        logger.info(f"[ServerStatus] 成功提取系统日志行数: {log_num}")
                        reply = Reply()
                        reply.type = ReplyType.TEXT
                        reply.content = self.get_system_logs(log_num)
                        e_context["reply"] = reply
                        e_context.action = EventAction.BREAK_PASS
                        return
                    except Exception as e:
                        logger.error(f"[ServerStatus] 提取系统日志行数失败: {e}")
        
        # 测试命令处理 - 用于调试
        if content.startswith("#logtest"):
            try:
                remain = content[len("#logtest"):].strip()
                logger.info(f"[ServerStatus] 测试命令后缀: '{remain}'")
                
                reply = Reply()
                reply.type = ReplyType.TEXT
                reply.content = f"测试命令: 收到 '{content}', 后缀: '{remain}'"
                
                # 尝试提取数字
                import re
                num_match = re.search(r'\d+', remain)
                if num_match:
                    num = int(num_match.group())
                    reply.content += f"\n成功提取数字: {num}"
                else:
                    reply.content += "\n未能提取数字"
                
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
            except Exception as e:
                logger.error(f"[ServerStatus] 测试命令处理失败: {e}")

    def get_server_status(self):
        """获取服务器状态信息"""
        try:
            status_text = f"📊 服务器状态报告 📊\n\n"
            
            # 系统信息
            if self.show_system_info:
                try:
                    system_info = platform.system()
                    system_version = platform.version()
                    architecture = platform.architecture()[0]
                    
                    boot_time = psutil.boot_time()
                    uptime = time.time() - boot_time
                    uptime_str = self.format_time(uptime)
                    
                    # 获取系统负载
                    if system_info.lower() != 'windows':
                        load_avg = os.getloadavg()
                        load_avg_text = f"- 负载平均值: 1分钟: {load_avg[0]:.2f}, 5分钟: {load_avg[1]:.2f}, 15分钟: {load_avg[2]:.2f}\n"
                    else:
                        load_avg_text = ""
                    
                    status_text += f"系统信息:\n"
                    status_text += f"- 操作系统: {system_info} {system_version} {architecture}\n"
                    status_text += f"- 系统启动时间: {uptime_str}\n"
                    status_text += load_avg_text + "\n"
                except Exception as e:
                    status_text += f"系统信息获取失败: {str(e)}\n\n"
            
            # 硬件资源
            if self.show_hardware_info:
                try:
                    # CPU详细信息
                    cpu_count = psutil.cpu_count(logical=False)
                    cpu_count_logical = psutil.cpu_count()
                    cpu_percent = psutil.cpu_percent(interval=1)
                    cpu_times = psutil.cpu_times_percent(interval=1)
                    
                    # 内存详细信息
                    memory = psutil.virtual_memory()
                    memory_total = self.format_bytes(memory.total)
                    memory_used = self.format_bytes(memory.used)
                    memory_available = self.format_bytes(memory.available)
                    memory_percent = memory.percent
                    memory_cached = self.format_bytes(getattr(memory, 'cached', 0))
                    memory_buffers = self.format_bytes(getattr(memory, 'buffers', 0))
                    
                    # 交换空间信息
                    swap = psutil.swap_memory()
                    swap_total = self.format_bytes(swap.total)
                    swap_used = self.format_bytes(swap.used)
                    swap_percent = swap.percent
                    
                    # 磁盘信息
                    disk = psutil.disk_usage('/')
                    disk_total = self.format_bytes(disk.total)
                    disk_used = self.format_bytes(disk.used)
                    disk_percent = disk.percent
                    
                    # 获取磁盘IO统计
                    try:
                        disk_io = psutil.disk_io_counters()
                        disk_read = self.format_bytes(disk_io.read_bytes)
                        disk_write = self.format_bytes(disk_io.write_bytes)
                        disk_io_text = f"- 磁盘IO: 读取: {disk_read}, 写入: {disk_write}\n"
                    except Exception as e:
                        disk_io_text = f"- 磁盘IO: 获取失败 ({str(e)})\n"
                    
                    # 网络信息
                    try:
                        net_io = psutil.net_io_counters()
                        net_sent = self.format_bytes(net_io.bytes_sent)
                        net_recv = self.format_bytes(net_io.bytes_recv)
                        net_text = f"- 网络流量: 发送: {net_sent}, 接收: {net_recv}\n"
                        net_err = f"- 网络错误: 接收: {net_io.errin}, 发送: {net_io.errout}\n"
                        net_drop = f"- 网络丢包: 接收: {net_io.dropin}, 发送: {net_io.dropout}\n"
                    except Exception as e:
                        net_text = f"- 网络流量: 获取失败 ({str(e)})\n"
                        net_err = ""
                        net_drop = ""
                    
                    # 进程信息
                    process_count = len(psutil.pids())
                    # 查找僵尸进程
                    zombie_count = 0
                    for proc in psutil.process_iter(['status']):
                        try:
                            if proc.info['status'] == 'zombie':
                                zombie_count += 1
                        except:
                            pass
                    
                    # 文件系统信息
                    fs_info = []
                    for part in psutil.disk_partitions(all=False):
                        if os.name == 'nt':
                            if 'cdrom' in part.opts or part.fstype == '':
                                # 在Windows跳过CD-ROM驱动器
                                continue
                        try:
                            usage = psutil.disk_usage(part.mountpoint)
                            fs_info.append({
                                'device': part.device,
                                'mountpoint': part.mountpoint,
                                'fstype': part.fstype,
                                'total': usage.total,
                                'used': usage.used,
                                'free': usage.free,
                                'percent': usage.percent
                            })
                        except:
                            pass
                    
                    # 格式化输出
                    status_text += f"CPU状态:\n"
                    status_text += f"- CPU核心: {cpu_count}物理核心, {cpu_count_logical}逻辑核心\n"
                    status_text += f"- CPU使用率: {cpu_percent}%\n"
                    status_text += f"- 用户时间: {cpu_times.user:.1f}%\n"
                    status_text += f"- 系统时间: {cpu_times.system:.1f}%\n"
                    status_text += f"- 空闲时间: {cpu_times.idle:.1f}%\n"
                    if hasattr(cpu_times, 'iowait'):
                        status_text += f"- I/O等待: {cpu_times.iowait:.1f}%\n\n"
                    else:
                        status_text += "\n"
                    
                    status_text += f"内存状态:\n"
                    status_text += f"- 总内存: {memory_total}\n"
                    status_text += f"- 已用内存: {memory_used} ({memory_percent}%)\n"
                    status_text += f"- 可用内存: {memory_available}\n"
                    if int(getattr(memory, 'cached', 0)) > 0:
                        status_text += f"- 缓存: {memory_cached}\n"
                    if int(getattr(memory, 'buffers', 0)) > 0:
                        status_text += f"- 缓冲区: {memory_buffers}\n"
                    if swap.total > 0:
                        status_text += f"- 交换空间: {swap_used}/{swap_total} ({swap_percent}%)\n\n"
                    else:
                        status_text += "\n"
                    
                    status_text += f"磁盘状态:\n"
                    status_text += f"- 磁盘空间: {disk_used}/{disk_total} ({disk_percent}%)\n"
                    status_text += disk_io_text
                    
                    # 添加文件系统详细信息
                    if fs_info:
                        status_text += "- 文件系统详情:\n"
                        for fs in fs_info[:3]:  # 显示前3个挂载点
                            status_text += f"  * {fs['mountpoint']} ({fs['fstype']}): {self.format_bytes(fs['used'])}/{self.format_bytes(fs['total'])} ({fs['percent']}%)\n"
                        if len(fs_info) > 3:
                            status_text += f"  * ... 还有 {len(fs_info) - 3} 个挂载点 ...\n"
                    status_text += "\n"
                    
                    status_text += f"网络状态:\n"
                    status_text += net_text
                    status_text += net_err
                    status_text += net_drop + "\n"
                    
                    status_text += f"进程状态:\n"
                    status_text += f"- 进程总数: {process_count}\n"
                    status_text += f"- 僵尸进程: {zombie_count}\n"
                    if system_info.lower() != 'windows':
                        status_text += f"- 负载平均值: 1分钟: {load_avg[0]:.2f}, 5分钟: {load_avg[1]:.2f}, 15分钟: {load_avg[2]:.2f}\n"
                    status_text += "\n"
                    
                except Exception as e:
                    status_text += f"硬件资源获取失败: {str(e)}\n\n"
            
            # 进程信息
            if self.show_process_info:
                try:
                    current_pid = os.getpid()
                    current_process = psutil.Process(current_pid)
                    process_create_time = current_process.create_time()
                    process_uptime = time.time() - process_create_time
                    process_uptime_str = self.format_time(process_uptime)
                    process_memory = self.format_bytes(current_process.memory_info().rss)
                    process_cpu = current_process.cpu_percent(interval=0.1)
                    
                    # 获取进程的IO信息
                    try:
                        process_io = current_process.io_counters()
                        process_read = self.format_bytes(process_io.read_bytes)
                        process_write = self.format_bytes(process_io.write_bytes)
                        process_io_text = f"- IO操作: 读取: {process_read}, 写入: {process_write}\n"
                    except:
                        process_io_text = ""
                    
                    # 获取线程数
                    threads_count = current_process.num_threads()
                    
                    # 获取进程状态
                    status = current_process.status()
                    
                    status_text += f"当前程序信息:\n"
                    status_text += f"- 进程ID: {current_pid} (状态: {status})\n"
                    status_text += f"- 运行时间: {process_uptime_str}\n"
                    status_text += f"- 内存占用: {process_memory}\n"
                    status_text += f"- CPU使用: {process_cpu}%\n"
                    status_text += f"- 线程数: {threads_count}\n"
                    status_text += process_io_text
                    
                    # 获取前5个最占用CPU的进程
                    try:
                        processes = []
                        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
                            proc.cpu_percent(interval=None)  # 第一次调用总是返回0，这里只是初始化
                        
                        # 等待一小段时间以获取有意义的CPU使用率
                        time.sleep(0.5)
                        
                        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
                            try:
                                pinfo = proc.info
                                pinfo['memory_percent'] = proc.memory_percent()
                                processes.append(pinfo)
                            except:
                                pass
                        
                        # 按CPU使用率排序
                        top_cpu_procs = sorted(processes, key=lambda p: p['cpu_percent'], reverse=True)[:5]
                        
                        if top_cpu_procs:
                            status_text += "\n最占用CPU的进程:\n"
                            for proc in top_cpu_procs:
                                proc_mem = self.format_bytes(proc['memory_info'].rss if proc['memory_info'] else 0)
                                status_text += f"- {proc['name']} (PID: {proc['pid']}): CPU {proc['cpu_percent']:.1f}%, 内存: {proc_mem}\n"
                    except Exception as e:
                        status_text += f"\n获取占用资源最多的进程失败: {str(e)}\n"
                    
                except Exception as e:
                    status_text += f"程序信息获取失败: {str(e)}\n"
            
            return status_text
        except Exception as e:
            logger.error(f"[ServerStatus] 获取服务器状态异常: {e}")
            return f"获取服务器状态时出错: {str(e)}"

    def get_recent_logs(self, log_num):
        """获取最近的日志信息"""
        try:
            # 确保log_num是有效的正整数
            if not isinstance(log_num, int) or log_num <= 0:
                log_num = self.log_lines
            
            # 增加一个合理的上限，防止请求过多导致内存问题 
            max_lines = 1000
            if log_num > max_lines:
                log_text = f"📜 最近{log_num}条日志 (已限制为{max_lines}条) 📜\n\n"
                log_num = max_lines
            else:
                log_text = f"📜 最近{log_num}条日志 📜\n\n"
            
            # 获取日志文件绝对路径
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            log_path = os.path.join(base_dir, self.log_file_path)
            
            # 日志查找逻辑
            if not os.path.exists(log_path):
                logger.warning(f"[ServerStatus] 未找到配置的日志文件: {log_path}")
                
                # 尝试查找宝塔面板通用日志位置
                bt_log_paths = [
                    "/www/wwwlogs/",  # 宝塔网站日志默认位置
                    "/www/server/panel/logs/",  # 宝塔面板日志
                    base_dir  # 当前目录
                ]
                
                found_log = False
                for bt_path in bt_log_paths:
                    if os.path.exists(bt_path):
                        logger.info(f"[ServerStatus] 检查目录: {bt_path}")
                        log_files = []
                        try:
                            log_files = [f for f in os.listdir(bt_path) if f.endswith('.log')]
                        except:
                            continue
                            
                        if log_files:
                            log_path = os.path.join(bt_path, log_files[0])
                            log_text += f"找到日志文件: {log_path}\n\n"
                            found_log = True
                            break
                
                # 如果宝塔日志位置也找不到，尝试本地logs目录
                if not found_log:
                    log_dir = os.path.join(base_dir, "logs")
                    if os.path.exists(log_dir):
                        log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
                        if log_files:
                            log_path = os.path.join(log_dir, log_files[0])
                            log_text += f"找到日志文件: {log_files[0]}\n\n"
                        else:
                            return "未找到任何日志文件。请在配置中指定正确的日志文件路径。"
                    else:
                        return "未找到日志目录。请在配置中指定正确的日志文件路径。"
            
            logger.info(f"[ServerStatus] 读取日志文件: {log_path}, 读取行数: {log_num}")
            
            # 读取最后n行日志
            lines = self.read_last_n_lines(log_path, log_num)
            if not lines:
                return "日志文件为空或无法读取。"
            
            log_text += f"实际获取日志行数: {len(lines)}\n\n"
            
            # 格式化日志内容
            for i, line in enumerate(lines):
                log_text += f"{i+1}. {line.strip()}\n"
            
            return log_text
        except Exception as e:
            logger.error(f"[ServerStatus] 获取日志异常: {e}")
            return f"获取日志时出错: {str(e)}"

    def read_last_n_lines(self, file_path, n):
        """读取文件的最后n行"""
        try:
            # 检查文件大小
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return []
                
            # 如果文件太大，使用更高效的方法
            if file_size > 10 * 1024 * 1024:  # 10MB以上
                return self.tail_large_file(file_path, n)
                
            # 对于较小文件，直接读取
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # 使用双端队列存储最后n行
                from collections import deque
                last_lines = deque(maxlen=n)
                
                for line in f:
                    if line.strip():  # 跳过空行
                        last_lines.append(line)
                
                return list(last_lines)
        except Exception as e:
            logger.error(f"[ServerStatus] 读取日志文件异常: {e}")
            return []
            
    def tail_large_file(self, file_path, n):
        """高效读取大文件的最后n行"""
        try:
            # 使用系统tail命令
            if os.name != 'nt':  # Linux/Mac
                import subprocess
                result = subprocess.run(['tail', '-n', str(n), file_path], 
                                        capture_output=True, text=True, encoding='utf-8', errors='ignore')
                if result.returncode == 0:
                    return result.stdout.splitlines()
            
            # 回退到手动读取方式
            with open(file_path, 'rb') as f:
                f.seek(0, os.SEEK_END)
                block_size = 1024
                block_end = f.tell()
                lines = []
                
                while len(lines) < n and block_end > 0:
                    block_start = max(0, block_end - block_size)
                    f.seek(block_start)
                    block = f.read(block_end - block_start).decode('utf-8', errors='ignore')
                    block_end = block_start
                    
                    lines = block.splitlines() + lines
                
                return lines[-n:] if len(lines) > n else lines
        except Exception as e:
            logger.error(f"[ServerStatus] 读取大文件异常: {e}")
            return []

    def format_bytes(self, bytes_value):
        """将字节数转换为可读格式"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024 or unit == 'TB':
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024

    def format_time(self, seconds):
        """将秒数转换为可读时间格式"""
        days, seconds = divmod(seconds, 86400)
        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)
        
        if days > 0:
            return f"{int(days)}天 {int(hours)}小时 {int(minutes)}分钟"
        elif hours > 0:
            return f"{int(hours)}小时 {int(minutes)}分钟"
        else:
            return f"{int(minutes)}分钟"

    def get_system_logs(self, log_num):
        """获取系统日志信息"""
        try:
            # 确保log_num是有效的正整数
            if not isinstance(log_num, int) or log_num <= 0:
                log_num = self.log_lines
            
            # 增加一个合理的上限，防止请求过多导致内存问题
            max_lines = 1000
            if log_num > max_lines:
                log_text = f"📜 系统日志（最近{log_num}条，已限制为{max_lines}条）📜\n\n"
                log_num = max_lines
            else:
                log_text = f"📜 系统日志（最近{log_num}条）📜\n\n"
            
            # 查找第一个存在的系统日志文件
            found_log = False
            system_log_path = None
            
            for log_path in self.system_log_paths:
                if os.path.exists(log_path):
                    system_log_path = log_path
                    found_log = True
                    break
            
            # 在宝塔特定的位置查找
            if not found_log:
                bt_log_dirs = [
                    "/www/wwwlogs/",
                    "/www/server/panel/logs/"
                ]
                
                for bt_path in bt_log_dirs:
                    if os.path.exists(bt_path):
                        # 查找常见的错误日志文件
                        possible_logs = ['error.log', 'nginx_error.log', 'php_error.log', 'mysql_error.log']
                        for possible_log in possible_logs:
                            full_path = os.path.join(bt_path, possible_log)
                            if os.path.exists(full_path):
                                system_log_path = full_path
                                found_log = True
                                break
                    if found_log:
                        break
            
            if not found_log:
                return "未找到系统日志文件。请在配置中指定正确的系统日志文件路径。"
            
            log_text += f"日志文件: {system_log_path}\n\n"
            
            logger.info(f"[ServerStatus] 读取系统日志文件: {system_log_path}, 读取行数: {log_num}")
            
            # 读取系统日志
            lines = self.read_last_n_lines(system_log_path, log_num)
            if not lines:
                return f"系统日志文件 {system_log_path} 为空或无法读取。"
                
            log_text += f"实际获取日志行数: {len(lines)}\n\n"
            
            # 格式化日志内容
            for i, line in enumerate(lines):
                log_text += f"{i+1}. {line.strip()}\n"
            
            return log_text
        except Exception as e:
            logger.error(f"[ServerStatus] 获取系统日志异常: {e}")
            return f"获取系统日志时出错: {str(e)}"

    def get_help_text(self, **kwargs):
        help_text = "📊 服务器状态与日志插件 📊\n\n"
        help_text += "功能：查看服务器的运行状态信息与日志\n\n"
        help_text += "使用方法：\n"
        
        status_commands = "、".join([f"`{cmd}`" for cmd in self.custom_commands])
        help_text += f"- 发送 {status_commands} 获取服务器状态报告\n\n"
        
        # 日志命令帮助
        log_commands = "、".join([f"`{cmd}`" for cmd in self.log_commands])
        help_text += f"程序日志命令：\n"
        help_text += f"- 发送 {log_commands} 获取最近{self.log_lines}条程序日志\n"
        help_text += f"- 自定义日志条数的多种格式：\n"
        help_text += f"  * `{self.log_commands[0]}数字` 例如: `{self.log_commands[0]}20`\n"
        help_text += f"  * `{self.log_commands[0]} 数字` 例如: `{self.log_commands[0]} 20`\n" 
        help_text += f"  * `{self.log_commands[0]}=数字` 例如: `{self.log_commands[0]}=20`\n"
        help_text += f"  * `{self.log_commands[0]}-数字` 例如: `{self.log_commands[0]}-20`\n\n"
        
        # 系统日志命令帮助
        system_log_commands = "、".join([f"`{cmd}`" for cmd in self.system_log_commands])
        help_text += f"系统日志命令：\n"
        help_text += f"- 发送 {system_log_commands} 获取最近{self.log_lines}条系统日志\n"
        help_text += f"- 自定义日志条数的多种格式：\n"
        help_text += f"  * `{self.system_log_commands[0]}数字` 例如: `{self.system_log_commands[0]}50`\n"
        help_text += f"  * `{self.system_log_commands[0]} 数字` 例如: `{self.system_log_commands[0]} 50`\n"
        help_text += f"  * `{self.system_log_commands[0]}:数字` 例如: `{self.system_log_commands[0]}:50`\n\n"
        
        help_text += "状态报告包含：\n"
        if self.show_system_info:
            help_text += "- 系统信息：操作系统、运行时间、系统负载\n"
        if self.show_hardware_info:
            help_text += "- 硬件资源：CPU详情、内存状态、磁盘使用情况、网络流量\n"
            help_text += "- 进程状态：进程总数、僵尸进程数量\n"
            help_text += "- 文件系统：各挂载点使用情况\n"
        if self.show_process_info:
            help_text += "- 程序信息：进程ID、运行时间、资源占用\n"
            if self.show_top_processes:
                help_text += "- 占用资源最多的进程列表\n"
        return help_text