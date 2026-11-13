"""Offline native-tool protocol tests; no live provider or private settings."""
import copy
import hashlib
import json

import httpx
import pytest

from app.core.llm_client import GenericLLMClient, LLMClientConfig


def reply(content=None, calls=None, finish=None):
    return {
        'model': 'test',
        'choices': [{'message': {'role': 'assistant', 'content': content,
                                 'tool_calls': calls or []},
                     'finish_reason': finish or ('tool_calls' if calls else 'stop')}],
        'usage': {'prompt_tokens': 5, 'completion_tokens': 3, 'total_tokens': 8},
    }


def call(name, args, identifier='call_1'):
    return {'id': identifier, 'type': 'function',
            'function': {'name': name, 'arguments': json.dumps(args)}}


def client(handler):
    return GenericLLMClient(
        LLMClientConfig(model_name='test', base_url='https://example.test/v1',
                        api_key='test-only', max_retries=4, retry_backoff_seconds=0),
        transport=httpx.MockTransport(handler),
    )


async def test_native_tool_response_accepts_empty_content_and_preserves_wire_messages():
    seen = []
    native_call = call('get_current_file', {'start_line': 1, 'end_line': 2})

    def handler(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=reply(calls=[native_call]) if len(seen) == 1 else reply('done'))

    model = client(handler)
    try:
        result = await model.chat_tools([{'role': 'user', 'content': 'help'}], [])
        assert result.content == ''
        assert result.tool_calls == [native_call]
        await model.chat_tools([
            {'role': 'user', 'content': 'help'}, result.assistant_message,
            {'role': 'tool', 'tool_call_id': 'call_1', 'content': '{"snippets":[]}'},
        ], [])
    finally:
        await model.aclose()
    assert seen[1]['messages'][1]['tool_calls'] == [native_call]
    assert seen[1]['messages'][2]['tool_call_id'] == 'call_1'
    assert seen[0]['tool_choice'] == 'auto'


async def test_native_tool_errors_never_retry_or_fallback():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(429, json={'error': {'message': 'rate limit'}})

    model = client(handler)
    try:
        with pytest.raises(Exception, match='429'):
            await model.chat_tools([{'role': 'user', 'content': 'help'}], [])
    finally:
        await model.aclose()
    assert len(seen) == 1


def snapshot():
    files = {'main.py': 'from helper import add\nprint(add(1, 2))',
             'helper.py': 'def add(a, b):\n    return a - b'}
    return {'files': files, 'path': 'main.py',
            'buffer_hash': hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
            'diagnostics': [{'path': 'main.py', 'line': 2, 'message': 'example'}],
            'learning_history': [{'path': 'main.py', 'kind': 'hint-viewed'}]}


async def run_with(responses, snap=None, data=None):
    from app.services.project_agent import run_agent
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=responses[min(len(requests) - 1, len(responses) - 1)])

    model = client(handler)
    try:
        result = await run_agent(model, snap or snapshot(), data or {'snippets': []}, 'review')
    finally:
        await model.aclose()
    return result, requests


async def test_agent_records_only_evidence_sent_to_next_model_turn():
    result, requests = await run_with([
        reply(calls=[call('search_project', {'query': 'return', 'limit': 5})]), reply('final'),
    ])
    assert result['status'] == 'completed'
    assert result['content'] == 'final'
    assert result['snippets'] == [{'path': 'helper.py', 'line': 2, 'quote': '    return a - b'}]
    tool_result = json.loads(requests[1]['messages'][-1]['content'])
    assert tool_result['snippets'] == result['snippets']
    assert result['tool_trace'][0]['status'] == 'ok'
    assert result['usage']['total_tokens'] == 16


