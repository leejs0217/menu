import re
from itertools import combinations, permutations
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
    return rules_df, item_counts, pair_counts


rules_df, item_counts, pair_counts = calculate_association_rules(
    baskets, total_days
)

# 사이드바 컨트롤
st.sidebar.header("필터 및 정렬 설정")

selected_menu = st.sidebar.selectbox(
    "메뉴 선택 (전체 보기: '전체')", options=["전체"] + all_menu_list
)

sort_option = st.sidebar.radio(
    "정렬 기준 선택", options=["향상도", "신뢰도", "동시"]
)

# 최소 동시 일수 슬라이더 추가
min_cooccurrence = st.sidebar.slider(
    "최소 동시 일수", min_value=1, max_value=10, value=1
)

# 데이터 필터링 (최소 동시 일수 및 메뉴 필터 적용)
filtered_df = rules_df[rules_df["동시"] >= min_cooccurrence].copy()

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
st.write(
    f"**급식 일수:** {total_days}일 | **메뉴 종류 수:** {len(all_menu_list)}개 | **함께 나온 적이 있는 메뉴 쌍의 수:** {len(rules_df) // 2}쌍"
)

# 표에 남은 규칙 개수 안내 문구
st.info(f"💡 현재 조건(최소 동시 일수 {min_cooccurrence}일 이상)에 맞는 필터링된 연관 규칙 수: **{len(filtered_df)}개**")

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

# 함께 나온 적 없는 짝 화면 추가
st.markdown("---")
st.subheader("🚫 함께 나온 적 없는 짝")

target_menu = st.selectbox(
    "기준 메뉴를 선택하세요 (독립 분석용)",
    options=all_menu_list,
    key="unpaired_menu_select",
)

if target_menu:
    target_count = item_counts.get(target_menu, 0)
    st.write(f"📌 선택한 메뉴 **'{target_menu}'** 이(가) 나온 날 수: **{target_count}일**")

    # 함께 나온 적 없는 메뉴 탐색
    never_paired = []
    for other_menu in all_menu_list:
        if other_menu == target_menu:
            continue

        # 무순서 쌍 키 확인
        pair_key1 = (target_menu, other_menu)
        pair_key2 = (other_menu, target_menu)

        co_count = pair_counts.get(pair_key1, 0) + pair_counts.get(pair_key2, 0)

        # 한번도 같이 안 나왔고, 혼자서는 10일 이상 나온 메뉴
        if co_count == 0:
            other_count = item_counts.get(other_menu, 0)
            if other_count >= 10:
                never_paired.append({"메뉴": other_menu, "단독 등장 일수": other_count})

    if never_paired:
        never_paired_df = pd.DataFrame(never_paired).sort_values(
            by="단독 등장 일수", ascending=False
        ).reset_index(drop=True)
        st.dataframe(never_paired_df, use_container_width=True)
    else:
        st.write("해당 메뉴와 한 번도 같이 나오지 않은 10일 이상 등장 메뉴가 없습니다.")
