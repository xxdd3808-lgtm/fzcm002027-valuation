import streamlit as st
import pandas as pd
import akshare as ak
from datetime import datetime
import time

# ==========================================
# 页面基础配置
# ==========================================
st.set_page_config(page_title="分众传媒 - 老唐席勒估值模型", page_icon="📊", layout="wide")

# ==========================================
# 数据获取与缓存模块 (TTL=3600秒，即每小时刷新一次)
# ==========================================
@st.cache_data(ttl=3600)
def get_stock_info(symbol="002027"):
    """抓取最新总股本和当前时间"""
    fetch_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        # 使用 akshare 获取个股信息
        stock_info = ak.stock_individual_info_em(symbol=symbol)
        # 提取总股本 (返回单位通常是股，需要转换为亿股)
        total_shares_raw = stock_info[stock_info['item'] == '总股本']['value'].values[0]
        total_shares = round(float(total_shares_raw) / 100000000, 2)
    except Exception as e:
        # 如果接口请求失败，使用默认已知最新总股本兜底
        total_shares = 144.42 
        fetch_time += " (接口离线，使用缓存数据)"
        
    return total_shares, fetch_time

@st.cache_data(ttl=3600)
def get_financial_data():
    """获取历史财报数据（归母净利润和扣非净利润）"""
    # 兜底的硬编码数据 (亿元) - 防止 API 变更导致应用崩溃
    fallback_data = pd.DataFrame({
        '年份': ['2024', '2023', '2022', '2021', '2020', '2019', '2018', '2017', '2016', '2015'],
        '归母净利润(亿元)': [51.55, 48.27, 27.90, 60.63, 40.04, 18.75, 58.23, 60.05, 44.51, 33.89],
        '扣非净利润(亿元)': [46.68, 43.74, 23.94, 54.14, 36.46, 12.82, 47.96, 48.45, 35.84, 29.83]
    })
    
    try:
        # 注：实际生产环境中，由于 akshare 财务接口常变，此处采用结构化数据兜底。
        # 如果未来 akshare 更新了更稳定的财务接口，可在此处替换为自动抓取逻辑。
        # 例如：df = ak.stock_financial_abstract_em(symbol="002027")
        # 并进行数据清洗。目前为了 Streamlit 云部署100%成功，优先返回兜底格式。
        df = fallback_data
    except:
        df = fallback_data
        
    return df

# ==========================================
# 估值计算核心函数
# ==========================================
def calculate_valuation(df_10_years, total_shares):
    """根据传入的10年数据和总股本计算买卖点"""
    avg_net_profit = df_10_years['归母净利润(亿元)'].mean()
    avg_non_gaap = df_10_years['扣非净利润(亿元)'].mean()
    
    # 计算市值 (亿元)
    val_net_profit = {
        "合理估值": avg_net_profit * 25,
        "理想买点": avg_net_profit * 25 * 0.7,
        "一年卖点": avg_net_profit * 25 * 1.5
    }
    
    val_non_gaap = {
        "合理估值": avg_non_gaap * 25,
        "理想买点": avg_non_gaap * 25 * 0.7,
        "一年卖点": avg_non_gaap * 25 * 1.5
    }
    
    # 折算股价 (元)
    price_net_profit = {k: v / total_shares for k, v in val_net_profit.items()}
    price_non_gaap = {k: v / total_shares for k, v in val_non_gaap.items()}
    
    return avg_net_profit, avg_non_gaap, val_net_profit, val_non_gaap, price_net_profit, price_non_gaap

# ==========================================
# 网页 UI 布局构建
# ==========================================
st.title("🎯 分众传媒 (002027) - 老唐席勒估值系统")
st.markdown("基于十年来企业净利润与扣非净利润的平均值，平滑周期波动，寻找长线安全边际。")

# 1. 获取并展示基础数据
total_shares, fetch_time = get_stock_info("002027")
df_history = get_financial_data()

# 提取最新的10年数据 (假设表头已经按年份倒序)
df_current_10 = df_history.head(10).copy()
start_year = df_current_10['年份'].min()
end_year = df_current_10['年份'].max()

st.info(f"📡 **实时数据抓取状态**：当前总股本 **{total_shares} 亿股** | 数据更新时间：{fetch_time} | 当前财报计算区间：**{start_year}-{end_year}**")

# 2. 计算当前财报下的估值
avg_np, avg_ng, val_np, val_ng, p_np, p_ng = calculate_valuation(df_current_10, total_shares)

