
export const examples = [
  { id: 'boundary', name: '循环边界', goal: 'sum-all', code: `def total(xs):
    result = 0
    for i in range(len(xs) - 1):
        result += xs[i]
    return result
` },
  { id: 'empty', name: '空列表', goal: 'first-or-empty', code: `def first(xs):
    return xs[0]
` },
  { id: 'accumulator', name: '累加状态', goal: 'sum-all', code: `def total(xs):
    for x in xs:
        result = 0
        result += x
    return result
` },
] as const
