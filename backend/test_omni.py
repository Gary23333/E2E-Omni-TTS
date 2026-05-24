import asyncio
import websockets
import json
import base64
import struct

def get_wav_header(pcm_data: bytes, sample_rate: int = 16000) -> bytes:
    header = b'RIFF'
    header += struct.pack('<I', 36 + len(pcm_data))
    header += b'WAVEfmt '
    header += struct.pack('<I', 16)
    header += struct.pack('<H', 1)
    header += struct.pack('<H', 1)
    header += struct.pack('<I', sample_rate)
    header += struct.pack('<I', sample_rate * 2)
    header += struct.pack('<H', 2)
    header += struct.pack('<H', 16)
    header += b'data'
    header += struct.pack('<I', len(pcm_data))
    return header + pcm_data

async def test_omni():
    uri = "ws://localhost:8900/ws/voice/test_omni_session"
    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket (Omni Test)")
        
        # Start call
        start_msg = {
            "type": "start_call",
            "scenario": "inbound",
            "agentGroupId": ""
        }
        await websocket.send(json.dumps(start_msg))
        
        # Wait for greeting to finish
        async for message in websocket:
            if isinstance(message, str):
                data = json.loads(message)
                if data['type'] == 'tts_done':
                    print("Greeting finished. Sending voice input...")
                    break
        
        # Simulate voice input: 1 second of silence (16000 samples * 2 bytes)
        silence_pcm = b'\x00' * 32000
        # In real client, we send chunks
        # Send audio_chunk (base64)
        chunk_msg = {
            "type": "audio_chunk",
            "data": base64.b64encode(silence_pcm).decode('utf-8')
        }
        await websocket.send(json.dumps(chunk_msg))
        
        # Send audio_end
        end_msg = {"type": "audio_end"}
        await websocket.send(json.dumps(end_msg))
        print("Sent voice input and audio_end")
        
        # Wait for response
        async for message in websocket:
            if isinstance(message, str):
                data = json.loads(message)
                print(f"Received: {data['type']}")
                if data['type'] == 'transcript_entry' and data['role'] == 'user':
                    print(f"User (Voice) identified as: {data['text']}")
                if data['type'] == 'transcript_entry' and data['role'] == 'agent':
                    print(f"Agent response: {data['text']}")
                if data['type'] == 'tts_done':
                    print("Omni response finished")
                    break
            else:
                # Binary audio
                pass

if __name__ == "__main__":
    asyncio.run(test_omni())
