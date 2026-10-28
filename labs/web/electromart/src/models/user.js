'use strict'

const mongoose = require('mongoose')
const bcrypt = require('bcryptjs')

/**
 * User model.
 *
 * Security notes:
 * - `password` is hashed with bcrypt before it is ever stored and is
 *   `select: false`, so it is excluded from every query by default.
 * - `username` and `email` are unique; duplicate inserts are rejected by
 *   the database with E11000 and mapped to friendly messages in the routes.
 */
const userSchema = new mongoose.Schema(
  {
    username: {
      type: String,
      required: true,
      unique: true,
      minlength: 3,
      maxlength: 30,
      lowercase: true,
      trim: true,
    },
    email: {
      type: String,
      required: true,
      unique: true,
      lowercase: true,
      trim: true,
    },
    password: {
      type: String,
      required: true,
      minlength: 10,
      select: false,
    },
    firstName: {
      type: String,
      maxlength: 100,
      trim: true,
      default: '',
    },
    lastName: {
      type: String,
      maxlength: 100,
      trim: true,
      default: '',
    },
    address: {
      type: String,
      maxlength: 500,
      trim: true,
      default: '',
    },
  },
  { timestamps: true }
)

/**
 * Compare a candidate plaintext password with the stored bcrypt hash.
 */
userSchema.methods.comparePassword = function comparePassword(candidate) {
  const plain = String(candidate === undefined || candidate === null ? '' : candidate)
  const stored = this.password
  if (!plain || !stored) return Promise.resolve(false)
  return bcrypt.compare(plain, stored)
}

module.exports = mongoose.model('User', userSchema)
