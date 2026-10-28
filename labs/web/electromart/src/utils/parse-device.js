'use strict'

const fs = require('fs')
const path = require('path')

/**
 * Map from source .txt filename to product slug.
 */
const SLUG_MAP = {
  'Samsung-Galaxy-S25-Ultra-5G.txt': 'samsung-galaxy-s25-ultra',
  'iPhone-17-Pro-Max2.txt': 'iphone-17-pro-max',
  'Google-Pixel-10-Pro.txt': 'google-pixel-10-pro',
  '‎65-Neo-QLED-QN70H-4K-Samsung-Vision-AI-Smart-TV-(2026).txt': 'samsung-65-qn70h-neo-qled',
  '55-inch-LG-OLED-evo-AI-C5-4K-144Hz-Smart-TV-AI-Magic-remote-webOS25-2025.txt': 'lg-55-oled-evo-c5',
  'Samsung-65-Inch-Smart-TV-4K-UHD-LED-Built-In-Receiver.txt': 'samsung-65-u8000h-smart-tv',
  'samsung-Front-load-Washer-Bubble-Soak-8kg.txt': 'samsung-8kg-front-load-washer',
  '13KG-Top-Load-Washing-Machine-Smart-Inverter.txt': 'lg-13kg-top-load-washer',
  'Toshiba-T21-Inverter-Front-Load-Washing-Machine-8.5kg.txt': 'toshiba-8-5kg-front-load-washer',
  'Bosch-Gas-Cooker-5-Burners-Stainless-Steel.txt': 'bosch-gas-cooker-5-burners',
  'Fresh-Master-Gas-Cooker-4-Burners-Silver.txt': 'fresh-master-gas-cooker-4',
  'Unionaire-Max-Air-11-Gas-Cooker-5-Burners-Black.txt': 'unionaire-gas-cooker-5',
  'Mienta-BL1361B-Countertop-Blender-with-Attachments-400-Watt-Black.txt': 'mienta-bl1361b-blender',
  'Kenwood-Countertop-Blender-500-Watt-Black.txt': 'kenwood-blp18-150bk-blender',
  'Ultra-Countertop-Blender-600-Watt-White.txt': 'ultra-600w-countertop-blender',
  'Midea-Split-Air-Conditioner-1.5-HP-Cooling-Only.txt': 'midea-1-5hp-split-ac',
  'Fresh-Split-Air-Conditioner-3-HP-Cooling-Only.txt': 'fresh-3hp-split-ac',
  'Sharp-Inverter-Split-Air-Conditioner-1.5-HP-Cooling-Only.txt': 'sharp-1-5hp-inverter-split-ac',
  'Tank-Pro-Filter-6-Purification-Compact-Functions-(Digital Timer).txt': 'tank-pro-filter-6',
  'iFilter-Cold.txt': 'ifilter-cold',
}

/**
 * Find the matching .jpg image filename for a given .txt source file.
 */
function findImageFile(txtFile, devicesDir) {
  const files = fs.readdirSync(devicesDir).filter(f => f.endsWith('.jpg'))
  const baseName = txtFile.replace(/\.txt$/, '')

  // Direct match: same name with .jpg
  const directMatch = files.find(f => f === baseName + '.jpg')
  if (directMatch) return directMatch

  // Try without BOM/special invisible chars
  const cleanedBase = baseName.replace(/[\u200e\u200f]/g, '')
  const cleanedMatch = files.find(f => f.replace(/[\u200e\u200f]/g, '') === cleanedBase + '.jpg')
  if (cleanedMatch) return cleanedMatch

  return null
}

/**
 * Parse a single .txt product file and return structured data.
 */
