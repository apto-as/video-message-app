#!/usr/bin/env python3
"""
OpenVoice V2モデルダウンロード・セットアップスクリプト
"""

import os
import sys
import requests
import tarfile
import zipfile
from pathlib import Path
import shutil
import subprocess

# ダウンロードURL（OpenVoice V2の公式モデル）
OPENVOICE_MODELS = {
    "v2_checkpoint": {
        "url": "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/checkpoints_v2_0417.zip",
        "path": "checkpoints_v2.zip",
        "extract_to": "checkpoints_v2"
    }
}

def download_file(url: str, dest_path: Path) -> bool:
    """ファイルをダウンロード"""
    try:
        print(f"ダウンロード中: {url}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"完了: {dest_path}")
        return True
        
    except Exception as e:
        print(f"ダウンロードエラー {url}: {str(e)}")
        return False

def extract_archive(archive_path: Path, extract_to: Path) -> bool:
    """アーカイブを展開"""
    try:
        extract_to.mkdir(parents=True, exist_ok=True)
        
        if archive_path.suffix == '.gz' and '.tar' in archive_path.name:
            with tarfile.open(archive_path, 'r:gz') as tar:
                tar.extractall(extract_to)
        elif archive_path.suffix == '.zip':
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
        else:
            return False
            
        print(f"展開完了: {extract_to}")
        return True
        
    except Exception as e:
        print(f"展開エラー {archive_path}: {str(e)}")
        return False

def setup_openvoice_models(base_dir: Path = None) -> bool:
    """OpenVoice V2モデルをセットアップ"""
    
    if base_dir is None:
        base_dir = Path("./data/openvoice")
    
    print(f"OpenVoice V2モデルセットアップ開始: {base_dir}")
    
    success = True
    
    # OpenVoice V2チェックポイントのダウンロード
    print("\n=== OpenVoice V2チェックポイントのダウンロード ===")
    model_info = OPENVOICE_MODELS["v2_checkpoint"]
    
    # ZIPファイルをダウンロード
    zip_path = base_dir / model_info["path"]
    if download_file(model_info["url"], zip_path):
        # 展開
        extract_path = base_dir / model_info["extract_to"]
        if extract_archive(zip_path, extract_path):
            # ZIPファイルを削除
            zip_path.unlink()
            print(f"チェックポイント展開完了: {extract_path}")
        else:
            success = False
    else:
        success = False
    
    # 必要なPythonパッケージの確認
    print("\n=== Pythonパッケージの確認 ===")
    required_packages = [
        "torch",
        "torchaudio", 
        "numpy",
        "librosa",
        "unidecode",
        "eng_to_ipa",
        "inflect",
        "pydub"
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} (pip install {package})")
            success = False
    
    return success

def main():
    """メイン処理"""
    print("OpenVoice V2セットアップスクリプト")
    
    # ベースディレクトリの設定
    base_dir = Path("./data/openvoice")
    
    if len(sys.argv) > 1:
        base_dir = Path(sys.argv[1])
    
    print(f"インストール先: {base_dir.absolute()}")
    
    if setup_openvoice_models(base_dir):
        print("\n✅ セットアップ完了")
        
        # 構造確認
        print("\n=== ファイル構造 ===")
        for root, dirs, files in os.walk(base_dir):
            level = root.replace(str(base_dir), '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                print(f"{subindent}{file}")
                
        return 0
    else:
        print("\n❌ セットアップに失敗しました")
        return 1

if __name__ == "__main__":
    sys.exit(main())