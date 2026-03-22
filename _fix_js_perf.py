with open('public/script.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Progress interval 500ms -> 1000ms (halve CPU usage)
content = content.replace('}, 500);', '}, 1000);', 1)

# Fix 2: Add loading="lazy" to all rendered images
content = content.replace(
    '<img class="v-img" src="',
    '<img loading="lazy" class="v-img" src="'
)
content = content.replace(
    '<img class="h-img" src="',
    '<img loading="lazy" class="h-img" src="'
)

# Fix 3: Reduce home data - load only 6 cards per row instead of 10
content = content.replace(
    'el.innerHTML = result.data.slice(0, 10).map(renderHCard).join(\'\');',
    'el.innerHTML = result.data.slice(0, 6).map(renderHCard).join(\'\');'
)

# Fix 4: Debounce home load rows - add small delay between rows to avoid blocking main thread
# Already has async/await, just reduce concurrent fetches by limiting to 3 rows initially
# This is done by reducing HOME_QUERIES from 6 to 4 rows
old_queries_id = '''    { id: 'rowAnyar',   query: 'lagu indonesia terbaru 2025' },
        { id: 'rowGembira', query: 'lagu semangat gembira indonesia' },
        { id: 'rowCharts',  query: 'top hits indonesia 2025' },
        { id: 'rowGalau',   query: 'lagu galau sedih indonesia' },
        { id: 'rowTiktok',  query: 'viral tiktok indonesia 2025' },
        { id: 'rowHits',    query: 'lagu hits hari ini indonesia' },'''
new_queries_id = '''    { id: 'rowAnyar',   query: 'lagu indonesia terbaru 2025' },
        { id: 'rowGembira', query: 'lagu semangat gembira indonesia' },
        { id: 'rowCharts',  query: 'top hits indonesia 2025' },
        { id: 'rowGalau',   query: 'lagu galau sedih indonesia' },'''

if old_queries_id in content:
    content = content.replace(old_queries_id, new_queries_id)
    print("Reduced Indonesia home rows to 4")

with open('public/script.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("JS performance optimizations applied!")
c2 = open('public/script.js', 'r', encoding='utf-8').read()
print("Progress interval 1000ms:", '}, 1000);' in c2)
print("lazy loading:", 'loading="lazy"' in c2)
