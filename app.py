import streamlit as st
import pandas as pd
import akshare as ak
from datetime import datetime

# ==========================================
# 页面基础配置 (适合手机阅读的居中排版)
# ==========================================
st.set_page_config(page_title="分众传媒估值模型", page_icon="📈", layout="centered")

# ==========================================
# 数据获取与缓存模块
# ==========================================
@st.cache_data(ttl=3600)
def get_stock_info(symbol="002027"):
    fetch_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        stock_info = ak.stock_individual_info_em(symbol=symbol)
        total_shares_raw = stock_info[stock_info['item'] == '总股本']['value'].values[0]
        total_shares = round(float(total_shares_raw) / 100000000, 2)
    except Exception:
        total_shares = 144.42 
        fetch_time += " (离线缓存)"
    return total_shares, fetch_time

@st.cache_data(ttl=3600)
def get_financial_data():
    fallback_data = pd.DataFrame({
        '年份': ['2024', '2023', '2022', '2021', '2020', '2019', '2018', '2017', '2016', '2015'],
        '归母净利润(亿元)': [51.55, 48.27, 27.90, 60.63, 40.04, 18.75, 58.23, 60.05, 44.51, 33.89],
        '扣非净利润(亿元)': [46.68, 43.74, 23.94, 54.14, 36.46, 12.82, 47.96, 48.45, 35.84, 29.83]
    })
    return fallback_data

# ==========================================
# 估值计算核心函数
# ==========================================
def calculate_valuation(df_10_years, total_shares):
    avg_np = df_10_years['归母净利润(亿元)'].mean()
    avg_ng = df_10_years['扣非净利润(亿元)'].mean()
    
    val_np = {"合理估值": avg_np * 25, "理想买点": avg_np * 25 * 0.7, "卖点": avg_np * 25 * 1.5}
    val_ng = {"合理估值": avg_ng * 25, "理想买点": avg_ng * 25 * 0.7, "卖点": avg_ng * 25 * 1.5}
    
    price_np = {k: v / total_shares for k, v in val_np.items()}
    price_ng = {k: v / total_shares for k, v in val_ng.items()}
    
    return avg_np, avg_ng, val_np, val_ng, price_np, price_ng

# ==========================================
# 1. 网页头部信息与刷新
# ==========================================
st.title("🎯 分众传媒 (002027) 估值看板")

if st.button("🔄 刷新最新财报与股本数据", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

total_shares, fetch_time = get_stock_info()
df_history = get_financial_data()
df_current_10 = df_history.head(10).copy()
current_latest_year = int(df_current_10['年份'].max())
current_oldest_year = int(df_current_10['年份'].min())

st.caption(f"📊 当前总股本: **{total_shares} 亿股** | 数据抓取时间: {fetch_time}")
st.divider()

# 计算基础估值
avg_np, avg_ng, val_np, val_ng, p_np, p_ng = calculate_valuation(df_current_10, total_shares)

# ==========================================
# 2. 当前静态估值展示区
# ==========================================
st.header(f"📈 基于 {current_oldest_year}-{current_latest_year} 财报估值")

# --- 扣非净利润估值 (方案一) ---
st.markdown(f"### 🛡️ 方案一：扣非净利润体系 (推荐)")
st.markdown(f"> **十年平均扣非净利润：{avg_ng:.2f} 亿元**")
c1, c2, c3 = st.columns(3)
c1.metric(f"理想买点 (市值:{val_ng['理想买点']:.0f}亿)", f"{p_ng['理想买点']:.2f} 元")
c2.metric(f"合理估值 (市值:{val_ng['合理估值']:.0f}亿)", f"{p_ng['合理估值']:.2f} 元")
c3.metric(f"一年卖点 (市值:{val_ng['卖点']:.0f}亿)", f"{p_ng['卖点']:.2f} 元")

st.write("") # 留白换行

# --- 归母净利润估值 (方案二) ---
st.markdown(f"### 🟢 方案二：归母净利润体系")
st.markdown(f"> **十年平均归母净利润：{avg_np:.2f} 亿元**")
c4, c5, c6 = st.columns(3)
c4.metric(f"理想买点 (市值:{val_np['理想买点']:.0f}亿)", f"{p_np['理想买点']:.2f} 元")
c5.metric(f"合理估值 (市值:{val_np['合理估值']:.0f}亿)", f"{p_np['合理估值']:.2f} 元")
c6.metric(f"一年卖点 (市值:{val_np['卖点']:.0f}亿)", f"{p_np['卖点']:.2f} 元")

# --- 清晰列出计算所用的 10 年数据 ---
st.markdown("#### 📋 估值所采用的具体利润明细 (亿元)")
# 直接展示表格，不再折叠，方便随时查阅
st.table(df_current_10.set_index('年份').style.format("{:.2f}"))

st.divider()

# ==========================================
# 3. 动态前瞻预测模块
# ==========================================
st.header("🔮 动态滚动估值预测")
st.markdown("自行输入未来年份与预测利润，系统将向后顺延，自动截取**最新10年**数据重新计算。")

with st.container(border=True):
    # 允许用户自由输入任何年份
    pred_year = st.number_input("👉 设定预测年份", value=current_latest_year + 1, step=1)
    
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        pred_ng = st.number_input("预测扣非净利润 (亿元)", value=float(df_current_10.iloc[0]['扣非净利润(亿元)']), step=1.0)
    with col_in2:
        pred_np = st.number_input("预测归母净利润 (亿元)", value=float(df_current_10.iloc[0]['归母净利润(亿元)']), step=1.0)
    
    submitted = st.button("生成十年滚动估值", type="primary", use_container_width=True)

if submitted:
    new_row = pd.DataFrame({
        '年份': [str(pred_year)],
        '归母净利润(亿元)': [pred_np],
        '扣非净利润(亿元)': [pred_ng]
    })
    
    # 拼接并自动截取最新的10年数据
    df_combined = pd.concat([new_row, df_current_10], ignore_index=True)
    df_combined['年份数字'] = df_combined['年份'].astype(int)
    df_new_10 = df_combined.sort_values('年份数字', ascending=False).head(10)
    
    new_start = df_new_10['年份'].min()
    new_end = df_new_10['年份'].max()
    
    new_avg_np, new_avg_ng, nval_np, nval_ng, new_p_np, new_p_ng = calculate_valuation(df_new_10, total_shares)
