import logging
import platform
import subprocess
import sys
from pathlib import Path
import os
import zipfile
import shutil
import tempfile
import time

import requests
from packaging import version


class AutoUpdater:
    def __init__(self):
        self.current_version = "1.0.53"
        self.github_api = "https://api.github.com/repos/Fan-Yu0/cursor/releases/latest"
        
        # 获取当前程序路径
        if getattr(sys, 'frozen', False):
            # 如果是打包后的程序
            self.app_dir = Path(sys.executable).parent
        else:
            # 如果是源码运行
            self.app_dir = Path(os.path.abspath(sys.argv[0])).parent
            
        # 在程序目录下创建临时文件夹
        self.tmp_dir = self.app_dir / "temp"
        self.os_type = platform.system()
        
        logging.info(f"程序目录: {self.app_dir}")
        logging.info(f"临时目录: {self.tmp_dir}")

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
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/octet-stream"
            }
            
            response = requests.get(
                asset_url,
                headers=headers,
                stream=True,
                timeout=30
            )
            
            if response.status_code == 200:
                # 确保临时目录存在并有写入权限
                self.tmp_dir.mkdir(parents=True, exist_ok=True)
                
                # 使用唯一的临时文件名
                file_path = self.tmp_dir / f"update_{int(time.time())}.zip"
                
                total_size = int(response.headers.get('content-length', 0))
                block_size = 1024
                downloaded = 0
                
                # ANSI 颜色代码
                GREEN = "\033[32m"
                BLUE = "\033[34m"
                RESET = "\033[0m"
                
                with open(file_path, "wb") as f:
                    start_time = time.time()
                    for chunk in response.iter_content(chunk_size=block_size):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                percent = int(downloaded * 100 / total_size)
                                filled_width = int(50 * downloaded // total_size)
                                bar = "█" * filled_width + "░" * (50 - filled_width)
                                
                                # 计算下载速度
                                speed = downloaded / 1024  # KB
                                if speed > 1024:
                                    speed_str = f"{speed/1024:.1f} MB/s"
                                else:
                                    speed_str = f"{speed:.1f} KB/s"
                                
                                # 计算剩余时间
                                if downloaded > 0:
                                    eta = (total_size - downloaded) * (time.time() - start_time) / downloaded
                                    eta_str = f"{int(eta)}s"
                                else:
                                    eta_str = "计算中..."
                                
                                # 带颜色的进度条
                                print(f"\r{GREEN}下载进度: |{bar}| {percent}% {BLUE}{speed_str}{RESET} ETA: {eta_str}", 
                                      end="", flush=True)
                
                print()  # 完成后换行
                logging.info("下载完成！")
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
        try:
            import zipfile
            import shutil
            
            update_script = self.tmp_dir / f"update_{int(time.time())}.bat"
            app_path = self.app_dir.resolve()
            file_path = Path(file_path).resolve()
            backup_dir = self.tmp_dir / "backup"
            new_dir = self.tmp_dir / "new"
            extract_dir = self.tmp_dir / "extract"
            
            # 处理路径中的反斜杠
            app_path_str = str(app_path).replace('\\', '\\\\')
            file_path_str = str(file_path).replace('\\', '\\\\')
            backup_dir_str = str(backup_dir).replace('\\', '\\\\')
            new_dir_str = str(new_dir).replace('\\', '\\\\')
            extract_dir_str = str(extract_dir).replace('\\', '\\\\')
            
            # 如果是打包后的程序，使用 exe 路径
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
                exe_name = Path(sys.executable).name
            else:
                exe_path = f'"{sys.executable}" "{app_path / "main.py"}"'
                exe_name = "main.py"
            
            with open(update_script, "w", encoding='gbk') as f:
                f.write(f"""@echo off
chcp 936
echo 正在更新程序...
timeout /t 2 /nobreak > nul

rem 备份当前程序
echo 正在备份当前程序...
if exist "{backup_dir_str}" rmdir /s /q "{backup_dir_str}"
mkdir "{backup_dir_str}"
xcopy /s /e /y "{app_path_str}\\*" "{backup_dir_str}\\"

rem 创建临时目录
if exist "{extract_dir_str}" rmdir /s /q "{extract_dir_str}"
if exist "{new_dir_str}" rmdir /s /q "{new_dir_str}"
mkdir "{extract_dir_str}"
mkdir "{new_dir_str}"

rem 解压更新包
echo 正在解压更新文件...
powershell -Command "Expand-Archive -LiteralPath '{file_path_str}' -DestinationPath '{extract_dir_str}' -Force"
if %errorlevel% neq 0 (
    echo 解压更新失败，正在恢复备份...
    xcopy /s /e /y "{backup_dir_str}\\*" "{app_path_str}\\"
    pause
    exit /b 1
)

rem 处理压缩包内的文件夹结构
echo 正在处理文件...
for /d %%D in ("{extract_dir_str}\\*") do (
    xcopy /s /e /y "%%D\\*" "{new_dir_str}\\"
    goto :done_copy
)
:done_copy

rem 删除旧文件
echo 正在删除旧文件...
for %%F in ("{app_path_str}\\*") do (
    if not "%%~nxF"=="{exe_name}" del /f /q "%%F"
)
for /d %%D in ("{app_path_str}\\*") do (
    if not "%%~nxD"=="temp" rmdir /s /q "%%D"
)

rem 复制新文件
echo 正在复制新文件...
xcopy /s /e /y "{new_dir_str}\\*" "{app_path_str}\\"
if %errorlevel% neq 0 (
    echo 复制文件失败，正在恢复备份...
    xcopy /s /e /y "{backup_dir_str}\\*" "{app_path_str}\\"
    pause
    exit /b 1
)

rem 清理临时文件
echo 正在清理临时文件...
del /f /q "{file_path_str}"
rmdir /s /q "{extract_dir_str}"
rmdir /s /q "{new_dir_str}"
rmdir /s /q "{backup_dir_str}"

rem 重启应用
echo 更新完成，正在重启程序...
start "" {exe_path}

rem 删除更新脚本
del "%~f0"
""")
            
            # 执行更新脚本
            logging.info("开始执行更新脚本...")
            subprocess.Popen(
                ['cmd', '/c', str(update_script)],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=str(self.app_dir)
            )
            
            logging.info("更新程序已启动，当前程序将退出...")
            sys.exit(0)
            
        except Exception as e:
            logging.error(f"Windows 更新安装失败: {e}")
            if self.tmp_dir.exists():
                shutil.rmtree(self.tmp_dir, ignore_errors=True)
            raise

    def _install_update_macos(self, file_path):
        """macOS 更新安装逻辑 - 使用与 Windows 相同的方式"""
        try:
            import zipfile
            import shutil
            
            update_script = self.tmp_dir / f"update_{int(time.time())}.bat"
            app_path = self.app_dir.resolve()
            file_path = Path(file_path).resolve()
            backup_dir = self.tmp_dir / "backup"
            new_dir = self.tmp_dir / "new"
            extract_dir = self.tmp_dir / "extract"

            
            # 如果是打包后的程序，使用 exe 路径
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
                exe_name = Path(sys.executable).name
            else:
                exe_path = f'"{sys.executable}" "{app_path / "main.py"}"'
                exe_name = "main.py"
            
            with open(update_script, "w", encoding='utf-8') as f:
                f.write(f"""@echo off
echo 正在更新程序...
sleep 2

# 备份当前程序
echo 正在备份当前程序...
rm -rf "{backup_dir}"
mkdir -p "{backup_dir}"
cp -R "{app_path}/"* "{backup_dir}/"

# 创建临时目录
rm -rf "{extract_dir}" "{new_dir}"
mkdir -p "{extract_dir}" "{new_dir}"

# 解压更新包
echo 正在解压更新文件...
unzip -q "{file_path}" -d "{extract_dir}"
if [ $? -ne 0 ]; then
    echo "解压更新失败，正在恢复备份..."
    cp -R "{backup_dir}/"* "{app_path}/"
    read -p "按回车键继续..."
    exit 1
fi

# 处理压缩包内的文件夹结构
echo 正在处理文件...
first_dir=$(ls "{extract_dir}" | head -n 1)
if [ -d "{extract_dir}/$first_dir" ]; then
    cp -R "{extract_dir}/$first_dir/"* "{new_dir}/"
else
    cp -R "{extract_dir}/"* "{new_dir}/"
fi

# 删除旧文件
echo 正在删除旧文件...
find "{app_path}" -type f ! -name "{exe_name}" -delete
find "{app_path}" -type d ! -name "temp" -delete

# 复制新文件
echo 正在复制新文件...
cp -R "{new_dir}/"* "{app_path}/"
if [ $? -ne 0 ]; then
    echo "复制文件失败，正在恢复备份..."
    cp -R "{backup_dir}/"* "{app_path}/"
    read -p "按回车键继续..."
    exit 1
fi

# 清理临时文件
echo 正在清理临时文件...
rm -f "{file_path}"
rm -rf "{extract_dir}" "{new_dir}" "{backup_dir}"

# 设置权限
chmod +x "{app_path}/main.py"

# 重启应用
echo 更新完成，正在重启程序...
{exe_path} &

# 删除更新脚本
rm "$0"
""")
            
            # 设置脚本执行权限
            os.chmod(update_script, 0o755)
            
            # 执行更新脚本
            logging.info("开始执行更新脚本...")
            subprocess.Popen(['bash', str(update_script)], cwd=str(self.app_dir))
            
            logging.info("更新程序已启动，当前程序将退出...")
            sys.exit(0)
            
        except Exception as e:
            logging.error(f"macOS 更新安装失败: {e}")
            if self.tmp_dir.exists():
                shutil.rmtree(self.tmp_dir, ignore_errors=True)
            raise

    def _install_update_linux(self, file_path):
        """Linux 更新安装逻辑 - 复用 macOS 的逻辑"""
        return self._install_update_macos(file_path)

    def auto_update(self):
        """执行自动更新流程"""
        print("检查更新中...")
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