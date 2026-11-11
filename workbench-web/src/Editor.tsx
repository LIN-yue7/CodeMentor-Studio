
import { useEffect, useRef } from 'react'
import { basicSetup } from 'codemirror'
import { python } from '@codemirror/lang-python'
import { StateEffect, StateField } from '@codemirror/state'
import { Decoration, EditorView } from '@codemirror/view'
import { HighlightStyle, syntaxHighlighting } from '@codemirror/language'
import { tags } from '@lezer/highlight'

const laboratoryTheme = EditorView.theme({
  '&': { color: '#d8e3dc', backgroundColor: '#121619' },
  '.cm-content': { caretColor: '#9bdfbd' },
  '.cm-cursor, .cm-dropCursor': { borderLeftColor: '#9bdfbd' },
  '&.cm-focused .cm-selectionBackground, .cm-selectionBackground, ::selection': { backgroundColor: '#355044' },
  '.cm-gutters': { backgroundColor: '#121619', color: '#7a8b81', border: 'none' },
  '.cm-activeLineGutter': { backgroundColor: '#202a25', color: '#b6c9bd' },
  '.cm-activeLine': { backgroundColor: '#ffffff04' },
  '.cm-foldPlaceholder': { backgroundColor: '#27352d', color: '#b8cbbf', border: 'none' },
  '.cm-panels, .cm-tooltip': { backgroundColor: '#20262a', color: '#e3e9e6', borderColor: '#45534b' },
  '.cm-searchMatch': { backgroundColor: '#665332' },
  '.cm-searchMatch.cm-searchMatch-selected': { backgroundColor: '#8c713e' },
}, { dark: true })
const laboratorySyntax = HighlightStyle.define([
  { tag: tags.keyword, color: '#c6b2e5' },
  { tag: [tags.function(tags.variableName), tags.definition(tags.variableName)], color: '#b4dfc7' },
  { tag: tags.number, color: '#e5bb7b' },
  { tag: tags.string, color: '#aecb98' },
  { tag: [tags.comment, tags.meta], color: '#899b91' },
  { tag: tags.operator, color: '#a4c5d8' },
  { tag: tags.special(tags.variableName), color: '#8ecbd3' },
])

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

export default function Editor({ code, onChange, line, jump, pythonMode = true, onCursor }: {
  code: string; onChange: (code: string) => void; line: number | null; jump: number; pythonMode?: boolean; onCursor?: (line:number)=>void
}) {
  const target = useRef<HTMLDivElement>(null)
  const editor = useRef<EditorView | null>(null)
  const onChangeRef = useRef(onChange)
  const cursorRef=useRef(onCursor)
  useEffect(()=>{cursorRef.current=onCursor},[onCursor])
  const initialCode = useRef(code)
  const lastJump = useRef(jump)
  useEffect(() => { onChangeRef.current = onChange }, [onChange])

  useEffect(() => {
    if (!target.current) return
    const view = new EditorView({
      doc: initialCode.current,
      extensions: [
        basicSetup, ...(pythonMode ? [python()] : []), laboratoryTheme, syntaxHighlighting(laboratorySyntax), evidenceLine, EditorView.lineWrapping,
        EditorView.contentAttributes.of({ 'aria-label': pythonMode ? 'Python 代码' : '文本代码' }),
        EditorView.updateListener.of(update => {
          if (update.docChanged) onChangeRef.current(update.state.doc.toString())
          if(update.selectionSet||update.docChanged) cursorRef.current?.(update.state.doc.lineAt(update.state.selection.main.head).number)
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