@pytest.mark.parametrize('name,args', [
    ('read_file', {'path': '/etc/passwd'}),
    ('get_current_file', {'path': '../secret', 'start_line': 1, 'end_line': 5}),
    ('get_current_file', {'start_line': True, 'end_line': 5}),
    ('search_project', {'query': 'x', 'limit': 9999}),
    ('search_project', {'query': 'x', 'limit': 1, 'command': 'dir'}),
])
async def test_agent_rejects_unknown_tools_and_non_strict_arguments(name, args):
    result, requests = await run_with([reply(calls=[call(name, args)]), reply('final')])
    tool_result = json.loads(requests[1]['messages'][-1]['content'])
    assert tool_result['status'] == 'rejected'
    assert result['tool_trace'][0]['status'] == 'rejected'
    assert result['snippets'] == []


async def test_agent_bounds_turns_and_does_not_count_unsent_snippets():
    responses = [reply(calls=[call('get_current_file', {'start_line': 1, 'end_line': 2}, f'c{i}')])
                 for i in range(3)]
    result, requests = await run_with(responses)
    assert len(requests) == 3
    assert result['failure_kind'] == 'model-turn-limit'
    assert result['model_turns'] == 3
    assert len(result['tool_trace']) == 2


async def test_agent_bounds_tool_calls_before_executing_an_oversized_batch():
    calls = [call('get_diagnostics', {}, f'c{i}') for i in range(7)]
    result, requests = await run_with([reply(calls=calls)])
    assert result['failure_kind'] == 'tool-call-limit'
    assert len(requests) == 1
    assert result['tool_trace'] == []


async def test_plain_json_is_never_dispatched_as_a_tool():
    result, requests = await run_with([reply('{"tool":"get_current_file","arguments":{}}')])
    assert len(requests) == 1
    assert result['tool_trace'] == []


async def test_execution_result_requires_matching_snapshot_hash():
    snap = snapshot()
    snap['execution_result'] = {'buffer_hash': 'stale', 'stdout': 'never send stale output'}
    result, requests = await run_with([
        reply(calls=[call('get_execution_result', {})]), reply('done'),
    ], snap)
    assert 'never send stale output' not in json.dumps(requests)
    assert json.loads(requests[1]['messages'][-1]['content'])['status'] == 'stale'
    assert result['tool_trace'][0]['status'] == 'stale'


async def test_secret_snapshot_is_blocked_before_any_request():
    snap = snapshot()
    snap['files']['helper.py'] = 'password = "sensitive-value"'
    result, requests = await run_with([reply('done')], snap)
    assert result['failure_kind'] == 'sensitive-content'
    assert requests == []


async def test_snapshot_cannot_escape_virtual_paths():
    snap = snapshot()
    snap['files']['../secret.py'] = 'hidden = 1'
    result, requests = await run_with([reply('done')], snap)
    assert result['failure_kind'] == 'invalid-snapshot'
    assert requests == []


async def test_tool_outputs_are_bounded_and_input_snapshot_is_unchanged():
    snap = snapshot()
    snap['learning_history'] = [{'path': 'main.py', 'message': 'x' * 5000}] * 100
    before = copy.deepcopy(snap)
    result, requests = await run_with([
        reply(calls=[call('get_learning_history', {'limit': 10})]), reply('done'),
    ], snap)
    assert len(requests[1]['messages'][-1]['content']) <= 8000
    assert snap == before


async def test_all_six_tools_return_real_snapshot_data_with_linked_protocol_ids():
    snap = snapshot()
    snap['execution_result'] = {'buffer_hash': snap['buffer_hash'], 'stdout': '-1', 'status': 'completed'}
    names_args = [
        ('get_current_file', {'start_line': 1, 'end_line': 2}),
        ('search_project', {'query': 'return'}),
        ('get_diagnostics', {}), ('get_references', {'symbol': 'add'}),
        ('get_learning_history', {}), ('get_execution_result', {}),
    ]
    result, requests = await run_with([
        reply(calls=[call(n, a, f'call_{i}') for i, (n, a) in enumerate(names_args)]), reply('done'),
    ], snap)
    outputs = [json.loads(m['content']) for m in requests[1]['messages'] if m['role'] == 'tool']
    assert len(result['tool_trace']) == 6
    assert outputs[0]['snippets'][1]['quote'] == 'print(add(1, 2))'
    assert outputs[1]['snippets'][0]['path'] == 'helper.py'
    assert outputs[2]['items'][0]['message'] == 'example'
    assert len(outputs[3]['snippets']) == 3
    assert outputs[3]['match_kind'] == 'lexical-occurrence'
    assert outputs[4]['items'][0]['kind'] == 'hint-viewed'
    assert outputs[5]['result']['stdout'] == '-1'
    assert [m['tool_call_id'] for m in requests[1]['messages'] if m['role'] == 'tool'] == [
        'call_0', 'call_1', 'call_2', 'call_3', 'call_4', 'call_5',
    ]


