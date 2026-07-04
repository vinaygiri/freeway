#!/usr/bin/env node
/**
 * @file patch-openclaw-models.js
 * @description Helper function to patch OpenClaw's models.json with all NVIDIA models
 *
 * This is imported by bin/free-coding-models.js and called automatically
 * when setting a model in OpenClaw mode.
 */

import { readFileSync, writeFileSync, existsSync, copyFileSync } from 'fs'
import { homedir } from 'os'
import { join } from 'path'
import { nvidiaNim } from './sources.js'

const MODELS_JSON = join(homedir(), '.openclaw', 'agents', 'main', 'agent', 'models.json')

/**
 * Patch models.json to add all NVIDIA models from sources.js
 * @returns {Object} { added: number, total: number, wasPatched: boolean }
 */
export function patchOpenClawModelsJson() {
  // Read existing config
  let modelsConfig
  if (!existsSync(MODELS_JSON)) {
    return { added: 0, total: 0, wasPatched: false, error: 'models.json not found' }
  }

  try {
    modelsConfig = JSON.parse(readFileSync(MODELS_JSON, 'utf8'))
  } catch (err) {
    return { added: 0, total: 0, wasPatched: false, error: err.message }
  }

  // Ensure nvidia provider exists
  if (!modelsConfig.providers) modelsConfig.providers = {}
  if (!modelsConfig.providers.nvidia) {
    modelsConfig.providers.nvidia = {
      baseUrl: 'https://integrate.api.nvidia.com/v1',
      api: 'openai-completions',
      models: []
    }
  }

  // Get existing model IDs
  const existingModelIds = new Set(modelsConfig.providers.nvidia.models.map(m => m.id))

  // Helper to get model config by tier
  function getModelConfig(tier) {
    if (tier === 'S+' || tier === 'S') {
      return { contextWindow: 128000, maxTokens: 8192 }
    }
    if (tier === 'A+') {
      return { contextWindow: 131072, maxTokens: 4096 }
    }
    if (tier === 'A' || tier === 'A-') {
      return { contextWindow: 131072, maxTokens: 4096 }
    }
    return { contextWindow: 32768, maxTokens: 2048 }
  }

  // Add all models from sources.js
  let addedCount = 0
  for (const [modelId, label, tier] of nvidiaNim) {
    if (existingModelIds.has(modelId)) {
      continue // Skip already existing models
    }

    const config = getModelConfig(tier)
    const isThinking = modelId.includes('thinking')

    modelsConfig.providers.nvidia.models.push({
      id: modelId,
      name: label,
      contextWindow: config.contextWindow,
      maxTokens: config.maxTokens,
      reasoning: isThinking,
      input: ['text'],
      cost: {
        input: 0,
        output: 0,
        cacheRead: 0,
        cacheWrite: 0
      }
    })

    addedCount++
  }

  // Only write if we added something
  if (addedCount > 0) {
    // Backup
    const backupPath = `${MODELS_JSON}.backup-${Date.now()}`
    copyFileSync(MODELS_JSON, backupPath)

    // Write updated config
    writeFileSync(MODELS_JSON, JSON.stringify(modelsConfig, null, 2))

    return {
      added: addedCount,
      total: modelsConfig.providers.nvidia.models.length,
      wasPatched: true,
      backup: backupPath
    }
  }

  return {
    added: 0,
    total: modelsConfig.providers.nvidia.models.length,
    wasPatched: false
  }
}
