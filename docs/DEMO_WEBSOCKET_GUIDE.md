# Running the Live Demo with Frontend

This guide explains how to run the KEMTLS + OIDC demo with real-time WebSocket streaming to the frontend.

## Architecture

```
┌──────────────┐     WebSocket      ┌──────────────┐
│   Frontend   │ ◄────────────────► │ Demo Server  │
│ (React/Vite) │  ws://localhost:   │  (Flask-WS)  │
│  Port 5173   │      5002          │  Port 5002   │
└──────────────┘                    └──────────────┘
                                            │
                                            ▼
                                    ┌──────────────┐
                                    │ demo_full    │
                                    │ _flow.py     │
                                    │ (Python)     │
                                    └──────────────┘
```

## Quick Start

### 1. Generate Keys (First Time Only)
```powershell
python scripts/generate_keys.py
```

### 2. Start Demo WebSocket Server
```powershell
python scripts/demo_server.py
```

Output:
```
============================================================
KEMTLS Demo WebSocket Server
============================================================

✓ WebSocket server starting on http://localhost:5002
✓ CORS enabled for frontend connections

Endpoints:
  • WebSocket: ws://localhost:5002
  • Health:    http://localhost:5002/health

Events:
  Client → Server: 'start_demo'
  Server → Client: 'phase_start', 'phase_complete', 'log', 'demo_complete'

Press Ctrl+C to stop
```

### 3. Start Frontend (New Terminal)
```powershell
cd frontend
npm run dev
```

Output:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

### 4. Open Browser & Run Demo

1. Navigate to: **http://localhost:5173/**
2. Wait for "Ready" status badge (green)
3. Click **"Run Demo"** button
4. Watch the phases light up in real-time!
5. View live logs in the terminal window below

## What Happens

1. **Frontend connects** to WebSocket server on mount
2. **Click "Run Demo"** → Sends `start_demo` event
3. **Demo server** executes `demo_full_flow.py` in background thread
4. **Real-time events** stream to frontend:
   - `phase_start` → Highlights current phase card (cyan glow)
   - `log` → Appends message to live terminal
   - `phase_complete` → Adds checkmark to phase card
   - `demo_complete` → Shows success summary
5. **Frontend updates** UI instantly with each event

## Event Types

### From Server → Frontend

| Event | Payload | Description |
|-------|---------|-------------|
| `connected` | `{status: 'ready'}` | Server ready |
| `demo_started` | `{timestamp}` | Demo execution began |
| `phase_start` | `{phase, name, details}` | Phase started |
| `phase_complete` | `{phase, duration}` | Phase finished |
| `log` | `{message, level, timestamp}` | Log line |
| `demo_complete` | `{success, total_time, summary}` | Demo done |
| `error` | `{message, error}` | Error occurred |

### From Frontend → Server

| Event | Payload | Description |
|-------|---------|-------------|
| `start_demo` | (none) | Trigger demo execution |

## Troubleshooting

### Frontend shows "Disconnected"
- ✅ Make sure demo server is running: `python scripts/demo_server.py`
- ✅ Check port 5002 is not in use
- ✅ Check browser console for errors

### Demo doesn't start
- ✅ Ensure keys are generated: `python scripts/generate_keys.py`
- ✅ Check demo server terminal for errors
- ✅ Verify Python dependencies: `pip install -r requirements.txt`

### Logs don't appear
- ✅ Open browser DevTools → Network → WS tab
- ✅ Verify WebSocket connection is established
- ✅ Check demo server terminal for event emissions

## Standalone Demo (No Frontend)

To run the demo without the frontend:
```powershell
python demos/demo_full_flow.py
```

This runs the same demo logic but outputs to console only.

## Files Modified/Created

### Backend
- ✅ `scripts/demo_server.py` - WebSocket server (NEW)
- ✅ `requirements.txt` - Added flask-socketio, python-socketio

### Frontend
- ✅ `src/hooks/useDemoWebSocket.ts` - WebSocket hook (NEW)
- ✅ `src/pages/Index.tsx` - Updated to use WebSocket
- ✅ `package.json` - Added socket.io-client

## Advanced: Customizing Events

Edit `scripts/demo_server.py`:

```python
# Emit custom event
emitter.socketio.emit('custom_event', {
    'data': 'your_data',
    'timestamp': time.time()
})
```

Edit `frontend/src/hooks/useDemoWebSocket.ts`:

```typescript
// Listen for custom event
socket.on('custom_event', (data) => {
    console.log('Custom event:', data);
});
```

## Performance

- **WebSocket latency**: < 1ms (local)
- **Event throughput**: ~100 events/second
- **Demo duration**: ~8-12 seconds
- **Log lines**: ~50-60 messages

## Next Steps

- Add pause/resume controls
- Implement step-by-step mode
- Add demo recording/replay
- Export logs to file
- Add multiple demo scenarios

---

**Ready to see post-quantum cryptography in action? Start the servers and click "Run Demo"!** 🚀
