export default function NewsPage() {
  return (
    <div className="max-w-screen-xl mx-auto px-6 py-16 text-center">
      <div className="inline-flex items-center gap-2 border border-white/10 bg-white/5 rounded-full px-4 py-1.5 text-xs text-gray-400 font-mono mb-8">
        COMING IN PHASE 3
      </div>
      <h1 className="text-4xl font-bold text-white mb-4">Economic News Intelligence</h1>
      <p className="text-gray-400 text-lg max-w-xl mx-auto">
        GDELT-powered news pipeline with vector embeddings and semantic search.
        Find economic news by country and topic to contextualize model projections.
      </p>
    </div>
  )
}
