#!/usr/bin/env python3
"""
Hestia - Security Diagnosis for EC2 Connection Issues
セキュリティ監査による接続問題の根本原因分析
"""

import subprocess
import json
import socket
from datetime import datetime
import concurrent.futures
import time

class HestiaSecurityDiagnostic:
    """Hestiaによる包括的セキュリティ診断"""
    
    def __init__(self, target_ip: str = "18.118.69.100"):
        self.target_ip = target_ip
        self.target_ports = [22, 55433, 8001, 50021, 55434]  # SSH, Backend, OpenVoice, VOICEVOX, Frontend
        self.diagnosis_results = {
            "timestamp": datetime.now().isoformat(),
            "target_ip": target_ip,
            "tests_performed": []
        }
    
    def network_connectivity_test(self):
        """...ネットワーク接続の基本的な診断を実行します..."""
        print("🔒 Hestia: ネットワーク接続診断開始...")
        
        # Ping test
        ping_result = self._ping_test()
        
        # Port scan
        port_results = self._port_scan()
        
        # DNS resolution
        dns_result = self._dns_resolution_test()
        
        results = {
            "ping": ping_result,
            "ports": port_results,
            "dns": dns_result
        }
        
        self.diagnosis_results["tests_performed"].append({
            "test_name": "network_connectivity",
            "results": results
        })
        
        return results
    
    def _ping_test(self):
        """ICMP接続テスト"""
        print(f"   📡 ICMP ping to {self.target_ip}... ", end="", flush=True)
        
        try:
            # Mac/Linuxでのping実行
            result = subprocess.run(
                ["ping", "-c", "3", "-W", "3000", self.target_ip],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print("✅ 応答あり")
                return {"status": "success", "output": result.stdout}
            else:
                print("❌ 応答なし")
                return {"status": "failed", "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            print("⏰ タイムアウト")
            return {"status": "timeout"}
        except Exception as e:
            print(f"💥 エラー: {e}")
            return {"status": "error", "message": str(e)}
    
    def _port_scan(self):
        """重要ポートのスキャン"""
        print("   🚪 ポート接続テスト...")
        
        def test_port(port):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((self.target_ip, port))
                sock.close()
                
                is_open = result == 0
                status = "🟢 OPEN" if is_open else "🔴 CLOSED/FILTERED"
                print(f"      Port {port}: {status}")
                
                return {"port": port, "open": is_open}
            except Exception as e:
                print(f"      Port {port}: 💥 Error - {e}")
                return {"port": port, "open": False, "error": str(e)}
        
        # 並列ポートスキャン
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            port_results = list(executor.map(test_port, self.target_ports))
        
        return port_results
    
    def _dns_resolution_test(self):
        """DNS解決テスト"""
        print(f"   🔍 DNS resolution for {self.target_ip}... ", end="", flush=True)
        
        try:
            # IPアドレスなので逆引きDNS
            hostname = socket.gethostbyaddr(self.target_ip)
            print(f"✅ Resolved: {hostname[0]}")
            return {"status": "success", "hostname": hostname[0]}
        except socket.herror:
            print("⚠️  No reverse DNS")
            return {"status": "no_reverse_dns"}
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"status": "error", "message": str(e)}
    
    def analyze_security_implications(self):
        """...セキュリティ上の問題を分析します..."""
        print("🛡️  Hestia: セキュリティ分析実行中...")
        
        analysis = {
            "threat_level": "UNKNOWN",
            "potential_causes": [],
            "security_recommendations": [],
            "immediate_actions": []
        }
        
        # 前のテスト結果を分析
        if self.diagnosis_results["tests_performed"]:
            net_test = next((t for t in self.diagnosis_results["tests_performed"] 
                           if t["test_name"] == "network_connectivity"), None)
            
            if net_test:
                results = net_test["results"]
                
                # Ping失敗の分析
                if results["ping"]["status"] != "success":
                    analysis["potential_causes"].append("ICMP traffic blocked (Security Group/NACL)")
                    analysis["immediate_actions"].append("Check AWS Security Group ICMP rules")
                
                # 全ポート閉鎖の分析
                closed_ports = [p for p in results["ports"] if not p.get("open", False)]
                if len(closed_ports) == len(results["ports"]):
                    analysis["threat_level"] = "HIGH"
                    analysis["potential_causes"].extend([
                        "AWS Security Group rules blocking all traffic",
                        "Network ACL denying access",
                        "EC2 instance firewall (iptables) blocking",
                        "Services not running on target instance",
                        "Instance may be stopped or terminated"
                    ])
                    
                    analysis["security_recommendations"].extend([
                        "Verify AWS Security Group has proper inbound rules",
                        "Check Network ACL configuration",
                        "Confirm EC2 instance is running",
                        "Verify services are started inside instance",
                        "Check iptables/firewall rules on instance"
                    ])
                    
                    analysis["immediate_actions"].extend([
                        "SSH into instance to check service status",
                        "Review AWS Console for Security Group rules",
                        "Check CloudWatch logs for instance activity",
                        "Verify Elastic IP association"
                    ])
        
        self.diagnosis_results["security_analysis"] = analysis
        return analysis
    
    def generate_hestia_report(self):
        """Hestiaによる最終診断レポート"""
        print("\n" + "="*60)
        print("🛡️  HESTIA: セキュリティ診断レポート")
        print("="*60)
        
        # Network connectivity summary
        if self.diagnosis_results["tests_performed"]:
            net_test = next((t for t in self.diagnosis_results["tests_performed"] 
                           if t["test_name"] == "network_connectivity"), None)
            
            if net_test:
                results = net_test["results"]
                
                print(f"📡 接続テスト結果 ({self.target_ip}):")
                print(f"   ICMP Ping: {self._format_status(results['ping']['status'])}")
                
                print(f"   ポート状況:")
                for port_info in results["ports"]:
                    port = port_info["port"]
                    status = "✅ OPEN" if port_info.get("open", False) else "❌ CLOSED"
                    service_name = self._get_service_name(port)
                    print(f"      {port:5d} ({service_name}): {status}")
        
        # Security analysis
        if "security_analysis" in self.diagnosis_results:
            analysis = self.diagnosis_results["security_analysis"]
            
            print(f"\n🚨 脅威レベル: {analysis['threat_level']}")
            
            if analysis["potential_causes"]:
                print(f"\n🔍 考えられる原因:")
                for cause in analysis["potential_causes"]:
                    print(f"   • {cause}")
            
            if analysis["immediate_actions"]:
                print(f"\n⚡ 緊急対応アクション:")
                for action in analysis["immediate_actions"]:
                    print(f"   1️⃣ {action}")
        
        # Hestiaの最終判定
        print(f"\n🛡️  HESTIA最終判定:")
        if "security_analysis" in self.diagnosis_results:
            threat_level = self.diagnosis_results["security_analysis"]["threat_level"]
            if threat_level == "HIGH":
                print("   ❌ 重大なセキュリティ設定問題を検出")
                print("   📋 AWS Console での Security Group 確認が必要")
                print("   🔧 インスタンス内部での診断が必要")
            else:
                print("   ⚠️  ネットワーク設定の詳細調査が必要")
        
        return self.diagnosis_results
    
    def _format_status(self, status):
        status_map = {
            "success": "✅ 正常",
            "failed": "❌ 失敗", 
            "timeout": "⏰ タイムアウト",
            "error": "💥 エラー"
        }
        return status_map.get(status, f"❓ {status}")
    
    def _get_service_name(self, port):
        service_map = {
            22: "SSH",
            55433: "Backend API",
            8001: "OpenVoice GPU",
            50021: "VOICEVOX",
            55434: "Frontend"
        }
        return service_map.get(port, "Unknown")
    
    def run_full_diagnostic(self):
        """完全な診断実行"""
        print("🛡️  Hestia: 包括的セキュリティ診断を開始")
        print("=" * 60)
        
        # Step 1: Network connectivity
        self.network_connectivity_test()
        
        # Step 2: Security analysis  
        self.analyze_security_implications()
        
        # Step 3: Generate report
        report = self.generate_hestia_report()
        
        # Save results
        with open("hestia_security_diagnosis.json", "w", encoding="utf-8") as f:
            json.dump(self.diagnosis_results, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 診断結果を hestia_security_diagnosis.json に保存")
        
        return report

if __name__ == "__main__":
    diagnostic = HestiaSecurityDiagnostic()
    
    print("🔒 Hestia: Security Guardian - EC2 Connection Diagnostic")
    print("...すべての脅威を詳細に分析します...")
    print("=" * 60)
    
    diagnostic.run_full_diagnostic()