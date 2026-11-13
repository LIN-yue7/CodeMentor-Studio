import {test} from 'node:test'
import assert from 'node:assert/strict'
const state=await import('../src/review-state.ts').catch(()=>({}))
test('full request identity changes for related file, revision, cursor and question',()=>{
 assert.equal(typeof state.requestFingerprint,'function')
 const body={files:{'main.py':'x = 1','helper.py':'return 1'},revision:1,path:'main.py',cursor_line:1,request:'why',language:'auto'}
 for(const change of [{revision:2},{cursor_line:2},{request:'example'},{files:{...body.files,'helper.py':'return 2'}}])assert.notEqual(state.requestFingerprint(body),state.requestFingerprint({...body,...change}))
 assert.equal(state.requestFingerprint(body),state.requestFingerprint({...body,files:{'helper.py':'return 1','main.py':'x = 1'}}))
})
test('patch is atomic and undo rejects later manual changes anywhere in project',()=>{
 assert.equal(typeof state.applyReviewedPatches,'function')
 const before={'main.py':'a = 1\nb = 2','helper.py':'value = 3'}
 const applied=state.applyReviewedPatches(before,[{path:'main.py',line:1,before:'a = 1',after:'a = 4'}])
 assert.deepEqual(applied,{'main.py':'a = 4\nb = 2','helper.py':'value = 3'})
 assert.deepEqual(state.undoReviewedPatch(applied,{before,after:applied}),before)
 assert.throws(()=>state.undoReviewedPatch({...applied,'helper.py':'manual = 4'},{before,after:applied}),/手动/)
 assert.throws(()=>state.applyReviewedPatches(before,[{path:'main.py',line:1,before:'a = 1',after:'a = 4'},{path:'main.py',line:2,before:'wrong',after:'bad'}]),/变化/)
 assert.equal(before['main.py'],'a = 1\nb = 2')
})
