import logging
import platform
import subprocess
import sys
from pathlib import Path
import os
import zipfile
import shutil

import requests
from packaging import version


class AutoUpdater:
    def __init__(self):
        self.current_version = "1.0.4"  # 当前版本号
        self.github_api = "https://api.github.com/repos/Fan-Yu0/cursor/releases/latest"
        self.app_dir = Path(__file__).parent
        self.tmp_dir = self.app_dir / "temp"
        self.os_type = platform.system()

    def check_for_updates(self):
        """检查是否有新版本"""
        try:
            response = requests.get(self.github_api)
            if response.status_code == 200:
                latest_release = response.json()
                latest_version = latest_release["tag_name"].lstrip("v")
                
                if version.parse(latest_version) > version.parse(self.current_version):
                    logging.info(f"发现新版本: {latest_version}")
                    return latest_release
                else:
                    logging.info("当前已是最新版本")
                    return None
        except Exception as e:
            logging.error(f"检查更新失败: {e}")
            return None

    def download_update(self, asset_url):
        """下载更新文件"""
        try:
            response = requests.get(asset_url, stream=True)
            if response.status_code == 200:
                # 确保临时目录存在
                self.tmp_dir.mkdir(exist_ok=True)
                
                # 下载文件
                file_path = self.tmp_dir / "update.zip"
                with open(file_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return file_path
            return None
        except Exception as e:
            logging.error(f"下载更新失败: {e}")
            return None

    def install_update(self, file_path):
        """安装更新"""
        try:
            # 这里根据操作系统类型执行不同的更新逻辑
            if self.os_type == "Windows":
                self._install_update_windows(file_path)
            elif self.os_type == "Darwin":  # macOS
                self._install_update_macos(file_path)
            elif self.os_type == "Linux":
                self._install_update_linux(file_path)
            
            return True
        except Exception as e:
            logging.error(f"安装更新失败: {e}")
            return False

    def _install_update_windows(self, file_path):
        """Windows 更新安装逻辑"""
        # 创建更新批处理文件
        update_script = self.tmp_dir / "update.bat"
        with open(update_script, "w") as f:
            f.write(f"""
@echo off
timeout /t 2 /nobreak
powershell Expand-Archive -Path "{file_path}" -DestinationPath "{self.app_dir}" -Force
del "{file_path}"
start "" "{sys.executable}" "{self.app_dir / 'main.py'}"
del "%~f0"
            """)
        
        # 执行更新脚本
        subprocess.Popen([update_script], shell=True)
        sys.exit(0)

    def _install_update_macos(self, file_path):
        """macOS 更新安装逻辑"""
        try:
            # 创建临时解压目录
            extract_dir = self.tmp_dir / "update_extract"
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
            extract_dir.mkdir(parents=True)
            
            # 解压更新包
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # 创建更新脚本
            update_script = self.tmp_dir / "update.sh"
            with open(update_script, "w") as f:
                f.write(f"""#!/bin/bash
sleep 2
# 复制新文件
cp -R "{extract_dir}/"* "{self.app_dir}/"
# 清理临时文件
rm -rf "{self.tmp_dir}"
# 设置权限
chmod +x "{self.app_dir}/main.py"
# 重启应用
python3 "{self.app_dir}/main.py" &
exit 0
""")
            
            # 设置脚本执行权限
            os.chmod(update_script, 0o755)
            
            # 执行更新脚本
            subprocess.Popen(['bash', str(update_script)])
            sys.exit(0)
            
        except Exception as e:
            logging.error(f"macOS 更新安装失败: {e}")
            # 清理临时文件
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
            raise

    def _install_update_linux(self, file_path):
        """Linux 更新安装逻辑"""
        # Linux 的更新逻辑基本可以复用 macOS 的逻辑
        return self._install_update_macos(file_path)

    def auto_update(self):
        """执行自动更新流程"""
        latest_release = self.check_for_updates()
        if latest_release:
            # 获取对应操作系统的下载链接
            asset_url = None
            for asset in latest_release["assets"]:
                if self.os_type.lower() in asset["name"].lower():
                    asset_url = asset["browser_download_url"]
                    break
            
            if asset_url:
                logging.info("开始下载更新...")
                update_file = self.download_update(asset_url)
                if update_file:
                    logging.info("开始安装更新...")
                    if self.install_update(update_file):
                        logging.info("更新成功！")
                        return True
            else:
                logging.error("未找到适配当前系统的更新包")
        
        return False

def main():
    logging.basicConfig(level=logging.INFO)
    updater = AutoUpdater()
    updater.auto_update()

if __name__ == "__main__":
    main() 