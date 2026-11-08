
import { useEffect, useRef } from 'react'
import { basicSetup } from 'codemirror'
import { python } from '@codemirror/lang-python'
import { StateEffect, StateField } from '@codemirror/state'
import { Decoration, EditorView } from '@codemirror/view'

const mark = StateEffect.define<number | null>()
const evidenceLine = StateField.define({
  create: () => Decoration.none,
  update(decorations, transaction) {
    let next = decorations.map(transaction.changes)
    for (const effect of transaction.effects) {
      if (effect.is(mark)) {
        next = effect.value && effect.value <= transaction.state.doc.lines
          ? Decoration.set([Decoration.line({ class: 'cm-evidence-line' }).range(transaction.state.doc.line(effect.value).from)])
          : Decoration.none
      }
    }
    return next
  },
  provide: field => EditorView.decorations.from(field),
})

export default function Editor({ code, onChange, line, jump }: {
  code: string; onChange: (code: string) => void; line: number | null; jump: number
}) {
  const target = useRef<HTMLDivElement>(null)
  const editor = useRef<EditorView | null>(null)
  const onChangeRef = useRef(onChange)
  const initialCode = useRef(code)
  const lastJump = useRef(jump)
  useEffect(() => { onChangeRef.current = onChange }, [onChange])

  useEffect(() => {
    if (!target.current) return
    const view = new EditorView({
      doc: initialCode.current,
      extensions: [
        basicSetup, python(), evidenceLine, EditorView.lineWrapping,
        EditorView.contentAttributes.of({ 'aria-label': 'Python 代码' }),
        EditorView.updateListener.of(update => {
          if (update.docChanged) onChangeRef.current(update.state.doc.toString())
        }),
      ],
      parent: target.current,
    })
    editor.current = view
    return () => { view.destroy(); editor.current = null }
  }, [])

  useEffect(() => {
    const view = editor.current
    if (view && view.state.doc.toString() !== code) {
      view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: code } })
    }
  }, [code])

  useEffect(() => {
    const view = editor.current
    if (!view) return
    const shouldJump = jump !== lastJump.current && line && line <= view.state.doc.lines
    lastJump.current = jump
    if (shouldJump && line) {
      view.dispatch({ effects: mark.of(line), selection: { anchor: view.state.doc.line(line).from }, scrollIntoView: true })
      view.focus()
    } else {
      view.dispatch({ effects: mark.of(line) })
    }
  }, [line, jump])
  return <div className="editor" ref={target} />
}
