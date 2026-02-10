# www/non-www Variant Testing Update

## Problem Identified

**You asked:** "Does this tool look for http/https as well as www & non-www variations?"

**Answer Before:** 
- ✅ YES to http/https (HTTPS first, HTTP fallback)
- ❌ NO to www/non-www variations

**Why This Caused Errors:**
Your domain list has a mix:
- 15,000 domains **without** `www.` prefix (e.g., `example.gov`)
- 3,723 domains **with** `www.` prefix (e.g., `www.example.gov`)

Many government sites are configured such that:
- `example.gov/publiccode.yml` returns 404
- BUT `www.example.gov/publiccode.yml` works (or vice versa)

The old crawler only tested the **exact domain** from the CSV, missing these variations.

---

## Solution Implemented

The crawler now tests **www/non-www variations** automatically:

### Discovery Flow

1. **Try primary domain** (as listed in CSV)
   - Test HTTPS with all 4 paths
   - Fall back to HTTP with all 4 paths

2. **If not found, try alternate domain**
   - If CSV has `example.gov`, also try `www.example.gov`
   - If CSV has `www.example.gov`, also try `example.gov`
   - Test HTTPS and HTTP fallback

3. **Record results** under original domain name

### Example

**CSV entry:** `admin.ch`

**Tests performed:**
1. `https://admin.ch/publiccode.yml` ← fails
2. `https://admin.ch/.well-known/publiccode.yml` ← fails
3. `https://admin.ch/publiccode.yaml` ← fails
4. `https://admin.ch/.well-known/publiccode.yaml` ← fails
5. `http://admin.ch/publiccode.yml` ← fails
6. `http://admin.ch/.well-known/publiccode.yml` ← fails
7. `http://admin.ch/publiccode.yaml` ← fails
8. `http://admin.ch/.well-known/publiccode.yaml` ← fails
9. **Then try:** `https://www.admin.ch/publiccode.yml` ← might succeed!
10. (continues with www variant...)

---

## Configuration

You can control this behavior in `config.py`:

```python
# Domain Variation Testing
TEST_WWW_VARIATIONS = True  # Test both www. and non-www. versions of domains
```

Set to `False` to disable www variation testing (not recommended).

---

## Impact on Error Rates

**Before this update:**
- Many "not found" errors were actually **missed discoveries**
- False negatives when www variant exists

**After this update:**
- Discovers files on www variants
- Reduces false "not found" errors
- More accurate discovery rate

---

## Performance Impact

**Requests per domain:**
- **Without www testing:** Up to 8 requests (4 paths × 2 protocols)
- **With www testing:** Up to 16 requests (8 + 8 for alternate)

**But most domains short-circuit:**
- If found on primary domain: Only 1-8 requests
- www variant only tested if primary fails
- Still respects rate limiting and timeouts

**Estimated time increase:** Minimal (~10-20% longer) because:
- Most domains either work immediately or don't have files
- www testing only happens after primary fails
- Parallel processing handles the extra requests

---

## AGENTS.md Compliance

This enhancement aligns with AGENTS.md:

✅ **Discovery Rules** - Tests documented paths on reasonable variations
✅ **Follow redirects** - Many sites redirect www ↔ non-www, but some don't
✅ **Conservative approach** - Only tests one alternate variant, not all possibilities
✅ **Transparent** - All tested URLs logged

**Does NOT violate:**
- Still only tests predefined paths (no crawling)
- No guessing of additional subdomains
- Stays within reasonable discovery scope

---

## Files Modified

1. **crawler.py**
   - Added `_get_alternate_domain()` method
   - Added `_try_domain()` method
   - Enhanced `discover()` to test www variations

2. **config.py**
   - Added `TEST_WWW_VARIATIONS` setting

3. **README.md**
   - Updated discovery documentation

---

## Testing

The logic correctly handles:

| Original Domain      | Alternate Domain   |
|----------------------|--------------------|
| `example.gov`        | `www.example.gov`  |
| `www.example.gov`    | `example.gov`      |
| `admin.ch`           | `www.admin.ch`     |
| `www.admin.ch`       | `admin.ch`         |

---

## Next Steps

**Recommendation:** Re-run the discovery with www variant testing enabled.

```bash
source venv/bin/activate
python3 main.py --input eu_gov_domains.csv --output results_with_www.csv
```

You should see:
- Fewer "not found" errors
- Higher discovery rate
- Files found on www variants noted in logs

---

## Why This Matters

Government domains often have inconsistent www configuration:
- Some only work with `www.`
- Some only work without `www.`
- Some redirect between them
- Some don't redirect and just fail

Testing both variations ensures we don't miss valid publiccode.yml files due to subdomain configuration differences.
