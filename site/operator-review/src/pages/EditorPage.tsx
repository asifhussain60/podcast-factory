// Stub — M4/M5 fill this in.
import { IconSprite } from '../components/Icons'
import { useParams } from 'react-router-dom'

export function EditorPage() {
  const { slug } = useParams()
  return (
    <>
      <IconSprite />
      <div className="h-full flex items-center justify-center text-ink-100">
        <p className="font-display text-2xl">Editor — {slug} — scaffold (M5 fills this)</p>
      </div>
    </>
  )
}
