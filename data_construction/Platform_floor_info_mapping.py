import pandas as pd
import re

# 저장 폴더 설정 (없으면 자동 생성)
save_dir = "data"
os.makedirs(save_dir, exist_ok=True)

# CSV 불러오는 경로 설정
save_path = os.path.join(save_dir, ".서울교통공사_역사건축정보_20250310.csv")
df_arch = pd.read_csv(save_path)



def parse_any_floors(s: str):
    """
    문자열에 포함된 층 정보를 숫자로 변환하는 함수.
    - '지하'층(B로 시작)은 음수(-)로 변환
    - '지상'층(F로 끝)은 양수(+)로 변환

    예시:
        'B2' → [-2]
        '1F' → [1]
        'B2, B3' → [-2, -3]
        '지하1층~지하2층' → [-1, -2]
    """
    if s is None:
        return []

    # 대소문자 구분 없이 'B', 'F' 인식되도록 대문자로 변환
    S = str(s).upper()
    floors = []

    # 1) 'B숫자' 패턴 (지하층) → 음수로 변환하여 리스트에 추가
    for m in re.finditer(r'B(\d+)', S):
        floors.append(-int(m.group(1)))

    # 2) '숫자F' 패턴 (지상층) → 양수로 변환하여 리스트에 추가
    for m in re.finditer(r'(\d+)F', S):
        floors.append(int(m.group(1)))

    # 3) 여러 층이 포함된 경우, 예: "B1~B2" → [-1, -2] 반환
    return floors


def ho_label(n) -> str:
    """
    입력값을 'X호선' 형태로 변환하는 함수.
    - 숫자가 들어오면 정수형으로 변환 후 '호선' 접미사 추가
    - 이미 '호선'이 붙어있는 문자열은 그대로 유지

    예시:
        2 → '2호선'
        '3' → '3호선'
        '7호선' → '7호선'
    """
    try:
        # 숫자형이면 'X호선'으로 변환
        return f"{int(n)}호선"
    except:
        # 문자열일 경우 여백 제거 후 처리
        s = str(n).strip()
        # 이미 '호선'으로 끝나면 그대로 반환, 아니면 '호선' 붙이기
        return s if s.endswith("호선") else s + "호선"


def build_platform_map_from_arch(arch_df: pd.DataFrame) -> pd.DataFrame:
    """
    역사 구조 데이터(arch_df)를 기반으로 각 역의 플랫폼(승강장) 층 정보를 도출하는 함수.

    처리 과정:
    1. 원본 데이터 복사 → '호선'을 'X호선' 형태로 정규화
    2. 각 층수 문자열에서 가장 깊은 층(=플랫폼층)을 계산
    3. 역명 + 호선별로 그룹화하여 가장 깊은 층(지하 최하층)을 플랫폼층으로 확정
    4. 숫자층(-2 → B2, 1 → 1F) 형태로 사람이 읽기 좋은 라벨 생성
    5. 최종적으로 [역명, 호선, 플랫폼층_int, 플랫폼층] 컬럼만 반환

    반환 예시:
        역명     호선   플랫폼층_int   플랫폼층
        서울역   1호선     -2          B2
        서울역   4호선     -3          B3
        강남역   2호선     -2          B2
    """

    # 1. 원본 복사 및 호선명 정규화
    tmp = arch_df.copy()
    tmp["호선라벨"] = tmp["호선"].apply(ho_label)

    # 2. 각 층 정보에서 가장 깊은 층(숫자로) 계산
    def deepest(s):
        arr = parse_any_floors(s)
        if not arr:
            return None
        # 예: [-1, -2] → -2 반환 (가장 깊은 층)
        return min(arr)

    # '층수' 컬럼에서 각 행별로 최하층 계산
    tmp["deepest_floor_int"] = tmp["층수"].apply(deepest)

    # 3. 역명 + 호선 기준으로 그룹화하여 최하층(플랫폼층) 계산
    plat = (
        tmp.groupby(["역명", "호선라벨"], as_index=False)
           .agg(플랫폼층_int=("deepest_floor_int", "min"))
    )

    # 4. 숫자층(-2, 1 등)을 사람이 읽기 좋은 라벨(B2, 1F 등)로 변환
    def to_label(n):
        if pd.isna(n):
            return None
        n = int(n)
        # 음수면 'B숫자' (지하층), 양수면 '숫자F' (지상층)
        return f"B{abs(n)}" if n < 0 else f"{n}F"

    plat["플랫폼층"] = plat["플랫폼층_int"].apply(to_label)

    # 5. 필요한 컬럼만 정리하여 반환
    return plat[["역명", "호선라벨", "플랫폼층_int", "플랫폼층"]]


# 플랫폼 맵 생성 및 컬럼명 정리
platform_map_df = build_platform_map_from_arch(df_arch)

# '호선라벨' 컬럼명을 최종적으로 '호선'으로 변경
platform_map_df = platform_map_df.rename(columns={'호선라벨': '호선'})

# CSV 저장
save_path = os.path.join(save_dir, "탑승구_층.csv")
platform_map_df.to_csv(save_path, index=False)