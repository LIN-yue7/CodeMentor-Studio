
"""Reviewed Python exercises. Published template IDs carry their version."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Exercise:
    id: str
    title: str
    prompt: str
    answer: str
    hints: tuple[str, str]
    explanation: str


CURRICULUM = {
    "loop-boundary": (
        Exercise("boundary-a-v1", "最后一站", "对 [2, 3] 的所有元素求和。遍历应包含最后一个元素。填写正确的和。",
                 "5", ("先写出列表包含的两个下标。", "下标从 0 到 len(xs)-1，range 的上界不包含在内。"),
                 "0 和 1 都应访问，结果是 2 + 3 = 5。"),
        Exercise("boundary-b-v1", "单日库存", "对 [7] 的所有元素求和。填写正确的和。",
                 "7", ("检查长度为 1 时循环会运行几次。", "range(len(xs)) 在这个例子里产生下标 0。"),
                 "唯一的元素也需要被遍历，因此总和是 7。"),
        Exercise("boundary-c-v1", "三段路程", "对 [1, 4, 6] 的所有元素求和。填写正确的和。",
                 "11", ("列出所有下标。", "把下标 2 对应的元素也累加进去。"),
                 "完整访问下标 0、1、2，结果为 11。"),
    ),
    "empty-list": (
        Exercise("empty-a-v1", "空队列", "约定无任务时返回 -1。代码应对空列表 [] 返回什么？",
                 "-1", ("索引之前先判断列表是否为空。", "空列表应进入约定的默认值分支。"),
                 "空列表没有下标 0，应走默认值 -1 分支。"),
        Exercise("empty-b-v1", "无库存", "约定无库存时返回 0。代码应对空列表 [] 返回什么？",
                 "0", ("检查输入是否包含任何元素。", "此场景的默认值由题目指定。"),
                 "空列表返回 0，避免直接访问首项。"),
        Exercise("empty-c-v1", "首位乘客", "规则为有元素时返回首项，否则返回 -1。输入 [8, 2] 应返回什么？",
                 "8", ("先选空列表分支或非空分支。", "非空时读取下标 0。"),
                 "列表非空，应读取首项 8。"),
    ),
    "accumulator": (
        Exercise("accumulator-a-v1", "两次积分", "累加器只初始化一次。依次加入 3、4 后，总积分是多少？",
                 "7", ("第二轮开始时应保留第一轮结果。", "累加过程是 0 → 3 → 7。"),
                 "累加器应跨轮保留，最终结果是 7。"),
        Exercise("accumulator-b-v1", "账本结余", "从 0 开始，依次累加 4、-1、2。填写最终值。",
                 "5", ("每轮把新数加到当前总量。", "第一轮后为 4，第二轮后为 3。"),
                 "连续累加得到 0 → 4 → 3 → 5。"),
        Exercise("accumulator-c-v1", "零次更新", "初值为 0 的累加器遍历 [] 后，应返回什么？",
                 "0", ("空列表不会进入循环。", "初始化必须在循环之外。"),
                 "循环未执行，返回初始化值 0。"),
    ),
}
EXERCISES = {item.id: item for items in CURRICULUM.values() for item in items}
LABELS = {"loop-boundary": "循环边界", "empty-list": "空列表", "accumulator": "累加状态"}
