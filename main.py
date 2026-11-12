import json
import math
import re
import time
from collections import Counter
from pathlib import Path

EPSILON = 1e-9
LABEL_ALIASES = {
    "+": "Cross",
    "cross": "Cross",
    "x": "X",
}
PATTERN_KEY = re.compile(r"size_([1-9]\d*)_([A-Za-z0-9-]+)\Z")
SIZE_GROUP_KEY = re.compile(r"size_([1-9]\d*)\Z")


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


def mac_2d(left, right, debug=False):
    size = validate_matrix(left)
    validate_matrix(right, size)
    total = 0.0
    for row in range(size):
        for col in range(size):
            total += left[row][col] * right[row][col]
            if debug:
                print(f"중간 누적합 [{row + 1},{col + 1}]: {total:g}")
    return total


def mac_1d(left, right):
    validate_matrix(left)
    validate_matrix(right, len(left))
    return sum(a * b for a, b in zip(sum(left, []), sum(right, [])))


def classify(score_a, score_b, mode="mode1"):
    if math.isclose(score_a, score_b, rel_tol=EPSILON, abs_tol=EPSILON):
        return "판정 불가" if mode == "mode1" else "UNDECIDED"
    return "A" if score_a > score_b else "B"


def average_ms(function, repetitions=10):
    if not callable(function):
        raise ValueError("측정 대상은 호출할 수 있어야 합니다.")
    if isinstance(repetitions, bool) or not isinstance(repetitions, int) or repetitions < 1:
        raise ValueError("반복 횟수는 1 이상의 정수여야 합니다.")
    start = time.perf_counter()
    for _ in range(repetitions):
        function()
    return (time.perf_counter() - start) * 1000 / repetitions


def normalize_label(label):
    if not isinstance(label, str):
        return None
    return LABEL_ALIASES.get(label.strip().casefold())


def load_data(path="data.json"):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _available_size_keys(filters_by_size):
    keys = [
        key for key in filters_by_size
        if isinstance(key, str) and SIZE_GROUP_KEY.fullmatch(key)
    ]
    return sorted(keys, key=lambda key: int(SIZE_GROUP_KEY.fullmatch(key).group(1)))


def analyze_json(path="data.json"):
    data = load_data(path)
    if not isinstance(data, dict):
        raise ValueError("JSON 최상위 값은 객체여야 합니다.")
    patterns = data.get("patterns", {})
    filters_by_size = data.get("filters", {})
    if not isinstance(patterns, dict):
        raise ValueError("patterns는 객체여야 합니다.")
    if not isinstance(filters_by_size, dict):
        raise ValueError("filters는 객체여야 합니다.")

    available_sizes = _available_size_keys(filters_by_size)
    results = []
    for key, item in patterns.items():
        category = "key"
        warnings = []
        try:
            match = PATTERN_KEY.fullmatch(key) if isinstance(key, str) else None
            if match is None:
                raise ValueError("패턴 키 형식은 size_<양의정수>_<식별자>여야 합니다.")
            size = int(match.group(1))
            filter_key = f"size_{size}"
            if filter_key not in filters_by_size:
                choices = ", ".join(available_sizes) if available_sizes else "없음"
                raise ValueError(f"필터 {filter_key}가 없습니다. 사용 가능한 크기: {choices}.")

            category = "format"
            if not isinstance(item, dict):
                raise ValueError("패턴 데이터는 객체여야 합니다.")
            filters = filters_by_size[filter_key]
            if not isinstance(filters, dict):
                raise ValueError(f"{filter_key} 필터는 객체여야 합니다.")
            if "values" not in item:
                raise ValueError("패턴에 values 행렬이 없습니다.")
            pattern = item["values"]
            validate_matrix(pattern, size)

            scores = {}
            for label, values in filters.items():
                normalized = normalize_label(label)
                if normalized is None:
                    warnings.append(f"지원하지 않는 필터 라벨 {label!r}은 제외했습니다.")
                    continue
                validate_matrix(values, size)
                scores[normalized] = mac_2d(values, pattern)
            if not scores:
                raise ValueError("지원하는 필터가 없습니다. Cross 또는 X 라벨을 확인하세요.")

            category = "match"
            best = max(scores.values())
            winners = [
                label for label, score in scores.items()
                if math.isclose(score, best, rel_tol=EPSILON, abs_tol=EPSILON)
            ]
            predicted = winners[0] if len(winners) == 1 else "UNDECIDED"
            expected = normalize_label(item.get("expected", ""))
            if expected is None:
                warnings.append(f"기대 라벨 {item.get('expected')!r}은 지원하지 않는 값입니다.")

            passed = predicted == expected
            if len(winners) > 1:
                reason = "최고 점수 동점"
            elif passed:
                reason = "예측과 기대 라벨이 일치합니다."
            else:
                reason = f"기대 라벨 {expected!r}과 예측 {predicted!r}이 다릅니다."
            results.append({
                "key": key,
                "size": size,
                "scores": scores,
                "best_score": best,
                "tied_candidates": winners if len(winners) > 1 else [],
                "expected": expected,
                "predicted": predicted,
                "passed": passed,
                "category": category,
                "reason": reason,
                "warnings": warnings,
            })
        except (KeyError, TypeError, ValueError) as error:
            results.append({
                "key": key,
                "passed": False,
                "category": category,
                "reason": str(error),
                "warnings": warnings,
            })
    return results


