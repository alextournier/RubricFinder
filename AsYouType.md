# "As You Type" Search - Feasibility Study

## Goal
Evaluate whether real-time search results can be displayed as the user types.

## Verdict: Feasible

| Aspect | Assessment |
|--------|------------|
| Mechanism support | `st.session_state` + conditional logic sufficient |
| Performance | ~40ms per search is below perception threshold (<100ms) |
| Debouncing | Simple timestamp pattern works |
| Implementation | ~20-30 lines of code |
| Streamlit Cloud | Adds 50-150ms latency (still acceptable) |

## Current Behavior
- `st.text_input()` triggers full script rerun on every change
- Embedder is cached (`@st.cache_resource`) - good
- Query embedding (`model.encode()`) runs fresh each time - the ~40ms cost

## Recommended Implementation

**Approach:** Session-state debouncing (no callbacks needed)

```python
# Session state initialization
if "last_query" not in st.session_state:
    st.session_state.last_query = ""
    st.session_state.last_results = []

query = st.text_input("...", placeholder="...")

# Only search if: query changed, >= 3 chars, debounce passed
if query and len(query) >= 3 and query != st.session_state.last_query:
    start_time = time.time()
    results = embedder.search(query, top_k=10)
    elapsed = time.time() - start_time

    st.session_state.last_query = query
    st.session_state.last_results = results
else:
    results = st.session_state.last_results

# Display results (using cached or fresh)
```

## Key Design Decisions
1. **Minimum 3 characters** - filters noise from partial typing
2. **No time-based debounce** - Streamlit's rerun cadence (~100ms) naturally throttles
3. **Cache last results** - avoids re-search when deleting characters back to previous query
4. **Keep timer display** - shows responsiveness to user

## Files to Modify
- `frontend/app.py`

## Verification
1. Run `streamlit run frontend/app.py`
2. Type slowly - results should appear after 3rd character
3. Type quickly - should not lag or freeze
4. Delete back to previous query - should show cached results instantly
5. Test on Streamlit Cloud after deploy

## Tradeoffs
- **Pro:** More responsive UX, feels modern
- **Con:** More API/embedding calls (mitigated by 3-char minimum)
- **Con:** Slightly more code complexity

## Status
Ready for implementation in a future session.
