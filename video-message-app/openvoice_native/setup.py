#!/usr/bin/env python3
"""
OpenVoice Native Service セットアップスクリプト
"""

import os
import sys
import subprocess
import asyncio
from pathlib import Path

def run_command(command, description):
    """コマンド実行"""
    print(f"\n🔧 {description}")
    print(f"実行: {command}")
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            capture_output=True, 
            text=True
        )
        print(f"✅ {description} 完了")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} 失敗")
        print(f"エラー: {e.stderr}")
        return False

async def main():
    """メイン処理"""
    print("🚀 OpenVoice Native Service セットアップ開始")
    
    # 現在のディレクトリ確認
    current_dir = Path(__file__).parent
    print(f"📁 作業ディレクトリ: {current_dir}")
    
    # Python バージョン確認
    python_version = sys.version
    print(f"🐍 Python バージョン: {python_version}")
    
    # 仮想環境作成
    venv_path = current_dir / "venv"
    if not venv_path.exists():
        if not run_command(
            "python3 -m venv venv", 
            "Python仮想環境作成"
        ):
            return False
    else:
        print("✅ 仮想環境は既に存在します")
    
    # 仮想環境のactivateスクリプトパス
    if sys.platform == "win32":
        activate_script = venv_path / "Scripts" / "activate"
        pip_path = venv_path / "Scripts" / "pip"
    else:
        activate_script = venv_path / "bin" / "activate"
        pip_path = venv_path / "bin" / "pip"
    
    # OpenVoice GitHub リポジトリをクローン（一時的）
    openvoice_dir = current_dir / "openvoice_temp"
    if not openvoice_dir.exists():
        if not run_command(
            "git clone https://github.com/myshell-ai/OpenVoice.git openvoice_temp",
            "OpenVoice リポジトリクローン"
        ):
            return False
    
    # 依存関係インストール
    install_commands = [
        f"{pip_path} install --upgrade pip",
        f"{pip_path} install torch torchaudio --index-url https://download.pytorch.org/whl/cpu",
        f"{pip_path} install -r requirements.txt",
        f"cd openvoice_temp && {pip_path} install -e .",
        f"{pip_path} install git+https://github.com/myshell-ai/MeloTTS.git",
    ]
    
    for command in install_commands:
        if not run_command(command, f"依存関係インストール: {command.split()[-1]}"):
            print("⚠️  依存関係のインストールに失敗しましたが、継続します")
    
    # unidic 辞書ダウンロード
    run_command(
        f"{venv_path / 'bin' / 'python'} -m unidic download",
        "Unidic辞書ダウンロード"
    )
    
    # テンポラリディレクトリ作成
    temp_dir = current_dir / "temp"
    temp_dir.mkdir(exist_ok=True)
    print(f"✅ テンポラリディレクトリ作成: {temp_dir}")
    
    # 一時クローンディレクトリ削除
    if openvoice_dir.exists():
        import shutil
        shutil.rmtree(openvoice_dir)
        print("✅ 一時ファイル削除完了")
    
    # 起動スクリプト作成
    start_script = current_dir / "start.sh"
    with open(start_script, 'w') as f:
        f.write(f"""#!/bin/bash
# OpenVoice Native Service 起動スクリプト

cd {current_dir}
source venv/bin/activate
python main.py
""")
    
    # 実行権限付与
    os.chmod(start_script, 0o755)
    print(f"✅ 起動スクリプト作成: {start_script}")
    
    print("\n🎉 OpenVoice Native Service セットアップ完了!")
    print(f"🚀 起動方法: {start_script}")
    print("📊 ヘルスチェック: http://localhost:8001/health")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)