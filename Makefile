PYTHON ?= $(if $(wildcard .venv/bin/python),$(CURDIR)/.venv/bin/python,python3)
BOOTSTRAP_PYTHON ?= python3.14
SHELL := /bin/bash
.PHONY: help bootstrap doctor lint test validate demo security clean-clone record gate publish clean integration plan apply destroy teardown
help:
	@printf '%s\n' 'bootstrap: install pinned tools and locked provider locally; public network downloads' 'doctor: inspect versions and execution boundary' 'lint: Ruff, native HCL formatting, TFLint, shell/workflow/docs checks' 'test: unit guards, native mock plans and accepting/rejecting policy controls' 'validate: all required static and mock checks; no AWS API calls' 'demo: narrated mock-only failure/recovery demonstration' 'security: working, staged and full outgoing history secret scans' 'record: record checks for a clean committed revision' 'clean-clone: execute quickstart in a temporary clone and remove it' 'gate: current checks plus matching revision-bound evidence' 'publish: show credential-free publishing instructions' 'clean: report retained local caches; no cloud deletion' 'integration/plan/apply/destroy/teardown: BLOCKED, live cloud operations unauthorized'
bootstrap:
	$(BOOTSTRAP_PYTHON) scripts/bootstrap.py
	.venv/bin/python scripts/iac.py init
doctor:
	$(PYTHON) scripts/doctor.py
lint:
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .
	.tools/bin/tofu fmt -check -recursive modules stacks
	$(PYTHON) scripts/quality.py
	.tools/bin/shellcheck scripts/demo.sh
	.tools/bin/shfmt -d -i 2 scripts/demo.sh
	PATH="$(CURDIR)/.tools/bin:$$PATH" .tools/bin/actionlint
	$(PYTHON) scripts/iac.py lint
test:
	$(PYTHON) -m unittest discover -s tests -v
	$(PYTHON) scripts/iac.py test
validate: lint
	$(PYTHON) scripts/iac.py validate
	$(MAKE) test
demo:
	bash scripts/demo.sh
security:
	$(PYTHON) scripts/security.py
record:
	$(PYTHON) scripts/record_validation.py
clean-clone:
	$(PYTHON) scripts/clean_clone.py
gate: doctor validate demo security
	$(PYTHON) scripts/evidence.py
publish:
	$(PYTHON) scripts/publish.py
clean integration plan apply destroy teardown:
	$(PYTHON) scripts/iac.py $@
