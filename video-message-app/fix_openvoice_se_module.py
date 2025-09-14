#!/usr/bin/env python3
"""
OpenVoice se_module エラー修正スクリプト
EC2上のOpenVoiceサービスのse_moduleエラーを修正します
"""

import os
import sys
import tempfile
import shutil

# 修正対象のファイル
SERVICE_FILE = "/home/ec2-user/video-message-app/video-message-app/openvoice_native/openvoice_service.py"

def create_patch():
    """se_module エラーを修正するパッチを作成"""
    
    patch_code = '''
# se_module グローバル変数エラー修正パッチ
# 491行目付近のse_extractor.get_se呼び出し部分を修正

# 修正前の問題: 
# reference_se, audio_name = se_extractor.get_se(...)
# でse_extractorがスコープ外になる問題

# 修正: インスタンス変数として保存されたse_extractorを使用
'''
    
    # 修正する内容
    fix_content = """
                else:
                    # 通常モード: se_extractorを使用（最適化済み）
                    se_start = time.time()
                    logger.info(f"se_extractor.get_se開始 (index={index})")
                    
                    # FIXED: グローバル変数ではなくインスタンス変数を使用
                    if hasattr(self, '_se_extractor_module') and self._se_extractor_module:
                        reference_se, audio_name = self._se_extractor_module.get_se(
                            temp_audio_path, 
                            self._tone_color_converter, 
                            vad=False  # VADを無効化（Whisper処理）
                        )
                    else:
                        # フォールバック: グローバルからアクセス
                        global se_extractor
                        if 'se_extractor' in globals():
                            reference_se, audio_name = se_extractor.get_se(
                                temp_audio_path, 
                                self._tone_color_converter, 
                                vad=False  # VADを無効化（Whisper処理）
                            )
                        else:
                            raise Exception("se_extractor モジュールが初期化されていません")
                    
                    logger.info(f"se_extractor.get_se完了: {time.time() - se_start:.2f}秒")
"""
    
    # 初期化部分の修正
    init_fix = """
        # se_extractorをインスタンス変数として保存（修正版）
        try:
            global ToneColorConverter, se_extractor, TTS
            
            # OpenVoice v2のインポート
            from melo.api import TTS
            from openvoice import ToneColorConverter
            from openvoice import se_extractor
            
            # インスタンス変数として保存
            self._se_extractor_module = se_extractor
            
            # EC2環境でのse_extractorのWhisperModelをパッチ
            import torch
            import openvoice.se_extractor as se_module
            from faster_whisper import WhisperModel
            
            # グローバル変数として保存
            globals()['se_module'] = se_module
            
            # パッチ適用
            original_split_audio_whisper = se_module.split_audio_whisper
"""
    
    return patch_code, fix_content, init_fix

def apply_emergency_fix():
    """緊急修正を適用"""
    patch_script = f'''
# 緊急修正: OpenVoiceサービスを停止して修正を適用

# 1. サービス停止
sudo systemctl stop openvoice

# 2. バックアップ作成
cp {SERVICE_FILE} {SERVICE_FILE}.backup.$(date +%Y%m%d_%H%M%S)

# 3. 修正を適用 (sed によるインライン修正)
# グローバル変数の問題を修正
sed -i 's/global se_module/global se_module, se_extractor/' {SERVICE_FILE}

# se_extractor呼び出し部分をより安全に修正
sed -i '/reference_se, audio_name = se_extractor.get_se(/c\\
                    # FIXED: より安全なse_extractor呼び出し\\
                    try:\\
                        global se_extractor\\
                        if se_extractor is None:\\
                            from openvoice import se_extractor as global_se_extractor\\
                            se_extractor = global_se_extractor\\
                        reference_se, audio_name = se_extractor.get_se(\\
                            temp_audio_path, \\
                            self._tone_color_converter, \\
                            vad=False\\
                        )\\
                    except NameError as ne:\\
                        logger.error(f"se_extractor not found: {{ne}}")\\
                        raise Exception("se_extractor module initialization failed")' {SERVICE_FILE}

# 4. サービス再起動
sudo systemctl start openvoice

echo "OpenVoice修正完了 - サービスを再起動しました"
'''
    
    return patch_script

if __name__ == "__main__":
    patch_code, fix_content, init_fix = create_patch()
    emergency_script = apply_emergency_fix()
    
    print("=== OpenVoice se_module エラー修正パッチ ===")
    print("問題: name 'se_module' is not defined エラー")
    print("原因: グローバル変数のスコープ問題")
    print()
    print("修正内容:")
    print(patch_code)
    print()
    print("緊急修正スクリプト:")
    print(emergency_script)
    
    # 緊急修正スクリプトをファイルに保存
    with open("/tmp/fix_openvoice.sh", "w") as f:
        f.write("#!/bin/bash\n")
        f.write(emergency_script)
    
    print("\n緊急修正スクリプトを /tmp/fix_openvoice.sh に保存しました")
    print("EC2で実行してください: bash /tmp/fix_openvoice.sh")