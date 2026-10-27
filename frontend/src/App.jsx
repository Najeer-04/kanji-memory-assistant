
import { useState } from 'react'
import './App.css'

const API_BASE_URL = 'http://127.0.0.1:8000'
const VOCABULARY_STEPS = [2, 5, 10, 15]

function App() {
  const [character, setCharacter] = useState('')
  const [kanji, setKanji] = useState(null)
  const [vocabulary, setVocabulary] = useState([])
  const [visibleLimit, setVisibleLimit] = useState(2)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function searchKanji(event) {
    event.preventDefault()

    const search = character.trim()

    if (!search) {
      setError('Please enter a kanji.')
      setKanji(null)
      setVocabulary([])
      return
    }

    setLoading(true)
    setError('')
    setKanji(null)
    setVocabulary([])
    setVisibleLimit(2)

    try {
      const encodedCharacter = encodeURIComponent(search)

      // Fetch the kanji details.
      const kanjiResponse = await fetch(
        `${API_BASE_URL}/kanji/${encodedCharacter}`
      )

      if (!kanjiResponse.ok) {
        if (kanjiResponse.status === 404) {
          throw new Error('Kanji not found.')
        }

        throw new Error('Could not load kanji details.')
      }

      const kanjiData = await kanjiResponse.json()
      setKanji(kanjiData)

      // Fetch up to 15 vocabulary entries for the Show More feature.
      const vocabularyResponse = await fetch(
        `${API_BASE_URL}/kanji/${encodedCharacter}/vocabulary?limit=15`
      )

      if (!vocabularyResponse.ok) {
        throw new Error('Could not load related vocabulary.')
      }

      const vocabularyData = await vocabularyResponse.json()
      setVocabulary(vocabularyData)
    } catch (err) {
      setKanji(null)
      setVocabulary([])

      setError(
        err instanceof TypeError
          ? 'Could not connect to the backend. Make sure the API is running.'
          : err.message
      )
    } finally {
      setLoading(false)
    }
  }

  function showMoreVocabulary() {
    const nextStep = VOCABULARY_STEPS.find(
      (step) => step > visibleLimit
    )

    if (nextStep) {
      setVisibleLimit(nextStep)
    }
  }

  const nextLimit = VOCABULARY_STEPS.find(
    (step) => step > visibleLimit
  )

  return (
    <main>
      <header>
        <h1>Kanji Memory Assistant</h1>
        <p>Learn kanji. Remember them better.</p>
      </header>

      <form onSubmit={searchKanji}>
        <input
          type="text"
          placeholder="Enter a kanji, e.g. 学"
          aria-label="Kanji to search"
          value={character}
          onChange={(event) => setCharacter(event.target.value)}
        />

        <button type="submit" disabled={loading}>
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {loading && (
        <p role="status">Looking up kanji and vocabulary...</p>
      )}

      {error && <p role="alert">{error}</p>}

      {kanji && (
        <section aria-labelledby="kanji-heading">
          <h2 id="kanji-heading">{kanji.character}</h2>

          <p>
            <strong>Stroke count:</strong>{' '}
            {kanji.stroke_count ?? 'Unknown'}
          </p>

          <p>
            <strong>On'yomi:</strong>{' '}
            {kanji.on_readings.join(', ') || 'None listed'}
          </p>

          <p>
            <strong>Kun'yomi:</strong>{' '}
            {kanji.kun_readings.join(', ') || 'None listed'}
          </p>

          <p>
            <strong>Meanings:</strong>{' '}
            {kanji.meanings.join(', ') || 'None listed'}
          </p>

          <section aria-labelledby="vocabulary-heading">
            <h3 id="vocabulary-heading">Related vocabulary</h3>

            {vocabulary.length === 0 ? (
              <p>No related vocabulary found.</p>
            ) : (
              <>
                {vocabulary.slice(0, visibleLimit).map((word) => (
                  <article key={word.entry_id}>
                    <h4>{word.written_forms.join(' / ')}</h4>

                    <p>
                      <strong>Reading:</strong>{' '}
                      {word.readings.join(', ') || 'None listed'}
                    </p>

                    <p>
                      <strong>Meaning:</strong>{' '}
                      {word.meanings.slice(0, 3).join('; ') ||
                        'No English meaning listed'}
                    </p>
                  </article>
                ))}

                {nextLimit && vocabulary.length > visibleLimit && (
                  <button
                    type="button"
                    onClick={showMoreVocabulary}
                  >
                    Show more ({nextLimit})
                  </button>
                )}

                {visibleLimit > 2 && (
                  <button
                    type="button"
                    onClick={() => setVisibleLimit(2)}
                  >
                    Show less
                  </button>
                )}
              </>
            )}
          </section>
        </section>
      )}
    </main>
  )
}

export default App
