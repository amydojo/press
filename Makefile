.PHONY: install dev test check lint typecheck build contracts e2e

install:
	corepack enable
	pnpm install --frozen-lockfile
	uv sync --project services/generation-api --frozen

dev:
	pnpm dev

test:
	pnpm test

lint:
	pnpm lint

typecheck:
	pnpm typecheck

build:
	pnpm build

contracts:
	pnpm contracts:check

e2e:
	pnpm e2e

check: lint typecheck test contracts build
