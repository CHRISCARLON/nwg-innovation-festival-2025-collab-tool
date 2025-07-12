# Get the current date
DATE := $(shell date +%Y-%m-%d)

# Import commit types from existing configuration
define COMMIT_TYPES
feat:     A new feature
fix:      A bug fix
docs:     Documentation only changes
style:    Changes that do not affect the meaning of the code
refactor: A code change that neither fixes a bug nor adds a feature
perf:     A code change that improves performance
test:     Adding missing tests or correcting existing tests
build:    Changes that affect the build system or external dependencies
ci:       Changes to CI configuration files and scripts
chore:    Other changes that don't modify src or test files
revert:   Reverts a previous commit
endef
export COMMIT_TYPES

AVAILABLE_FOLDERS := backend frontend

# Docker configuration
DOCKER_IMAGE_NAME := rapid-street-assessments-backend
DOCKER_CONTAINER_NAME := rapid-street-assessments-container
DOCKER_PORT := 8080

# Environment loading
load-env:
	@if [ -f backend/.env ]; then \
		echo "Loading environment variables from backend/.env..."; \
		set -a && source backend/.env && set +a; \
	else \
		echo "Warning: backend/.env file not found"; \
	fi

# Run commands with environment loaded
run-backend: load-env
	@echo "Starting backend with environment loaded..."
	@set -a && source backend/.env && set +a && cd backend && python app.py

run-frontend: load-env
	@echo "Starting frontend with environment loaded..."
	@set -a && source backend/.env && set +a && cd frontend && streamlit run streamlit_app.py

run-frontend-multi-usrn: load-env
	@echo "Starting frontend with environment loaded..."
	@set -a && source backend/.env && set +a && cd frontend && streamlit run multi_usrn_app.py
	
# Development helpers
dev-backend: load-env
	@echo "Starting backend in development mode..."
	@set -a && source backend/.env && set +a && cd backend && python -m uvicorn app:app --reload

dev-test: load-env
	@echo "Running tests with environment loaded..."
	@set -a && source backend/.env && set +a && python -m pytest tests/

# Docker commands
docker-build:
	@echo "Building Docker image for backend..."
	@cd backend && docker build -t $(DOCKER_IMAGE_NAME) .

docker-run: docker-build
	@echo "Running backend in Docker container..."
	@docker run -d \
		--name $(DOCKER_CONTAINER_NAME) \
		-p $(DOCKER_PORT):8080 \
		--env-file backend/.env \
		$(DOCKER_IMAGE_NAME)
	@echo "Backend container started on port $(DOCKER_PORT)"
	@echo "API available at: http://localhost:$(DOCKER_PORT)"

docker-dev: docker-build
	@echo "Running backend in Docker with volume mounting for development..."
	@docker run -d \
		--name $(DOCKER_CONTAINER_NAME)-dev \
		-p $(DOCKER_PORT):8080 \
		--env-file backend/.env \
		-v $(PWD)/backend:/app \
		$(DOCKER_IMAGE_NAME)
	@echo "Backend development container started on port $(DOCKER_PORT)"
	@echo "Code changes will be reflected (may require container restart)"

docker-stop:
	@echo "Stopping Docker containers..."
	-@docker stop $(DOCKER_CONTAINER_NAME) 2>/dev/null || true
	-@docker stop $(DOCKER_CONTAINER_NAME)-dev 2>/dev/null || true

docker-clean: docker-stop
	@echo "Cleaning up Docker containers and images..."
	-@docker rm $(DOCKER_CONTAINER_NAME) 2>/dev/null || true
	-@docker rm $(DOCKER_CONTAINER_NAME)-dev 2>/dev/null || true
	-@docker rmi $(DOCKER_IMAGE_NAME) 2>/dev/null || true

docker-logs:
	@echo "Showing logs for backend container..."
	@docker logs -f $(DOCKER_CONTAINER_NAME) 2>/dev/null || docker logs -f $(DOCKER_CONTAINER_NAME)-dev

docker-shell:
	@echo "Opening shell in backend container..."
	@docker exec -it $(DOCKER_CONTAINER_NAME) /bin/bash 2>/dev/null || docker exec -it $(DOCKER_CONTAINER_NAME)-dev /bin/bash

# Combined docker development workflow
docker-restart: docker-stop docker-dev
	@echo "Restarted backend in development mode"

repo-update:
	@echo "Available folders: $(AVAILABLE_FOLDERS)"
	@echo ""
	@echo "Examples:"
	@echo "  • Press enter to commit all folders"
	@echo "  • Type 'backend' to commit only backend"
	@echo "  • Type 'frontend' to commit only frontend"
	@echo ""
	@read -p "Enter the names of the folders you wish to update (space-separated, or just hit enter to update all): " folders; \
	if [ -z "$$folders" ]; then \
		make git-add-all git-commit git-push; \
	else \
		make git-add-selected FOLDERS="$$folders" git-commit git-push; \
	fi

git-add-all:
	git add .

git-add-selected:
	@for folder in $(FOLDERS); do \
		if [[ " $(AVAILABLE_FOLDERS) " =~ " $$folder " ]]; then \
			echo "Adding folder: $$folder"; \
			git add $$folder/.; \
		else \
			echo "Warning: $$folder is not a recognized folder"; \
		fi \
	done

git-commit:
	@echo "Available commit types:"
	@echo "$$COMMIT_TYPES" | sed 's/^/  /'
	@echo
	@read -p "Enter commit type: " type; \
	if echo "$$COMMIT_TYPES" | grep -q "^$$type:"; then \
		read -p "Enter commit scope (optional, press enter to skip): " scope; \
		read -p "Is this a breaking change? (y/N): " breaking; \
		read -p "Enter commit message: " msg; \
		if [ "$$breaking" = "y" ] || [ "$$breaking" = "Y" ]; then \
			if [ -n "$$scope" ]; then \
				git commit -m "$$type!($$scope): $$msg [$(DATE)]" -m "BREAKING CHANGE: $$msg"; \
			else \
				git commit -m "$$type!: $$msg [$(DATE)]" -m "BREAKING CHANGE: $$msg"; \
			fi; \
		else \
			if [ -n "$$scope" ]; then \
				git commit -m "$$type($$scope): $$msg [$(DATE)]"; \
			else \
				git commit -m "$$type: $$msg [$(DATE)]"; \
			fi; \
		fi; \
	else \
		echo "Invalid commit type. Please use one of the available types."; \
		exit 1; \
	fi

git-push:
	git push

# Help command to show available targets
help:
	@echo "Available commands:"
	@echo ""
	@echo "Local Development:"
	@echo "  run-backend     - Run backend locally with environment"
	@echo "  run-frontend    - Run frontend locally with environment"
	@echo "  dev-backend     - Run backend in development mode with auto-reload"
	@echo "  dev-test        - Run tests with environment loaded"
	@echo ""
	@echo "Docker Commands:"
	@echo "  docker-build    - Build Docker image for backend"
	@echo "  docker-run      - Build and run backend in Docker (production mode)"
	@echo "  docker-dev      - Build and run backend in Docker with volume mounting"
	@echo "  docker-stop     - Stop all running containers"
	@echo "  docker-clean    - Stop containers and remove images"
	@echo "  docker-logs     - Show container logs"
	@echo "  docker-shell    - Open shell in running container"
	@echo "  docker-restart  - Stop and restart in development mode"
	@echo ""
	@echo "Git Commands:"
	@echo "  repo-update     - Interactive git add, commit, and push"
	@echo ""
	@echo "Other:"
	@echo "  help           - Show this help message"