function parseDeviceFile(filePath, slug) {
  const raw = fs.readFileSync(filePath, 'utf8').replace(/\r\n/g, '\n')
  const lines = raw.split('\n')

  // ---------- Extract product info (key-value before DESCRIPTION) ----------
  const infoLines = []
  const descIdx = raw.indexOf('\nDESCRIPTION\n')
  if (descIdx !== -1) {
    infoLines.push(...raw.slice(0, descIdx).split('\n'))
  } else {
    infoLines.push(...raw.split('\n'))
  }

  const info = {}
  let currentKey = null
  for (const rawLine of infoLines) {
    const line = rawLine.trim()
    if (!line || line.startsWith('===') || line === 'PRODUCT INFORMATION') {
      // separator or section header
      currentKey = null
      continue
    }
    if (line.endsWith(':')) {
      currentKey = line.slice(0, -1).trim().toLowerCase()
      info[currentKey] = ''
      continue
    }
    if (currentKey) {
      info[currentKey] = info[currentKey] ? info[currentKey] + ' ' + line : line
    }
  }

  const name = (info['product name'] || '').trim()
  const brand = (info['brand'] || '').trim()
  const model = (info['model'] || '').trim()
  const categoryRaw = (info['category'] || '').trim()
  const priceMatch = (info['price'] || '').match(/([\d,]+)/)
  const price = priceMatch ? parseInt(priceMatch[1].replace(/,/g, ''), 10) : 0
  const stock = parseInt((info['stock availability'] || '0'), 10) || 0
  const ratingMatch = (info['rating'] || '').match(/([\d.]+)\/5/)
  const rating = ratingMatch ? parseFloat(ratingMatch[1]) : 0

  // ---------- Extract description ----------
  const descStart = raw.indexOf('DESCRIPTION')
  const specsStart = raw.indexOf('Main Specifications:')
  const reviewsStart = raw.indexOf('REVIEWS / COMMENTS')
  let description = ''

  if (descStart !== -1) {
    let endIdx = specsStart !== -1 ? specsStart : (reviewsStart !== -1 ? reviewsStart : raw.length)
    const descSection = raw.slice(descStart, endIdx)
    // Remove section header lines and separator lines
    const descLines = descSection.split('\n')
    const cleaned = descLines.filter(l => {
      const t = l.trim()
      return t !== 'DESCRIPTION' && !t.startsWith('===')
    }).join('\n')
    description = cleaned.replace(/\n{3,}/g, '\n\n').trim()
  }

  // ---------- Extract specs ----------
  const specs = []
  if (specsStart !== -1) {
    let specsEnd = reviewsStart !== -1 ? reviewsStart : raw.length
    const specsSection = raw.slice(specsStart, specsEnd)
    const specLines = specsSection.split('\n')
    for (const line of specLines) {
      const trimmed = line.trim()
      if (trimmed.startsWith('- ') && trimmed.length > 3) {
        const specText = trimmed.slice(2) // remove "- "
        const colonIdx = specText.indexOf(':')
        if (colonIdx > 0 && colonIdx < specText.length - 1) {
          specs.push({
            label: specText.slice(0, colonIdx).trim(),
            value: specText.slice(colonIdx + 1).trim(),
          })
        } else {
          specs.push({ label: 'Feature', value: specText.trim() })
        }
      }
    }
  }

  // ---------- Extract reviews ----------
  const reviews = []
  if (reviewsStart !== -1) {
    const reviewsSection = raw.slice(reviewsStart)
    // Split by the numbered review markers: "\n1.\nName:" pattern
    const reviewPattern = /\n(\d+)\.\nName:\s*([^\n]+)\nRating:\s*(\d+)\/5\nComment:\n([\s\S]*?)(?=\n\d+\.\nName:|\n\s*={5,}|$)/g
    let m
    while ((m = reviewPattern.exec(reviewsSection)) !== null) {
      const commentLines = m[4].split('\n')
      // Stop at any separator line
      let endIndex = commentLines.length
      for (let i = 0; i < commentLines.length; i++) {
        if (commentLines[i].trim().startsWith('===')) { endIndex = i; break }
      }
      const comment = commentLines.slice(0, endIndex)
        .filter(l => l.trim() !== 'END OF REVIEWS / COMMENTS')
        .join(' ')
        .replace(/\s+/g, ' ')
        .trim()

      if (comment) {
        reviews.push({
          name: m[2].trim(),
          rating: parseInt(m[3], 10),
          comment,
        })
      }
    }
  }

  // ---------- Category normalization ----------
  const categoryMap = {
    'phone': 'phone',
    'tv': 'TV',
    'water filter': 'water filter',
    'washing machine': 'washing machine',
    'stove': 'stove',
    'blender': 'blender',
    'air conditioner': 'AC',
  }
  const category = categoryMap[categoryRaw.toLowerCase()] || categoryRaw.toLowerCase()
  const categoryLabelMap = {
    phone: 'Phone',
    TV: 'TV',
    'water filter': 'Water Filter',
    'washing machine': 'Washing Machine',
    stove: 'Stove',
    blender: 'Blender',
    AC: 'Air Conditioner',
  }
  const categoryLabel = categoryLabelMap[category] || categoryRaw

  return { slug, name, brand, model, category, categoryLabel, price, stock, rating, description, specs, reviews }
}

/**
 * List all .txt files in the devices directory that have a known slug.
 */
function listDeviceFiles(devicesDir) {
  if (!fs.existsSync(devicesDir)) return []
  const files = fs.readdirSync(devicesDir).filter(f => f.endsWith('.txt'))
  return files
    .filter(f => SLUG_MAP[f])
    .map(f => ({ file: f, slug: SLUG_MAP[f], path: path.join(devicesDir, f) }))
}

module.exports = { parseDeviceFile, listDeviceFiles, findImageFile, SLUG_MAP }
