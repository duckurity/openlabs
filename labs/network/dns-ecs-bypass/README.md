# DNS ECS Bypass

An internal DNS service is running on the target. It hosts a protected zone containing a flag. Access is restricted to clients from the internal network.

## Goal

Retrieve the flag from the protected zone.

## Setup

Run the container and interact with the service on `127.0.0.1:5353/udp`.

## Brief

لاب عن تجاوز قيود DNS باستخدام EDNS Client Subnet (ECS): السيناريو، الهدف، وإيه اللي المتدرب هيتعلمه.
