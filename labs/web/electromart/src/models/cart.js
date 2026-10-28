'use strict'

const mongoose = require('mongoose')

const cartItemSchema = new mongoose.Schema(
  {
    productSlug: { type: String, required: true },
    name: { type: String, required: true },
    brand: { type: String, required: true },
    price: { type: Number, required: true },
    image: { type: String, required: true },
    quantity: { type: Number, required: true, min: 1, max: 10 },
    stock: { type: Number, default: 0 },
  },
  { _id: false }
)

const cartSchema = new mongoose.Schema(
  {
    user: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true, unique: true },
    items: { type: [cartItemSchema], default: [] },
  },
  { timestamps: true }
)

module.exports = mongoose.model('Cart', cartSchema)