async def test_provider_tool_rejection_has_explicit_failure_and_one_request():
    from app.services.project_agent import run_agent
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(400, json={'error': {'message': 'tools is unsupported'}})

    model = client(handler)
    try:
        result = await run_agent(model, snapshot(), {'snippets': []}, 'review')
    finally:
        await model.aclose()
    assert result['failure_kind'] == 'tools-unsupported'
    assert len(seen) == 1


async def test_duplicate_call_ids_rejected_without_any_dispatch():
    result, requests = await run_with([reply(calls=[
        call('get_diagnostics', {}), call('get_learning_history', {}),
    ])])
    assert result['failure_kind'] == 'invalid-tool-protocol'
    assert result['tool_trace'] == []
    assert len(requests) == 1


async def test_event_sequence_is_real_and_source_cannot_mutate_mid_run():
    from app.services.project_agent import run_agent
    snap, events, requests = snapshot(), [], []

    async def event(name, data):
        events.append(name)
        snap['files']['main.py'] = 'hostile mutation'

    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=reply(calls=[call('get_current_file', {})])
                              if len(requests) == 1 else reply('done'))

    model = client(handler)
    try:
        result = await run_agent(model, snap, {'snippets': []}, 'review', on_event=event)
    finally:
        await model.aclose()
    assert events == ['model-turn', 'tool-start', 'tool-result', 'model-turn']
    assert result['snippets'][0]['quote'] == 'from helper import add'
    assert 'hostile mutation' not in json.dumps(requests)


async def test_initial_evidence_must_match_authorized_source():
    result, requests = await run_with([reply('done')], data={'snippets': [
        {'path': 'main.py', 'line': 2, 'quote': 'made up evidence'},
    ]})
    assert result['failure_kind'] == 'invalid-initial-evidence'
    assert requests == []


async def test_invalid_json_tool_arguments_are_rejected_without_dispatch():
    native_call = call('get_diagnostics', {})
    native_call['function']['arguments'] = '{bad json}'
    result, requests = await run_with([reply(calls=[native_call]), reply('done')])
    assert result['tool_trace'][0]['status'] == 'rejected'
    assert json.loads(requests[1]['messages'][-1]['content'])['reason'] == 'invalid-arguments'


async def test_reasoning_only_tool_response_is_not_final_answer():
    payload = reply()
    payload['choices'][0]['message']['reasoning_content'] = 'private reasoning'
    result, requests = await run_with([payload])
    assert result['failure_kind'] == 'invalid-tool-protocol'
    assert result['content'] == ''


async def test_duplicate_json_argument_keys_are_rejected():
    native_call = call('search_project', {})
    native_call['function']['arguments'] = '{"query":"return","query":"add"}'
    result, requests = await run_with([reply(calls=[native_call]), reply('done')])
    assert result['tool_trace'][0]['status'] == 'rejected'


async def test_last_turn_requires_final_answer_without_more_tool_requests():
    result, requests = await run_with([
        reply(calls=[call('get_diagnostics',{},'a')]),
        reply(calls=[call('get_execution_result',{},'b')]),reply('done')])
    assert result['status']=='completed'
    assert requests[-1]['tool_choice']=='none'


