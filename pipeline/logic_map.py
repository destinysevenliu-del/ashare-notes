"""选股逻辑地图：按“什么在推动股价上涨”给A股、港股的选股逻辑分类，写清每条的定义、上涨动力、有效与失效条件、证据、执行信号和本站覆盖情况。
页面：docs/stocks/logic-map.html（个股页两层导航上方有入口）。
内容为研究结论，改动时同步改交接文档；证据只写已核对的来源。
"""
from pathlib import Path
from html import escape as E
import stockpick as SP

# 上涨动力分类：股价＝每股利润×估值；资金与事件改变短期供求；情绪改变短期定价。
GROUPS = [
    ('fz', '分子：利润在涨', '股价跟着公司赚的钱走。关键是利润（或利润预期）变化，而且市场还没有完全反映。'),
    ('fm', '分母：估值在变', '利润不变，市场愿意给的价格变了。驱动是利率、股息率、政策对估值的要求，或同一公司在两地的价差。'),
    ('sl', '水龙头：资金在买', '谁在买、买多少。机构逐步建仓带来趋势，被动资金和托底资金决定短期供求。'),
    ('sj', '事件：有明确的买方或时点', '公司或大股东真金白银买入、私有化要约、并购重组。上涨动力有明确的发起人和兑现时间。'),
    ('qx', '情绪：注意力在追', '题材、小市值、高换手。上涨靠散户注意力和流动性，来得快、去得也快。'),
]

