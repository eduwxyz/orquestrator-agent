# Quick Start Guide - Auto-Cleanup Feature Testing

## Prerequisites

Before testing, ensure:

1. **Backend server is RESTARTED** (this is critical!)
   ```bash
   # Stop current server (Ctrl+C), then:
   cd backend
   source venv/bin/activate
   python -m src.main
   ```

2. **Frontend is running**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Both servers are healthy**
   ```bash
   curl http://localhost:3001/health
   curl http://localhost:5173
   ```

---

## 5-Minute Smoke Test

### Step 1: Verify Completed Column (30 seconds)
1. Open: http://localhost:5173
2. Look for "Completed" column after "Done"
3. Click header to collapse/expand
4. ✅ Column should collapse with ▶ indicator

### Step 2: Test Settings API (1 minute)
```bash
# Get settings
curl http://localhost:3001/api/settings/auto-cleanup

# Update settings
curl -X PUT http://localhost:3001/api/settings/auto-cleanup \
  -H "Content-Type: application/json" \
  -d '{"cleanup_after_days": 5}'
```
✅ Both should return HTTP 200 with JSON

### Step 3: Test Settings UI (2 minutes)
1. Navigate to: http://localhost:5173/settings
2. Find "Auto-limpeza de Cards Concluídos" section
3. Toggle checkbox ON/OFF
4. Change days to 5
5. Refresh page (F5)
6. ✅ Settings should persist

### Step 4: Test Card Movement (1.5 minutes)
1. Create or find a card in Done
2. Drag to Completed column
3. ✅ Card should move successfully
4. Refresh page
5. ✅ Card should still be in Completed

---

## Full Test Suite

For comprehensive testing, follow:
1. **Manual Browser Tests:** See `playwright-validation-report.md` Part 3
2. **API Tests:** See `api-test-results.txt`
3. **Screenshot Documentation:** Save to `screenshots/` directory

---

## Test Report Files

- `playwright-validation-report.md` - Complete validation report with test scripts
- `api-test-results.txt` - API endpoint test results
- `QUICK_START_GUIDE.md` - This file
- `screenshots/` - Directory for test screenshots (create if needed)

---

## Expected Results

### Visual Checks
- ✅ Completed column visible on board
- ✅ Column has muted/faded appearance (opacity 0.7)
- ✅ Column is collapsible like Archived
- ✅ Settings page has auto-cleanup section
- ✅ Info box explains Completed column purpose

### Functional Checks
- ✅ Cards can move from Done to Completed
- ✅ Cards persist in Completed after refresh
- ✅ Settings toggle works and persists
- ✅ Days input validates (1-30 range)
- ✅ Invalid transitions are blocked

### API Checks
- ✅ GET /api/settings/auto-cleanup returns settings
- ✅ PUT /api/settings/auto-cleanup updates settings
- ✅ Validation rejects values outside 1-30 range
- ✅ Cards in Done have completedAt timestamp

---

## Troubleshooting

### Settings endpoints return 404
**Problem:** Backend server running old code
**Solution:** Restart backend server

### Settings don't persist after refresh
**Problem:** Settings stored in-memory (expected behavior)
**Note:** Settings will reset on server restart (this is a known limitation)

### Cards don't move to Completed
**Problem:** SDLC transition validation
**Solution:** Cards must be in Done before moving to Completed

### Completed column not visible
**Problem:** Frontend not updated
**Solution:** Hard refresh (Cmd+Shift+R or Ctrl+Shift+R)

---

## Success Criteria

The implementation is considered successful if:

1. ✅ All visual elements match the spec
2. ✅ Settings can be toggled and persist (during session)
3. ✅ Cards move correctly through workflow
4. ✅ API endpoints respond correctly
5. ✅ No console errors in browser
6. ✅ No server errors in backend logs

---

## Report Issues

If you encounter issues, document:
1. Steps to reproduce
2. Expected vs actual behavior
3. Screenshots of the issue
4. Browser console errors (F12 → Console)
5. Backend server logs

Add findings to: `test-findings.md`

---

**Happy Testing! 🚀**
