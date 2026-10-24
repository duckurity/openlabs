FROM python:3.12-alpine@sha256:1b668429b3511ab407d8e00648891631b0b1a4d7e15e3ca70f38ab5b91ad4ab4
USER nobody

# This lab has no server-side component. The intended solve path never
# builds or runs this image: the player runs bin/game.exe and
# bin/checker.exe directly (natively on Windows, or under Wine on
# Linux/macOS). See README.md, "Delivery model (artifact-only exception)".
#
# docker-compose.yml runs the pinned image above as-is, with no custom
# build step, to serve the two binaries and the docs over plain HTTP for
# convenience. This file exists to document that image and satisfy the
# catalog's Dockerfile convention; it is not referenced by the compose
# service's `image:` directive.
