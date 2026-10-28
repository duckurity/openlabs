'use strict'

const mongoose = require('mongoose')

const reviewSchema = new mongoose.Schema(
  {
    productSlug: { type: String, required: true, index: true },
    author: { type: String, required: true },
    rating: { type: Number, required: true, min: 1, max: 5 },
    comment: { type: String, required: true, maxlength: 2000 },
    userName: { type: String, default: '' },
    isAuthor: { type: Boolean, default: false },
  },
  { timestamps: true }
)

reviewSchema.index({ productSlug: 1, createdAt: -1 })

module.exports = mongoose.model('Review', reviewSchema)
