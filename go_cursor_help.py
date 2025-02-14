import platform
import os
import subprocess
from logger import logging
import sys


def go_cursor_help():
    system = platform.system()
    logging.info(f"当前操作系统: {system}")

    # 获取程序运行时的绝对路径
    if getattr(sys, 'frozen', False):
        # 如果是打包后的exe运行
        script_folder = os.path.join(sys._MEIPASS, "sh")
    else:
        # 如果是直接运行python脚本
        script_folder = "sh"
    
    logging.info(f"脚本文件夹路径: {script_folder}")

    if system == "Darwin":  # macOS
        script_path = os.path.join(script_folder, "cursor_mac_id_modifier.sh")
        cmd = f'sudo bash {script_path}'
        logging.info("执行macOS命令")
        os.system(cmd)
    elif system == "Linux":
        script_path = os.path.join(script_folder, "cursor_linux_id_modifier.sh")
        cmd = f'sudo bash {script_path}'
        logging.info("执行Linux命令")
        os.system(cmd)
    elif system == "Windows":
        script_path = os.path.join(script_folder, "cursor_win_id_modifier.ps1")
        cmd = f'powershell -ExecutionPolicy Bypass -File {script_path}'
        logging.info("执行Windows命令")
        subprocess.run(cmd, shell=True)
    else:
        logging.error(f"不支持的操作系统: {system}")
        return False

    return True
