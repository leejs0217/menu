import re
from itertools import permutations
import pandas as pd
import plotly.express as px
import streamlit as st

# 페이지 설정
st.set_page_config(page_title="급식 연관 규칙 분석", layout="wide")

st.title("🍱 급식 메뉴 연관 규칙 분석")

# Data loading and preprocessing
CSV_URL = "https://raw.githubusercontent.com/it-teacher-go/data-share-/main/songtan_meals_184.csv"


@st.cache_data
def load_and_preprocess_data(url):
    df = pd.read_csv(url, encoding="utf-8")

    total_days = len(df)
    baskets = []
    all_menus = set()

    for raw_menu in df["메뉴"].dropna():
        # 괄호 및 괄호 안 내용 제거
        cleaned = re.sub(r"\(.*?\)", "", str(raw_menu))
        # 세로줄(|)로 분리하고 공백 제거 후 중복 제거
        items = list(
            set(item.strip() for item in cleaned.split("|") if item.strip())
        )
        if items:
            baskets.append(items)
            all_menus.update(items)

    return baskets, total_days, sorted(list(all_menus))


baskets, total_days, all_menu_list = load_and_preprocess_data(CSV_URL)


@st.cache_data
def calculate_association_rules(baskets, total_days):
    # 1개 아이템 빈도 계산
    item_counts = {}
    for basket in baskets:
        for item in basket:
            item_counts[item] = item_counts.get(item, 0) + 1

    # 2개 아이템 동시 등장 빈도 계산
    pair_counts = {}
    for basket in baskets:
        # 한 장바구니 안에서 가능한 모든 2개 조합 (순서 고려)
        for itemA, itemB in permutations(basket, 2):
            pair_counts[(itemA, itemB)] = pair_counts.get((itemA, itemB), 0) + 1

    rules = []
    for (itemA, itemB), count_AB in pair_counts.items():
        count_A = item_counts[itemA]
        count_B = item_counts[itemB]

        support = count_AB / total_days
        confidence = count_AB / count_A
        lift = (count_AB * total_days) / (count_A * count_B)

        rules.append(
            {
                "조건": itemA,
                "결과": itemB,
                "동시": count_AB,
                "지지도": support,
                "신뢰도": confidence,
                "향상도": lift,
            }
        )

    rules_df = pd.DataFrame(rules)
    return rules_df


rules_df = calculate_association_rules(baskets, total_days)

# 사이드바 컨트롤
st.sidebar.header("필터 및 정렬 설정")

selected_menu = st.sidebar.selectbox(
    "메뉴 선택 (전체 보기: '전체')", options=["전체"] + all_menu_list
)

sort_option = st.sidebar.radio(
    "정렬 기준 선택", options=["향상도", "신뢰도", "동시"]
)

# 데이터 필터링
filtered_df = rules_df.copy()
if selected_menu != "전체":
    filtered_df = filtered_df[
        (filtered_df["조건"] == selected_menu)
        | (filtered_df["결과"] == selected_menu)
    ]

# 정렬 적용
filtered_df = filtered_df.sort_values(by=sort_option, ascending=False).reset_index(
    drop=True
)

# 상단 요약 정보 출력
unique_pairs_count = len(filtered_df) // 2  # 양방향 규칙이므로 쌍의 수는 절반
st.write(
    f"**급식 일수:** {total_days}일 | **메뉴 종류 수:** {len(all_menu_list)}개 | **함께 나온 적이 있는 메뉴 쌍의 수:** {len(rules_df) // 2}쌍"
)

st.markdown("---")

# 표 출력
st.subheader("📋 연관 규칙 목록")
st.dataframe(
    filtered_df.style.format(
        {"지지도": "{:.4f}", "신뢰도": "{:.4f}", "향상도": "{:.4f}"}
    ),
    use_container_width=True,
)

# Plotly 가로 막대그래프 (향상도 상위 10개)
st.markdown("---")
st.subheader("📊 향상도 상위 10개 규칙")

top10_df = filtered_df.sort_values(by="향상도", ascending=False).head(10)

if not top10_df.empty:
    # 그래프 시각화를 위한 규칙 이름 생성
    top10_df["규칙"] = top10_df["조건"] + " ➔ " + top10_df["결과"]

    # 가로 막대그래프 생성 (상위 항목이 위로 오도록 y축 설정)
    fig = px.bar(
        top10_df,
        x="향상도",
        y="규칙",
        orientation="h",
        text=top10_df["향상도"].apply(lambda x: f"{x:.2f}"),
        color="향상도",
        color_continuous_scale="Viridis",
    )
    fig.update_layout(
        yaxis={"categoryorder": "total ascending"},
        xaxis_title="향상도 (Lift)",
        yaxis_title="연관 규칙 (조건 ➔ 결과)",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("표시할 연관 규칙이 없습니다.")
