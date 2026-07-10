# 分众传媒估值看板

## 项目用途

老唐席勒估值法的分众传媒(002027)估值工具，部署在 **Streamlit Community Cloud**。

## 估值逻辑

- **老唐席勒估值法**：十年平均净利润 × 25 倍 PE → 合理市值
- 理想买点 = 合理估值 × 0.7（30% 安全边际）
- 卖点 = 合理估值 × 1.5
- 双体系：扣非净利润（⭐ 推荐）+ 归母净利润

## 架构

```
Streamlit Cloud (关联 GitHub 自动部署)
  → app.py (216 行，单文件)
    → push2.eastmoney.com API（f43 股价 + f84 总股本，一次请求）
    → 利润数据：硬编码在 get_financial_data()，手动每年更新
```

## 关键文件

| 文件 | 作用 |
|------|------|
| `app.py` | 完整应用（估值计算 + 股价抓取 + 图表渲染） |
| `requirements.txt` | streamlit + pandas + requests |

## 重要约束（务必遵守）

1. **不接 akshare**：已全面替换为 `push2.eastmoney.com` 直连。akshare (`stock_individual_info_em`) 在 Streamlit Cloud 上偶发超时，push2 直连已证明更稳定。
2. **利润数据每年手动更新**：年报发布（4-5 月）后，在 `get_financial_data()` 的 fallback 数据最前面加一行新数据。十年窗口 `head(10)` 自动滚动。
3. **PE 倍数固定 25**：对应 4% 无风险收益率。不要擅自改为浮动 PE，除非用户明确要求。
4. **不抓预测价格**：功能范围严格限定于估值计算。不接入任何分析师预测或爬虫。
5. **所有 API 调用用 requests 直连**：不要回退到 akshare 封装层。push2 API 的 `fltt=2, invt=2` 参数组合已验证正确。

## 部署

- Streamlit Cloud 自动部署，push 到 `main` 即生效
- 网址：`https://fzcm002027-valuation-fbgdtmr4bhxvjyokm7vsmu.streamlit.app/`
- 免费 tier，闲置会休眠，首次访问需唤醒（约 30-60 秒）
- 重新部署时如果 URL 变化，更新此文档

## 改动历史

### 2026-07-10 第二轮（commit 6791307）

1. **合并 API 请求**：`get_market_data()` 一次请求取 `f43+f84`，省 HTTP 往返，页面加载更快
2. **股价显示时间戳**：`股价: 4.83 元 (03:00:20)`，用户知道数据新鲜度
3. **中文语义 delta**：`高于买点 5.7%` / `低于合理估值 26.0%`，替代 `距当前 +5.7%`
4. **走势图加均值参考线**：Altair 实现，橙色虚线标注十年均值
5. **扣非视觉高亮**：加 ⭐ 标记 + `st.container(border=True)` 边框
6. **依赖清理**：移除 akshare（代码 import + requirements.txt），只留 streamlit + pandas + requests
7. **按钮文案精简**：`🔄 刷新数据`（去掉"最新财报与股本"）

### 2026-07-10 第一轮（commit 019f5ef）

1. **更新 2025 年财报数据**：归母净利润 29.46 亿（同比 -42.85%），扣非净利润 27.19 亿（同比 -41.74%）。十年窗口自动滚动为 2016-2025
2. **新增 `get_current_price()`**：直连 push2 API（f43），实时股价 4.82 元
3. **估值卡片加距当前百分比**：6 个 metric 均显示 `距当前 +X%`
4. **新增两张走势图**：`st.bar_chart` 归母 + 扣非十年柱状图
5. **修复总股本接口**：`get_stock_info()` 改为 push2 API（f84）直连，替代 akshare
6. **修复浮点精度**：预测模块默认值 `round(..., 2)`，消除 `27.190000534057617`

### 2026-03-22（原始版本）

- 初始版本：硬编码 2015-2024 财报数据 + akshare 总股本
- 老唐席勒估值法（固定 25 PE）
- 动态滚动估值预测模块
- 估值逻辑说明书（页面底部）

## 仓库信息

- 仓库：`xxdd3808-lgtm/fzcm002027-valuation` (PUBLIC)
- 主分支：`main`
- 关联项目：`xxdd3808-lgtm/dingshi-renwu`（新股/转债上市提醒）
