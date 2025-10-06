from your_module import fetch_all_fst_exit  
import os
import re
import pandas as pd
import numpy as np
from dotenv import load_dotenv

BASE_URL = "http://apis.data.go.kr/B553766/inout/getFstExit"

def fetch_all_fst_exit(
    service_key: str,
    stnNm: Optional[str] = None,
    lineNm_contains: Optional[str] = None,
    page_size: int = 500,
    select_fields: Optional[str] = None,
    timeout: int = 15,
) -> List[dict]:
    """
    지하철 '빠른 승하차' 정보를 조건에 맞춰 모두 조회.
    - stnNm가 주어지면 해당 역만, 주어지지 않으면 전체 역
    - lineNm_contains가 주어지면 호선 포함 검색.
    - select_fields를 지정하지 않으면 유용한 기본 필드 세트 사용.
    """
    items: List[dict] = []
    page_no = 1

    if not select_fields:
        select_fields = ",".join([
            "stnNm","stnCd","stnNo","lineNm",
            "upbdnbSe","drtnInfo",
            "plfmCmgFac","qckgffVhclDoorNo",
            "facPstnNm","fwkPstnNm","crtrYmd",
            "elvtrNo","facNo"
        ])

    while True:
        params: Dict[str, Union[str, int]] = {
            "serviceKey": service_key,
            "pageNo": page_no,
            "numOfRows": page_size,
            "dataType": "JSON",
            "selectFields": select_fields,
        }
        # stnNm이 주어졌을 때만 파라미터 포함 (없으면 전체 검색)
        if stnNm:
            params["stnNm"] = stnNm
        if lineNm_contains:
            params["lineNm"] = lineNm_contains  # 포함검색

        resp = requests.get(BASE_URL, params=params, timeout=timeout)
        resp.raise_for_status()
        j = resp.json()

        response = j.get("response", {})
        body = response.get("body", {})
        raw_items = body.get("items", {}).get("item", [])

        # 단일 객체 케이스 보정
        if isinstance(raw_items, dict):
            raw_items = [raw_items]

        if not raw_items:
            break

        items.extend(raw_items)

        # totalCount 기반 종료 (가능하면 더 정확)
        total = body.get("totalCount")
        if total is not None and isinstance(total, (int, str)):
            try:
                if len(items) >= int(total):
                    break
            except ValueError:
                pass

        # 마지막 페이지(이번 페이지가 page_size보다 적음)
        if len(raw_items) < page_size:
            break

        page_no += 1

    return items


load_dotenv()  # .env 파일에서 환경변수 로드
KEY = os.getenv("API_KEY")

items = fetch_all_fst_exit(service_key=KEY)
df_빠른하차 = pd.DataFrame(items)

## 불러온 데이터 전처리 및 저장.
# 컬럼명 한글화
df_빠른하차 = df_빠른하차.rename(columns = {
                          'lineNm': '호선',
                          'stnNm': '역명',
                          'stnNo': '역코드',
                          'upbdnbSe': '상하행',
                          'drtnInfo': '방면',
                          'qckgffVhclDoorNo': '탑승구',
                          'plfmCmgFac': '근접이동시설',
                          'elvtrNo': '승강기_일련번호',
                          'fwkPstnNm': '탑승구_층',
                          'facPstnNm': '방면_탑승구'
                          })

df = df_빠른하차.copy()

# 1) '탑승구_층'에서 B2/4F/B3만 추출
df['탑승구_층'] = df['탑승구_층'].astype(str).str.extract(r'(B\d+|\d+F)', expand=False)

# 2) 승강장 유형 컬럼
df['탑승구_층'] = df['탑승구_층'].astype(str).str.extract(r'(B\d+|\d+F)', expand=False)
df['호선'] = df['호선'].str.extract(r'(\d+)')[0].astype(int)
df_승강장유형 = df_arch[['호선', '역명', '승강장유형']].copy()
df = df.merge(
    df_승강장유형,
    on=['호선', '역명'],   # 두 컬럼이 같을 때 병합
    how='left'            # df 기준으로 병합, 없는 값은 NaN
)

# 최종 결과를 df_빠른하차로 저장
df_빠른하차 = df[['호선', '역명', '역코드', '상하행', '방면', '탑승구', '근접이동시설', '승강기_일련번호', '탑승구_층', '방면_탑승구', '승강장유형']]
df_빠른하차.loc[df_빠른하차['승강장유형'].isna(), '승강장유형'] = '섬식'

# 저장 폴더 설정 (없으면 자동 생성)
save_dir = "data"
os.makedirs(save_dir, exist_ok=True)

# CSV 저장 경로 설정
save_path = os.path.join(save_dir, "df_빠른하차.csv")

# CSV 저장
df_빠른하차.to_csv(save_path, index=False)