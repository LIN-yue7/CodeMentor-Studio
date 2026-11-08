
"""Small versioned course corpus. Each card includes an attributable source."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class Card:
    id: str
    knowledge_id: str
    version: int
    title: str
    content: str
    source: str


TYPES = "https://docs.python.org/3/library/stdtypes.html"
TUTORIAL = "https://docs.python.org/3/tutorial/controlflow.html"
CARDS = (
    Card("loop-boundary-range-v1", "loop-boundary", 1, "range 的停止位置",
         "range(start, stop) 从 start 生成整数，正步长下生成的值始终小于 stop。用 len(xs) 作为 stop 可覆盖全部下标。",
         TYPES + "#ranges"),
    Card("loop-boundary-iteration-v1", "loop-boundary", 1, "直接遍历列表元素",
         "只需要值时使用 for item in xs；同时需要位置和值时可用 enumerate(xs)。用单元素输入核对循环是否漏掉末项。",
         TUTORIAL + "#the-range-function"),
    Card("empty-list-index-v1", "empty-list", 1, "空列表没有下标 0",
         "访问序列元素前保证下标有效。空列表没有首项；应按题意走默认值或显式错误分支。",
         TYPES + "#common-sequence-operations"),
    Card("empty-list-truth-v1", "empty-list", 1, "用真值判断空列表",
         "空列表的真值为 False。if not xs 可处理空输入，但默认值需符合题目契约。",
         TYPES + "#truth-value-testing"),
    Card("accumulator-order-v1", "accumulator", 1, "初始化与更新的顺序",
         "加法累加器在循环之前初始化为 0。循环体只做更新。试着写出每轮前后的值，检查是否丢失历史。",
         TUTORIAL + "#for-statements"),
    Card("accumulator-sum-v1", "accumulator", 1, "用 sum 复核累计结果",
         "对整数序列可使用 sum(xs) 作为结果参考。空输入时 sum([]) 为默认初值 0。",
         "https://docs.python.org/3/library/functions.html#sum"),
)


def retrieve(knowledge_id: str, limit: int = 2) -> list[dict]:
    return [asdict(card) for card in CARDS if card.knowledge_id == knowledge_id][:limit]