# 状态：已覆盖 / 部分覆盖 / 缺口（建议补） / 不做
LOGICS = [
    {'id': 'cycle', 'g': 'fz', 'name': '景气顺势', 'mkt': 'A股、港股',
     'def': '大盘和行业驱动处于顺风时，在行业里买基本面最好、价格不贵的公司。',
     'drive': '行业利润上升：产品价格上涨或销量增长，公司利润随之增长，股价跟随利润。',
     'works': '行业驱动刚转向、市场还没有完全定价（本站称“前半段”）。',
     'fails': '驱动见顶、行业估值分位已高、成交拥挤。',
     'evidence': '中国市场存在盈利公告后漂移：利润超预期的股票在公告后继续上涨，市场上涨期和小盘、价值股更明显，原因是散户注意力有限（Chen, Gao & Liu, 2021）。',
     'signal': '板块档位（顺风、前半段）＋个股六层判断链（板块、初筛、核验、估值、价格、筹码）。',
     'status': '已覆盖', 'where': 'A股、港股“分子 · 景气顺势”', 'href': 'index.html',
     'verify': '每周对账：已触发买入的候选，13周后相对板块指数的超额收益。'},
    {'id': 'growth', 'g': 'fz', 'name': '长期成长', 'mkt': 'A股、港股',
     'def': '收入能连续多年高速增长的公司（技术替代、渗透率提升），愿意为未来利润付较高估值。',
     'drive': '长期利润增长；但估值高，对利率和风险偏好敏感，所以同时受分母影响。',
     'works': '行业需求开关打开（如订单、渗透率拐点），且利率不再上行。',
     'fails': '增长兑现慢于预期、利率上行、估值已透支。',
     'evidence': '本站A股成长板块（半导体、算力硬件、创新药）以“开关”判断：开关打开前任何价格都不买。',
     'signal': '开关条件＋价格先站上60日均线。',
     'status': '部分覆盖', 'where': 'A股景气顺势里的“等开关”板块', 'href': 'index.html#logic1',
     'verify': '开关打开后的候选，按同一买点回测；开关关闭期的候选作为对照。'},
    {'id': 'revision', 'g': 'fz', 'name': '业绩反转与预期上调', 'mkt': 'A股、港股',
     'def': '盈利预期正在被上调、而股价和财报还没有完全反映的公司；包括行业已经反转、自己利润还在谷底的落后者。',
     'drive': '机构上调盈利预测，市场按新的利润重新计算估值。',
     'works': '以机构定价为主的市场；同一行业多家公司同时被上调；股价已开始确认。',
     'fails': '上调来自一次性收益或并表；空头在增加；只有机构对单个公司“明年大增”的预测而行业没有跟上。',
     'evidence': '中国分析师的评级上调和下调有信息含量，2004—2015年按上调做多、下调做空的组合年化超额8.1%，对小公司和首次覆盖更明显（Chi, 2018）。本站港股回测：行业上调广度＞0.2、利润仍下降、站上26周均线，46个样本13周超额中位数+9.6%；用公开财报定义的反转反而跑输。本站A股回测（2025-11至2026-08）：机构上调组相对中位数−1.8%、下调组反而+1.5%；财报确认单季利润由负转正、股价仍在26周均线下方、回撤小于25%的779个样本中位数+4.2%、跑赢65%。两地相反，与“港股机构定价有动量、A股散户为主短期反转”一致。',
     'signal': '港股：行业上调广度＋个股利润仍下降＋站上26周均线＋空头不增加。A股：财报确认单季利润由负转正＋股价仍在26周均线下方＋回撤小于25%（A股机构预测上调在本站回测中无效）。',
     'status': '已覆盖', 'where': 'A股、港股“分子 · 业绩反转”（两地规则不同）', 'href': 'a-turn.html',
     'verify': '用A股研报盈利预测数据，按港股同一口径回测；样本足够后每季度滚动复核。'},
    {'id': 'dividend', 'g': 'fm', 'name': '红利与高股息', 'mkt': 'A股、港股',
     'def': '分红稳定、股息率明显高于国债收益率的公司，当作“债券替代”持有。',
     'drive': '无风险利率下行时，股息率相对国债的吸引力上升，保险等长期资金配置。',
     'works': '10年国债收益率下行、经济偏弱、分红率稳定或提高。',
     'fails': '利率上行、分红被削减、成交过度拥挤。',
     'evidence': '本站回测：A股股息率4%—12%的2097个样本13周相对中位数超额+5.1%、跑赢67%；港股股息率5%—15%的1341个样本中位数+2.0%，其中已站上26周均线的+3.9%；港股股息率超过15%的中位数−15.1%（陷阱）。跟踪A股红利策略的资产从2013年约20亿元增至2023年末约420亿元（标普道琼斯指数）。本站银行板块以“股息率－10年国债”定买卖价，成交拥挤度超过95%时暂停新增。港股通个人投资者买H股的红利要缴20%税，同一公司有时买A股更划算。',
     'signal': '税后股息率－10年国债利差；分红可持续性（分红率×利润增速）；拥挤度。',
     'status': '已覆盖', 'where': 'A股、港股“分母 · 红利高股息”（银行已从景气顺势移入）', 'href': 'dividend.html',
     'verify': '按“股息率－国债利差”分档，看各档随后的超额收益；分红削减作为失效事件单独统计。'},
    {'id': 'rerate', 'g': 'fm', 'name': '估值修复（破净与市值管理）', 'mkt': 'A股为主',
     'def': '长期低于净资产交易、现金充足的公司，在政策要求下提高分红、回购，估值向净资产回归。',
     'drive': '监管把估值纳入要求：主要指数成分股须制定市值管理制度，长期破净公司须披露估值提升计划（证监会《上市公司监管指引第10号——市值管理》，2024-11-15发布）。',
     'works': '政策执行期，且公司真的提高分红或回购。',
     'fails': '只发计划、不落实；净资产本身在缩水（亏损、减值）。',
     'evidence': '指引写明分红、回购、控股股东增持是估值提升的工具，但没有规定具体比例，所以要逐家看兑现。',
     'signal': '市净率＜1＋估值提升计划已披露＋分红或回购实际兑现。',
     'status': '部分覆盖', 'where': 'A股“分母 · 估值修复（国资箱体）”：已加分红是否提高；估值提升计划是否披露尚无数据源', 'href': 'box.html',
     'verify': '对比“披露计划且兑现”与“只披露未兑现”的破净公司，随后一年的超额收益。'},
    {'id': 'ah', 'g': 'fm', 'name': '两地比价（A股与H股）', 'mkt': '港股',
     'def': '同一公司H股较A股大幅折价时买H股，等折价收窄。',
     'drive': '南向资金买入使H股折价收窄。',
     'works': '南向资金持续流入、H股流动性改善。',
     'fails': '折价长期不收敛。',
     'evidence': '沪港通开通后，67家A＋H公司的AH溢价平均反而扩大18.4%（Liu & Tang, 2011—2019年数据），开通互联互通并不会自动让两地价格收敛。',
     'signal': '只作为“同一公司买A股还是H股”的比较工具（含红利税差），不单独作为上涨逻辑。',
     'status': '已覆盖', 'where': '作为港股红利高股息页里“买A还是买H”的比较工具，不单独选股', 'href': 'hk-dividend.html#ah',
     'verify': '如要启用，先回测“折价分档→随后折价是否收窄”，证据不足前不选股。'},
    {'id': 'momentum', 'g': 'sl', 'name': '动量与趋势', 'mkt': '港股有效，A股相反',
     'def': '过去3—12个月涨得好的股票继续持有或买入回调。',
     'drive': '机构资金逐步建仓、信息逐步扩散，价格形成趋势。',
     'works': '机构定价为主的市场：港股、B股。',
     'fails': 'A股以散户为主，月度收益反转、动量不存在（Chui, Subrahmanyam & Titman, 2021；Yue, Li & Ruan, 2023）。',
     'evidence': '同一批公司的A股（散户为主）呈月度反转、B股（境外机构为主）有动量（Chui, Subrahmanyam & Titman, 2021）。港股动量在中期持有期显著（Cheng & Wu, 2010）。本站港股回测：离一年高点10%以内的股票13周超额+1.3%，回撤≥40%的−4.8%。',
     'signal': '港股：买点放在上升趋势中回调到12周均线附近；A股：不追涨，买点放在一年区间下部。',
     'status': '已覆盖', 'where': '作为港股景气顺势、业绩反转、回购的买点规则，不单独成为一条选股逻辑', 'href': 'hk.html#hk-price',
     'verify': '港股买点规则每季度按同一口径重跑；A股如要验证，用相同分组看反转是否仍成立。'},
    {'id': 'flow', 'g': 'sl', 'name': '被动与政策资金', 'mkt': 'A股、港股',
     'def': '因指数调整、ETF申购、南向配置、平准资金托底而被动买入的股票。',
     'drive': '短期供求：被动买盘集中进入。',
     'works': '调整生效前后短期。',
     'fails': '长期看不是优势：沪深300调出的股票四年持有期反而跑赢调入的股票（Chu, Goodell, Li & Zhang, 2021）。',
     'evidence': '同上。资金托底更适合判断大盘下有没有垫子，而不是选股。',
     'signal': '不作为选股逻辑；作为大盘层“托底”读数和个股“筹码”层的读数。',
     'status': '不做', 'where': '已用在总览“水龙头”和个股筹码层', 'href': '../index.html',
     'verify': '—'},
    {'id': 'small', 'g': 'qx', 'name': '小市值与壳价值', 'mkt': 'A股',
     'def': '买市值最小的一批股票。',
     'drive': '壳价值和散户流动性；量化资金集中持有。',
     'works': '注册制以前壳资源稀缺时；流动性宽松时。',
     'fails': '注册制后壳价值下降；量化拥挤时踩踏：2024年2月5日中证2000单日下跌9.49%，年内跌32.8%，杠杆量化多头集中卖出（第一财经）。',
     'evidence': '中国市值最小的30%公司价格中包含壳价值，研究因子时要剔除（Liu, Stambaugh & Yuan, 2019）。',
     'signal': '不做。',
     'status': '不做', 'where': '—', 'href': '',
     'verify': '—'},
    {'id': 'theme', 'g': 'qx', 'name': '题材与情绪', 'mkt': 'A股',
     'def': '围绕政策或新闻主题的集中炒作、涨停接力。',
     'drive': '散户注意力和短期资金。',
     'works': '主题刚出现的几天。',
     'fails': '异常换手率高的股票随后跑输（中国市场的情绪因子，Liu, Stambaugh & Yuan, 2019）；A股短期反转。',
     'evidence': '同上。',
     'signal': '不作为买入逻辑；高换手、融资快速增加、股东户数大增作为风险提示（本站筹码层已在用）。',
     'status': '不做', 'where': '风险提示已在个股筹码层', 'href': '',
     'verify': '—'},
    {'id': 'buyback', 'g': 'sj', 'name': '回购、增持与私有化', 'mkt': '港股为主',
     'def': '公司或大股东用现金买入自己的股票，或提出私有化要约。',
     'drive': '有明确、持续的买方；私有化有确定的要约价和时间表。',
     'works': '公司现金充足、估值低、回购持续执行；私有化条件清楚、否决风险低。',
     'fails': '回购只是公告、执行少；私有化被小股东否决或撤回。',
     'evidence': '本站港股回测（21个检验日）：近13周回购占市值≥0.5%本身没有超额（中位数−0.3%）；同时已站上26周均线的56个样本中位数+6.4%、跑赢61%。2025年全球回购创纪录，但中国内地回购同比减少35%，香港也下降（Capital Group，经南华早报报道）。',
     'signal': '回购金额占流通市值、已执行比例；私有化要约价相对现价的空间、条件与时间表。',
     'status': '部分覆盖', 'where': '港股“事件 · 回购与私有化”：回购已做；私有化只有规则，缺数据源', 'href': 'hk-event.html',
     'verify': '统计已执行回购占市值≥一定比例的公司随后的超额收益；私有化逐单记录要约价、成败与持有期收益。'},
    {'id': 'ma', 'g': 'sj', 'name': '并购重组与分拆', 'mkt': 'A股、港股',
     'def': '资产注入、并购、分拆上市带来的重估。',
     'drive': '资产质量或业务结构一次性改变。',
     'works': '方案确定、审批通过、注入资产质量高。',
     'fails': '审批不确定、信息不对称、方案终止。',
     'evidence': '难以事前规则化，且容易涉及未公开信息。',
     'signal': '不做。',
     'status': '不做', 'where': '—', 'href': '',
     'verify': '—'},
]

