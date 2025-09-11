#!/usr/bin/env python3
"""
Artemis主導 - GPU音声合成パフォーマンステスト
目標: 音声合成処理時間 2秒以内（従来15秒からの大幅改善）
"""

import time
import json
import requests
import statistics
from typing import Dict, List, Tuple
from datetime import datetime

class ArtemisPerformanceTester:
    """技術完璧主義者による徹底的パフォーマンステスト"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.backend_url = f"{base_url}:55433"
        self.openvoice_url = f"{base_url}:8001"
        self.voicevox_url = f"{base_url}:50021"
        self.test_results = []
        
    def test_service_connectivity(self) -> Dict[str, bool]:
        """全サービスの疎通確認"""
        print("🔍 Artemis: サービス疎通確認を開始する")
        
        services = {
            "Backend": f"{self.backend_url}/health",
            "OpenVoice GPU": f"{self.openvoice_url}/health", 
            "VOICEVOX": f"{self.voicevox_url}/version"
        }
        
        results = {}
        for service, url in services.items():
            try:
                response = requests.get(url, timeout=5)
                results[service] = response.status_code == 200
                print(f"   ✅ {service}: {'正常' if results[service] else '異常'}")
            except Exception as e:
                results[service] = False
                print(f"   ❌ {service}: 接続失敗 - {e}")
                
        return results
    
    def measure_voice_synthesis_performance(self, test_text: str = "これはパフォーマンステストです。") -> Dict:
        """音声合成パフォーマンス測定"""
        print("⚡ Artemis: GPU音声合成性能テストを開始する")
        
        test_cases = [
            {"text": test_text, "speaker": 1},
            {"text": "短いテスト", "speaker": 3},
            {"text": "これは長めのテキストで、音声合成のパフォーマンスを詳細に測定するためのサンプルテストです。GPUの処理能力を最大限に活用し、従来の15秒から2秒以内への劇的な改善を確認します。", "speaker": 5}
        ]
        
        results = []
        
        for i, case in enumerate(test_cases):
            print(f"   🎯 テストケース {i+1}: {case['text'][:30]}...")
            
            # VOICEVOX テスト
            voicevox_time = self._test_voicevox_synthesis(case["text"], case["speaker"])
            
            # OpenVoice テスト（プロファイルがある場合）
            openvoice_time = self._test_openvoice_synthesis(case["text"])
            
            result = {
                "case": i+1,
                "text_length": len(case["text"]),
                "voicevox_time": voicevox_time,
                "openvoice_time": openvoice_time,
                "target_achieved": voicevox_time < 2.0 if voicevox_time else False
            }
            
            results.append(result)
            
        return self._analyze_performance_results(results)
    
    def _test_voicevox_synthesis(self, text: str, speaker: int) -> float:
        """VOICEVOX音声合成時間測定"""
        try:
            start_time = time.perf_counter()
            
            # 音声クエリ生成
            audio_query_response = requests.post(
                f"{self.voicevox_url}/audio_query",
                params={"text": text, "speaker": speaker},
                timeout=30
            )
            
            if audio_query_response.status_code != 200:
                print(f"   ⚠️  音声クエリ生成失敗: {audio_query_response.status_code}")
                return None
                
            audio_query = audio_query_response.json()
            
            # 音声合成実行
            synthesis_response = requests.post(
                f"{self.voicevox_url}/synthesis",
                params={"speaker": speaker},
                json=audio_query,
                timeout=30
            )
            
            end_time = time.perf_counter()
            processing_time = end_time - start_time
            
            if synthesis_response.status_code == 200:
                print(f"   ⚡ VOICEVOX処理時間: {processing_time:.3f}秒")
                return processing_time
            else:
                print(f"   ❌ 音声合成失敗: {synthesis_response.status_code}")
                return None
                
        except Exception as e:
            print(f"   💥 VOICEVOX エラー: {e}")
            return None
    
    def _test_openvoice_synthesis(self, text: str) -> float:
        """OpenVoice音声合成時間測定"""
        try:
            # プロファイル一覧取得
            profiles_response = requests.get(f"{self.backend_url}/api/voice-clone/profiles", timeout=10)
            
            if profiles_response.status_code != 200:
                print("   ⚠️  OpenVoice: プロファイル取得失敗")
                return None
                
            profiles = profiles_response.json()
            if not profiles:
                print("   ℹ️  OpenVoice: テスト用プロファイルなし")
                return None
                
            profile_id = profiles[0]["profile_id"]
            
            start_time = time.perf_counter()
            
            synthesis_response = requests.post(
                f"{self.backend_url}/api/voice-clone/synthesize",
                json={"profile_id": profile_id, "text": text},
                timeout=60
            )
            
            end_time = time.perf_counter()
            processing_time = end_time - start_time
            
            if synthesis_response.status_code == 200:
                print(f"   🚀 OpenVoice GPU処理時間: {processing_time:.3f}秒")
                return processing_time
            else:
                print(f"   ❌ OpenVoice合成失敗: {synthesis_response.status_code}")
                return None
                
        except Exception as e:
            print(f"   💥 OpenVoice エラー: {e}")
            return None
    
    def _analyze_performance_results(self, results: List[Dict]) -> Dict:
        """Artemis: パフォーマンス結果の徹底分析"""
        
        voicevox_times = [r["voicevox_time"] for r in results if r["voicevox_time"]]
        openvoice_times = [r["openvoice_time"] for r in results if r["openvoice_time"]]
        
        analysis = {
            "total_tests": len(results),
            "successful_voicevox": len(voicevox_times),
            "successful_openvoice": len(openvoice_times),
            "target_achievement_rate": sum(1 for r in results if r["target_achieved"]) / len(results) * 100,
            "voicevox_performance": self._calculate_stats(voicevox_times),
            "openvoice_performance": self._calculate_stats(openvoice_times),
            "improvement_analysis": self._calculate_improvement(voicevox_times + openvoice_times),
            "timestamp": datetime.now().isoformat()
        }
        
        return analysis
    
    def _calculate_stats(self, times: List[float]) -> Dict:
        """統計計算"""
        if not times:
            return {"error": "No successful measurements"}
            
        return {
            "average": statistics.mean(times),
            "median": statistics.median(times),
            "min": min(times),
            "max": max(times),
            "stdev": statistics.stdev(times) if len(times) > 1 else 0
        }
    
    def _calculate_improvement(self, times: List[float]) -> Dict:
        """改善度分析（従来15秒との比較）"""
        if not times:
            return {"error": "No measurements to analyze"}
            
        avg_time = statistics.mean(times)
        baseline = 15.0  # 従来の処理時間
        
        improvement_ratio = ((baseline - avg_time) / baseline) * 100
        speed_multiplier = baseline / avg_time
        
        return {
            "baseline_seconds": baseline,
            "current_average_seconds": avg_time,
            "improvement_percentage": improvement_ratio,
            "speed_multiplier": f"{speed_multiplier:.1f}x faster",
            "target_achieved": avg_time <= 2.0,
            "performance_grade": self._get_performance_grade(avg_time)
        }
    
    def _get_performance_grade(self, avg_time: float) -> str:
        """Artemis基準でのパフォーマンス評価"""
        if avg_time <= 1.0:
            return "S級 - 完璧な最適化"
        elif avg_time <= 2.0:
            return "A級 - 目標達成"
        elif avg_time <= 5.0:
            return "B級 - 許容範囲"
        elif avg_time <= 10.0:
            return "C級 - 改善必要"
        else:
            return "D級 - 大幅改善必要"
    
    def monitor_system_resources(self) -> Dict:
        """システムリソース監視"""
        print("📊 システムリソース使用状況の監視")
        
        try:
            # Backend経由でシステム統計取得
            response = requests.get(f"{self.backend_url}/api/system/stats", timeout=10)
            
            if response.status_code == 200:
                stats = response.json()
                print(f"   💾 メモリ使用率: {stats.get('memory_percent', 'N/A')}%")
                print(f"   🖥️  CPU使用率: {stats.get('cpu_percent', 'N/A')}%")
                return stats
            else:
                print("   ⚠️  システム統計取得失敗")
                return {}
                
        except Exception as e:
            print(f"   💥 リソース監視エラー: {e}")
            return {}
    
    def run_comprehensive_test(self) -> Dict:
        """包括的パフォーマンステスト実行"""
        print("🎯 Artemis: 包括的パフォーマンステストを開始")
        print("=" * 60)
        
        test_report = {
            "test_start": datetime.now().isoformat(),
            "connectivity": self.test_service_connectivity(),
            "voice_performance": self.measure_voice_synthesis_performance(),
            "system_resources": self.monitor_system_resources(),
            "test_end": datetime.now().isoformat()
        }
        
        self._print_final_report(test_report)
        return test_report
    
    def _print_final_report(self, report: Dict):
        """Artemisによる最終評価レポート"""
        print("\n" + "=" * 60)
        print("📋 Artemis: 最終パフォーマンス評価レポート")
        print("=" * 60)
        
        # 接続状況
        connectivity = report["connectivity"]
        print(f"🔗 サービス接続状況:")
        for service, status in connectivity.items():
            print(f"   {service}: {'✅ 正常' if status else '❌ 異常'}")
        
        # パフォーマンス結果
        perf = report["voice_performance"]
        if "improvement_analysis" in perf:
            imp = perf["improvement_analysis"]
            print(f"\n⚡ パフォーマンス分析結果:")
            print(f"   目標達成率: {perf['target_achievement_rate']:.1f}%")
            print(f"   平均処理時間: {imp['current_average_seconds']:.3f}秒")
            print(f"   改善率: {imp['improvement_percentage']:.1f}%")
            print(f"   速度倍率: {imp['speed_multiplier']}")
            print(f"   評価: {imp['performance_grade']}")
        
        print("\n🎯 Artemis最終判定:")
        if perf.get("target_achievement_rate", 0) >= 80:
            print("   ✅ 優秀！GPU移行は大成功。目標を上回る性能を達成。")
        elif perf.get("target_achievement_rate", 0) >= 50:
            print("   ⚠️  良好。更なる最適化で完璧な性能を目指す。")
        else:
            print("   ❌ 不十分。追加の最適化が必要。")

if __name__ == "__main__":
    # テスト実行
    tester = ArtemisPerformanceTester("http://18.118.69.100")
    
    print("🏹 Artemis: Technical Perfectionist Performance Test")
    print("妥協なき品質とパフォーマンスの追求開始")
    print("=" * 60)
    
    results = tester.run_comprehensive_test()
    
    # 結果をJSONファイルに保存
    with open("performance_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 詳細結果を performance_test_results.json に保存")