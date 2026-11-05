# DNS ECS Bypass

An internal DNS service is running on the target. It hosts a protected zone containing a flag. Access is restricted to clients from the internal network.

## Brief

You are a penetration tester. You have discovered a DNS service on port `5353/udp`. Your goal is to retrieve the flag from the protected zone.

## Setup

Run the container and interact with the service on `127.0.0.1:5353/udp`.
