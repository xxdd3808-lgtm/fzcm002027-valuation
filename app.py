import streamlit as st
import pandas as pd
import akshare as ak
from datetime import datetime

# ==========================================
# 页面基础配置 (适合手机阅读的居中排版)
# ==========================================
st.set_page_config(page_title="分众传媒估值", page_icon="📈", layout="centered")

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
    
    val_np = {"合理估值": avg_np * 25, "理想买点": avg_np * 25 * 0.7, "一年卖点": avg_np * 25 * 1.5}
    val_ng = {"合理估值": avg_ng * 25, "理想买点": avg_ng * 25 * 0.7, "一年卖点": avg_ng * 25 * 1.5}
    
    price_np = {k: v / total_shares for k, v in val_np.items()}
    price_ng = {k: v / total_shares for k, v in val_ng.items()}
    
    return avg_np, avg_ng, val_np, val_ng, price_np, price_ng

# ==========================================
# 网页 UI 布局
# ==========================================
st.title("🎯 分众传媒 (002027) 估值看板")

# 刷新按钮 (占满整行，方便手机点击)
if st.button("🔄 刷新最新财报与股本数据", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# 加载数据
total_shares, fetch_time = get_stock_info()
df_history = get_financial_data()
df_current_10 = df_history.head(10).copy()
current_latest_year = int(df_current_10['年份'].max())
current_oldest_year = int(df_current_10['年份'].min())

st.caption(f"📊 当前总股本: **{total_shares} 亿股** | 更新于: {fetch_time}")
st.divider()

# 计算基础估值
avg_np, avg_ng, val_np, val_ng, p_np, p_ng = calculate_valuation(df_current_10, total_shares)

# --- 估值展示区 (上下排列，手机友好) ---
st.markdown(f"### 🛡️ 方案一：扣非净利润估值 (更严谨)")
st.markdown(f"*基于 **{current_oldest_year}-{current_latest_year}** 十年平均扣非净利润: **{avg_ng:.2f} 亿元***")
c1, c2, c3 = st.columns(3)
c1.metric("理想买点", f"{p_ng['理想买点']:.2f} 元")
c2.metric("合理估值", f"{p_ng['合理估值']:.2f} 元")
c3.metric("一年卖点", f"{p_ng['一年卖点']:.2f} 元")

st.write("") # 留白

st.markdown(f"### 🟢 方案二：归母净利润估值")
st.markdown(f"*基于 **{current_oldest_year}-{current_latest_year}** 十年平均归母净利润: **{avg_np:.2f} 亿元***")
c4, c5, c6 = st.columns(3)
c4.metric("理想买点", f"{p_np['理想买点']:.2f} 元")
c5.metric("合理估值", f"{p_np['合理估值']:.2f} 元")
c6.metric("一年卖点", f"{p_np['一年卖点']:.2f} 元")

with st.expander("展开查看过去十年详细财务数据"):
    st.dataframe(df_current_10.set_index('年份'), use_container_width=True)

st.divider()

# ==========================================
# 动态前瞻预测模块
# ==========================================
st.subheader("🔮 动态滚动估值预测")
st.markdown("自定义年份与业绩，系统将自动向后顺延计算最新的十年滚动均值。")

with st.container(border=True):
    # 允许用户自由选择年份
    pred_year = st.number_input("👉 设定预测年份", value=current_latest_year + 1, step=1)
    
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        pred_ng = st.number_input("预测扣非净利润 (亿元)", value=float(df_current_10.iloc[0]['扣非净利润(亿元)']), step=1.0)
    with col_in2:
        pred_np = st.number_input("预测归母净利润 (亿元)", value=float(df_current_10.iloc[0]['归母净利润(亿元)']), step=1.0)
    
    # 将整个按钮拉宽，在手机上更好点
    submitted = st.button("开始计算动态估值", type="primary", use_container_width=True)

if submitted:
    # 动态构建新十年数据表
    new_row = pd.DataFrame({
        '年份': [str(pred_year)],
        '归母净利润(亿元)': [pred_np],
        '扣非净利润(亿元)': [pred_ng]
    })
    
    # 拼接数据，按年份倒序排序，然后只取前10个
    df_combined = pd.concat([new_row, df_current_10], ignore_index=True)
    df_combined['年份数字'] = df_combined['年份'].astype(int)
    df_new_10 = df_combined.sort_values('年份数字', ascending=False).head(10)
    
    new_start = df_new_10['年份'].min()
    new_end = df_new_10['年份'].max()
    
    new_avg_np, new_avg_ng, _, _, new_p_np, new_p_ng = calculate_valuation(df_new_10, total_shares)
    
    st.success(f"✅ 计算完成！已自动截取 **{new_start} - {new_end}** 的十年数据。")
    
    # 对比展示最新预测结果
    st.markdown("#### 🎯 预测结果 (对比当前财报估值)")
    
    # 扣非对比
    st.markdown(f"**扣非体系** (新均值: {new_avg_ng:.2f} 亿)")
    nc1, nc2, nc3 = st.columns(3)
    nc1.metric("新理想买点", f"{new_p_ng['理想买点']:.2f} 元", f"{new_p_ng['理想买点'] - p_ng['理想买点']:+.2f} 元")
    nc2.metric("新合理估值", f"{new_p_ng['合理估值']:.2f} 元", f"{new_p_ng['合理估值'] - p_ng['合理估值']:+.2f} 元")
    nc3.metric("新一年卖点", f"{new_p_ng['一年卖点']:.2f} 元", f"{new_p_ng['一年卖点'] - p_ng['一年卖点']:+.2f} 元")
    
    # 归母对比
    st.markdown(f"**归母体系** (新均值: {new_avg_np:.2f} 亿)")
