from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Response
from fastapi.responses import HTMLResponse
import uvicorn
import cv2
import numpy as np
from pyzbar.pyzbar import decode, ZBarSymbol
import base64

app = FastAPI()

# Serve the HTML frontend
@app.get("/", response_class=HTMLResponse)
async def get():
    with open('index.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    return HTMLResponse(content=html_content, media_type='text/html')

# WebSocket endpoint for receiving frames and sending back QR data
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Receive base64-encoded JPEG image
            data = await websocket.receive_text()
            if data.startswith('data:image'):
                data = data.split(',')[1]

            # Decode base64 to bytes and convert to image
            img_bytes = base64.b64decode(data)
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # Preprocess: convert to grayscale and apply sharpening
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Sharpening kernel
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            sharpened = cv2.filter2D(gray, -1, kernel)

            # Decode only QR codes to suppress warnings
            decoded = decode(sharpened, symbols=[ZBarSymbol.QRCODE])
            results = [d.data.decode('utf-8') for d in decoded]

            # Send JSON list of codes
            await websocket.send_json({"codes": results})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print("Error in WebSocket loop:", e)
        await websocket.close()

if __name__ == "__main__":
    uvicorn.run(
        app,
        host='0.0.0.0',
        port=8000)