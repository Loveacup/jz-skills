# Mobile PDF Layout Research · 2026-06-01

> Session: diary PDF generation + newsletter theme optimization
> Sources: Responsive PDF (pdf.leandre.io), 2026 Newsletter Design Guides (dupple.com, tajo.io), Playwright page.pdf() API

## Key Findings

### Typography for Mobile PDF

| Element | Before (v1 newsletter) | After (v2) | Source |
|:---|:---:|:---:|:---|
| Body | 15px | **16px** | Mobile minimum readable standard |
| H1 | 20px | 22px | Hierarchy differentiation |
| H2 | 17px | 18px | |
| Line-height | 1.8 | 1.8 | Good for CJK, kept unchanged |
| Paragraph margin | 6px | 8px | Visual breathing room |

### Layout for 430px pages

| Element | Before | After | Rationale |
|:---|:---:|:---:|:---|
| @page margin | 20mm (硬编码) | 12mm (mobile) / 20mm (A4) | 20mm = 75px on 430px = 35% wasted width |
| Max body width | 430px | 430px | Unchanged |

### Playwright page.pdf() API Gotcha

`page.pdf()` accepts:
- ✅ `format: 'A4'` (predefined string)
- ✅ `width: '430px', height: '932px'` (separate params)
- ❌ `format: { width: '430px', height: '932px' }` (object — NOT supported)

The fix: generate `pw_format` as a complete property string (`format: 'A4'` or `width: '430px', height: '932px'`) and remove the hardcoded `format:` prefix from the JS template.

### CJK-specific concerns

- Avoid italic for CJK body text — characters become hard to read
- Line-height ≥1.8 prevents vertical overlap of tall characters
- Bold should be used sparingly — CJK glyphs lose detail when bolded
- System fonts (PingFang SC, Hiragino Sans GB) preferred over serif for screen reading