# --- 估值展示区 ---
st.header(f"📊 基于 {start_year}-{end_year} 财报的最新估值")
tab1, tab2 = st.tabs(["🛡️ 方案二：扣非净利润估值 (更严谨推荐)", "🟢 方案一：归母净利润估值"])

with tab1:
    st.subheader(f"十年平均扣非净利润: {avg_ng:.2f} 亿元")
    col1, col2, col3 = st.columns(3)
    col1.metric("理想买点 (打七折)", f"{p_ng['理想买点']:.2f} 元", f"市值: {val_ng['理想买点']:.0f} 亿")
    col2.metric("合理估值 (25倍PE)", f"{p_ng['合理估值']:.2f} 元", f"市值: {val_ng['合理估值']:.0f} 亿", delta_color="off")
    col3.metric("一年内卖点 (溢价1.5倍)", f"{p_ng['一年卖点']:.2f} 元", f"市值: {val_ng['一年卖点']:.0f} 亿", delta_color="inverse")

with tab2:
    st.subheader(f"十年平均归母净利润: {avg_np:.2f} 亿元")
    col1, col2, col3 = st.columns(3)
    col1.metric("理想买点 (打七折)", f"{p_np['理想买点']:.2f} 元", f"市值: {val_np['理想买点']:.0f} 亿")
    col2.metric("合理估值 (25倍PE)", f"{p_np['合理估值']:.2f} 元", f"市值: {val_np['合理估值']:.0f} 亿", delta_color="off")
    col3.metric("一年内卖点 (溢价1.5倍)", f"{p_np['一年卖点']:.2f} 元", f"市值: {val_np['一年卖点']:.0f} 亿", delta_color="inverse")

# 展示历史数据表格与柱状图
with st.expander("展开查看过去十年财务数据详情"):
    col_table, col_chart = st.columns([1, 2])
    with col_table:
        st.dataframe(df_current_10.set_index('年份'), use_container_width=True)
    with col_chart:
        chart_data = df_current_10.set_index('年份')[['归母净利润(亿元)', '扣非净利润(亿元)']].sort_index()
        st.bar_chart(chart_data)

st.divider()

# ==========================================
# 动态前瞻预测模块 (What-if 分析)
# ==========================================
next_year = str(int(end_year) + 1)
st.header(f"🔮 {next_year} 年财报前瞻与滚动动态估值")
st.markdown(f"输入你对 **{next_year}年** 业绩的预测。系统将自动剔除最老的 **{start_year}年** 数据，生成全新的十年滚动估值。")

with st.form("prediction_form"):
    col1, col2 = st.columns(2)
    with col1:
        pred_np = st.number_input(f"预测 {next_year} 年归母净利润 (亿元)", value=float(df_current_10.iloc[0]['归母净利润(亿元)']), step=1.0)
    with col2:
        pred_ng = st.number_input(f"预测 {next_year} 年扣非净利润 (亿元)", value=float(df_current_10.iloc[0]['扣非净利润(亿元)']), step=1.0)
    
    submitted = st.form_submit_button("计算滚动十年估值")

if submitted:
    # 构建新的十年数据 (去掉最后一行，在头部插入预测数据)
    df_new_10 = df_current_10.iloc[:-1].copy()
    new_row = pd.DataFrame({
        '年份': [next_year],
        '归母净利润(亿元)': [pred_np],
        '扣非净利润(亿元)': [pred_ng]
    })
    df_new_10 = pd.concat([new_row, df_new_10], ignore_index=True)
    
    # 重新计算
    new_avg_np, new_avg_ng, new_val_np, new_val_ng, new_p_np, new_p_ng = calculate_valuation(df_new_10, total_shares)
    
    st.success(f"✅ 计算完成！采用新十年区间：{df_new_10['年份'].min()}-{df_new_10['年份'].max()}")
    
    # 展示预测结果 (重点突出买卖点变化)
    st.subheader(f"基于预测数据的扣非净利润估值 (十年平均: {new_avg_ng:.2f} 亿)")
    c1, c2, c3 = st.columns(3)
    c1.metric("🎯 新理想买点", f"{new_p_ng['理想买点']:.2f} 元", f"{new_p_ng['理想买点'] - p_ng['理想买点']:+.2f} 元 (对比当前)")
    c2.metric("⚖️ 新合理估值", f"{new_p_ng['合理估值']:.2f} 元", f"{new_p_ng['合理估值'] - p_ng['合理估值']:+.2f} 元 (对比当前)")
    c3.metric("🚀 新一年卖点", f"{new_p_ng['一年卖点']:.2f} 元", f"{new_p_ng['一年卖点'] - p_ng['一年卖点']:+.2f} 元 (对比当前)")
