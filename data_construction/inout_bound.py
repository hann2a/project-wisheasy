import re
import pandas as pd

# 저장 폴더 설정 (없으면 자동 생성)
save_dir = "data"
os.makedirs(save_dir, exist_ok=True)

# CSV 불러오는 경로 설정
save_path = os.path.join(save_dir, "df_에스컬레이터_빠른하차_merge.csv")
df = pd.read_csv(save_path)

# 층 정보 문자열을 숫자형으로 변환하는 함수 (지상/지하 구분 포함)
def pair_floor_to_num(grade, level):
    """
    예: 
        grade = '지하', level = '2'  →  -2
        grade = '지상', level = '1'  →   1
    역할:
        - '지하'면 음수, '지상'이면 양수로 층수를 변환
        - 비어 있거나 잘못된 값은 None 반환
    """
    if pd.isna(grade) or pd.isna(level):   # 결측값 처리
        return None
    g = str(grade).strip()                 # '지상' / '지하' 텍스트 정리
    m = re.search(r'(\d+)', str(level))    # 층 번호 추출 (예: 1, 2, 3)
    if not m:                              # 숫자가 없으면 None 반환
        return None
    n = int(m.group(1))                    # 정수로 변환

    # '지하'는 음수로 변환
    if '지하' in g:
        return -n
    # '지상'은 양수로 변환
    if '지상' in g:
        return n
    # 둘 다 해당 안 되면 None
    return None

# 일반적인 층 텍스트를 숫자형으로 변환하는 함수
def text_floor_to_num(s):
    """
    예시 입력 → 출력:
        'B2'   → -2
        '3층'  → 3
        '지상' → 0
        'GF'   → 0
    역할:
        - 문자열에서 숫자형 층수 추출
        - B(지하)는 음수, F(지상)은 양수
    """
    if pd.isna(s):
        return None
    t = str(s).strip().upper()  # 대문자로 통일 ('b2' → 'B2')

    # 지상층 또는 Ground층(GF) 처리
    if t in {"G", "GF", "GR", "G층", "지상", "0", "0층"}:
        return 0

    # 'B숫자' 패턴 (예: 'B2', 'B 3')
    m = re.search(r'B\s*([0-9]+)', t)
    if m:
        return -int(m.group(1))

    # '숫자층' 패턴 (예: '2층')
    m = re.search(r'(\d+)\s*층', t)
    if m:
        return int(m.group(1))

    # 그냥 숫자 형태인 경우 (예: '3', '-2')
    m = re.match(r'^[+-]?\d+$', t)
    if m:
        return int(t)

    # 어떤 패턴에도 맞지 않으면 None
    return None

# 시작/종료 층을 숫자로 변환하여 새 컬럼 생성
df["시작_층_num"] = [
    pair_floor_to_num(a, b) for a, b in zip(df.get("시작_지상지하"), df.get("시작_층"))
]
df["종료_층_num"] = [
    pair_floor_to_num(a, b) for a, b in zip(df.get("종료_지상지하"), df.get("종료_층"))
]

# 탑승구의 층 정보도 숫자형으로 변환 (예: 'B2' → -2)
df["탑승구_층_num"] = (
    df["탑승구_층"].apply(text_floor_to_num) if "탑승구_층" in df.columns else None
)

# 역 / 방면탑승구 / 플랫폼층별로 그룹화하여 에스컬레이터의 방향(상행/하행)을 판정
records = []  # 결과를 저장할 리스트
group_cols = ["역명", "방면_탑승구", "탑승구_층_num"]

for (stn, dirgate, plat), sub in df.groupby(group_cols, dropna=False):
    # 플랫폼 층 정보가 없으면 스킵
    if plat is None or pd.isna(plat):
        continue
    
    # 들어오는 방향(inbound): 종료층이 플랫폼층과 같고, 시작층이 존재할 때
    inbound = ((sub["종료_층_num"] == plat) & sub["시작_층_num"].notna()).any()
    # 나가는 방향(outbound): 시작층이 플랫폼층과 같고, 종료층이 존재할 때
    outbound = ((sub["시작_층_num"] == plat) & sub["종료_층_num"].notna()).any()

    """
    환승역에는 각 호선별로 역이 구성되어있다. 때문에 한 호선에서만 보면 지하1층 지하2층이지만
    실제로는 지하1층 지하3층인 경우가 있다. 그래서 데이터 상에는 실제 역과 정보가 일치하지 않는다
    때문에 하행인데 플랫폼이 더 아래면 inbound 상행인데 플랫폼이 더 위쪽이면 outbound 라고 판단
    해주는 로직을 추가하여 판정했다. 
    """
    sub_ok = sub[sub["시작_층_num"].notna() & sub["종료_층_num"].notna()].copy()
    if len(sub_ok):
        # 시작/종료층과 플랫폼층 간의 거리(차이 절댓값) 계산
        dist_start = (sub_ok["시작_층_num"] - plat).abs()
        dist_end = (sub_ok["종료_층_num"] - plat).abs()

        # 거리 비교를 통해 방향 추론
        infer_inbound = (dist_end < dist_start).any()    # 플랫폼과 가까워지는 방향 → 들어오는 방향
        infer_outbound = (dist_start < dist_end).any()   # 플랫폼에서 멀어지는 방향 → 나가는 방향

        # 하행(시작층 > 종료층)인데 플랫폼이 더 아래쪽이면 → 들어오는 방향(inbound)
        more_inbound = (
            ((sub_ok["시작_층_num"] > sub_ok["종료_층_num"]) &
             (plat <= sub_ok[["시작_층_num", "종료_층_num"]].min(axis=1))
            ).any()
        )

        # 상행(시작층 < 종료층)인데 플랫폼이 더 위쪽이면 → 나가는 방향(outbound)
        more_outbound = (
            ((sub_ok["시작_층_num"] < sub_ok["종료_층_num"]) &
             (plat >= sub_ok[["시작_층_num", "종료_층_num"]].max(axis=1))
            ).any()
        )

        # 기존 값(False)이면 추론/보정 결과를 반영
        if not inbound and (infer_inbound or more_inbound):
            inbound = True
        if not outbound and (infer_outbound or more_outbound):
            outbound = True


    # 최종 판정 태그 부여
    if inbound and outbound:
        tag = "양방향 가능"
    elif inbound and not outbound:
        tag = "들어오기만 가능"
    elif (not inbound) and outbound:
        tag = "나가기만 가능"
    else:
        tag = "에스컬레이터 없음"

    # 결과 기록 저장
    records.append({
        "역명": stn,
        "방면_탑승구": dirgate,
        "탑승구_층": plat,
        "inbound": bool(inbound),
        "outbound": bool(outbound),
        "판정": tag
    })

# 결과 DataFrame 생성 및 정렬
status = pd.DataFrame(records).sort_values(["역명", "방면_탑승구", "탑승구_층"])

# CSV 저장
save_path = os.path.join(save_dir, "탑승구_판정.csv")
status.to_csv(save_path, index=False)