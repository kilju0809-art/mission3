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
    total = 0.0
    for row in range(size):
        for col in range(size):
            total += left[row][col] * right[row][col]
    return total


def mac_1d(left, right):
    validate_matrix(left)
    validate_matrix(right, len(left))
    return sum(a * b for a, b in zip(sum(left, []), sum(right, [])))


def classify(score_a, score_b, mode="mode1"):
    if math.isclose(score_a, score_b, abs_tol=EPSILON, rel_tol=0):
        return "판정 불가" if mode == "mode1" else "UNDECIDED"
    return "A" if score_a > score_b else "B"


def average_ms(function, repetitions=10):
    start = time.perf_counter()
    for _ in range(repetitions):
        function()
    return (time.perf_counter() - start) * 1000 / repetitions


def normalize_label(label):
    if not isinstance(label, str):
        return None
    return {"+": "Cross", "cross": "Cross", "x": "X"}.get(label.strip().lower(), label.strip() if label in {"Cross", "X"} else None)


def load_data(path="data.json"):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def analyze_json(path="data.json"):
    data = load_data(path)
    results = []
    for key, item in data.get("patterns", {}).items():
        try:
            parts = key.split("_")
            if len(parts) < 3 or parts[0] != "size":
                raise ValueError("패턴 키 형식은 size_N_번호여야 합니다.")
            size = int(parts[1])
            filters = data["filters"][f"size_{size}"]
            pattern = item["values"]
            validate_matrix(pattern, size)
            scores = {normalize_label(label): mac_2d(values, pattern) for label, values in filters.items() if normalize_label(label)}
            if not scores:
                raise ValueError("지원하는 필터가 없습니다.")
            best = max(scores.values())
            winners = [label for label, score in scores.items() if math.isclose(score, best, abs_tol=EPSILON, rel_tol=0)]
            predicted = winners[0] if len(winners) == 1 else "UNDECIDED"
            expected = normalize_label(item.get("expected", ""))
            passed = predicted == expected
            reason = "점수 최대 필터(점수가 높을수록 유사도가 높음)" if predicted != "UNDECIDED" else "최고 점수 동점"
            results.append({"key": key, "size": size, "scores": scores, "expected": expected, "predicted": predicted, "passed": passed, "reason": reason})
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            results.append({"key": key, "passed": False, "reason": str(error)})
    return results


def performance_table(sizes=(3, 5, 13, 25), repetitions=10):
    rows = []
    for size in sizes:
        matrix = generate_pattern(size, "Cross")
        elapsed = average_ms(lambda: mac_2d(matrix, matrix), repetitions)
        rows.append({"size": size, "average_ms": elapsed, "operations": size * size, "repetitions": repetitions})
    return rows


def generate_pattern(size, label):
    if size < 3 or size % 2 == 0:
        raise ValueError("자동 패턴 크기는 3 이상의 홀수여야 합니다.")
    normalized = normalize_label(label)
    if normalized not in {"Cross", "X"}:
        raise ValueError("Cross 또는 X만 지원합니다.")
    center = size // 2
    return [[int(row == center or col == center) if normalized == "Cross" else int(row == col or row + col == size - 1) for col in range(size)] for row in range(size)]


def read_matrix(input_func=input, size=3):
    while True:
        try:
            matrix = []
            for index in range(size):
                values = input_func(f"{index + 1}행(숫자 {size}개): ").split()
                if len(values) != size:
                    raise ValueError(f"숫자 {size}개를 입력하세요.")
                matrix.append([float(value) for value in values])
            validate_matrix(matrix, size)
            return matrix
        except ValueError as error:
            print(f"입력이 잘못되었습니다: {error} 다시 입력하세요.")


def run_mode1(input_func=input):
    print("필터 A를 입력하세요.")
    filter_a = read_matrix(input_func)
    print("필터 B를 입력하세요.")
    filter_b = read_matrix(input_func)
    print("입력 패턴을 입력하세요.")
    pattern = read_matrix(input_func)
    score_a = mac_2d(filter_a, pattern)
    score_b = mac_2d(filter_b, pattern)
    elapsed = average_ms(lambda: (mac_2d(filter_a, pattern), mac_2d(filter_b, pattern)), 10)
    decision = classify(score_a, score_b, "mode1")
    print(f"A 점수: {score_a} / B 점수: {score_b} / 평균 MAC 시간: {elapsed:.6f} ms (10회)")
    print(f"최종 판정: {decision}")
    return {"score_a": score_a, "score_b": score_b, "average_ms": elapsed, "decision": decision}


def run_mode2(path="data.json"):
    results = analyze_json(path)
    for result in results:
        print(f"{result['key']}: {result.get('scores', {})}, 예상={result.get('expected')}, 판정={result.get('predicted')}, {'PASS' if result['passed'] else 'FAIL'} - {result['reason']}")
    failures = [f"{item['key']}: {item['reason']}" for item in results if not item["passed"]]
    print(f"전체 {len(results)}건 / PASS {sum(item['passed'] for item in results)} / FAIL {len(failures)}")
    if failures:
        print("실패 목록:")
        print("\n".join(f"- {failure}" for failure in failures))
    print("크기 | 평균 ms(10회) | N² 연산 수")
    for row in performance_table():
        print(f"{row['size']} | {row['average_ms']:.6f} | {row['operations']}")
    return results


def main():
    print("=== AI 방식 작은 MAC 계산기 ===")
    print("1. 3x3 직접 입력  2. data.json 자동 분석  3. 패턴 자동 생성")
    choice = input("선택: ").strip()
    if choice == "1":
        run_mode1()
    elif choice == "2":
        run_mode2()
    elif choice == "3":
        size = int(input("홀수 크기: "))
        label = input("Cross 또는 X: ")
        pattern = generate_pattern(size, label)
        print(f"{size}x{size} {normalize_label(label)} 생성 완료, MAC 자기 점수: {mac_2d(pattern, pattern)}")
    else:
        print("1~3 중에서 선택하세요.")


if __name__ == "__main__":
    main()
