import { useState } from 'react'
import { useBooks } from '../hooks/useBooks'
import { BookCard } from '../components/BookCard'
import { IconSprite, Icon } from '../components/Icons'
import { Pill, Dot } from '../components/ui/Pill'
import { cn } from '../lib/utils'

type Filter = 'all' | 'needs-review' | 'in-flight' | 'done'

export function BooksListPage() {
  const { data, isLoading, error } = useBooks()
  const [filter, setFilter] = useState<Filter>('all')

  const books = data?.books ?? []
  const counts = {
    all: books.length,
    'needs-review': books.filter((b) => b.phase_status === 'halted-for-transcript-review').length,
    'in-flight': books.filter(
      (b) =>
        !['shipped', 'done', 'halted-for-transcript-review', 'unknown'].includes(b.phase_status),
    ).length,
    done: books.filter((b) => b.phase_status === 'shipped' || b.phase_status === 'done').length,
  }

  const filtered = books.filter((b) => {
    if (filter === 'all') return true
    if (filter === 'needs-review') return b.phase_status === 'halted-for-transcript-review'
    if (filter === 'done') return b.phase_status === 'shipped' || b.phase_status === 'done'
    return !['shipped', 'done', 'halted-for-transcript-review', 'unknown'].includes(b.phase_status)
  })

  return (
    <>
      <IconSprite />
      <div className="absolute inset-0 flex flex-col overflow-hidden">
        <header className="px-8 pt-10 pb-6 border-b border-white/[0.06]">
          <div className="max-w-7xl mx-auto flex justify-between items-end gap-8">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="w-11 h-11 rounded-[12px] bg-gradient-to-br from-accent-purple to-accent-cyan flex items-center justify-center text-white font-bold font-display shadow-[0_0_20px_rgba(123,97,255,0.35),0_0_40px_rgba(123,97,255,0.15)] relative">
                  RS
                </div>
                <div>
                  <div className="font-display text-2xl font-bold tracking-tight">
                    <span className="bg-gradient-to-br from-accent-purple to-accent-cyan bg-clip-text text-transparent">
                      Operator
                    </span>{' '}
                    Review Studio
                  </div>
                  <div className="font-mono text-xs text-ink-200">
                    localhost:8766 · feat/operator-review-studio
                  </div>
                </div>
              </div>
              <p className="text-sm text-ink-200">
                {counts.all} books · {counts['needs-review']} awaiting review ·{' '}
                {counts['in-flight']} in flight · {counts.done} shipped
              </p>
            </div>

            <div className="flex gap-2 items-center">
              <FilterChip cur={filter} val="all" set={setFilter}>
                All · {counts.all}
              </FilterChip>
              <FilterChip cur={filter} val="needs-review" set={setFilter} hot>
                Needs review · {counts['needs-review']}
              </FilterChip>
              <FilterChip cur={filter} val="in-flight" set={setFilter}>
                In flight · {counts['in-flight']}
              </FilterChip>
              <FilterChip cur={filter} val="done" set={setFilter}>
                Done · {counts.done}
              </FilterChip>
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-auto scroll-thin">
          <div className="max-w-7xl mx-auto px-8 py-8">
            {data?.worktree_roots.map((root) => (
              <div key={root} className="mb-8 last:mb-0">
                <div className="flex items-center gap-2.5 mb-4">
                  <Icon name="branch" size="sm" className="text-accent-cyan" />
                  <span className="font-mono text-sm text-ink-100">{root}</span>
                  <Pill tone="cyan">
                    <Dot style={{ background: 'var(--accent-cyan)' }} />
                    active worktree
                  </Pill>
                </div>

                {isLoading && <div className="text-ink-200">Loading books...</div>}
                {error && (
                  <div className="text-accent-rose font-mono text-sm">
                    Error: {(error as Error).message}
                    <div className="text-ink-200 mt-2 text-xs">
                      Is the FastAPI backend running?
                      <code className="ml-2 text-accent-cyan">
                        python3 scripts/podcast/review_server.py --repo-root .
                      </code>
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                  {filtered
                    .filter((b) => b.worktree_root === root)
                    .map((book) => (
                      <BookCard key={`${root}__${book.slug}`} book={book} />
                    ))}
                </div>

                {!isLoading && !error && filtered.filter((b) => b.worktree_root === root).length === 0 && (
                  <div className="text-ink-200 text-sm italic">No books match this filter in this worktree.</div>
                )}
              </div>
            ))}

            <div className="mt-10 p-5 rounded-[10px] border border-dashed border-white/10 text-center text-xs text-ink-200">
              <code className="font-mono text-ink-100">~/.journal-worktrees.yaml</code> — add more
              worktree paths to list books across multiple branches in one view.
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

function FilterChip({
  cur,
  val,
  set,
  hot,
  children,
}: {
  cur: Filter
  val: Filter
  set: (v: Filter) => void
  hot?: boolean
  children: React.ReactNode
}) {
  const active = cur === val
  return (
    <button
      onClick={() => set(val)}
      className={cn(
        'px-3.5 py-1.5 rounded-pill border text-xs font-medium font-ui transition',
        active && !hot && 'bg-[rgba(30,41,59,0.35)] text-ink-50 border-white/[0.16]',
        active && hot && 'bg-accent-amber/10 border-accent-amber/40 text-accent-amber font-semibold',
        !active && 'bg-transparent border-white/10 text-ink-200 hover:text-ink-50 hover:border-white/[0.16]',
      )}
    >
      {children}
    </button>
  )
}
