'use strict'

const path = require('path')
const fs = require('fs')
const crypto = require('crypto')

const { mongoose } = require('./db')
const Product = require('./models/product')
const Review = require('./models/review')
const { parseDeviceFile, listDeviceFiles, findImageFile } = require('./utils/parse-device')
const { connectWithRetry } = require('./db')
const { seedVictim } = require('./seed-victim')

/**
 * Assign varied dates to source reviews (Jan 2021 – Sep 2026) for idempotency.
 * Each review gets a deterministic but distinct date based on a hash of its content.
 */
/**
 * Deterministically assign a varied date between Jan 2021 and Sep 2026.
 * Uses first two hash bytes (0–65535) as a day offset into an ~5.7 year range
 * so dates spread across the whole period.
 */
function assignReviewDate(review, productSlug, index) {
  const seedStr = productSlug + '|' + review.name + '|' + review.comment + '|' + index
  const hash = crypto.createHash('md5').update(seedStr).digest()
  const base = Date.UTC(2021, 0, 1)   // Jan 1 2021
  const end  = Date.UTC(2026, 8, 30) // Sep 30 2026
  const totalDays = Math.floor((end - base) / 86400000) // ≈ 2068 days
  const dayOffset = (hash[0] * 256 + hash[1]) % totalDays
  return new Date(base + dayOffset * 86400000)
}

async function seed() {
  const devicesDir = path.join(__dirname, '..', 'devices')
  if (!fs.existsSync(devicesDir)) {
    console.warn('[seed] devices/ directory not found — skipping seed')
    return
  }

  const files = listDeviceFiles(devicesDir)
  console.log(`[seed] Found ${files.length} product files`)

  let created = 0
  let skipped = 0
  let reviewsCreated = 0

  for (const { file, slug, path: filePath } of files) {
    // Idempotency: skip if this product already exists
    const existing = await Product.findOne({ slug }).exec()
    if (existing) {
      console.log(`[seed] SKIP  ${slug} (already exists)`)
      skipped++
      continue
    }

    const data = parseDeviceFile(filePath, slug)

    // Find the matching image file
    const image = findImageFile(file, devicesDir)
    if (!image) {
      console.warn(`[seed] WARN  No image found for ${file}`)
    }

    // Create the product
    const product = await Product.create({
      slug: data.slug,
      name: data.name,
      brand: data.brand,
      model: data.model,
      category: data.category,
      categoryLabel: data.categoryLabel,
      price: data.price,
      stock: data.stock,
      rating: data.rating,
      description: data.description,
      specs: data.specs,
      image: image || '',
      sourceFile: file,
    })
    console.log(`[seed] CREATE ${slug} — ${data.name} (${data.price} EGP, ${data.stock} in stock, ${data.specs.length} specs, ${data.reviews.length} reviews)`)
    created++

    // Create source reviews
    // First check if any reviews already exist for this product
    const existingReviews = await Review.countDocuments({ productSlug: slug })
    if (existingReviews > 0) {
      console.log(`[seed]   SKIP reviews (already ${existingReviews} exist)`)
    } else {
      for (let i = 0; i < data.reviews.length; i++) {
        const review = data.reviews[i]
        await Review.create({
          productSlug: slug,
          author: review.name,
          rating: review.rating,
          comment: review.comment,
          isAuthor: false,
          createdAt: assignReviewDate(review, slug, i),
        })
        reviewsCreated++
      }
      // Update product rating from actual reviews
      const stats = await Review.aggregate([
        { $match: { productSlug: slug } },
        { $group: { _id: null, avg: { $avg: '$rating' } } },
      ])
      if (stats.length > 0) {
        product.rating = Math.round(stats[0].avg * 10) / 10
        await product.save()
      }
    }
  }

  const total = await Product.countDocuments()
  console.log(`[seed] Done. Created: ${created}, Skipped: ${skipped}, Total products: ${total}, Reviews added: ${reviewsCreated}`)

  // Phase 1.3 — the lab victim account (idempotent; safe on every boot).
  const victim = await seedVictim()
  if (victim.created) {
    console.log(`[seed] CREATE victim account "${victim.username}" (lab target; flag in Delivery address).`)
  } else if (victim.exists) {
    console.log(`[seed] SKIP  victim account "${victim.username}" (already exists).`)
  } else {
    console.warn('[seed] WARN  victim account was not created (email/username already in use).')
  }
}

// Run standalone (node src/seed.js) or import as a function
if (require.main === module) {
  connectWithRetry()
    .then(() => seed())
    .then(() => {
      mongoose.disconnect().then(() => process.exit(0)).catch(() => process.exit(0))
    })
    .catch((err) => {
      console.error('[seed] failed:', err)
      process.exit(1)
    })
}

module.exports = { seed }
