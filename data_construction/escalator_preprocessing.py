import pandas as pd
# 저장 폴더 설정 (없으면 자동 생성)
save_dir = "data"
os.makedirs(save_dir, exist_ok=True)

# CSV 불러오는 경로 설정
save_path = os.path.join(save_dir, "서울교통공사_에스컬레이터.csv")
df_에스컬레이터 = pd.read_csv(save_path)

# 0) 컬럼 표준화(내부에서 쓰기 편하게 리네임)
df_에스컬레이터 = df_에스컬레이터.rename(columns={
    "역  명": "역명",
    "관리번호(호기)": "호기",
    "상하행구분": "상하행",
    "(근접)출입구번호": "출입구",
    "시작층(지상_지하)": "시작_지상지하",
    "시작층(운행역층)": "시작_층",
    "시작층(상세위치)": "시작_상세",
    "종료층(지상_지하)": "종료_지상지하",
    "종료층(운행역층)": "종료_층",
    "종료층(상세위치)": "종료_상세",
})

# 문자열 컬럼 정리
for c in ["호선","역명","상하행","출입구","시작_지상지하","시작_층","시작_상세",
          "종료_지상지하","종료_층","종료_상세"]:
    df_에스컬레이터[c] = df_에스컬레이터[c].astype(str).str.strip()

# 출입구->출구로 변수명 통일 전처리
df_에스컬레이터['출입구'] = df_에스컬레이터['출입구'].str.replace('출입구', '출구', regex=False)
df_에스컬레이터['시작_상세'] = df_에스컬레이터['시작_상세'].str.replace('출입구', '출구', regex=False)
df_에스컬레이터['종료_상세'] = df_에스컬레이터['종료_상세'].str.replace('출입구', '출구', regex=False)

# df['출입구'] 변수명 전처리
df_에스컬레이터['출입구'] = df_에스컬레이터['출입구'].str.replace('창동 방면2-4', '내부', regex=False)
df_에스컬레이터['출입구'] = df_에스컬레이터['출입구'].str.replace('내부 도봉산 방면 1-1', '내부', regex=False)

# 분류기: EXIT / INTERNAL (출구와 내부를 쉽게 구분하기 위함)
def classify(row: pd.Series) -> str:
    text = f"{row.get('출입구','')}"
    if '출구' in text:
        return "EXIT"

    return "INTERNAL"


df_에스컬레이터["etype"] = df_에스컬레이터.apply(classify, axis=1)

# CSV 저장
save_path = os.path.join(save_dir, "df_에스컬레이터.csv")
df_에스컬레이터.to_csv(save_path, index=False)