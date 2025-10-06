import pandas as pd
import numpy as np

# 저장 폴더 설정 (없으면 자동 생성)
save_dir = "data"
os.makedirs(save_dir, exist_ok=True)

# CSV 불러오는 경로 설정
save_path1 = os.path.join(save_dir, "df_에스컬레이터.csv")
save_path2 = os.path.join(save_dir, "df_빠른하차.csv")
df_에스컬레이터 = pd.read_csv(save_path1)
df_빠른하차 = pd.read_csv(save_path2)

# df_빠른하차와 컬럼이름, 역명 통일
df_에스컬레이터 = df_에스컬레이터.rename(columns = {'승강기 일련번호':'승강기_일련번호'})
df_에스컬레이터['역명'] = (
    df_에스컬레이터['역명']
    .astype(str)
    .str.replace(r'\s*\(\d+\)$', '', regex=True)

left  = _norm_keys(df_에스컬레이터)
right = _norm_keys(df_빠른하차)

# 1. 오른쪽에서 붙일 컬럼만 선택 (존재하는 것만)
right_cols_to_take = ['탑승구_층','방면_탑승구','승강장유형','탑승구','방면']
keep = ['승강기_일련번호','역명'] + [c for c in right_cols_to_take if c in right.columns]
right_sub = right[keep]

# 2. 병합 (df_에스컬레이터 중심의 left join)
merged = left.merge(
    right_sub,
    on=['승강기_일련번호','역명'],
    how='left'
)

# 3. 병합 실패한 행은 지정 컬럼을 None으로 
for c in right_cols_to_take:
    if c in merged.columns:
        merged[c] = merged[c].astype('object').where(merged[c].notna(), None)
    else:
        # 우측에 없던 컬럼은 생성해서 모두 None
        merged[c] = None

# 결과 저장
df_에스컬레이터_병합 = merged

# 중복 행제거
df_에스컬레이터_병합 = df_에스컬레이터_병합.drop_duplicates().reset_index(drop=True)

# 병합 데이터 저장
save_path = os.path.join(save_dir, "df_에스컬레이터_빠른하차_merge.csv")
df_에스컬레이터_병합.to_csv(save_path, index=False)