# Product Manager Agent (Internal)

This directory contains the product-manager-style agent implementation used in Worklone.

## Purpose

The PM agent specializes in:

- product planning and requirement framing
- research synthesis
- prioritization support
- structured output generation for downstream workflows

## Runtime Integration

- loaded through backend services and routers
- uses shared tool catalog and function-calling loop
- uses centralized LLM configuration (`settings` + user credentials)

## Important

This is internal implementation documentation.
For end-user docs, use repository-level docs in `docs/` and root `README.md`.
