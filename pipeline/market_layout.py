"""Desktop layout shared by the two market homepages; research stays upstream."""
from html.parser import HTMLParser
from html import escape


def diagram(states, notes, titles, prefix='market'):
    """Reflow the existing A-share edges into a taller, readable desktop diagram."""
    positions = {'A': (20, 20), 'B': (540, 20), 'C': (20, 175), 'D': (540, 175),
                 'E': (20, 330), 'F': (280, 330), 'G': (540, 330), 'H': (280, 505)}
    paths = ['M100 120 V175', 'M590 120 V145 H180 V175', 'M710 120 V175',
             'M100 275 V330', 'M620 275 V300 H400 V330',
             'M140 430 V480 H340 V505', 'M400 430 V505', 'M660 430 V480 H460 V505']
    out = '<svg class="fw market-compact-diagram" viewBox="0 0 800 630" role="img" aria-label="A股A–H传导图"><defs>'
    out += '<marker id="'+prefix+'-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7" fill="#8592a3"/></marker></defs>'
    for path in paths:
        out += '<path d="'+path+'" fill="none" stroke="#8592a3" stroke-width="1.5" marker-end="url(#'+prefix+'-arrow)"/>'
    out += '<path d="M500 505 V465 H730 V430" fill="none" stroke="#D88B1F" stroke-dasharray="5 4" marker-end="url(#'+prefix+'-arrow)"/>'
    for k, (x, y) in positions.items():
        state = states[k]
        fill = {'up': '#FBE8E6', 'down': '#E2F2E9', 'price': '#18202B'}.get(state, '#f5f6f8')
        color = '#fff' if k == 'H' else '#18202B'
        border = {'up': '#C8312B', 'down': '#15804E'}.get(state, '#aab4c0')
        title = k + ' · ' + titles[k]
        title_lines = [title] if len(title) <= 18 else [title[:15], title[15:]]
        note = notes[k]
        note_lines = [note[i:i+18] for i in range(0, len(note), 18)]
        out += '<a href="#node-'+k+'"><rect x="'+str(x)+'" y="'+str(y)+'" width="240" height="100" rx="9" fill="'+fill+'" stroke="'+border+'"/>'
        for i, line in enumerate(title_lines):
            out += '<text x="'+str(x+12)+'" y="'+str(y+25+i*19)+'" fill="'+color+'" style="font:600 14px var(--sans)">'+escape(line)+'</text>'
        for i, line in enumerate(note_lines):
            out += '<text x="'+str(x+12)+'" y="'+str(y+64+i*17)+'" fill="'+color+'" style="font:13px var(--sans)">'+escape(line)+'</text>'
        out += '</a>'
    return out+'</svg>'


class TopLevelBlocks(HTMLParser):
    """Split rendered node HTML without changing nested tables, SVGs or text."""
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.depth = 0
        self.parts = []
        self.current = []
        self.classes = set()

    def flush(self):
        if self.current:
            self.parts.append((self.classes, ''.join(self.current)))
        self.current = []
        self.classes = set()

    def handle_starttag(self, tag, attrs):
        if self.depth == 0:
            self.flush()
            self.classes = set(dict(attrs).get('class', '').split())
        self.current.append(self.get_starttag_text())
        if tag not in self.VOID:
            self.depth += 1
        elif self.depth == 0:
            self.flush()

    def handle_endtag(self, tag):
        self.current.append('</' + tag + '>')
        self.depth -= 1
        if self.depth == 0:
            self.flush()

    def handle_startendtag(self, tag, attrs):
        self.current.append(self.get_starttag_text())
        if self.depth == 0:
            self.flush()

    def handle_data(self, data):
        self.current.append(data)

    def handle_entityref(self, name):
        self.current.append('&' + name + ';')

    def handle_charref(self, name):
        self.current.append('&#' + name + ';')


def node_columns(body):
    parser = TopLevelBlocks()
    parser.feed(body)
    parser.flush()
    evidence, judgment = [], []
    for classes, fragment in parser.parts:
        (judgment if classes & {'verdict', 'rules'} else evidence).append(fragment)
    if not ''.join(evidence).strip() or not judgment:
        return body
    return ('<div class="market-node-columns"><div class="market-node-data">'
            '<h4 class="column-label">数据与变化</h4>' + ''.join(evidence)
            + '</div><aside class="market-node-reason"><h4 class="column-label">判断依据与规则</h4>'
            + ''.join(judgment) + '</aside></div>')


def shell(body, market, prefix):
    return '<div class="market-research"><div class="market-content">'+body+'</div></div>'
