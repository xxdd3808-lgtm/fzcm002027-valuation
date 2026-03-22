# -*- coding: utf-8 -*-
"""
分众传媒（002027）估值工具 - Streamlit 网页应用
使用方法：streamlit run app.py
"""

import streamlit as st
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta, time
import os
import json

# 页面配置
st.set_page_config(
    page_title="分众传媒估值",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 自定义样式
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .stock-code {
        font-size: 1rem;
        color: #666;
        text-align: center;
    }
    .price-display {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        padding: 1rem;
    }
    .price-up { color: #ff0000; }
    .price-down { color: #00aa00; }
    .valuation-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #1f77b4;
    }
    .data-info {
        background-color: #e8f4f8;
        border-radius: 5px;
        padding: 0.8rem;
        margin: 0.5rem 0;
        font-size: 0.9rem;
    }
    .source-note {
        font-size: 0.8rem;
        color: #888;
        text-align: right;
    }
</style>
""", unsafe_allow_html=True)


# ========== 配置参数 ==========
STOCK_CODE = "002027"
P_E_RATIO = 25
BUY_POINT_RATIO = 0.7
SELL_POINT_RATIO = 1.5
DATA_FILE = "d:/workbuddy/分众传媒/fengzhong_valuation/financial_data.json"


# ========== 工具函数 ==========

def is_trading_hours():
    """判断当前是否为A股交易时间段"""
    now = datetime.now()
    # 周六周日不是交易日
    if now.weekday() >= 5:
        return False
    current_time = now.time()
    # 上午: 9:30-11:30, 下午: 13:00-15:00
    morning_start = time(9, 30)
    morning_end = time(11, 30)
    afternoon_start = time(13, 0)
    afternoon_end = time(15, 0)

    if morning_start <= current_time <= morning_end:
        return True
    if afternoon_start <= current_time <= afternoon_end:
        return True
    return False


def load_local_data():
    """从本地文件加载历史财务数据"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return pd.DataFrame(data)
        except:
            pass
    return pd.DataFrame()


def save_local_data(df):
    """保存财务数据到本地文件"""
    try:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(df.to_dict('records'), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存数据失败: {e}")


# ========== 数据获取函数 ==========

@st.cache_data(ttl=3600)
def get_financial_data_with_backup():
    """
    获取财务数据（双数据源+自动切换+本地持久化）
    逻辑：有新用新，没新用前十年的
    """
    warnings = []

    # 先尝试加载本地数据
    local_df = load_local_data()
    local_years = set(local_df['年份'].tolist()) if not local_df.empty else set()

    # 主数据源：东方财富
    try:
        df = ak.stock_financial_abstract(symbol=STOCK_CODE)

        parent_netprofit_row = df.iloc[0]
        non_recurring_row = df.iloc[4]
        dates = df.columns[1:]

        result_data = []
        for date in dates:
            if not date.endswith('1231'):
                continue
            year = int(date[:4])
            parent_netprofit = parent_netprofit_row[date]
            non_recurring = non_recurring_row[date]

            if parent_netprofit is None or pd.isna(parent_netprofit):
                continue

            result_data.append({
                '年份': year,
                '报告日期': date,
                '归母净利润_亿元': round(float(parent_netprofit) / 100000000, 2),
                '扣非净利润_亿元': round(float(non_recurring) / 100000000, 2) if non_recurring and not pd.isna(non_recurring) else None,
            })

        result_df = pd.DataFrame(result_data).sort_values('年份').reset_index(drop=True)
        online_years = set(result_df['年份'].tolist())

        # 合并数据：在线数据覆盖本地数据
        if not local_df.empty:
            # 本地有但线上没有的年份，保留本地数据
            missing_years = local_years - online_years
            if missing_years:
                missing_data = local_df[local_df['年份'].isin(missing_years)]
                result_df = pd.concat([result_df, missing_data], ignore_index=True)
                result_df = result_df.sort_values('年份').reset_index(drop=True)

        # 保存合并后的数据到本地
        save_local_data(result_df)

        return result_df, "东方财富", warnings
    except Exception as e:
        warnings.append(f"东方财富数据获取失败: {e}")

        # 备用：使用本地数据
        if not local_df.empty:
            warnings.append("使用本地缓存数据")
            return local_df, "本地缓存", warnings

        # 备用数据源：新浪财经
        try:
            df = ak.stock_financial_summary_sina(symbol=f"sh{STOCK_CODE}")
            result_df = pd.DataFrame()
            return result_df, "新浪财经", warnings
        except Exception as e:
            warnings.append(f"备用数据源也获取失败: {e}")
            return pd.DataFrame(), "无", warnings


@st.cache_data(ttl=60)
def get_realtime_price_with_backup():
    """
    获取实时/最新股价
    交易时间段返回实时价，非交易时间段返回最近收盘价
    """
    warnings = []
    trading = is_trading_hours()

    # 交易时间段：尝试获取实时价格
    if trading:
        try:
            # 使用东方财富实时行情接口
            df = ak.stock_zh_a_spot_em()
            stock_row = df[df['代码'] == STOCK_CODE]
            if not stock_row.empty:
                price = float(stock_row['最新价'].values[0])
                change_pct = float(stock_row['涨跌幅'].values[0])
                return price, change_pct, "实时行情", warnings
        except Exception as e:
            warnings.append(f"实时行情获取失败: {e}，尝试备用...")

    # 非交易时间段 或 实时获取失败：获取最近收盘价
    try:
        today = datetime.now().strftime('%Y%m%d')
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
        df = ak.stock_zh_a_hist(symbol=STOCK_CODE, period='daily',
                                  start_date=week_ago, end_date=today, adjust='')
        if not df.empty:
            latest = df.iloc[-1]
            price = float(latest['收盘'])
            change_pct = float(latest['涨跌幅'])
            trade_date = latest['日期'].strftime('%Y-%m-%d')
            price_type = "收盘价" if not trading else "收盘价(备用)"
            return price, change_pct, f"{price_type}({trade_date})", warnings
    except Exception as e:
        warnings.append(f"收盘价获取失败: {e}")

    return None, None, "获取失败", warnings


@st.cache_data(ttl=3600)
def get_share_capital_with_backup():
    """
    获取总股本
    """
    warnings = []

    # 主数据源：东方财富个股信息
    try:
        df = ak.stock_individual_info_em(symbol=STOCK_CODE)
        for _, row in df.iterrows():
            if "总股本" in str(row['item']):
                value = row['value']
                if isinstance(value, (int, float)):
                    share_capital = round(value / 1e8, 2)
                else:
                    share_capital = round(float(str(value).replace(',', '')) / 1e8, 2)
                return share_capital, "东方财富", datetime.now().strftime('%Y-%m-%d %H:%M'), warnings
    except Exception as e:
        warnings.append(f"东方财富股本获取失败: {e}，尝试备用...")

    return None, "获取失败", datetime.now().strftime('%Y-%m-%d %H:%M'), warnings


def get_latest_10_years_data(df):
    """
    获取最近10年数据，自动判断用哪些年份
    逻辑：有新年报用新年报，没有则用前十年的
    """
    current_year = datetime.now().year

    if df.empty:
        return df, "数据加载失败", []

    available_years = sorted(df['年份'].tolist())
    last_year = current_year - 1

    target_years = []

    if last_year in available_years:
        # 去年年报已出，使用 last_year-9 到 last_year
        target_years = list(range(last_year - 9, last_year + 1))
    else:
        # 去年年报未出，使用 last_year-10 到 last_year-1
        target_years = list(range(last_year - 10, last_year))

    # 只保留有数据的年份
    target_years = [y for y in target_years if y in available_years]
    filtered_df = df[df['年份'].isin(target_years)].copy()
    filtered_df = filtered_df.sort_values('年份').reset_index(drop=True)

    # 生成说明
    if last_year in available_years:
        note = f"已包含 {last_year} 年报"
    else:
        note = f"{last_year} 年报暂未发布，使用更早年份补足"

    return filtered_df, note, target_years


def calculate_valuation(financial_df, share_capital):
    """
    计算老唐席勒估值
    """
    if financial_df.empty or share_capital is None:
        return None

    avg_parent = financial_df['归母净利润_亿元'].mean()
    avg_non_recurring = financial_df['扣非净利润_亿元'].mean()

    # 方案A：归母净利润
    fair_a = avg_parent * P_E_RATIO
    buy_a = fair_a * BUY_POINT_RATIO
    sell_a = fair_a * SELL_POINT_RATIO
    buy_price_a = buy_a / share_capital
    sell_price_a = sell_a / share_capital

    # 方案B：扣非净利润
    fair_b = avg_non_recurring * P_E_RATIO
    buy_b = fair_b * BUY_POINT_RATIO
    sell_b = fair_b * SELL_POINT_RATIO
    buy_price_b = buy_b / share_capital
    sell_price_b = sell_b / share_capital

    return {
        '方案A': {
            'avg_profit': avg_parent,
            'fair_value': fair_a,
            'buy_point': buy_a,
            'sell_point': sell_a,
            'buy_price': buy_price_a,
            'sell_price': sell_price_a,
        },
        '方案B': {
            'avg_profit': avg_non_recurring,
            'fair_value': fair_b,
            'buy_point': buy_b,
            'sell_point': sell_b,
            'buy_price': buy_price_b,
            'sell_price': sell_price_b,
        }
    }


# ========== 主界面 ==========

def main():
    # 收集所有警告信息
    all_warnings = []

    # 标题
    st.markdown('<p class="main-header">📈 分众传媒（002027）估值工具</p>', unsafe_allow_html=True)
    st.markdown('<p class="stock-code">老唐席勒估值法 · 十年平均净利润</p>', unsafe_allow_html=True)

    # ========== 实时/收盘价（标题下方大字显示） ==========
    price, change_pct, price_source, price_warnings = get_realtime_price_with_backup()
    all_warnings.extend(price_warnings)

    if price:
        price_class = "price-up" if change_pct >= 0 else "price-down"
        change_sign = "+" if change_pct >= 0 else ""
        st.markdown(f"""
        <div style="text-align: center; padding: 0.5rem 0 1.5rem 0;">
            <div style="font-size: 1rem; color: #666;">{price_source}</div>
            <div class="price-display {price_class}">¥{price:.2f}</div>
            <div style="font-size: 1.4rem;" class="{price_class}">{change_sign}{change_pct:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # 自动获取失败，显示手动输入股价
        st.warning("⚠️ 自动获取股价失败，请手动输入当前股价")
        col1, col2 = st.columns([2, 1])
        with col1:
            manual_price = st.number_input(
                "当前股价（元）",
                min_value=0.0,
                max_value=1000.0,
                value=7.0,
                step=0.01,
                format="%.2f",
                key="manual_price_input"
            )
        with col2:
            st.write("")  # 占位
            st.write("")
            if st.button("使用此价格", type="primary"):
                price = manual_price
                change_pct = 0.0
                price_source = "手动输入"
                st.rerun()
        all_warnings.append("股价为手动输入")

    st.divider()

    # ========== 获取数据 ==========
    financial_df, financial_source, fin_warnings = get_financial_data_with_backup()
    all_warnings.extend(fin_warnings)

    share_capital, capital_source, capital_time, cap_warnings = get_share_capital_with_backup()
    all_warnings.extend(cap_warnings)

    if share_capital is None:
        share_capital = 144.42
        capital_source = "默认值"
        capital_time = datetime.now().strftime('%Y-%m-%d %H:%M')

    # 处理10年数据
    filtered_df, data_note, year_range = get_latest_10_years_data(financial_df)

    if filtered_df.empty:
        st.error("无法获取财务数据，请检查网络连接")
        return

    # 计算估值
    valuation = calculate_valuation(filtered_df, share_capital)

    # ========== 数据概览 ==========
    with st.container():
        st.markdown("### 📊 数据概览")

        col1, col2 = st.columns(2)

        with col1:
            if year_range:
                year_range_text = str(year_range[0]) + "-" + str(year_range[-1])
            else:
                year_range_text = "加载中"
            st.markdown(f"""
            <div class="data-info">
                <strong>📅 数据年份：</strong>{year_range_text}（共 {len(filtered_df)} 年）<br>
                <strong>📝 说明：</strong>{data_note}
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="data-info">
                <strong>🏭 总股本：</strong>{share_capital:.2f} 亿股<br>
                <strong>📡 来源/时间：</strong>{capital_source} · {capital_time}
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # ========== 估值结果 ==========
    st.markdown("### 🎯 估值结果")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 方案A（归母净利润）")
        st.markdown(f"""
        <div class="valuation-card">
            <table style="width: 100%;">
                <tr>
                    <td>十年平均净利润</td>
                    <td style="text-align: right; font-weight: bold;">{valuation['方案A']['avg_profit']:.2f} 亿元</td>
                </tr>
                <tr>
                    <td>合理估值（PE=25）</td>
                    <td style="text-align: right; font-weight: bold;">{valuation['方案A']['fair_value']:.2f} 亿元</td>
                </tr>
                <tr style="background-color: #d4edda;">
                    <td>✅ 理想买点</td>
                    <td style="text-align: right; font-weight: bold; color: #155724;">{valuation['方案A']['buy_point']:.2f} 亿元（¥{valuation['方案A']['buy_price']:.2f}）</td>
                </tr>
                <tr style="background-color: #f8d7da;">
                    <td>🔴 一年内卖点</td>
                    <td style="text-align: right; font-weight: bold; color: #721c24;">{valuation['方案A']['sell_point']:.2f} 亿元（¥{valuation['方案A']['sell_price']:.2f}）</td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("#### 方案B（扣非净利润）")
        st.markdown(f"""
        <div class="valuation-card">
            <table style="width: 100%;">
                <tr>
                    <td>十年平均净利润</td>
                    <td style="text-align: right; font-weight: bold;">{valuation['方案B']['avg_profit']:.2f} 亿元</td>
                </tr>
                <tr>
                    <td>合理估值（PE=25）</td>
                    <td style="text-align: right; font-weight: bold;">{valuation['方案B']['fair_value']:.2f} 亿元</td>
                </tr>
                <tr style="background-color: #d4edda;">
                    <td>✅ 理想买点</td>
                    <td style="text-align: right; font-weight: bold; color: #155724;">{valuation['方案B']['buy_point']:.2f} 亿元（¥{valuation['方案B']['buy_price']:.2f}）</td>
                </tr>
                <tr style="background-color: #f8d7da;">
                    <td>🔴 一年内卖点</td>
                    <td style="text-align: right; font-weight: bold; color: #721c24;">{valuation['方案B']['sell_point']:.2f} 亿元（¥{valuation['方案B']['sell_price']:.2f}）</td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

    # ========== 当前股价位置 ==========
    if price:
        st.divider()
        st.markdown("### 📍 当前股价位置")

        buy_a = valuation['方案A']['buy_price']
        sell_a = valuation['方案A']['sell_price']
        buy_b = valuation['方案B']['buy_price']
        sell_b = valuation['方案B']['sell_price']

        if price <= buy_a:
            position_a = "🟢 低于理想买点（低估）"
        elif price <= valuation['方案A']['fair_value'] / share_capital:
            position_a = "🟡 介于买点和合理估值之间"
        elif price >= sell_a:
            position_a = "🔴 高于一年内卖点（高估）"
        else:
            position_a = "🟠 介于合理估值和卖点之间（正常偏高）"

        if price <= buy_b:
            position_b = "🟢 低于理想买点（低估）"
        elif price <= valuation['方案B']['fair_value'] / share_capital:
            position_b = "🟡 介于买点和合理估值之间"
        elif price >= sell_b:
            position_b = "🔴 高于一年内卖点（高估）"
        else:
            position_b = "🟠 介于合理估值和卖点之间"

        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**方案A视角**：当前价 ¥{price:.2f} → {position_a}")
        with col2:
            st.info(f"**方案B视角**：当前价 ¥{price:.2f} → {position_b}")

    st.divider()

    # ========== 历年数据表格 ==========
    st.markdown("### 📈 历年财务数据")

    display_df = filtered_df.copy()
    display_df.columns = ['年份', '报告日期', '归母净利润(亿元)', '扣非净利润(亿元)']

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    st.markdown(f"""
    <div class="source-note">
        数据来源：{financial_source} · 更新于 {datetime.now().strftime('%Y-%m-%d %H:%M')}<br>
        ⚠️ 财务数据每年4月更新（发布上年度年报）
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ========== 手动输入净利润 ==========
    st.markdown("### ✏️ 手动更新净利润数据")

    col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
    with col1:
        input_year = st.number_input(
            "年份",
            min_value=2000,
            max_value=datetime.now().year + 1,
            value=datetime.now().year,
            step=1,
            key="input_year"
        )
    with col2:
        input_parent_profit = st.number_input(
            "归母净利润",
            min_value=0.0,
            max_value=10000.0,
            value=0.0,
            step=0.01,
            format="%.2f",
            key="input_parent_profit"
        )
    with col3:
        input_non_recurring_profit = st.number_input(
            "扣非净利润",
            min_value=0.0,
            max_value=10000.0,
            value=0.0,
            step=0.01,
            format="%.2f",
            key="input_non_recurring_profit"
        )
    with col4:
        st.write("")  # 占位对齐
        if st.button("💾 保存并重新计算", use_container_width=True, type="primary"):
            if input_parent_profit <= 0 and input_non_recurring_profit <= 0:
                st.warning("请至少输入一项净利润（归母或扣非）")
            else:
                try:
                    # 更新本地数据
                    local_df = load_local_data()

                    # 检查是否已有该年份数据
                    existing_idx = local_df[local_df['年份'] == int(input_year)].index

                    if len(existing_idx) > 0:
                        # 覆盖已有年份的数据
                        if input_parent_profit > 0:
                            local_df.loc[existing_idx[0], '归母净利润_亿元'] = input_parent_profit
                        if input_non_recurring_profit > 0:
                            local_df.loc[existing_idx[0], '扣非净利润_亿元'] = input_non_recurring_profit
                        st.success(f"已更新 {input_year} 年数据")
                    else:
                        # 新增年份
                        new_record = {
                            '年份': int(input_year),
                            '报告日期': f"{int(input_year)}1231",
                            '归母净利润_亿元': input_parent_profit if input_parent_profit > 0 else None,
                            '扣非净利润_亿元': input_non_recurring_profit if input_non_recurring_profit > 0 else None,
                        }
                        local_df = pd.concat([local_df, pd.DataFrame([new_record])], ignore_index=True)
                        local_df = local_df.sort_values('年份').reset_index(drop=True)
                        st.success(f"已新增 {input_year} 年数据")

                    # 保存
                    save_local_data(local_df)

                    # 清除缓存并重新运行
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"保存失败: {e}")

    st.markdown("""
    <div class="source-note">
        💡 提示：手动输入的数据会保存到本地文件，下次启动自动加载。<br>
        &nbsp;&nbsp;&nbsp;&nbsp;年报发布后，系统会自动使用年报数据，不再使用手动数据。
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ========== 警告信息折叠区 ==========
    with st.expander("⚙️ 调试信息（数据获取日志）", expanded=False):
        if all_warnings:
            for w in all_warnings:
                st.warning(w)
        else:
            st.success("所有数据获取正常，无警告信息")

    st.divider()

    # ========== 页脚 ==========
    st.markdown("""
    <div style="text-align: center; color: #888; font-size: 0.8rem; padding: 1rem;">
        <p>📌 估值方法：老唐席勒估值法（10年平均净利润 × 25）</p>
        <p>📌 理想买点 = 合理估值 × 0.7 | 一年内卖点 = 合理估值 × 1.5</p>
        <p>⚠️ 本工具仅供参考，不构成投资建议</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()