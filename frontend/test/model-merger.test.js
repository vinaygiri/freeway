import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { buildMergedModels } from '../src/model-merger.js'

const SAMPLE_MODELS = [
  ['deepseek-ai/deepseek-v4-flash', 'DeepSeek V4 Flash', 'S+', '72.0%', '128k', 'nvidia'],
  ['deepseek-v4-flash', 'DeepSeek V4 Flash', 'S+', '72.0%', '128k', 'groq'],
  ['deepseek-v4-flash', 'DeepSeek V4 Flash', 'S+', '72.0%', '128k', 'cerebras'],
  ['unique-model-xyz', 'Unique Model', 'A', '55%', '32k', 'fireworks'],
]

describe('buildMergedModels', () => {
  it('merges same-label models into one entry', () => {
    const merged = buildMergedModels(SAMPLE_MODELS)
    const deepseek = merged.find(m => m.label === 'DeepSeek V4 Flash')
    assert.ok(deepseek)
    assert.strictEqual(deepseek.providers.length, 3)
    assert.deepStrictEqual(
      deepseek.providers.map(p => p.providerKey).sort(),
      ['cerebras', 'groq', 'nvidia']
    )
  })

  it('keeps unique models as single-provider entries', () => {
    const merged = buildMergedModels(SAMPLE_MODELS)
    const unique = merged.find(m => m.label === 'Unique Model')
    assert.ok(unique)
    assert.strictEqual(unique.providers.length, 1)
    assert.strictEqual(unique.providers[0].providerKey, 'fireworks')
  })

  it('uses best tier and highest SWE score', () => {
    const models = [
      ['m1', 'TestModel', 'A+', '65%', '64k', 'p1'],
      ['m2', 'TestModel', 'S', '70%', '128k', 'p2'],
    ]
    const merged = buildMergedModels(models)
    const tm = merged.find(m => m.label === 'TestModel')
    assert.strictEqual(tm.tier, 'S')       // best tier
    assert.strictEqual(tm.sweScore, '70%')  // highest score
    assert.strictEqual(tm.ctx, '128k')      // largest context
  })

  it('returns providerCount', () => {
    const merged = buildMergedModels(SAMPLE_MODELS)
    const deepseek = merged.find(m => m.label === 'DeepSeek V4 Flash')
    assert.strictEqual(deepseek.providerCount, 3)
  })

  it('generates unique slug per model', () => {
    const models = [
      ['m1', 'Test Model!', 'A', '50%', '32k', 'p1'],
      ['m2', 'Test Model!', 'A', '50%', '32k', 'p2'],
      ['m3', 'Test-Model', 'B', '40%', '32k', 'p3'],
    ]
    const merged = buildMergedModels(models)
    const slugs = merged.map(m => m.slug)
    // All slugs unique
    assert.strictEqual(new Set(slugs).size, slugs.length, 'Slugs must be unique')
    // Slug format: lowercase, no special chars
    for (const slug of slugs) {
      assert.match(slug, /^[a-z0-9-]+$/, `Slug "${slug}" must be lowercase alphanumeric with dashes`)
    }
  })

  it('each provider entry has modelId and providerKey', () => {
    const merged = buildMergedModels(SAMPLE_MODELS)
    const deepseek = merged.find(m => m.label === 'DeepSeek V4 Flash')
    const nvidia = deepseek.providers.find(p => p.providerKey === 'nvidia')
    assert.strictEqual(nvidia.modelId, 'deepseek-ai/deepseek-v4-flash')
  })
})
