import streamlit as st
import requests
import pandas as pd
import random
from collections import Counter
import plotly.express as px
import urllib3

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================= 1. 页面基本配置 =================
st.set_page_config(page_title="LottoPrecision Terminal", layout="wide")

# ================= 2. 核心 UI 样式渲染 (采用之前的 UI 排版) =================
st.markdown("""
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .stApp { background-color: #020617; color: #e4e2e4; }
        .neon-glow { text-shadow: 0 0 10px rgba(173, 255, 47, 0.6); }
        /* 球体样式 */
        .ball-red { width: 35px; height: 35px; border: 2px solid #ADFF2F; color: #ADFF2F; display: inline-flex; align-items: center; justify-content: center; border-radius: 50%; font-weight: bold; margin: 4px; font-size: 14px; }
        .ball-blue { width: 35px; height: 35px; border: 2px solid #a78bfa; color: #a78bfa; display: inline-flex; align-items: center; justify-content: center; border-radius: 50%; font-weight: bold; margin: 4px; font-size: 14px; }
        .ball-p3 { width: 35px; height: 35px; border: 2px solid #fbbf24; color: #fbbf24; display: inline-flex; align-items: center; justify-content: center; border-radius: 50%; font-weight: bold; margin: 4px; font-size: 14px; }
        /* 卡片样式 */
        .predict-card { background: #1e293b; padding: 20px; border-radius: 8px; border-left: 4px solid #ADFF2F; margin-top: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
        /* 选项卡字体适配 */
        .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p { font-size: 16px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# ================= 3. 数据抓取与加载逻辑 =================
@st.cache_data(ttl=600)
def get_live_data(game_id):
    url = f"https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo={game_id}&provinceId=0&pageSize=1&isVerify=1"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=5, verify=False).json()
        if res.get('success'):
            item = res['value']['list'][0]
            return {
                "term": item['lotteryDrawNum'],
                "date": item['lotteryDrawTime'],
                "balls": item['lotteryDrawResult'].split(' '),
                "pool": item.get('poolBalanceAfterDraw', "---")
            }
    except: return None

@st.cache_data
def load_local_csv(game_mode):
    try:
        if game_mode == "大乐透":
            df = pd.read_csv('lotto-20260421.csv', header=None)
            df.columns = ['期号', '红1', '红2', '红3', '红4', '红5', '蓝1', '蓝2']
        else:
            df = pd.read_csv('p3-20260421.csv', header=None)
            df.columns = ['期号', '百位', '十位', '个位']
        return df
    except: return None

# ================= 4. 侧边栏控制面板 =================
with st.sidebar:
    st.markdown('<h2 class="text-[#ADFF2F] font-bold neon-glow">TERMINAL CONTROL</h2>', unsafe_allow_html=True)
    game_mode = st.radio("切换分析系统", ["大乐透", "排列3"])
    st.divider()
    period = st.select_slider("分析历史深度", options=[50, 100, 200, 500, 1000], value=100)
    
    if game_mode == "大乐透":
        game_id, k_qty = "85", st.slider("红球强杀数", 5, 25, 18)
        k_blue_val = st.slider("蓝球强杀数", 1, 8, 4)
    else:
        game_id, k_qty = "35", st.slider("每位强杀数 (0-9)", 1, 6, 3)

    if "seed" not in st.session_state: st.session_state.seed = random.randint(1, 999)
    if st.button("🔄 刷新全域随机算力"): st.session_state.seed += 1

# 数据加载
live = get_live_data(game_id)
df = load_local_csv(game_mode)

# 断网/数据兜底逻辑
if not live and df is not None:
    last = df.iloc[0]
    if game_mode == "大乐透":
        balls = [f"{int(last[c]):02d}" for c in ['红1','红2','红3','红4','红5','蓝1','蓝2']]
    else:
        balls = [str(int(last[c])) for c in ['百位','十位','个位']]
    live = {"term": str(last['期号']), "date": "本地文件库", "balls": balls}

# ================= 5. 核心逻辑计算 (自洽系统) =================
random.seed(st.session_state.seed)
if df is not None:
    recent_df = df.head(period)
    if game_mode == "大乐透":
        r_counts = Counter(recent_df[['红1','红2','红3','红4','红5']].values.flatten())
        b_counts = Counter(recent_df[['蓝1','蓝2']].values.flatten())
        red_killed = sorted(list(range(1,36)), key=lambda x: r_counts[x])[:k_qty]
        red_res = sorted(list(set(range(1,36)) - set(red_killed)))
        blue_killed = sorted(list(range(1,13)), key=lambda x: b_counts[x])[:k_blue_val]
        blue_res = sorted(list(set(range(1,13)) - set(blue_killed)))
    else:
        p3_res, p3_kill, p3_counts = [], [], []
        for col in ['百位', '十位', '个位']:
            counts = Counter(recent_df[col].values)
            p3_counts.append(counts)
            killed = sorted(list(range(10)), key=lambda x: counts[x])[:k_qty]
            p3_kill.append(killed)
            p3_res.append(sorted(list(set(range(10)) - set(killed))))

# ================= 6. UI 界面渲染 =================
st.markdown(f'<h1 class="text-white font-bold text-3xl mb-4">🏆 {game_mode}智能数据分析终端</h1>', unsafe_allow_html=True)

# 实时开奖看板 (UI 复用)
if live:
    b_style = "ball-red" if game_mode == "大乐透" else "ball-p3"
    r_nums = live['balls'][:5 if game_mode=="大乐透" else 3]
    b_nums = live['balls'][5:] if game_mode=="大乐透" else []
    
    r_html = "".join([f'<div class="{b_style}">{n}</div>' for n in r_nums])
    b_html = "".join([f'<div class="ball-blue">{n}</div>' for n in b_nums])
    
    st.markdown(f"""
        <div style="background: #0f172a; border: 1px solid #1e293b; padding: 20px; border-radius: 8px; margin-bottom: 25px; position: relative;">
            <div style="position: absolute; top: 15px; right: 20px; display: flex; align-items: center; gap: 8px;">
                <span style="width: 8px; height: 8px; background: #ADFF2F; border-radius: 50%; box-shadow: 0 0 10px #ADFF2F;"></span>
                <span style="color: #ADFF2F; font-size: 10px; font-weight: bold;">LIVE SYNC</span>
            </div>
            <p style="color: #64748b; font-size: 12px; margin: 0;">最新开奖：第 {live['term']} 期 ({live['date']})</p>
            <div style="margin: 15px 0;">{r_html} <span style="margin:0 10px; color:#334155;">|</span> {b_html}</div>
        </div>
    """, unsafe_allow_html=True)

# 功能标签页 (修复了解包错误)
if df is not None:
    tabs = st.tabs(["✨ 智能预测", "🚫 杀号实验室", "📊 频率走势", "📅 历史开奖"])
    
    # --- Tab 1: 智能预测 ---
    with tabs[0]:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🚀 算力生成 1 注", use_container_width=True):
                if game_mode == "大乐透":
                    st.session_state.p = f"{' '.join([f'{x:02d}' for x in sorted(random.sample(red_res, 5))])} + {' '.join([f'{x:02d}' for x in sorted(random.sample(blue_res, 2))])}"
                else:
                    st.session_state.p = " ".join([str(random.choice(p3_res[i])) for i in range(3)])
            if "p" in st.session_state:
                st.markdown(f'<div class="predict-card"><h2 class="text-[#ADFF2F] neon-glow font-bold text-xl">{st.session_state.p}</h2></div>', unsafe_allow_html=True)
        with c2:
            if st.button("🎰 算力生成 5 注", use_container_width=True):
                batch = []
                for _ in range(5):
                    if game_mode == "大乐透":
                        batch.append(f"{' '.join([f'{x:02d}' for x in sorted(random.sample(red_res, 5))])} + {' '.join([f'{x:02d}' for x in sorted(random.sample(blue_res, 2))])}")
                    else:
                        batch.append(" ".join([str(random.choice(p3_res[i])) for i in range(3)]))
                st.session_state.batch = batch
            if "batch" in st.session_state:
                for b in st.session_state.batch: st.code(b)

    # --- Tab 2: 杀号实验室 ---
    with tabs[1]:
        if game_mode == "大乐透":
            st.error(f"🔴 已杀红球: {red_killed}")
            st.success(f"✅ 保留红球: {red_res}")
            st.info(f"🔵 已杀蓝球: {blue_killed}")
        else:
            cols = st.columns(3)
            for i, n in enumerate(["百位", "十位", "个位"]):
                with cols[i]:
                    st.error(f"{n}杀: {p3_kill[i]}")
                    st.success(f"{n}留: {p3_res[i]}")

    # --- Tab 3: 频率走势 ---
    with tabs[2]:
        if game_mode == "排列3":
            plot_df = pd.DataFrame({
                "号码": [str(i) for i in range(10)],
                "百位": [p3_counts[0][i] for i in range(10)],
                "十位": [p3_counts[1][i] for i in range(10)],
                "个位": [p3_counts[2][i] for i in range(10)]
            })
            fig = px.line(plot_df, x="号码", y=["百位", "十位", "个位"], title="分位号码热度分布图", markers=True)
            fig.update_layout(template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
        else:
            fig = px.bar(x=list(r_counts.keys()), y=list(r_counts.values()), title="红球历史出现频率")
            fig.update_layout(template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

    # --- Tab 4: 历史详情 ---
    with tabs[3]:
        st.dataframe(df.head(period), use_container_width=True)

else:
    st.warning("⚠️ 未检测到本地 CSV 数据文件，请检查文件路径。")