MILESTONES = [
    ('2014-11-17', '沪港通开通', '南向资金开始参与港股定价；但AH溢价随后平均扩大，两地比价不能指望自动收敛。'),
    ('2019-07-22', '科创板首批注册制股票上市', '上市不再稀缺，壳价值开始下降，小市值逻辑的基础变弱。'),
    ('2023-02-17', '全面实行股票发行注册制', '同上，壳价值进一步下降。'),
    ('2024-02-05', '中证2000单日下跌9.49%', '小市值和量化拥挤的风险集中暴露。'),
    ('2024-11-15', '证监会发布《市值管理》指引', '估值修复和红利有了制度推动：主要指数成分股要有市值管理制度，长期破净公司要披露估值提升计划。'),
    ('2026-11', '本站A股、港股回测', '港股：动量、行业预期上调、回购＋站上均线有效，用公开财报判断的反转无效。A股：机构预测上调无效，财报确认的反转（股价还没涨）有效。两地高股息都有效。'),
]

SOURCES = [
    ('Liu, Stambaugh & Yuan (2019), Size and Value in China, Journal of Financial Economics', 'https://alphaarchitect.com/2019/01/size-and-value-in-china/'),
    ('Chui, Subrahmanyam & Titman (2021), Momentum, Reversals, and Investor Clientele, Review of Financial Studies', 'https://alphaarchitect.com/2021/11/the-momentum-factor-is-driven-by-behavioral-bias-not-risk'),
    ('Yue, Li & Ruan (2023), Does short-term momentum exist in China? Pacific-Basin Finance Journal', 'https://ourarchive.otago.ac.nz/esploro/outputs/journalArticle/Does-short-term-momentum-exist-in-China/9926495433401891'),
    ('Chen, Gao & Liu (2021), Limited Attention and Post-Earnings Announcement Drift: Evidence from China', 'https://ideas.repec.org/a/eco/journ1/2021-01-1.html'),
    ('Cheng & Wu (2010), momentum in the Hong Kong stock market, International Review of Economics & Finance', 'https://ideas.repec.org/a/eee/reveco/v19y2010i4p527-538.html'),
    ('Chi (2018), Performance Evaluation of Chinese Equity Analysts', 'https://acfr.aut.ac.nz/__data/assets/pdf_file/0007/188089/20180718_PerformanceEvaluationOfChineseEquityAnalysts.pdf'),
    ('Liu & Tang, A-H Premium and the Shanghai-Hong Kong Stock Connect (arXiv)', 'https://arxiv.org/abs/2602.14754'),
    ('Chu, Goodell, Li & Zhang (2021), CSI 300 index reconstitutions, Pacific-Basin Finance Journal', 'https://ideas.repec.org/a/eee/pacfin/v69y2021ics0927538x2100158x.html'),
    ('中国证券报：证监会发布《上市公司监管指引第10号——市值管理》（2024-11-16）', 'https://cs.com.cn/xwzx/hg/202411/t20241116_6454375.html'),
    ('第一财经：中证2000单日下跌9.49%（2024-02-05）', 'https://www.yicai.com/news/101985905.html'),
    ('南华早报：Capital Group统计2025年全球回购', 'https://www.scmp.com/business/china-business/article/3347826/global-buy-backs-hit-record-mainland-china-hong-kong-see-declines-capital-group'),
    ('标普道琼斯指数：A股红利与高股息策略', 'https://www.spglobal.com/spdji/en/research/article/exploring-china-a-share-dividends-and-high-yield-strategy-performance'),
]

