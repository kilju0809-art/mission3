import json
import math
import time
from pathlib import Path

EPSILON = 1e-9


def validate_matrix(matrix, size=None):
    if not isinstance(matrix, list) or not matrix:
        raise ValueError("행렬은 비어 있지 않은 리스트여야 합니다.")
    actual = len(matrix)
    if size is not None and actual != size:
        raise ValueError(f"행 수가 {size}가 아닙니다.")
    for row in matrix:
        if not isinstance(row, list) or len(row) != actual:
            raise ValueError("정사각 행렬이어야 합니다.")
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in row):
            raise ValueError("모든 원소는 유한한 숫자여야 합니다.")
    return actual


def mac_2d(left, right):
    size = validate_matrix(left)
    validate_matrix(right, size)
    return sum(left[row][col] * right[row][col] for row in range(size) for col in range(size))


def mac_1d(left, right):
    validate_matrix(left)
    validate_matrix(right, len(left))
    return sum(a * b for a, b in zip(sum(left, []), sum(right, [])))


def classify(score_a, score_b):
    if math.isclose(score_a, score_b, abs_tol=EPSILON, rel_tol=0):
        return "UNDECIDED"
    return "A" if score_a > score_b else "B"


def average_ms(function, repetitions=10):
    start = time.perf_counter()
    for _ in range(repetitions):
        function()
    return (time.perf_counter() - start) * 1000 / repetitions


def normalize_label(label):
    return {"+": "Cross", "cross": "Cross", "Cross": "Cross", "x": "X", "X": "X"}.get(label)


def load_data(path="data.json"):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def analyze_json(path="data.json"):
    data = load_data(path)
    results = []
    for key, item in data.get("patterns", {}).items():
        try:
            size = int(key.split("_")[1])
            filters = data["filters"][f"size_{size}"]
            pattern = item["values"]
            validate_matrix(pattern, size)
            scores = {normalize_label(label): mac_2d(values, pattern) for label, values in filters.items() if normalize_label(label)}
            if not scores:
                raise ValueError("지원하는 필터가 없습니다.")
            predicted = max(scores, key=scores.get)
            expected = normalize_label(item.get("expected", ""))
            passed = predicted == expected
            results.append({"key": key, "size": size, "scores": scores, "expected": expected, "predicted": predicted, "passed": passed, "reason": "점수 최대 필터"})
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            results.append({"key": key, "passed": False, "reason": str(error)})
    return results


def generate_pattern(size, label):
    if size < 3 or size % 2 == 0:
        raise ValueError("자동 패턴 크기는 3 이상의 홀수여야 합니다.")
    normalized = normalize_label(label)
    if normalized not in {"Cross", "X"}:
        raise ValueError("Cross 또는 X만 지원합니다.")
    center = size // 2
    return [[int(row == center or col == center) if normalized == "Cross" else int(row == col or row + col == size - 1) for col in range(size)] for row in range(size)]


def main():
    print("=== AI 방식 작은 MAC 계산기 ===")
    print("1. 3x3 직접 계산  2. data.json 자동 분석  3. 패턴 자동 생성")
    choice = input("선택: ").strip()
    if choice == "2":
        results = analyze_json()
        for result in results:
            print(result)
        print(f"전체 {len(results)}건 / PASS {sum(item['passed'] for item in results)} / FAIL {sum(not item['passed'] for item in results)}")
    elif choice == "3":
        size = int(input("홀수 크기: "))
        label = input("Cross 또는 X: ")
        pattern = generate_pattern(size, label)
        print(f"{size}x{size} {normalize_label(label)} 생성 완료, MAC 자기 점수: {mac_2d(pattern, pattern)}")
    else:
        print("모드 1은 main.py의 함수와 테스트에서 3x3 입력을 검증합니다.")


if __name__ == "__main__":
    main()
