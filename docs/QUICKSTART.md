# 🚀 Quick Start Guide - WebSocket Demo

## Prerequisites Check

Run this first:
```powershell
python scripts/check_setup.py
```

This verifies:
- ✅ Keys generated
- ✅ Python dependencies installed
- ✅ Frontend dependencies installed
- ✅ Ports 5002 and 5173 available

## Running the Demo (3 Steps)

### Step 1: Start Demo Server
```powershell
python scripts/demo_server.py
```

You should see:
```
============================================================
KEMTLS Demo WebSocket Server
============================================================

✓ WebSocket server starting on http://localhost:5002
✓ CORS enabled for frontend connections
```

**Keep this terminal open!**

### Step 2: Start Frontend (New Terminal)
```powershell
cd frontend
npm run dev
```

You should see:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
```

**Keep this terminal open!**

### Step 3: Open Browser & Run
1. Open: **http://localhost:5173/**
2. Wait for **"Ready"** status (green badge, Wifi icon)
3. Click **"Run Demo"** button
4. Watch the magic happen! ✨

## What You'll See

1. **Phase 1 card lights up** (cyan glow) - KEMTLS Handshake
2. **Logs stream in real-time** below the phase cards
3. **Phase 1 completes** (green checkmark)
4. **Phases 2-4 execute** sequentially
5. **Success message** - "🎉 POST-QUANTUM OIDC + KEMTLS COMPLETE!"

## Troubleshooting

### "Disconnected" status in browser
→ Make sure demo server is running (Step 1)

### Demo doesn't start
→ Check demo server terminal for errors
→ Ensure keys exist: `python scripts/generate_keys.py`

### No logs appearing
→ Check browser console (F12) for errors
→ Verify WebSocket connection in DevTools → Network → WS

## Terminal Layout

Recommended terminal setup:

```
┌─────────────────────────────┬─────────────────────────────┐
│                             │                             │
│   Terminal 1                │   Terminal 2                │
│                             │                             │
│   python scripts/           │   cd frontend               │
│   demo_server.py            │   npm run dev               │
│                             │                             │
│   [Demo Server Logs]        │   [Vite Dev Server]         │
│                             │                             │
└─────────────────────────────┴─────────────────────────────┘
                      
                  Browser: http://localhost:5173/
```

## Files You Created

**Backend:**
- ✅ `scripts/demo_server.py` - WebSocket server (450+ lines)
- ✅ `scripts/start_demo.py` - Quick launcher
- ✅ `scripts/check_setup.py` - Status checker

**Frontend:**
- ✅ `src/hooks/useDemoWebSocket.ts` - WebSocket React hook (120+ lines)
- ✅ Updated `src/pages/Index.tsx` - Integrated WebSocket

**Docs:**
- ✅ `DEMO_WEBSOCKET_GUIDE.md` - Detailed guide
- ✅ `IMPLEMENTATION_SUMMARY.md` - Technical summary
- ✅ `QUICKSTART.md` - This file

## Next: Record Your Video! 🎥

The demo now shows:
- ✅ Real cryptographic operations
- ✅ Actual execution timing
- ✅ Live logs from Python backend
- ✅ Phase-by-phase progression with visual feedback

Perfect for your demo video! 🎬

## Need Help?

Check the detailed guides:
- **User Guide**: `DEMO_WEBSOCKET_GUIDE.md`
- **Technical Details**: `IMPLEMENTATION_SUMMARY.md`
- **Project Overview**: `README.md`

---

**Ready? Run the 3 steps above and enjoy the show!** 🚀
