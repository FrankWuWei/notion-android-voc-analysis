import { useEffect, useState } from 'react'
import { chapters } from '../content/portfolioContent'

function useActiveChapter() {
  const [activeChapter, setActiveChapter] = useState<string>(chapters[0].id)

  useEffect(() => {
    const targets = chapters
      .map((chapter) => document.getElementById(chapter.id))
      .filter((target): target is HTMLElement => target !== null)

    if (targets.length === 0 || !('IntersectionObserver' in window)) {
      return undefined
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const visibleEntry = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]

        if (visibleEntry) setActiveChapter(visibleEntry.target.id)
      },
      { rootMargin: '-18% 0px -68% 0px', threshold: [0, 0.2, 0.6] },
    )

    targets.forEach((target) => observer.observe(target))
    return () => observer.disconnect()
  }, [])

  return activeChapter
}

function NavigationList({
  activeChapter,
  onNavigate,
}: {
  activeChapter: string
  onNavigate?: () => void
}) {
  return (
    <ol className="chapter-list">
      {chapters.map((chapter) => {
        const isActive = activeChapter === chapter.id
        return (
          <li key={chapter.id}>
            <a
              className="chapter-link"
              data-active={isActive || undefined}
              href={`#${chapter.id}`}
              aria-current={isActive ? 'location' : undefined}
              onClick={onNavigate}
            >
              <span className="chapter-link__number">{chapter.number}</span>
              <span>{chapter.label}</span>
            </a>
          </li>
        )
      })}
    </ol>
  )
}

export function ChapterNavigation() {
  const activeChapter = useActiveChapter()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const currentChapter =
    chapters.find((chapter) => chapter.id === activeChapter) ?? chapters[0]

  useEffect(() => {
    if (!mobileMenuOpen) return undefined

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMobileMenuOpen(false)
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [mobileMenuOpen])

  return (
    <>
      <aside className="desktop-navigation" aria-label="案例研究章節">
        <a className="navigation-mark" href="#overview" aria-label="回到專案概覽">
          <span aria-hidden="true">VOC</span>
          <span aria-hidden="true">/</span>
          <span aria-hidden="true">01</span>
        </a>
        <NavigationList activeChapter={activeChapter} />
        <p className="navigation-note">Android reviews<br />2025—2026</p>
      </aside>

      <div className="mobile-navigation">
        <a className="mobile-navigation__current" href={`#${currentChapter.id}`}>
          <span>{currentChapter.number}</span>
          <span aria-hidden="true">/</span>
          <strong>{currentChapter.label}</strong>
        </a>
        <button
          className="mobile-navigation__toggle"
          type="button"
          aria-expanded={mobileMenuOpen}
          aria-controls="mobile-chapter-menu"
          onClick={() => setMobileMenuOpen((open) => !open)}
        >
          章節
          <span aria-hidden="true">{mobileMenuOpen ? '↑' : '↓'}</span>
        </button>
        <nav
          id="mobile-chapter-menu"
          className="mobile-navigation__menu"
          data-open={mobileMenuOpen || undefined}
          aria-label="案例研究章節"
        >
          <NavigationList
            activeChapter={activeChapter}
            onNavigate={() => setMobileMenuOpen(false)}
          />
        </nav>
      </div>
    </>
  )
}
