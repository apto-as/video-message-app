import httpx
import asyncio
import base64
import wave
import io

async def test_synthesis():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test synthesis
        response = await client.post(
            'http://3.115.141.166:8001/voice-clone/synthesize',
            data={
                'text': 'こんにちは、これは音声合成のテストです。',
                'voice_profile_id': 'openvoice_78450a3c',
                'language': 'ja',
                'speed': 1.0
            }
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success') and result.get('audio_data'):
                # Decode audio
                audio_data = base64.b64decode(result['audio_data'])
                print(f"Success! Audio size: {len(audio_data)} bytes")
                
                # Save to file
                with open('test_output.wav', 'wb') as f:
                    f.write(audio_data)
                print("Saved to test_output.wav")
            else:
                print(f"Error: {result.get('error', 'Unknown error')}")
        else:
            print(f"HTTP Error: {response.text}")

asyncio.run(test_synthesis())
