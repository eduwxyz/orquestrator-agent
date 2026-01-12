# Fix Instructions for Chat UI Improvements

## 🔴 Critical Issue #1: Markdown Not Rendering

### Problem
Markdown is displaying as plain text instead of rendered HTML.

### Root Cause
Frontend likely needs rebuild after adding react-markdown dependencies, or browser cache is serving old version.

### Solution Steps

```bash
# Step 1: Navigate to frontend directory
cd /Users/eduardo/Documents/youtube/orquestrator-agent/.worktrees/card-0e87acd6/frontend

# Step 2: Clean build artifacts
rm -rf node_modules dist .vite

# Step 3: Fresh install
npm install

# Step 4: Verify dependencies
npm list react-markdown remark-gfm react-syntax-highlighter
# Should show:
# react-markdown@10.1.0
# remark-gfm@4.0.1
# react-syntax-highlighter@16.1.0

# Step 5: Start dev server
npm run dev

# Step 6: Open browser in INCOGNITO/PRIVATE mode
# Visit: http://localhost:5173
# Click "Abrir Chat AI"
# Send a test message with markdown:
# Test: **bold** and `code`

# Step 7: If still not working, check browser console for errors
```

### Verification
After fix, you should see:
- `**bold**` renders as **bold text**
- `` `code` `` renders with cyan background
- `# Heading` renders as large heading
- Code blocks have syntax highlighting

---

## 🔴 Issue #2: OpenAI Model in Selector

### Problem
GPT-4 Turbo (OpenAI) appears in model dropdown, should only show Anthropic + Gemini.

### Investigation Steps

```bash
# Step 1: Check source code (already verified - code is correct)
cd /Users/eduardo/Documents/youtube/orquestrator-agent/.worktrees/card-0e87acd6/frontend
grep -r "gpt" src/components/Chat/ModelSelector.tsx
# Should return no results

# Step 2: Check for other model configuration files
find src -name "*model*" -type f
grep -r "GPT-4" src/

# Step 3: Check if backend is providing model list
# Open browser DevTools Network tab
# Click model selector
# Look for API calls fetching models

# Step 4: Clear browser storage
# Open browser console (F12)
# Run:
localStorage.clear();
sessionStorage.clear();
location.reload(true);

# Step 5: Check .env files
cat .env.local .env.development 2>/dev/null | grep -i model
```

### Possible Fixes

**If it's cached data:**
```javascript
// In browser console:
localStorage.removeItem('availableModels');
localStorage.removeItem('modelCache');
sessionStorage.clear();
location.reload(true);
```

**If backend is providing models:**
```bash
# Check backend model configuration
cd /Users/eduardo/Documents/youtube/orquestrator-agent/.worktrees/card-0e87acd6/backend
grep -r "gpt-4" . --include="*.ts" --include="*.js"
```

**If environment variable:**
```bash
# Check for AVAILABLE_MODELS or similar env vars
env | grep -i model
```

### Verification
After fix, model dropdown should show ONLY:
- Opus 4.5 (Anthropic)
- Sonnet 4.5 (Anthropic)
- Haiku 4.5 (Anthropic)
- Claude 3 Sonnet (Anthropic)
- Claude 3 Opus (Anthropic)
- Gemini 3 Pro (Google)
- Gemini 3 Flash (Google)

GPT-4 Turbo should NOT appear.

---

## Re-run Validation

After applying fixes:

```bash
cd /Users/eduardo/Documents/youtube/orquestrator-agent/.worktrees/card-0e87acd6

# Run validation again
npx playwright test test-reports/playwright/2026-01-12_17-01-37/markdown-test.spec.ts --reporter=list

# Expected output:
# Headings: 3+ ✓
# Code blocks: 2+ ✓
# Links: 1+ ✓
# Tables: 1+ ✓
```

---

## Quick Manual Test

1. Open http://localhost:5173 in **incognito window**
2. Click "Abrir Chat AI"
3. Type this message:
   ```
   # Test
   **bold** and *italic*
   `code`
   ```
4. Send message
5. Check if it renders properly (not as plain text)
6. Click model dropdown
7. Verify no OpenAI/GPT models appear

---

## If Issues Persist

### Markdown Still Not Rendering

1. Check ChatMessage.tsx is actually being used:
   ```bash
   grep -r "ChatMessage" src/components/Chat/
   ```

2. Check for TypeScript/JSX compilation errors:
   ```bash
   npm run build
   # Look for errors in output
   ```

3. Check React DevTools:
   - Install React DevTools browser extension
   - Inspect ChatMessage component
   - Check if ReactMarkdown component is in tree

4. Check for conflicting CSS:
   ```bash
   grep -r "white-space: pre" src/components/Chat/
   # pre-wrap or pre styles can prevent markdown rendering
   ```

### Model Still Shows OpenAI

1. Check if there's a model API endpoint:
   ```bash
   # Search for API calls
   grep -r "/api/models" src/
   grep -r "fetchModels" src/
   ```

2. Monitor network requests:
   - Open DevTools Network tab
   - Click model selector
   - Check if any API calls are made
   - Inspect response payload

3. Check Redux/Context state (if using state management):
   ```bash
   grep -r "useContext" src/components/Chat/
   grep -r "useSelector" src/components/Chat/
   ```

---

## Contact for Help

If both fixes don't work, provide:
1. Browser console errors (if any)
2. Network tab requests (when opening model selector)
3. Output of `npm list react-markdown`
4. Screenshot of rendered message
5. Screenshot of model dropdown

---

## Estimated Fix Time

- Markdown rendering fix: 5-10 minutes (clean install + rebuild)
- Model filtering fix: 10-20 minutes (investigation + cache clear)
- Total: 15-30 minutes

---

## Success Criteria

When both issues are fixed:
- Markdown message shows proper HTML rendering
- Model selector shows exactly 8 models (5 Anthropic + 2 Gemini + 1 Claude 3)
- No OpenAI models visible
- All validation tests pass

Run final validation:
```bash
npx playwright test test-reports/playwright/2026-01-12_17-01-37/complete-validation.spec.ts
```

Should output:
```
✓ AC1: Markdown rendering - PASSED
✓ AC2: Model filtering - PASSED
✓ AC3: Dark theme - PASSED
✓ AC4: Responsive - PASSED
✓ AC5: Streaming - PASSED

All tests passed!
```
