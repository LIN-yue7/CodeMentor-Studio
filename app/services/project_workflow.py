"""Version-bound project review cache. Consent is checked by the API for every hit."""
import asyncio
import hashlib
import json
import time
from copy import deepcopy
from app.services.project_review import review

async def run_workflow(tutor,owner,project_id,payload,data,snapshot,on_event=None):
    key=hashlib.sha256(json.dumps([owner,project_id,data,payload.path,payload.language,payload.mode,payload.use_tools,snapshot.get('execution_result'),snapshot.get('learning_history')],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    if not hasattr(tutor,'project_cache'):
        tutor.project_cache={};tutor.project_locks={}
    now=time.monotonic()
    tutor.project_cache={k:v for k,v in tutor.project_cache.items() if now-v[0]<120}
    cached=tutor.project_cache.get(key)
    if cached:
        if on_event:await on_event('cache-hit',{'buffer_hash':data['buffer_hash']})
        return {**deepcopy(cached[1]),'cache_hit':True}
    lock=tutor.project_locks.setdefault(key,asyncio.Lock())
    try:
        async with lock:
            cached=tutor.project_cache.get(key)
            if cached:return {**deepcopy(cached[1]),'cache_hit':True}
            result=await review(tutor,owner,data,payload.mode,snapshot=snapshot,use_tools=payload.use_tools,on_event=on_event)
            if result['status']=='accepted':
                if len(tutor.project_cache)>=64:tutor.project_cache.pop(next(iter(tutor.project_cache)))
                tutor.project_cache[key]=(time.monotonic(),deepcopy(result))
            return {**result,'cache_hit':False}
    finally:
        # Keep the same lock while waiters are still queued; bounded by active requests.
        if not lock.locked() and not getattr(lock,'_waiters',None):tutor.project_locks.pop(key,None)
