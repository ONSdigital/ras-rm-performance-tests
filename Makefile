.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: install-dev-dependencies
install-dev-dependendencies: ## Install the development dependencies
	pipenv install --dev --deploy

.PHONY: test
test: install-dev-dependendencies ## Run the tests
	pipenv run python -m pytest
