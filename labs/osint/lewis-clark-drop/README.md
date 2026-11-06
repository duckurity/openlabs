# The Lewis and Clark Trail Drop

## Brief

A contact was traveling along the Lewis and Clark Trail when they disappeared. Before going dark, they sent a photo of a monument. There are several similar monuments along the trail, but only one matches this exact photo.

Find the correct monument and the detail left behind in the field note.

## Setup

Start the lab:

    docker compose up -d --build

Then open http://localhost:8089 in your browser (the lab listens on 127.0.0.1 only). The page shows the photo and the field note.

This lab needs limited internet access. You may use only these three websites, and nothing else (no search engines):

- `www.openstreetmap.org`
- `nominatim.openstreetmap.org`
- `en.wikipedia.org`

## Goal

Identify the monument from the photo, find its location on OpenStreetMap, and use the field note to find a date on Wikipedia.

Submit one flag in the form `duck{...}`, built like this (lowercase letters, digits and underscores only):

- `n` or `s`, then the latitude rounded to 3 decimals, with the dot written as `_`
- `e` or `w`, then the longitude rounded to 3 decimals, with the minus sign dropped and the dot written as `_`
- the month and day as four digits (`mmdd`)
- the four-digit year

Join the four parts with `_` and put them inside `duck{` and `}`.
