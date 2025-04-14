# 服务器状态查看插件 (Server Status)

该插件用于查看服务器的运行状态信息，包括系统信息、硬件资源使用情况和程序信息。

## 功能特点

- 查看系统信息（操作系统、版本、架构、启动时间）
- 查看硬件资源使用情况（CPU、内存、磁盘）
- 查看程序运行信息（进程ID、运行时间、资源占用）
- 数据以格式化的方式展示，便于阅读

## 安装方法

1. 确保项目根目录下的 `plugins` 文件夹中包含本插件文件夹 `server_status`
2. 安装依赖：在插件目录中执行 `pip install -r requirements.txt` 或使用管理员指令：`#installp server_status`
3. 重启程序或执行 `#scanp` 命令加载插件

## 使用方法

向机器人发送以下指令之一：
- `#status`
- `#服务器状态`

机器人将返回格式化的服务器状态报告。

## 配置说明

配置文件位于 `plugins/server_status/config.json`，包含以下选项：

```json
{
    "enabled": true,                     // 是否启用插件
    "show_system_info": true,            // 是否显示系统信息
    "show_hardware_info": true,          // 是否显示硬件信息
    "show_process_info": true,           // 是否显示进程信息
    "custom_commands": ["#status", "#服务器状态"] // 自定义触发命令
}
```

## 依赖项

- `psutil>=5.9.0`: 用于获取系统和进程信息

## 注意事项

- 插件需要读取系统信息，请确保程序有足够的权限
- 在某些云服务或容器环境中，可能无法获取完整的系统信息 