# AI 방식 작은 MAC 계산기

원본 `data.json`이 제공되지 않아 학습용 합성 데이터를 만들었습니다. Cross/X 기본과제와 2D/1D MAC 비교, 홀수 크기 패턴 자동 생성을 포함합니다.

## 실행

```powershell
python main.py
python -m unittest discover -s . -p "test_*.py"
```

메뉴 2는 JSON 로드→`size_N` 추출→필터 선택→사례별 점수와 PASS/FAIL을 출력합니다. 메뉴 3은 홀수 크기의 Cross/X를 자동 생성합니다. `mac_2d`는 이중 반복 MAC, `mac_1d`는 펼친 배열 MAC입니다. `EPSILON=1e-9` 이내 점수 차이는 `UNDECIDED`입니다.

행렬은 정사각형·유한 숫자만 허용합니다. JSON 사례 하나가 잘못되어도 해당 사례만 FAIL 처리하고 나머지는 계속 분석합니다.

## 파일

- `main.py`: 검증, 2D/1D MAC, 동점 판정, JSON 분석, 패턴 생성
- `data.json`: 학습용 필터·패턴 데이터
- `test_main.py`: 계산·동점·JSON·패턴·오류 테스트
- `evidence/test-run.txt`: 실제 테스트 결과

MAC의 시간복잡도는 `O(N²)`입니다. 1000×1000은 1,000,000개 위치를 처리하므로 CPU와 메모리 대역폭의 영향을 받습니다. NPU 비교는 이론 설명이며 실제 NPU에서 실행하지 않았습니다. Cross는 홀수 크기의 가운데 행·열을 사용하고 짝수 크기는 제한합니다.

실행 결과는 실제 측정값만 기록하며, 원본 데이터가 제공되면 `data.json`만 교체해 다시 분석할 수 있습니다.