def performance_table(sizes=(3, 5, 13, 25), repetitions=10):
    rows = []
    for size in sizes:
        matrix = generate_pattern(size, "Cross")
        elapsed = average_ms(lambda: mac_2d(matrix, matrix), repetitions)
        rows.append({
            "size": size,
            "average_ms": elapsed,
            "operations": size * size,
            "repetitions": repetitions,
        })
    return rows


def generate_pattern(size, label):
    if isinstance(size, bool) or not isinstance(size, int) or size < 3 or size % 2 == 0:
        raise ValueError("자동 패턴 크기는 3 이상의 홀수여야 합니다.")
    normalized = normalize_label(label)
    if normalized not in {"Cross", "X"}:
        raise ValueError("Cross 또는 X만 지원합니다.")
    center = size // 2
    return [
        [
            int(row == center or col == center)
            if normalized == "Cross"
            else int(row == col or row + col == size - 1)
            for col in range(size)
        ]
        for row in range(size)
    ]


def _retry_message(error):
    return f"입력 오류: {error} 다시 입력하세요."


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
            print(_retry_message(error))


def read_pattern_size(input_func=input):
    while True:
        try:
            size = int(input_func("홀수 크기(3 이상): ").strip())
            if size < 3 or size % 2 == 0:
                raise ValueError("3 이상의 홀수를 입력하세요.")
            return size
        except ValueError as error:
            print(_retry_message(error))


def read_pattern_label(input_func=input):
    while True:
        label = input_func("라벨(Cross, +, cross, X): ").strip()
        normalized = normalize_label(label)
        if normalized is not None:
            return normalized
        print(_retry_message("Cross, +, cross 또는 X 중 하나를 입력하세요."))


def read_debug_option(input_func=input):
    while True:
        value = input_func("중간 누적합 디버그 출력? (y/n, 기본 n): ").strip().casefold()
        if value in {"", "n", "no", "아니오", "아니요"}:
            return False
        if value in {"y", "yes", "예"}:
            return True
        print(_retry_message("y 또는 n을 입력하세요."))


def run_mode1(input_func=input, debug=False):
    print("필터 A를 입력하세요.")
    filter_a = read_matrix(input_func)
    print("필터 B를 입력하세요.")
    filter_b = read_matrix(input_func)
    print("입력 패턴을 입력하세요.")
    pattern = read_matrix(input_func)
    score_a = mac_2d(filter_a, pattern, debug=debug)
    score_b = mac_2d(filter_b, pattern, debug=debug)
    elapsed = average_ms(lambda: (mac_2d(filter_a, pattern), mac_2d(filter_b, pattern)), 10)
    decision = classify(score_a, score_b, "mode1")
    print(
        f"입력 크기: 3×3 | A 점수: {score_a} / B 점수: {score_b} "
        f"/ 평균 MAC 시간: {elapsed:.6f} ms (10회)"
    )
    print(f"최종 판정: {decision}")
    return {
        "size": 3,
        "score_a": score_a,
        "score_b": score_b,
        "average_ms": elapsed,
        "decision": decision,
    }


def run_mode2(path="data.json"):
    try:
        results = analyze_json(path)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
        print(f"입력 오류: JSON을 분석할 수 없습니다. {error} 수정 후 다시 실행하세요.")
        return []

    for result in results:
        scores = result.get("scores", {})
        score_text = ", ".join(f"{label}={score:g}" for label, score in scores.items())
        print(
            f"{result['key']}: {score_text}, 예상={result.get('expected')}, "
            f"판정={result.get('predicted')}, {'PASS' if result['passed'] else 'FAIL'} "
            f"[{result.get('category', 'format')}] - {result['reason']}"
        )
        if result.get("tied_candidates"):
            tied = ", ".join(
                f"{label}={scores[label]:g}" for label in result["tied_candidates"]
            )
            print(f"  동점 후보(동일 점수 {result['best_score']:g}): {tied}")
        for warning in result.get("warnings", []):
            print(f"  경고: {warning}")

    failures = [item for item in results if not item["passed"]]
    failure_counts = Counter(item.get("category", "format") for item in failures)
    print(
        f"전체 {len(results)}건 / PASS {len(results) - len(failures)} / FAIL {len(failures)}"
    )
    print(
        "실패 요약: "
        f"키 형식·필터 누락 {failure_counts['key']}건 / "
        f"데이터 형식 {failure_counts['format']}건 / "
        f"예측·기대값 불일치 {failure_counts['match']}건"
    )
    if failures:
        print("실패 목록:")
        print(
            "\n".join(
                f"- {item['key']} [{item.get('category', 'format')}]: {item['reason']}"
                for item in failures
            )
        )

    print("크기 | 평균 시간(ms) | 반복수 | 위치 연산 수(N²)")
    for row in performance_table():
        print(
            f"{row['size']} | {row['average_ms']:.6f} | "
            f"{row['repetitions']} | {row['operations']}"
        )
    return results


def main():
    print("=== AI 방식 작은 MAC 계산기 ===")
    print("1. 3x3 직접 입력  2. data.json 자동 분석  3. 패턴 자동 생성")
    while True:
        choice = input("선택: ").strip()
        if choice in {"1", "2", "3"}:
            break
        print(_retry_message("1~3 중에서 메뉴를 선택하세요."))
    if choice == "1":
        run_mode1(debug=read_debug_option())
    elif choice == "2":
        run_mode2()
    else:
        size = read_pattern_size()
        label = read_pattern_label()
        pattern = generate_pattern(size, label)
        print(f"{size}x{size} {label} 생성 완료, MAC 자기 점수: {mac_2d(pattern, pattern)}")


if __name__ == "__main__":
    main()
