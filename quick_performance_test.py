#!/usr/bin/env python3
"""
Artemis - Quick Performance Test for EC2 GPU Instance
"""

import requests
import time
import json
from datetime import datetime

def quick_connectivity_test():
    """Quick connectivity test"""
    base_url = "http://18.118.69.100"
    services = {
        "Backend": f"{base_url}:55433/health",
        "OpenVoice": f"{base_url}:8001/health", 
        "VOICEVOX": f"{base_url}:50021/version"
    }
    
    print("🔍 Artemis: Quick Service Connectivity Test")
    print("=" * 50)
    
    results = {}
    for service, url in services.items():
        try:
            print(f"Testing {service}... ", end="", flush=True)
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                results[service] = True
                print("✅ OK")
            else:
                results[service] = False
                print(f"❌ HTTP {response.status_code}")
        except requests.exceptions.ConnectionError:
            results[service] = False  
            print("❌ Connection refused")
        except requests.exceptions.Timeout:
            results[service] = False
            print("❌ Timeout")
        except Exception as e:
            results[service] = False
            print(f"❌ Error: {e}")
    
    return results

def test_voicevox_performance():
    """Test VOICEVOX performance specifically"""
    print("\n⚡ Artemis: VOICEVOX Performance Test")
    print("=" * 50)
    
    base_url = "http://18.118.69.100:50021"
    test_text = "パフォーマンステストです"
    speaker = 1
    
    try:
        print(f"Testing synthesis: '{test_text}' with speaker {speaker}")
        start_time = time.perf_counter()
        
        # Generate audio query
        audio_query_response = requests.post(
            f"{base_url}/audio_query",
            params={"text": test_text, "speaker": speaker},
            timeout=10
        )
        
        if audio_query_response.status_code != 200:
            print(f"❌ Audio query failed: {audio_query_response.status_code}")
            return None
            
        # Synthesize
        synthesis_response = requests.post(
            f"{base_url}/synthesis",
            params={"speaker": speaker},
            json=audio_query_response.json(),
            timeout=15
        )
        
        end_time = time.perf_counter()
        processing_time = end_time - start_time
        
        if synthesis_response.status_code == 200:
            audio_size = len(synthesis_response.content)
            print(f"✅ Success! Processing time: {processing_time:.3f} seconds")
            print(f"   Audio size: {audio_size:,} bytes")
            
            # Performance evaluation
            if processing_time <= 2.0:
                grade = "🏆 EXCELLENT - Target achieved!"
            elif processing_time <= 5.0:
                grade = "👍 GOOD - Acceptable performance"
            else:
                grade = "⚠️  NEEDS IMPROVEMENT"
                
            print(f"   Artemis Grade: {grade}")
            
            return {
                "processing_time": processing_time,
                "audio_size": audio_size,
                "target_achieved": processing_time <= 2.0,
                "grade": grade
            }
        else:
            print(f"❌ Synthesis failed: {synthesis_response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return None

def main():
    print("🏹 Artemis: Quick EC2 GPU Performance Validation")
    print("Target: <2 second voice synthesis (vs. 15 seconds baseline)")
    print("=" * 60)
    
    # Connectivity test
    connectivity = quick_connectivity_test()
    
    # Performance test
    performance = test_voicevox_performance()
    
    # Summary
    print("\n📊 ARTEMIS PERFORMANCE SUMMARY")
    print("=" * 60)
    
    print("🔗 Service Status:")
    for service, status in connectivity.items():
        print(f"   {service}: {'✅ Online' if status else '❌ Offline'}")
    
    if performance:
        print(f"\n⚡ Performance Results:")
        print(f"   Processing Time: {performance['processing_time']:.3f} seconds")
        print(f"   Target (<2s): {'✅ ACHIEVED' if performance['target_achieved'] else '❌ MISSED'}")
        print(f"   Grade: {performance['grade']}")
        
        improvement = ((15.0 - performance['processing_time']) / 15.0) * 100
        speed_multiplier = 15.0 / performance['processing_time']
        print(f"   Improvement: {improvement:.1f}% faster than baseline")
        print(f"   Speed multiplier: {speed_multiplier:.1f}x")
    else:
        print("\n❌ Performance test failed - service issues detected")
    
    # Save results
    results = {
        "timestamp": datetime.now().isoformat(),
        "connectivity": connectivity,
        "performance": performance,
        "test_type": "quick_validation"
    }
    
    with open("quick_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: quick_test_results.json")
    
    # Final Artemis judgment
    print("\n🎯 ARTEMIS FINAL JUDGMENT:")
    if performance and performance['target_achieved']:
        print("   ✅ PERFORMANCE TARGET ACHIEVED")
        print("   GPU migration is a SUCCESS!")
    elif connectivity.get('VOICEVOX', False):
        print("   ⚠️  Service online but performance needs verification")
    else:
        print("   ❌ Service connectivity issues - investigate required")

if __name__ == "__main__":
    main()