STATUS_CLS = {'已覆盖': 'ok', '部分覆盖': 'part', '缺口': 'gap', '不做': 'no'}
PRIORITY = [
    ('1', '港股私有化逐单登记', '规则已写，缺数据源；按港交所公告登记要约价、条件和时间表，积累样本后再回测。'),
    ('2', '估值修复补“估值提升计划”', '国资箱体已加分红是否提高；长期破净公司是否披露估值提升计划、回购是否执行，还没有数据源。'),
    ('3', 'A股筹码层接入融资余额', 'A股没有空头数据，业绩反转与红利页的筹码层目前只有提示。'),
    ('4', '各逻辑每季度滚动复核', '所有回测只覆盖2025—2026年一年左右，结论可能随市场风格变化。'),
]


def page(root):
    out = '<style>' + SP.CSS + CSS + '</style>' + SP.head(0)
    out += ('<div class="hero"><h1>选股逻辑地图</h1><p class="sum">股价＝每股利润×估值，再加上资金和事件的短期影响。按“什么在推动股价上涨”，选股逻辑分为五类、12条。'
            '每条写清定义、上涨动力、什么时候有效或失效、证据和执行信号，并标出本站是否已覆盖。</p><p class="hero-meta">2026-11-26整理；证据只引用已核对的研究和报道</p></div>')
    cnt = {k: sum(1 for x in LOGICS if x['status'] == k) for k in STATUS_CLS}
    out += ('<section id="lm-sum"><h2>结论</h2><ol class="lm-key">'
            '<li><b>覆盖情况：</b>12条逻辑里，本站已覆盖' + str(cnt['已覆盖']) + '条、部分覆盖' + str(cnt['部分覆盖']) + '条、有缺口' + str(cnt['缺口']) + '条，另有' + str(cnt['不做']) + '条有意不做。个股页按“分子、分母、事件”重新命名，每条逻辑一个标签页。</li>'
            '<li><b>同一条逻辑，A股和港股的做法相反。</b>港股以机构为主、有趋势：业绩反转看机构上调预测、等股价站上26周均线，回购也要等站上均线。A股以散户为主、短期反转：机构上调预测无效，财报确认的反转才有效，而且买还没涨到26周均线的。</li>'
            '<li><b>红利高股息在两地都有效。</b>A股股息率4%以上、港股5%—15%的股票这一年明显跑赢；港股股息率超过15%是陷阱。</li>'
            '<li><b>不做的四条：</b>被动资金、小市值、题材情绪、并购重组。前三条在本站只作为风险或大盘读数，不用来选股。</li></ol></section>')
    # 总图
    out += '<section id="lm-map"><h2>总图：五类上涨动力</h2><div class="lm-groups">'
    for g, gname, gdesc in GROUPS:
        xs = [x for x in LOGICS if x['g'] == g]
        out += ('<article class="lm-g lm-' + g + '"><h3>' + E(gname) + '</h3><p>' + E(gdesc) + '</p><ul>' +
                ''.join('<li><a href="#lm-' + x['id'] + '">' + E(x['name']) + '</a><span class="lm-st ' + STATUS_CLS[x['status']] + '">' + E(x['status']) + '</span></li>' for x in xs) + '</ul></article>')
    out += '</div></section>'
    # 本站逻辑页与分类的对应
    pages = [('A股 · 分子 · 景气顺势', 'index.html', '行业利润上升', '景气顺势（含成长板块）', '成长板块（半导体、算力、创新药）以开关判断，开关前不买；银行已移到红利高股息。'),
             ('A股 · 分子 · 业绩反转', 'a-turn.html', '财报确认利润由降转升', '业绩反转与预期上调', '买还没涨到26周均线的；机构预测上调在A股无效。'),
             ('A股 · 分母 · 红利高股息', 'dividend.html', '股息率相对国债的吸引力', '红利与高股息', '按股息率定买卖价；银行成交拥挤时暂停新增。'),
             ('A股 · 分母 · 估值修复（国资箱体）', 'box.html', '净资产地板＋分红兑现＋偶发主题脉冲', '估值修复（含情绪脉冲）', '交易型逻辑：地板附近买、天花板附近卖；新增分红是否提高。'),
             ('港股 · 分子 · 景气顺势', 'hk.html', '行业利润上升', '景气顺势；买点用动量', '买点是上升趋势中回调到12周均线附近。'),
             ('港股 · 分子 · 业绩反转', 'hk-turn.html', '机构上调盈利预期', '业绩反转与预期上调', '行业上调广度判断反转，个股找落后者，站上26周均线再买。'),
             ('港股 · 分母 · 红利高股息', 'hk-dividend.html', '税后股息率', '红利与高股息；两地比价作为工具', '按税后股息率定价；同一公司买A还是买H在本页比较。'),
             ('港股 · 事件 · 回购与私有化', 'hk-event.html', '公司真金白银买入', '回购、增持与私有化', '回购≥0.5%且站上26周均线；私有化逐单登记。')]
    out += ('<section id="lm-site"><h2>本站逻辑页与分类的对应</h2><div class="tblwrap"><table class="mt lp-table"><thead><tr><th>本站页面</th><th>主要上涨动力</th><th>归类</th><th>说明</th></tr></thead><tbody>' +
            ''.join('<tr><th scope="row"><a href="' + h + '">' + E(a) + '</a></th><td>' + E(b) + '</td><td>' + E(c) + '</td><td>' + E(d) + '</td></tr>' for a, h, b, c, d in pages) +
            '</tbody></table></div></section>')
    # 逐条定义
    out += '<section id="lm-cards"><h2>12条逻辑的定义</h2>'
    for g, gname, _ in GROUPS:
        out += '<h3 class="lm-gh">' + E(gname) + '</h3><div class="lm-grid">'
        for x in [x for x in LOGICS if x['g'] == g]:
            link = ('<a href="' + x['href'] + '">本站：' + E(x['where']) + ' →</a>') if x['href'] else '本站：' + E(x['where'])
            out += ('<article class="lm-c" id="lm-' + x['id'] + '"><header><b>' + E(x['name']) + '</b><span class="lm-st ' + STATUS_CLS[x['status']] + '">' + E(x['status']) + '</span></header>'
                    '<p class="lm-mkt">适用：' + E(x['mkt']) + '</p><dl><dt>定义</dt><dd>' + E(x['def']) + '</dd><dt>上涨动力</dt><dd><b>' + E(x['drive']) + '</b></dd><dt>执行信号</dt><dd>' + E(x['signal']) + '</dd></dl>'
                    '<details class="more"><summary>有效、失效、证据与验证</summary><dl><dt>什么时候有效</dt><dd>' + E(x['works']) + '</dd><dt>什么时候失效</dt><dd>' + E(x['fails']) + '</dd><dt>证据</dt><dd>' + E(x['evidence']) +
                    '</dd><dt>怎么验证</dt><dd>' + E(x['verify']) + '</dd></dl></details><p class="lm-where">' + link + '</p></article>')
        out += '</div>'
    out += '</section>'
    out += ('<section id="lm-next"><h2>还要补的</h2><ol class="lm-key">' + ''.join('<li><b>' + E(b) + '：</b>' + E(c) + '</li>' for _, b, c in PRIORITY) + '</ol></section>')
    out += ('<section id="lm-ms"><h2>来源与里程碑</h2><p class="note">这些事件改变了哪些逻辑有效。</p><div class="tblwrap"><table class="mt lp-table"><thead><tr><th>日期</th><th>事件</th><th>对选股逻辑的影响</th></tr></thead><tbody>' +
            ''.join('<tr><td style="white-space:nowrap">' + a + '</td><td>' + E(b) + '</td><td>' + E(c) + '</td></tr>' for a, b, c in MILESTONES) + '</tbody></table></div>'
            '<ul class="lens-ul">' + ''.join('<li><a href="' + u + '" rel="noopener">' + E(t) + '</a></li>' for t, u in SOURCES) + '</ul></section>')
    return out


