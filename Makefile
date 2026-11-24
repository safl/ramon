# SPDX-FileCopyrightText: Simon A. F. Lund <os@safl.dk>
#
# SPDX-License-Identifier: GPL-2.0-only

PROJECT=ramon

.PHONY: default
default: test

.PHONY: deps
deps:
	uv sync

.PHONY: format
format:
	@echo "## ${PROJECT}: format"
	@pre-commit run
	@echo "## ${PROJECT}: format [DONE]"

.PHONY: format-all
format-all:
	@echo "## ${PROJECT}: format-all"
	@pre-commit run --all-files
	@echo "## ${PROJECT}: format-all [DONE]"

.PHONY: test
test:
	@echo "## ${PROJECT}: test"
	uv run pytest
	@echo "## ${PROJECT}: test [DONE]"

.PHONY: run
run:
	uv run ramon
