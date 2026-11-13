# R8 真实模型评测账

实际请求 **42/42**；24个不同源码案例，直接结构校验接受 **20/24**。另有6组A/B检索对照、3个原生工具场景以及1次工具修复复验。

逐项评审由开发助手对照源码、explanation、hints及关键patch进行，非独立盲评、非教师实验，不代表所有教学文本已核验。位置覆盖只测期望行是否在引用中，不等于语义正确。

## 核心质量检查

| 案例 | 原始状态 | 根因 | 修复 | 审阅意见 |
|---|---|---|---|---|
| syntax-colon | accepted | pass | pass | 对照合成源码，核心根因及条件化建议一致；未把静态推断冒充执行。 |
| cross-arity | failed | unavailable | unavailable | 原始请求未产生可交付结果：invalid-output |
| syntax-indent | accepted | pass | pass | 对照合成源码，核心根因及条件化建议一致；未把静态推断冒充执行。 |
| syntax-bracket | accepted | pass | pass | 对照合成源码，核心根因及条件化建议一致；未把静态推断冒充执行。 |
| syntax-quote | accepted | pass | pass | 对照合成源码，核心根因及条件化建议一致；未把静态推断冒充执行。 |
| boundary-empty | accepted | pass | pass | 对照合成源码，核心根因及条件化建议一致；未把静态推断冒充执行。 |
| boundary-last | accepted | pass | pass | 对照合成源码，核心根因及条件化建议一致；未把静态推断冒充执行。 |
| boundary-range | accepted | pass | pass | 对照合成源码，核心根因及条件化建议一致；未把静态推断冒充执行。 |
| boundary-single | accepted | pass | pass | 对照合成源码，核心根因及条件化建议一致；未把静态推断冒充执行。 |
| scope-local | accepted | pass | pass | 对照合成源码，核心根因及条件化建议一致；未把静态推断冒充执行。 |
| scope-branch | failed | unavailable | unavailable | 原始请求未产生可交付结果：invalid-output |
| scope-shadow | accepted | pass | fail | 首条建议和补丁把求和改成固定返回0；第二条删除遮蔽赋值才保留求和。禁止把这一案例记为有效修复。 |
| return-none | accepted | partial | pass | 正确讲出隐式None及反例，但缺完整文件标记导致过度保留“后面可能还有return”的不确定性。 |
| return-mutator | accepted | pass | pass | 对照合成源码，核心根因及条件化建议一致；未把静态推断冒充执行。 |
| return-type | accepted | pass | pass | 对照合成源码，核心根因及条件化建议一致；未把静态推断冒充执行。 |
| cross-alias | accepted | pass | pass | 对照合成源码，核心根因及条件化建议一致；未把静态推断冒充执行。 |
| cross-relative | accepted | pass | pass | 对照合成源码，核心根因及条件化建议一致；未把静态推断冒充执行。 |
| cross-docs | failed | unavailable | unavailable | 原始请求未产生可交付结果：invalid-output |
| correct-empty | accepted | pass | pass | 对照合成源码，核心根因及条件化建议一致；未把静态推断冒充执行。 |
| correct-scope | accepted | partial | pass | 正确判断没有已确认错误，但附带声称字符串元素会拼接不正确：整数0加字符串会TypeError。 |
| correct-return | failed | unavailable | unavailable | 原始请求未产生可交付结果：provider-error |
| recheck-colon | accepted | pass | pass | 对照合成源码，核心根因及条件化建议一致；未把静态推断冒充执行。 |
| recheck-boundary | accepted | pass | partial | 正确保留空输入修复，但建议再加None分支多余：当前if not values已经处理None。 |
| recheck-return | accepted | pass | pass | 对照合成源码，核心根因及条件化建议一致；未把静态推断冒充执行。 |

## 必须保留的限制

- 工具场景确实发生模型自主tool_calls，并保存每轮请求、参数、工具响应及最终文本。初测仅cross-arity完整接受；cross-alias被建议条数拒绝；cross-relative超轮次。限制末轮tool_choice=none后，cross-relative用3次真实请求复验通过。
- cross-alias等建议条数失败以当前校验器离线重放可恢复，不能改写成新的真实模型通过。对象数组等类型错误继续拒绝。
- scope-shadow错误补丁、correct-scope附加错误说明、return-none过度不确定均影响教学质量。已补充完整片段标记和提示约束；额度用尽后没有再做真实验证，不能宣称彻底解决。
- 正确源码样本仅3例，其中1例服务失败；另外3例修改后复查。可用回复没有将正确源码断言为确定错误，但附加解释仍有错误，不能推出误报率为零。
- A只给调用片段时会明确缺少实现；B/C能识别别名返回整数和相对导入空输入风险。这3组小样本不足以证明C比B诊断更准确。
- 检索24例是开发集；C标注行召回100%，B为87.5%，A为46.875%。非标注上下文不必然有害。没有向量数据库，不称为语义检索。

已返回请求延迟中位数 7044 ms，P95 9088 ms。记录token：{'prompt_tokens': 40257, 'completion_tokens': 34208, 'total_tokens': 74465}。失败请求缺失usage，不能当作零费用。

原始证据：live-pilot、live-main、live-recheck；汇总：evaluation-summary.json；检索：retrieval-evaluation.json。所有源码为合成，不含本机密钥。
