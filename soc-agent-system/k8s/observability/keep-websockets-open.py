#!/usr/bin/env python3
"""
Keep WebSocket connections open for dashboard testing.
Press Ctrl+C to close all connections and exit.
"""

import asyncio
import websockets
import signal
import sys

connections = []
running = True

def signal_handler(sig, frame):
    global running
    print('\n\n🛑 Closing all WebSocket connections...')
    running = False

signal.signal(signal.SIGINT, signal_handler)

async def connect_websocket(id):
    global running
    try:
        uri = "ws://localhost:8000/ws"
        async with websockets.connect(uri) as websocket:
            print(f"✓ WebSocket {id} connected")
            connections.append(websocket)
            
            # Keep connection alive until interrupted
            while running:
                await asyncio.sleep(1)
            
            print(f"  - WebSocket {id} closing")
    except Exception as e:
        print(f"✗ WebSocket {id} failed: {e}")

async def main():
    print("=" * 50)
    print("WebSocket Connection Manager")
    print("=" * 50)
    print("\nOpening 5 persistent WebSocket connections...")
    print("These will stay open until you press Ctrl+C\n")
    
    tasks = [connect_websocket(i) for i in range(1, 6)]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    print("\n✓ All WebSocket connections closed")
    print("=" * 50)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✓ Exiting...")
        sys.exit(0)

