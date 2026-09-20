#!/bin/sh
set -eu

mix ecto.create
mix ecto.migrate
exec mix phx.server
