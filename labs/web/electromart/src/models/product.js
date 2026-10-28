'use strict'

const mongoose = require('mongoose')

const specSchema = new mongoose.Schema(
  { label: { type: String, required: true }, value: { type: String, required: true } },
  { _id: false }
)

const productSchema = new mongoose.Schema(
  {
    slug: { type: String, required: true, unique: true, lowercase: true, index: true },
    name: { type: String, required: true },
    brand: { type: String, required: true },
    model: { type: String, required: true },
    category: { type: String, required: true, index: true },
    categoryLabel: { type: String, required: true },
    price: { type: Number, required: true },
    stock: { type: Number, required: true, default: 0 },
    rating: { type: Number, default: 0 },
    description: { type: String, required: true },
    specs: { type: [specSchema], default: [] },
    image: { type: String, required: true },
    sourceFile: { type: String, default: '' },
  },
  { timestamps: true }
)

module.exports = mongoose.model('Product', productSchema)
