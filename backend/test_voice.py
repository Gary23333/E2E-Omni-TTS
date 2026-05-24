import asyncio
import websockets
import json
import base64

async def test_call():
    uri = "ws://localhost:8900/ws/voice/test_session"
    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket")
        
        # Start call
        start_msg = {
            "type": "start_call",
            "scenario": "inbound",
            "agentGroupId": ""
        }
        await websocket.send(json.dumps(start_msg))
        print("Sent start_call")
        
        # Listen for messages
        async for message in websocket:
            if isinstance(message, str):
                data = json.loads(message)
                print(f"Received: {data['type']}")
                
                if data['type'] == 'transcript_entry' and data['role'] == 'agent':
                    print(f"Agent greeting: {data['text']}")
                    
                    # Send text input
                    text_msg = {
                        "type": "text_input",
                        "text": "你好，我想咨询一下业务。"
                    }
                    await websocket.send(json.dumps(text_msg))
                    print("Sent text_input")
                
                if data['type'] == 'llm_token':
                    pass # Just ignore tokens for brevity
                
                if data['type'] == 'llm_done':
                    print("LLM finished response")
                
                if data['type'] == 'tts_done':
                    print("TTS finished")
                    break # End test after first full response
            else:
                # Binary audio chunk
                print(f"Received audio chunk: {len(message)} bytes")

if __name__ == "__main__":
    asyncio.run(test_call())