def build(ctx):
    site = Path(ctx['SITE'])
    (site/'stocks/logic-map.html').write_text(ctx['page']('选股逻辑地图 | A 股框架笔记', 'gg', page(ctx['ROOT']), '../'), encoding='utf-8')


CSS = """
.lm-key{margin:10px 0 0;padding-left:22px}.lm-key li{font-size:15px;line-height:1.9;margin:4px 0}
#lm-sum,#lm-map,#lm-site,#lm-cards,#lm-next{margin:30px 0}
.lm-groups{display:grid;grid-template-columns:repeat(auto-fit,minmax(185px,1fr));gap:10px;margin:12px 0}
.lm-g{background:#fff;border:1px solid #dfe6ee;border-top:4px solid #8aa0b5;border-radius:10px;padding:12px 14px}.lm-g h3{font-size:15px;margin:0 0 4px}.lm-g p{font-size:12.5px;color:#5b6b7a;line-height:1.6;margin:0 0 8px}
.lm-g ul{list-style:none;margin:0;padding:0}.lm-g li{display:flex;justify-content:space-between;gap:6px;padding:5px 0;border-top:1px solid #eef2f6;font-size:13.5px}.lm-g a{color:#1f3b57;font-weight:600;text-decoration:none}
.lm-fz{border-top-color:#3f8a64}.lm-fm{border-top-color:#5a7ea6}.lm-sl{border-top-color:#d1a23d}.lm-sj{border-top-color:#7a5aa6}.lm-qx{border-top-color:#c4572a}
.lm-st{font-size:11.5px;padding:1px 8px;border-radius:9px;white-space:nowrap;align-self:center}.lm-st.ok{background:#e3f3ea;color:#2f6f53}.lm-st.part{background:#fff3d9;color:#8a5a00}.lm-st.gap{background:#fbe3dc;color:#9b3d27}.lm-st.no{background:#eef1f4;color:#6b7c8c}
.lm-gh{font-size:16px;margin:22px 0 4px;color:#2f4a63}
.lm-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,380px),1fr));gap:12px}
.lm-c{background:#fff;border:1px solid #dfe6ee;border-radius:12px;padding:14px 16px;align-self:start;scroll-margin-top:90px}.lm-c header{display:flex;justify-content:space-between;gap:8px;align-items:center}.lm-c header b{font-size:16px;color:#1b324a}
.lm-mkt{font-size:12px;color:#6b7c8c;margin:2px 0 6px}.lm-c dl{margin:0}.lm-c dt{font-size:12px;color:#6b7c8c;margin-top:8px}.lm-c dd{margin:2px 0 0;font-size:14px;line-height:1.75;color:#2d4053}
.lm-where{font-size:12.5px;color:#52687b;margin:10px 0 0;border-top:1px solid #eef2f6;padding-top:8px}
"""
